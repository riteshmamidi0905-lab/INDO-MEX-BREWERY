"""Launch-workspace HTTP routes (projects, research, suppliers, financial plan, procurement). Registered into the Growth OS app with its helpers: the tenant comes only from the path, sessions are tenant-bound,
bodies reject unknown fields, writes are role-checked and audited by the service, and the procurement recommendation runs on THE WEIR with a human decision. There is no operation that orders, contacts a supplier or pays."""
from datetime import date
from typing import Optional

from fastapi import Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from . import launch as L, present as PR

ID_RE = r"^[a-z]+-[A-Za-z0-9_-]{4,40}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectIn(Strict):
    name: str = Field(min_length=2, max_length=120)
    industry: str = Field(min_length=2, max_length=60)
    location: str = Field(min_length=2, max_length=80)
    concept: str = Field(min_length=10, max_length=800)
    budget_cents: int = Field(ge=0, le=100_000_000_000)
    launch_target: Optional[date] = None
    basis: str = Field(default="founder_input", pattern="^(synthetic|founder_input)$")


class AssumptionIn(Strict):
    label: str = Field(min_length=2, max_length=80)
    value: float = Field(ge=-1_000_000_000_000, le=1_000_000_000_000)
    unit: str = Field(min_length=1, max_length=30)
    basis: str = Field(pattern="^(founder|synthetic_assumption|public_reference)$")
    note: Optional[str] = Field(default=None, max_length=300)


class MilestoneIn(Strict):
    title: str = Field(min_length=3, max_length=160)
    phase: str = Field(pattern="^(idea|research|sourcing|financial_plan|roadmap)$")
    due: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=300)


class MilestoneStatusIn(Strict):
    status: str = Field(pattern="^(todo|doing|done)$")


class FindingIn(Strict):
    topic: str = Field(min_length=2, max_length=80)
    finding: str = Field(min_length=5, max_length=600)
    source_kind: str = Field(pattern="^(founder_note|synthetic_fixture|search_result|public_source)$")
    confidence: float = Field(ge=0, le=1)
    limitation: str = Field(min_length=5, max_length=300)
    source_url: Optional[str] = Field(default=None, max_length=300, pattern=r"^https://")
    retrieved_on: Optional[date] = None


class SupplierIn(Strict):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    service_area: str = Field(min_length=2, max_length=160)
    verification_status: str = Field(pattern="^(synthetic_fixture|lead_unverified|verified_public|stale)$")
    source_kind: str = Field(pattern="^(synthetic_fixture|search_result|official_site)$")
    website_url: Optional[str] = Field(default=None, max_length=200, pattern=r"^https://")
    contact_channel: str = Field(default="none recorded", max_length=120)
    verified_on: Optional[date] = None
    source_url: Optional[str] = Field(default=None, max_length=300, pattern=r"^https://")
    notes: Optional[str] = Field(default=None, max_length=300)
    confirm_distinct: bool = False


class SupplierSourceIn(Strict):
    kind: str = Field(pattern="^(official_site|contact_page|trade_directory|press|investor_profile|partner_listing|government_record)$")
    url: str = Field(max_length=300, pattern=r"^https://[^ ]+$")
    claim: str = Field(min_length=8, max_length=400)
    access: str = Field(pattern="^(page_read|search_snippet)$")
    observed_on: date


class RequirementIn(Strict):
    ref: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,59}$")
    name: str = Field(min_length=2, max_length=120)
    kind: str = Field(pattern="^(equipment|service|consumable)$")
    qty: float = Field(gt=0, le=1_000_000)
    unit: str = Field(min_length=1, max_length=20)
    recurrence: str = Field(pattern="^(one_time|per_week)$")
    note: Optional[str] = Field(default=None, max_length=200)


class RequirementQtyIn(Strict):
    qty: float = Field(gt=0, le=1_000_000)


