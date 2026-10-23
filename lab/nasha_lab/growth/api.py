"""Growth OS HTTP API (v1): tenant-aware CRM, pricing scenarios, the governed lead-qualification workflow, approvals and audit. Same conventions as the existing governed API: bearer sessions issued by the TENANT's own
authority, ONE error envelope, X-Request-Id correlation, Idempotency-Key on writes, opaque numeric cursors with a hard page cap, no existence oracle for unknown tenants.

Authorization layers: (1) the session must verify against the path tenant's authority (a request parameter can never change the tenant: bodies reject unknown fields and no header is read for tenant context);
(2) role policy in the service layer, default deny, every denial audited; (3) PostgreSQL row-level security; (4) THE WEIR gates the qualification workflow's CRM write behind a different person's approval.
There are no debug, export, raw-SQL or admin endpoints. Nothing here can send, publish or purchase."""
import hashlib
import json
import re
import threading
import uuid
from typing import Any, Optional

import psycopg
from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import identity as ID
from . import pricing as GP, service as SV, workflow as WF

MAX_PAGE = 50
BEARER = re.compile(r"^Bearer ([A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)$")
ID_RE = r"^[a-z]{2,6}-[a-f0-9]{8,12}$|^wf-[a-f0-9]{12}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountIn(Strict):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="business", pattern="^(business|household)$")
    segment_id: Optional[str] = Field(default=None, pattern=ID_RE)


class ContactIn(Strict):
    account_id: str = Field(pattern=ID_RE)
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=160, pattern=r"^[A-Za-z0-9._+-]+@example\.invalid$")


class ConsentIn(Strict):
    status: str = Field(pattern="^(none|opt_in|opt_out)$")


class SignalsIn(Strict):
    budget_confirmed: bool
    decision_maker: bool
    timeline_days: Optional[int] = Field(default=None, ge=0, le=3650)
    fit: float = Field(ge=0, le=1)
    engagement: float = Field(ge=0, le=1)


class LeadIn(Strict):
    contact_id: str = Field(pattern=ID_RE)
    source: str = Field(pattern=r"^synthetic[a-z0-9-]{0,40}$")
    signals: Optional[SignalsIn] = None


class ConvertIn(Strict):
    opportunity_name: str = Field(min_length=1, max_length=120)
    amount_cents: int = Field(ge=0, le=100_000_000)


class StageIn(Strict):
    to_stage: str = Field(pattern="^(new|qualified|proposal|negotiation|won|lost)$")


class ActivityIn(Strict):
    kind: str = Field(pattern="^(note|call_log|meeting)$")           # email_draft is created only by the consent-gated outreach path, never here
    body: str = Field(min_length=1, max_length=2000)
    opportunity_id: Optional[str] = Field(default=None, pattern=ID_RE)
    contact_id: Optional[str] = Field(default=None, pattern=ID_RE)


class ScenarioIn(Strict):
    label: str = Field(max_length=60)
    price_cents: Optional[int] = Field(default=None, gt=0, le=10_000_000)
    discount_pct: float = Field(default=0, ge=0, le=100)
    cost_shock: float = Field(default=0, ge=-0.5, le=2.0)


class PricingIn(Strict):
    product_id: str = Field(pattern=ID_RE)
    base_units: int = Field(default=100, gt=0, le=10_000_000)
    fixed_costs_cents: Optional[int] = Field(default=None, ge=0)
    scenarios: list[ScenarioIn] = Field(min_length=1, max_length=10)
    assumed_elasticity: Optional[float] = Field(default=None, ge=-6, le=0)


class PriceIn(Strict):
    amount_cents: int = Field(gt=0, le=10_000_000)
    status: str = Field(pattern="^(scenario|draft|current)$")
    basis: str = Field(min_length=3, max_length=120)


class QualifyIn(Strict):
    lead_id: str = Field(pattern=ID_RE)