class SupplierProductIn(Strict):
    name: str = Field(min_length=2, max_length=120)
    unit: str = Field(min_length=1, max_length=20)
    price_class: str = Field(pattern="^(SYNTHETIC_QUOTE|PUBLIC_REFERENCE|SUPPLIER_QUOTE|NONE_PUBLISHED)$")
    limitation: str = Field(min_length=5, max_length=300)
    unit_price_cents: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    ingredient_ref: Optional[str] = Field(default=None, max_length=60)
    pack_qty: Optional[float] = Field(default=None, gt=0)
    lead_days: Optional[int] = Field(default=None, ge=0, le=365)
    min_order_cents: Optional[int] = Field(default=None, ge=0)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    source_url: Optional[str] = Field(default=None, max_length=300, pattern=r"^https://")


class ShortlistIn(Strict):
    status: str = Field(pattern="^(shortlisted|preferred|rejected)$")
    note: Optional[str] = Field(default=None, max_length=300)


class OverridesIn(Strict):
    price_change_pct: Optional[float] = Field(default=None, ge=-0.9, le=3.0)
    cost_change_pct: Optional[float] = Field(default=None, ge=-0.9, le=3.0)
    weekly_orders: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    items_per_order: Optional[float] = Field(default=None, ge=0, le=100)
    avg_discount_pct: Optional[float] = Field(default=None, ge=0, le=100)
    variable_overhead_pct: Optional[float] = Field(default=None, ge=0, le=100)
    cost_inflation_pct: Optional[float] = Field(default=None, ge=-90, le=500)
    price_elasticity: Optional[float] = Field(default=None, ge=-6, le=0)
    rent_monthly_cents: Optional[int] = Field(default=None, ge=0)
    labor_monthly_cents: Optional[int] = Field(default=None, ge=0)
    utilities_monthly_cents: Optional[int] = Field(default=None, ge=0)
    marketing_monthly_cents: Optional[int] = Field(default=None, ge=0)
    insurance_monthly_cents: Optional[int] = Field(default=None, ge=0)
    other_fixed_monthly_cents: Optional[int] = Field(default=None, ge=0)
    startup_capex_cents: Optional[int] = Field(default=None, ge=0)
    capex_buildout_cents: Optional[int] = Field(default=None, ge=0)
    capex_equipment_cents: Optional[int] = Field(default=None, ge=0)
    capex_furniture_cents: Optional[int] = Field(default=None, ge=0)
    capex_technology_cents: Optional[int] = Field(default=None, ge=0)
    capex_other_cents: Optional[int] = Field(default=None, ge=0)
    preopen_licences_permits_cents: Optional[int] = Field(default=None, ge=0)
    preopen_deposits_cents: Optional[int] = Field(default=None, ge=0)
    preopen_professional_fees_cents: Optional[int] = Field(default=None, ge=0)
    preopen_training_cents: Optional[int] = Field(default=None, ge=0)
    preopen_launch_marketing_cents: Optional[int] = Field(default=None, ge=0)
    preopen_other_cents: Optional[int] = Field(default=None, ge=0)
    working_capital_months: Optional[float] = Field(default=None, ge=0, le=36)
    opening_inventory_weeks: Optional[float] = Field(default=None, ge=0, le=26)
    contingency_pct: Optional[float] = Field(default=None, ge=0, le=100)

    def clean(self):
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ScenarioIn(Strict):
    name: str = Field(min_length=2, max_length=80)
    overrides: OverridesIn = Field(default_factory=OverridesIn)


class CompareIn(Strict):
    scenarios: list[ScenarioIn] = Field(min_length=1, max_length=6)


class ProcureIn(Strict):
    period_weeks: int = Field(default=4, ge=1, le=26)


class DecisionIn(Strict):
    approve: bool
    comment: str = Field(default="", max_length=300)


def register(app, h):
    """h: helpers from create_growth_app (guarded, ok, err, idem, page, names, LIM, CUR, launch_flow, BEARER, as_of)."""
    guarded, ok, err, idem, page, names, LIM, CUR = (h[k] for k in ("guarded", "ok", "err", "idem", "page", "names", "LIM", "CUR"))
    launch_flow, BEARER, as_of = h["launch_flow"], h["BEARER"], h["as_of"]
    P = "/v1/tenants/{tenant}"
    IDK = Header(default=None, alias="Idempotency-Key")

    def missing(request):
        return err(request, 404, "not_found", "not found")

    @app.get(P + "/projects")
    def projects(tenant: str, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(items=s.list_projects())))(request, tenant)

    @app.get(P + "/projects/{project_id}/history")
    def history(tenant: str, project_id: str, request: Request):
        def go(request, tenant, who, s):
            if not s.project_overview(project_id):
                return missing(request)
            from . import present as PR
            nm, en = h["names"](s), h["entity_names"](s)
            items = s.project_history(project_id)
            for it in items:
                it["summary"] = PR.audit_summary(it, nm, en)
            return ok(request, dict(items=items, note="Exactly what the audit log recorded for this project. Nothing is inferred; no order was placed and no supplier was contacted."))
        return guarded(go)(request, tenant)

    @app.post(P + "/projects/{project_id}/requirements", status_code=201)
    def add_requirement(tenant: str, project_id: str, body: RequirementIn, request: Request):
        def go(request, tenant, who, s):
            if not s.project_overview(project_id):
                return missing(request)
            return ok(request, dict(id=s.add_requirement(project_id, **body.model_dump())), 201)
        return guarded(go)(request, tenant)

    @app.put(P + "/requirements/{requirement_id}")
    def set_requirement(tenant: str, requirement_id: str, body: RequirementQtyIn, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(id=s.set_requirement_qty(requirement_id, body.qty), qty=body.qty)))(request, tenant)

    @app.post(P + "/projects", status_code=201)
    def create_project(tenant: str, body: ProjectIn, request: Request, key: Optional[str] = IDK):
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, body.model_dump(), lambda: ok(request, dict(id=s.create_project(**body.model_dump())), 201)))(request, tenant)

    @app.get(P + "/projects/{project_id}")
    def project(tenant: str, project_id: str, request: Request):
        def go(request, tenant, who, s):
            ov = s.project_overview(project_id)
            return ok(request, ov) if ov else missing(request)
        return guarded(go)(request, tenant)

    @app.put(P + "/projects/{project_id}/assumptions/{key}")
    def assumption(tenant: str, project_id: str, key: str, body: AssumptionIn, request: Request):
        def go(request, tenant, who, s):
            if not s.project_overview(project_id) or not key.replace("_", "").isalnum() or len(key) > 60:
                return missing(request)
            return ok(request, dict(id=s.set_assumption(project_id, key, body.label, body.value, body.unit, body.basis, body.note)))
        return guarded(go)(request, tenant)

    @app.post(P + "/projects/{project_id}/milestones", status_code=201)
    def milestone(tenant: str, project_id: str, body: MilestoneIn, request: Request):
        def go(request, tenant, who, s):
            if not s.project_overview(project_id):
                return missing(request)
            return ok(request, dict(id=s.add_milestone(project_id, body.title, body.phase, body.due, body.note)), 201)
        return guarded(go)(request, tenant)

    @app.put(P + "/milestones/{milestone_id}/status")
    def milestone_status(tenant: str, milestone_id: str, body: MilestoneStatusIn, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(id=s.set_milestone_status(milestone_id, body.status), status=body.status)))(request, tenant)

    @app.post(P + "/projects/{project_id}/findings", status_code=201)
    def finding(tenant: str, project_id: str, body: FindingIn, request: Request):
        def go(request, tenant, who, s):
            if not s.project_overview(project_id):
                return missing(request)
            return ok(request, dict(id=s.add_finding(project_id, body.topic, body.finding, body.source_kind, body.confidence, body.limitation, body.source_url, body.retrieved_on)), 201)
        return guarded(go)(request, tenant)

    @app.get(P + "/suppliers")
    def suppliers(tenant: str, request: Request, project_id: Optional[str] = Query(None, pattern=ID_RE)):
        return guarded(lambda request, tenant, who, s: ok(request, dict(items=s.supplier_directory(as_of(), project_id), as_of=str(as_of()))))(request, tenant)

    @app.post(P + "/suppliers", status_code=201)
    def add_supplier(tenant: str, body: SupplierIn, request: Request, key: Optional[str] = IDK):
        return guarded(lambda request, tenant, who, s: idem(request, s, tenant, key, body.model_dump(mode="json"), lambda: ok(request, dict(id=s.add_supplier(**body.model_dump())), 201)))(request, tenant)

    @app.get(P + "/supplier-intelligence")
    def supplier_intelligence(tenant: str, request: Request, project_id: Optional[str] = Query(None, pattern=ID_RE)):
        return guarded(lambda request, tenant, who, s: ok(request, s.supplier_intelligence(project_id, as_of())))(request, tenant)

    @app.post(P + "/suppliers/{supplier_id}/sources", status_code=201)
    def add_source(tenant: str, supplier_id: str, body: SupplierSourceIn, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(id=s.add_supplier_source(supplier_id, **body.model_dump())), 201))(request, tenant)

    @app.post(P + "/suppliers/{supplier_id}/products", status_code=201)
    def add_product(tenant: str, supplier_id: str, body: SupplierProductIn, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(id=s.add_supplier_product(supplier_id, **body.model_dump())), 201))(request, tenant)

    @app.put(P + "/projects/{project_id}/suppliers/{supplier_id}")
    def shortlist(tenant: str, project_id: str, supplier_id: str, body: ShortlistIn, request: Request):
        def go(request, tenant, who, s):
            if not s.project_overview(project_id):
                return missing(request)
            return ok(request, dict(id=s.set_project_supplier(project_id, supplier_id, body.status, body.note), status=body.status))
        return guarded(go)(request, tenant)

    @app.post(P + "/projects/{project_id}/scenarios/preview")
    def preview(tenant: str, project_id: str, body: OverridesIn, request: Request):
        def go(request, tenant, who, s):
            try:
                r = s.preview_scenario(project_id, body.clean())
            except ValueError as e:
                return err(request, 422, "validation_error", str(e)[:160])
            return ok(request, r) if r else missing(request)
        return guarded(go)(request, tenant)

    @app.post(P + "/projects/{project_id}/scenarios/compare")
    def compare(tenant: str, project_id: str, body: CompareIn, request: Request):
        def go(request, tenant, who, s):
            from . import financials as FIN
            named = []
            for sc in body.scenarios:
                inp = s.scenario_inputs(project_id, sc.overrides.clean())
                if inp is None:
                    return missing(request)
                named.append((sc.name, inp))
            return ok(request, dict(rows=FIN.compare(named), kind="simulated", note="Simulated projections on stated assumptions; not actual business performance."))
        return guarded(go)(request, tenant)

    @app.post(P + "/projects/{project_id}/scenarios", status_code=201)
    def save_scenario(tenant: str, project_id: str, body: ScenarioIn, request: Request, key: Optional[str] = IDK):
        def go(request, tenant, who, s):
            if not s.project_overview(project_id):
                return missing(request)
            return idem(request, s, tenant, key, [project_id, body.model_dump()], lambda: ok(request, dict(id=s.save_scenario(project_id, body.name, body.overrides.clean())), 201))
        return guarded(go)(request, tenant)

    @app.get(P + "/projects/{project_id}/scenarios/{scenario_id}")
    def get_scenario(tenant: str, project_id: str, scenario_id: str, request: Request):
        def go(request, tenant, who, s):
            sc = s.get_scenario(scenario_id)
            return ok(request, sc) if sc and sc["project_id"] == project_id else missing(request)
        return guarded(go)(request, tenant)

    @app.get(P + "/marketing/offers")
    def offers(tenant: str, request: Request):
        return guarded(lambda request, tenant, who, s: ok(request, dict(offers=s.offer_economics(), campaigns=s.campaigns(), note="Drafts only: nothing is published, sent or paid for. Uplift needed is arithmetic; whether it occurs is not estimated.")))(request, tenant)

    # ---------------------------------------------------------------- governed procurement recommendation
    def out(r):
        return {k: r.get(k) for k in ("corr_id", "tenant", "workflow", "status", "state", "project_id", "failure", "detail", "approval_id", "duplicate_of", "side_effects", "agent_mode", "total_cost_cents")}

    @app.post(P + "/projects/{project_id}/procurement", status_code=202)
    def start(tenant: str, project_id: str, body: ProcureIn, request: Request, key: Optional[str] = IDK):
        import re
        if key is not None and not re.fullmatch(r"[A-Za-z0-9_\-]{8,64}", key):
            return err(request, 422, "validation_error", "Idempotency-Key must be 8-64 characters of [A-Za-z0-9_-]")
        def go(request, tenant, who, s):
            r = launch_flow(tenant).run(BEARER.match(request.headers["Authorization"]).group(1), project_id, body.period_weeks, idempotency_key=key, request_id=request.state.request_id)
            f = r.get("failure")
            if f == "AUTH_DENIED":
                return err(request, 401, "unauthenticated", "invalid or expired session")
            if f == "NO_SUCH_PROJECT":
                return err(request, 404, "not_found", "not found")
            if f in ("ROLE_DENIED", "TOOL_DENIED"):
                return err(request, 403, "forbidden", "this role may not request a procurement recommendation")
            return ok(request, out(r), 200 if r["status"] == "DUPLICATE" else 202)
        return guarded(go)(request, tenant)

    @app.get(P + "/procurement/runs")
    def runs(tenant: str, request: Request, limit: int = LIM, cursor: Optional[str] = CUR):
        sql = ("SELECT r.id, r.project_id, p.name, r.state, r.requester, r.period, r.agent_mode, (r.totals->>'total_cost_cents'), r.failure, r.created_at, (SELECT max(e.ts) FROM launch_events e WHERE e.tenant_id=r.tenant_id AND e.run_id=r.id) "
               "FROM procurement_recommendations r JOIN launch_projects p ON p.tenant_id=r.tenant_id AND p.id=r.project_id WHERE r.tenant_id=%s ORDER BY r.created_at DESC, r.id")
        cols = ("id", "project_id", "project", "state", "requester", "period", "agent_mode", "total_cost_cents", "failure", "created_at", "last_activity")
        def go(request, tenant, who, s):
            d = page(s, sql, (tenant,), limit, cursor, cols); nm = names(s)
            for it in d["items"]:
                it["status_label"], it["tone"] = PR.state_label(it["state"]), PR.TONE.get(it["state"], "info")
                it["total_cost_cents"] = int(it["total_cost_cents"]) if it["total_cost_cents"] is not None else None
                it["requested_by"] = nm.get(it["requester"], it["requester"]); it["agent"] = PR.AGENT_LABEL.get(it["agent_mode"])
            return ok(request, d)
        return guarded(go)(request, tenant)

    @app.get(P + "/procurement/runs/{run_id}")
    def run_detail(tenant: str, run_id: str, request: Request):
        def go(request, tenant, who, s):
            r = launch_flow(tenant).status(run_id)
            if r is None:
                return missing(request)
            proj = s.project_overview(r["project_id"])
            return ok(request, dict(id=r["id"], project_id=r["project_id"], state=r["state"], requester=r["requester"], failure=r["failure"], approval_id=r["approval_id"], agent_mode=r["agent_mode"], plan=r["items"], research=r["research"],
                                    events=r["events"], business=PR.launch_run_business(r, r["events"], proj, names(s))))
        return guarded(go)(request, tenant)

    @app.post(P + "/procurement/runs/{run_id}/decision")
    def decision(tenant: str, run_id: str, body: DecisionIn, request: Request):
        def go(request, tenant, who, s):
            r = launch_flow(tenant).decide(run_id, BEARER.match(request.headers["Authorization"]).group(1), body.approve, body.comment, request_id=request.state.request_id)
            f = r.get("failure")
            if f == "AUTH_DENIED":
                return err(request, 401, "unauthenticated", "invalid or expired session")
            if f in ("ROLE_DENIED", "MAKER_CHECKER"):
                return err(request, 403, "forbidden", "you may not decide on this request")
            if r.get("status") == "DENIED" and "no such run" in str(r.get("detail", "")):
                return err(request, 404, "not_found", "not found")
            if f in ("NOT_AWAITING_APPROVAL", "APPROVAL_REPLAY", "APPROVAL_MISMATCH", "APPROVAL_EXPIRED"):
                return err(request, 409, "conflict", {"APPROVAL_EXPIRED": "the approval expired", "APPROVAL_REPLAY": "this approval was already used"}.get(f, "the run is not awaiting approval"))
            return ok(request, out(r))
        return guarded(go)(request, tenant)