class DecisionIn(Strict):
    approve: bool
    comment: str = Field(default="", max_length=300)


def create_growth_app(envs: dict) -> FastAPI:
    """envs: {tenant_id: GrowthEnv}. One lock per tenant: services and the workflow own psycopg connections and an event loop."""
    app = FastAPI(title="NASHA Growth OS API", version="1.0.0", description="SYNTHETIC DATA. Tenant-aware CRM, pricing scenarios and a governed workflow. The API has no operation that sends, publishes or purchases anything.")
    locks = {t: threading.RLock() for t in envs}
    flows, svcs = {}, {}
    app.state.envs = envs

    def err(request, status, code, message):
        rid = getattr(request.state, "request_id", "-")
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "request_id": rid}}, headers={"X-Request-Id": rid})

    @app.middleware("http")
    async def ctx(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or "req-" + uuid.uuid4().hex[:10]
        if not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", rid):
            rid = "req-" + uuid.uuid4().hex[:10]
        request.state.request_id = rid
        try:
            resp = await call_next(request)
        except Exception:                                              # noqa: BLE001  (never leak internals)
            return err(request, 500, "internal_error", "unexpected error")
        resp.headers["X-Request-Id"] = rid
        return resp

    @app.exception_handler(RequestValidationError)
    async def _val(request, exc):
        return err(request, 422, "validation_error", "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in exc.errors())[:300])

    @app.exception_handler(StarletteHTTPException)
    async def _http(request, exc):
        return err(request, exc.status_code, "not_found" if exc.status_code == 404 else "http_error", "not found" if exc.status_code == 404 else str(exc.detail)[:120])

    # ---------------------------------------------------------------- plumbing
    def flow(tenant):
        if tenant not in flows:
            flows[tenant] = WF.GovernedLeadQualification(envs[tenant])
        return flows[tenant]

    def service(tenant, who):
        key = (tenant, who.id)
        if key not in svcs:
            svcs[key] = SV.GrowthService(envs[tenant].dsn, envs[tenant].schema, tenant, who.id)
        return svcs[key]

    def auth(request, tenant):
        """-> (identity, service, None) or (None, None, error response). The tenant comes ONLY from the path and must match the session's authority."""
        m = BEARER.match(request.headers.get("Authorization", ""))
        if not m or tenant not in envs:                              # an unknown tenant answers exactly like a bad session: no existence oracle
            return None, None, err(request, 401, "unauthenticated", "a valid bearer session for this tenant is required")
        try:
            who = envs[tenant].authority.identify(m.group(1))
        except ID.AuthError:
            return None, None, err(request, 401, "unauthenticated", "a valid bearer session for this tenant is required")
        s = service(tenant, who)
        if s.role != who.role:
            return None, None, err(request, 401, "unauthenticated", "a valid bearer session for this tenant is required")
        return who, s, None

    def guarded(fn):
        """Run a service call and translate domain errors into the single error envelope."""
        def wrap(request, tenant, *a, **kw):
            who, s, e = auth(request, tenant)
            if e:
                return e
            with locks[tenant]:
                try:
                    return fn(request, tenant, who, s, *a, **kw)
                except SV.Denied as ex:
                    return err(request, 403, "forbidden", f"{ex.action}: not permitted for your role")
                except SV.Blocked as ex:
                    return err(request, 409, "conflict", str(ex)[:160])
                except psycopg.errors.UniqueViolation:
                    return err(request, 409, "conflict", "a record with that unique value already exists")
                except (psycopg.errors.ForeignKeyViolation, psycopg.errors.CheckViolation, psycopg.errors.InsufficientPrivilege):
                    return err(request, 422, "validation_error", "the request violates a data rule")
        return wrap

    def idem(request, s, tenant, key, body, produce):
        """Idempotent write: the first call stores its response; a retry returns it; a different body under the same key is a conflict."""
        if key is None:
            return produce()
        if not re.fullmatch(r"[A-Za-z0-9_\-]{8,64}", key):
            return err(request, 422, "validation_error", "Idempotency-Key must be 8-64 characters of [A-Za-z0-9_-]")
        h = hashlib.sha256(json.dumps([request.method, request.url.path, body], sort_keys=True, default=str).encode()).hexdigest()
        row = s.con.execute("SELECT request_hash, status_code, response FROM idempotency_keys WHERE tenant_id=%s AND key=%s", (tenant, key)).fetchone()
        if row:
            if row[0] != h:
                return err(request, 409, "conflict", "Idempotency-Key was already used with a different request")
            return JSONResponse(status_code=row[1], content=row[2], headers={"X-Request-Id": request.state.request_id, "Idempotent-Replay": "true"})
        resp = produce()
        if isinstance(resp, JSONResponse) and resp.status_code < 300:
            s.con.execute("INSERT INTO idempotency_keys (tenant_id,key,request_hash,status_code,response) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", (tenant, key, h, resp.status_code, Jsonb(json.loads(resp.body))))
        return resp

    def ok(request, content, status=200):
        return JSONResponse(status_code=status, content=json.loads(json.dumps(content, default=str)), headers={"X-Request-Id": request.state.request_id})

    def page(s, sql, params, limit, cursor, cols):
        off = int(cursor or 0)
        rows = s.read(sql + " LIMIT %s OFFSET %s", (*params, limit + 1, off))
        items = [dict(zip(cols, r)) for r in rows[:limit]]
        return dict(items=items, next_cursor=str(off + limit) if len(rows) > limit else None)

    CUR = Query(None, pattern=r"^\d{1,9}$")
    LIM = Query(20, ge=1, le=MAX_PAGE)

    @app.get("/v1/health")
    def health():
        return {"status": "ok"}

    @app.get("/v1/tenants/{tenant}/me")
    def me(tenant: str, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(tenant=tenant, user=who.id, role=who.role)))(request, tenant)

    # ---------------------------------------------------------------- CRM
    @app.post("/v1/tenants/{tenant}/accounts", status_code=201)
    def create_account(tenant: str, body: AccountIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, body.model_dump(), lambda: ok(request, dict(id=s.create_account(body.name, body.kind, body.segment_id)), 201)))(request, tenant)

    @app.get("/v1/tenants/{tenant}/accounts")
    def list_accounts(tenant: str, request: Request, limit: int = LIM, cursor: Optional[str] = CUR):
        return guarded(lambda request, tenant, who, s: ok(request, page(s, "SELECT id, name, kind, segment_id, version, created_at FROM accounts WHERE tenant_id=%s ORDER BY created_at, id", (tenant,), limit, cursor, ("id", "name", "kind", "segment_id", "version", "created_at"))))(request, tenant)

    @app.get("/v1/tenants/{tenant}/accounts/{account_id}")
    def get_account(tenant: str, account_id: str, request: Request):
        def go(request, tenant, who, s):
            r = s.read("SELECT id, name, kind, segment_id, version, created_at FROM accounts WHERE tenant_id=%s AND id=%s", (tenant, account_id))
            return ok(request, dict(zip(("id", "name", "kind", "segment_id", "version", "created_at"), r[0]))) if r else err(request, 404, "not_found", "not found")
        return guarded(go)(request, tenant)

    @app.post("/v1/tenants/{tenant}/contacts", status_code=201)
    def create_contact(tenant: str, body: ContactIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, body.model_dump(), lambda: ok(request, dict(id=s.create_contact(body.account_id, body.full_name, body.email)), 201)))(request, tenant)

    @app.get("/v1/tenants/{tenant}/contacts")
    def list_contacts(tenant: str, request: Request, account_id: Optional[str] = Query(None, pattern=ID_RE), limit: int = LIM, cursor: Optional[str] = CUR):
        sql, params = ("SELECT id, account_id, full_name, email, consent_status, version FROM contacts WHERE tenant_id=%s" + (" AND account_id=%s" if account_id else "") + " ORDER BY created_at, id"), ((tenant, account_id) if account_id else (tenant,))
        return guarded(lambda request, tenant, who, s: ok(request, page(s, sql, params, limit, cursor, ("id", "account_id", "full_name", "email", "consent_status", "version"))))(request, tenant)

    @app.put("/v1/tenants/{tenant}/contacts/{contact_id}/consent")
    def set_consent(tenant: str, contact_id: str, body: ConsentIn, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(id=s.set_consent(contact_id, body.status), consent_status=body.status)))(request, tenant)

    @app.post("/v1/tenants/{tenant}/leads", status_code=201)
    def create_lead(tenant: str, body: LeadIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, body.model_dump(), lambda: ok(request, dict(id=s.create_lead(body.contact_id, body.source, body.signals.model_dump() if body.signals else None)), 201)))(request, tenant)

    @app.get("/v1/tenants/{tenant}/leads")
    def list_leads(tenant: str, request: Request, status: Optional[str] = Query(None, pattern="^(new|qualified|disqualified|converted)$"), limit: int = LIM, cursor: Optional[str] = CUR):
        sql, params = ("SELECT id, contact_id, source, status, score, version FROM leads WHERE tenant_id=%s" + (" AND status=%s" if status else "") + " ORDER BY created_at, id"), ((tenant, status) if status else (tenant,))
        return guarded(lambda request, tenant, who, s: ok(request, page(s, sql, params, limit, cursor, ("id", "contact_id", "source", "status", "score", "version"))))(request, tenant)

    @app.get("/v1/tenants/{tenant}/leads/{lead_id}")
    def get_lead(tenant: str, lead_id: str, request: Request):
        def go(request, tenant, who, s):
            c = s.get_lead_context(lead_id)
            return ok(request, c) if c else err(request, 404, "not_found", "not found")
        return guarded(go)(request, tenant)

    @app.post("/v1/tenants/{tenant}/leads/{lead_id}/convert", status_code=201)
    def convert(tenant: str, lead_id: str, body: ConvertIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, [lead_id, body.model_dump()], lambda: ok(request, dict(id=s.convert_lead(lead_id, body.opportunity_name, body.amount_cents)), 201)))(request, tenant)

    @app.get("/v1/tenants/{tenant}/opportunities")
    def list_opps(tenant: str, request: Request, stage: Optional[str] = Query(None, pattern="^(new|qualified|proposal|negotiation|won|lost)$"), limit: int = LIM, cursor: Optional[str] = CUR):
        sql, params = ("SELECT id, account_id, name, stage, amount_cents, version FROM opportunities WHERE tenant_id=%s" + (" AND stage=%s" if stage else "") + " ORDER BY created_at, id"), ((tenant, stage) if stage else (tenant,))
        return guarded(lambda request, tenant, who, s: ok(request, page(s, sql, params, limit, cursor, ("id", "account_id", "name", "stage", "amount_cents", "version"))))(request, tenant)

    @app.post("/v1/tenants/{tenant}/opportunities/{opp_id}/stage")
    def advance(tenant: str, opp_id: str, body: StageIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        def go(request, tenant, who, s):
            def produce():
                s.advance(opp_id, body.to_stage)
                return ok(request, dict(id=opp_id, stage=body.to_stage))
            return idem(request, s, tenant, key, [opp_id, body.model_dump()], produce)
        return guarded(go)(request, tenant)

    @app.get("/v1/tenants/{tenant}/pipeline")
    def pipeline(tenant: str, request: Request):
        def go(request, tenant, who, s):
            rows = {r[0]: (r[1], int(r[2])) for r in s.read("SELECT stage, count(*), coalesce(sum(amount_cents),0) FROM opportunities WHERE tenant_id=%s GROUP BY stage", (tenant,))}
            rules = s.read("SELECT from_stage, to_stage FROM stage_rules ORDER BY 1,2")
            stages = [dict(stage=st, count=rows.get(st, (0, 0))[0], amount_cents=rows.get(st, (0, 0))[1], next=[b for a, b in rules if a == st]) for st in ("new", "qualified", "proposal", "negotiation", "won", "lost")]
            return ok(request, dict(stages=stages, note="allowed transitions come from the database rules table"))
        return guarded(go)(request, tenant)

    @app.post("/v1/tenants/{tenant}/activities", status_code=201)
    def log_activity(tenant: str, body: ActivityIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, body.model_dump(), lambda: ok(request, dict(id=s.log_activity(body.kind, body.body, body.opportunity_id, body.contact_id)), 201)))(request, tenant)

    @app.get("/v1/tenants/{tenant}/activities")
    def list_activities(tenant: str, request: Request, limit: int = LIM, cursor: Optional[str] = CUR):
        return guarded(lambda request, tenant, who, s: ok(request, page(s, "SELECT id, kind, body, actor, opportunity_id, contact_id, created_at FROM activities WHERE tenant_id=%s ORDER BY created_at DESC, id", (tenant,), limit, cursor, ("id", "kind", "body", "actor", "opportunity_id", "contact_id", "created_at"))))(request, tenant)

    # ---------------------------------------------------------------- pricing
    @app.get("/v1/tenants/{tenant}/products")
    def products(tenant: str, request: Request, limit: int = LIM, cursor: Optional[str] = CUR):
        sql = ("SELECT p.id, p.name, p.kind, p.unit_cost_cents, p.cost_basis, pr.amount_cents FROM products p LEFT JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id AND pr.status='current' WHERE p.tenant_id=%s ORDER BY p.name")
        def go(request, tenant, who, s):
            d = page(s, sql, (tenant,), limit, cursor, ("id", "name", "kind", "unit_cost_cents", "cost_basis", "price_cents"))
            for it in d["items"]:
                it["margin"] = GP.gross_margin(it["price_cents"], it["unit_cost_cents"]) if it["price_cents"] and it["unit_cost_cents"] is not None else None
            return ok(request, d)
        return guarded(go)(request, tenant)

    @app.post("/v1/tenants/{tenant}/products/{product_id}/prices", status_code=201)
    def set_price(tenant: str, product_id: str, body: PriceIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        from datetime import date
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, [product_id, body.model_dump()], lambda: ok(request, dict(id=s.set_price(product_id, body.amount_cents, date.today(), body.status, body.basis)), 201)))(request, tenant)

    @app.post("/v1/tenants/{tenant}/pricing/scenarios")
    def scenarios(tenant: str, body: PricingIn, request: Request):
        def go(request, tenant, who, s):
            s._authorize("price.scenario", "prices", body.product_id)
            r = s.read("SELECT p.name, p.unit_cost_cents, p.cost_basis, pr.amount_cents FROM products p LEFT JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id AND pr.status='current' WHERE p.tenant_id=%s AND p.id=%s", (tenant, body.product_id))
            if not r:
                return err(request, 404, "not_found", "not found")
            name, cost, basis, price = r[0]
            if price is None or cost is None:
                return err(request, 409, "conflict", "the product needs a current price and a unit cost")
            rows = []
            for sc in body.scenarios:
                p = (sc.price_cents if sc.price_cents is not None else price) * (1 - sc.discount_pct / 100.0)
                c = cost * (1 + sc.cost_shock)
                unit = p - c
                rows.append(dict(label=sc.label, price_cents=p, cost_cents=c, unit_profit_cents=unit, margin=GP.gross_margin(p, c), gross_profit_at_base_units_cents=unit * body.base_units,
                                 breakeven_units=GP.breakeven_units(body.fixed_costs_cents, p, c) if body.fixed_costs_cents is not None else None))
            out = dict(product=dict(id=body.product_id, name=name, current_price_cents=price, unit_cost_cents=cost, cost_basis=basis), base=GP.margin_table(price, cost), scenarios=rows, inflation=GP.inflation(price, cost),
                       assumptions=["costs are planning assumptions, not supplier quotes", "base_units is a caller-supplied what-if volume, not a forecast"])
            if body.assumed_elasticity is not None:
                grid = sorted({round(price * f) for f in (0.9, 0.95, 1.0, 1.05, 1.1)})
                out["sensitivity"] = GP.sensitivity(price, cost, body.base_units, body.assumed_elasticity, grid)
            s._audit("price.scenario_computed", "products", body.product_id, "allow", {"scenarios": len(rows)})
            return ok(request, out)
        return guarded(go)(request, tenant)

    # ---------------------------------------------------------------- governed workflow, approvals, audit
    def wfout(r):
        keep = {k: r.get(k) for k in ("corr_id", "tenant", "workflow", "status", "state", "lead_id", "failure", "detail", "approval_id", "duplicate_of", "side_effects", "lead_status", "problems", "recovered_from")}
        if r.get("recommendation"):
            keep["recommendation"] = r["recommendation"]
        return keep

    @app.post("/v1/tenants/{tenant}/workflows/lead-qualification", status_code=202)
    def start_qualification(tenant: str, body: QualifyIn, request: Request, key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        if key is not None and not re.fullmatch(r"[A-Za-z0-9_\-]{8,64}", key):
            return err(request, 422, "validation_error", "Idempotency-Key must be 8-64 characters of [A-Za-z0-9_-]")
        def go(request, tenant, who, s):
            session = BEARER.match(request.headers["Authorization"]).group(1)
            r = flow(tenant).run(session, body.lead_id, idempotency_key=key, request_id=request.state.request_id)
            f = r.get("failure")
            if f == "AUTH_DENIED":
                return err(request, 401, "unauthenticated", "invalid or expired session")
            if f == "NO_SUCH_LEAD":
                return err(request, 404, "not_found", "not found")
            if f in ("ROLE_DENIED", "TOOL_DENIED"):
                return err(request, 403, "forbidden", "this role may not start lead qualification")
            return ok(request, wfout(r), 200 if r["status"] == "DUPLICATE" else 202)
        return guarded(go)(request, tenant)

    @app.get("/v1/tenants/{tenant}/workflows/runs")
    def runs(tenant: str, request: Request, limit: int = LIM, cursor: Optional[str] = CUR):
        return guarded(lambda request, tenant, who, s: ok(request, page(s, "SELECT id, lead_id, state, requester, failure, created_at FROM workflow_runs WHERE tenant_id=%s ORDER BY created_at DESC, id", (tenant,), limit, cursor, ("id", "lead_id", "state", "requester", "failure", "created_at"))))(request, tenant)

    @app.get("/v1/tenants/{tenant}/workflows/runs/{corr_id}")
    def run_detail(tenant: str, corr_id: str, request: Request):
        def go(request, tenant, who, s):
            r = flow(tenant).status(corr_id)
            if r is None:
                return err(request, 404, "not_found", "not found")
            return ok(request, dict(id=r["id"], lead_id=r["lead_id"], state=r["state"], requester=r["requester"], failure=r["failure"], approval_id=r["approval_id"], proposal=r["proposal"], events=r["events"]))
        return guarded(go)(request, tenant)

    @app.post("/v1/tenants/{tenant}/workflows/runs/{corr_id}/decision")
    def decision(tenant: str, corr_id: str, body: DecisionIn, request: Request):
        def go(request, tenant, who, s):
            session = BEARER.match(request.headers["Authorization"]).group(1)
            r = flow(tenant).decide(corr_id, session, body.approve, body.comment, request_id=request.state.request_id)
            f = r.get("failure")
            if f == "AUTH_DENIED":
                return err(request, 401, "unauthenticated", "invalid or expired session")
            if f in ("ROLE_DENIED", "MAKER_CHECKER"):
                return err(request, 403, "forbidden", "you may not decide on this request")
            if r.get("status") == "DENIED" and "no such run" in str(r.get("detail", "")):
                return err(request, 404, "not_found", "not found")
            if f in ("NOT_AWAITING_APPROVAL", "APPROVAL_REPLAY", "APPROVAL_MISMATCH", "APPROVAL_EXPIRED"):
                return err(request, 409, "conflict", {"APPROVAL_EXPIRED": "the approval expired", "APPROVAL_REPLAY": "this approval was already used"}.get(f, "the run is not awaiting approval"))
            return ok(request, wfout(r))
        return guarded(go)(request, tenant)

    @app.get("/v1/tenants/{tenant}/approvals")
    def approvals(tenant: str, request: Request, state: str = Query("pending", pattern="^(pending|history)$"), limit: int = LIM, cursor: Optional[str] = CUR):
        def go(request, tenant, who, s):
            if state == "pending":
                d = page(s, "SELECT id, lead_id, requester, approval_id, created_at FROM workflow_runs WHERE tenant_id=%s AND state='AWAITING_APPROVAL' ORDER BY created_at, id", (tenant,), limit, cursor, ("run_id", "lead_id", "requester", "approval_id", "requested_at"))
            else:
                d = page(s, "SELECT run_id, ts, detail FROM workflow_events WHERE tenant_id=%s AND kind='approval_decision' ORDER BY ts DESC, run_id, seq", (tenant,), limit, cursor, ("run_id", "ts", "detail"))
            return ok(request, d)
        return guarded(go)(request, tenant)

    @app.get("/v1/tenants/{tenant}/audit")
    def audit(tenant: str, request: Request, limit: int = LIM, cursor: Optional[str] = CUR):
        return guarded(lambda request, tenant, who, s: ok(request, page(s, "SELECT seq, ts, actor, role, action, entity, entity_id, decision, detail FROM audit_log WHERE tenant_id=%s ORDER BY seq DESC", (tenant,), limit, cursor, ("seq", "ts", "actor", "role", "action", "entity", "entity_id", "decision", "detail"))))(request, tenant)

    @app.get("/v1/tenants/{tenant}/audit/verify")
    def audit_verify(tenant: str, request: Request):
        def go(request, tenant, who, s):
            okk, n = s.verify_audit()
            return ok(request, dict(chain_valid=okk, rows=n if okk else None, first_bad_seq=None if okk else n))
        return guarded(go)(request, tenant)

    @app.get("/v1/tenants/{tenant}/dashboard")
    def dashboard(tenant: str, request: Request):
        def go(request, tenant, who, s):
            leads = {r[0]: r[1] for r in s.read("SELECT status, count(*) FROM leads WHERE tenant_id=%s GROUP BY status", (tenant,))}
            opp = s.read("SELECT stage, count(*), coalesce(sum(amount_cents),0) FROM opportunities WHERE tenant_id=%s GROUP BY stage ORDER BY stage", (tenant,))
            wfs = {r[0]: r[1] for r in s.read("SELECT state, count(*) FROM workflow_runs WHERE tenant_id=%s GROUP BY state", (tenant,))}
            recent = [dict(run_id=r[0], ts=r[1].isoformat(), kind=r[2], name=r[3]) for r in s.read("SELECT run_id, ts, kind, detail->>'name' FROM workflow_events WHERE tenant_id=%s ORDER BY ts DESC, seq DESC", (tenant,))[:8]]
            return ok(request, dict(leads=leads, lead_total=sum(leads.values()), pipeline=[dict(stage=a, count=b, amount_cents=int(c)) for a, b, c in opp], open_value_cents=sum(int(c) for a, b, c in opp if a not in ("won", "lost")),
                                    qualification_runs=wfs, approvals_pending=wfs.get("AWAITING_APPROVAL", 0), recent_events=recent, synthetic=True))
        return guarded(go)(request, tenant)

    return app
