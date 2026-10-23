"""Versioned HTTP API (v1) over the governed procurement workflow. Same conventions as the lab's existing API (nasha_lab/api.py): typed models, ONE error envelope, request ids, OpenAPI.

Security properties enforced here (and tested in tests/test_governed_api.py):
  * authentication is a bearer session issued by the TENANT's own authority; a token from another tenant fails verification;
  * the tenant in the path must exist in the registry (otherwise 404, with the same body for unknown and unauthorised tenants: no existence oracle);
  * writes accept an Idempotency-Key header (a retried POST returns the original run);
  * responses carry X-Request-Id; errors never include stack traces, tokens or file paths;
  * list endpoints are paginated with an opaque numeric cursor and a hard maximum page size.
This is a prototype: in-process services, no TLS, no rate limiting at the HTTP layer (the workflow has its own per-user limiter).
"""
import re
import threading
import time
import uuid
from typing import Optional

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

MAX_PAGE = 50
BEARER = re.compile(r"^Bearer ([A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)$")


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class RunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location_id: str = Field(pattern=r"^L\d{2}$")
    ingredient_id: Optional[str] = Field(default=None, pattern=r"^i-[a-z0-9-]{2,40}$")


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool
    comment: str = Field(default="", max_length=300)


class RunOut(BaseModel):
    corr_id: str
    tenant: str
    status: str
    state: Optional[str] = None
    failure: Optional[str] = None
    approval_id: Optional[str] = None
    proposal_id: Optional[str] = None
    po_id: Optional[str] = None
    po_state: Optional[str] = None
    duplicate_of: Optional[str] = None
    explanation_summary: Optional[str] = None
    side_effects: dict


class RunList(BaseModel):
    items: list[dict]
    next_cursor: Optional[str] = None


def _out(r):
    ex = r.get("explanation") or {}
    keep = {k: r.get(k) for k in ("corr_id", "tenant", "status", "state", "failure", "approval_id", "proposal_id", "po_id", "po_state", "duplicate_of", "side_effects")}
    return RunOut(**keep, explanation_summary=ex.get("summary")).model_dump()


def create_governed_app(services: dict) -> FastAPI:
    """services: {tenant_id: GovernedProcurement}. One lock per tenant: the workflow owns one event loop and SQLite connections."""
    app = FastAPI(title="NASHA governed procurement API", version="1.0.0", description="SYNTHETIC DATA. Drafts only: the API has no operation that sends anything to a supplier.")
    locks = {t: threading.RLock() for t in services}
    app.state.services = services

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

    def svc(request, tenant):
        s = services.get(tenant)
        if s is None:
            return None, err(request, 404, "not_found", "not found")
        return s, None

    def token(request):
        m = BEARER.match(request.headers.get("Authorization", ""))
        return m.group(1) if m else None

    @app.get("/v1/health")
    def health():
        return {"status": "ok"}

    @app.get("/v1/ready")
    def ready(request: Request):
        bad = []
        for t, s in services.items():
            try:
                with locks[t]:
                    s.ledger.con.execute("SELECT 1").fetchone()
            except Exception:                                          # noqa: BLE001
                bad.append(t)
        if bad:
            return err(request, 503, "not_ready", f"{len(bad)} tenant store(s) unavailable")
        return {"status": "ready", "tenants": len(services)}

    @app.post("/v1/tenants/{tenant}/procurement/runs", responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope}}, response_model=RunOut, status_code=202)
    def start_run(tenant: str, body: RunIn, request: Request, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
        s, e = svc(request, tenant)
        if e:
            return e
        t = token(request)
        if t is None:
            return err(request, 401, "unauthenticated", "a bearer session is required")
        if idempotency_key is not None and not re.fullmatch(r"[A-Za-z0-9_\-]{8,64}", idempotency_key):
            return err(request, 422, "validation_error", "Idempotency-Key must be 8-64 characters of [A-Za-z0-9_-]")
        with locks[tenant]:
            r = s.run(t, body.location_id, body.ingredient_id, idempotency_key=idempotency_key, request_id=request.state.request_id)
        if r.get("failure") == "AUTH_DENIED":
            return err(request, 401, "unauthenticated", "invalid or expired session")
        if r.get("failure") in ("ROLE_DENIED",):
            return err(request, 403, "forbidden", "this role may not start procurement runs")
        if r.get("failure") == "RATE_LIMITED":
            return err(request, 429, "rate_limited", "too many requests")
        return JSONResponse(status_code=200 if r["status"] == "DUPLICATE" else 202, content=_out(r), headers={"X-Request-Id": request.state.request_id})

    @app.get("/v1/tenants/{tenant}/procurement/runs/{corr_id}", response_model=RunOut, responses={404: {"model": ErrorEnvelope}})
    def get_run(tenant: str, corr_id: str, request: Request):
        s, e = svc(request, tenant)
        if e:
            return e
        t = token(request)
        if t is None:
            return err(request, 401, "unauthenticated", "a bearer session is required")
        try:
            s.env.authority.identify(t)
        except Exception:                                              # noqa: BLE001
            return err(request, 401, "unauthenticated", "invalid or expired session")
        with locks[tenant]:
            run = s.status(corr_id)
        if run is None:
            return err(request, 404, "not_found", "not found")
        return RunOut(corr_id=corr_id, tenant=tenant, status=run["state"], state=run["state"], failure=run["failure"] or None, approval_id=run["approval_id"], proposal_id=run["proposal_id"], side_effects=run["side_effects"]).model_dump()

    @app.get("/v1/tenants/{tenant}/procurement/runs", response_model=RunList)
    def list_runs(tenant: str, request: Request, limit: int = Query(20, ge=1, le=MAX_PAGE), cursor: Optional[str] = Query(None, pattern=r"^\d{1,9}$")):
        s, e = svc(request, tenant)
        if e:
            return e
        t = token(request)
        if t is None:
            return err(request, 401, "unauthenticated", "a bearer session is required")
        try:
            s.env.authority.identify(t)
        except Exception:                                              # noqa: BLE001
            return err(request, 401, "unauthenticated", "invalid or expired session")
        off = int(cursor or 0)
        with locks[tenant]:
            rows = s.ledger.con.execute("SELECT corr_id, state, location_id, ingredient_id FROM runs ORDER BY created, corr_id LIMIT ? OFFSET ?", (limit + 1, off)).fetchall()
        items = [dict(corr_id=a, state=b, location_id=c, ingredient_id=d) for a, b, c, d in rows[:limit]]
        return RunList(items=items, next_cursor=str(off + limit) if len(rows) > limit else None).model_dump()

    @app.post("/v1/tenants/{tenant}/procurement/runs/{corr_id}/decision", response_model=RunOut, responses={401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}})
    def decide(tenant: str, corr_id: str, body: DecisionIn, request: Request):
        s, e = svc(request, tenant)
        if e:
            return e
        t = token(request)
        if t is None:
            return err(request, 401, "unauthenticated", "a bearer session is required")
        with locks[tenant]:
            r = s.decide(corr_id, t, body.approve, body.comment, request_id=request.state.request_id)
        f = r.get("failure")
        if f == "AUTH_DENIED":
            return err(request, 401, "unauthenticated", "invalid or expired session")
        if f in ("ROLE_DENIED", "MAKER_CHECKER"):
            return err(request, 403, "forbidden", "you may not decide on this request")
        if r.get("status") == "DENIED" and "no such run" in str(r.get("detail", "")):
            return err(request, 404, "not_found", "not found")
        if f in ("NOT_AWAITING_APPROVAL", "APPROVAL_REPLAY", "APPROVAL_MISMATCH", "APPROVAL_EXPIRED"):
            return err(request, 409, "conflict", {"APPROVAL_EXPIRED": "the approval expired", "APPROVAL_REPLAY": "this approval was already used"}.get(f, "the run is not awaiting approval"))
        return _out(r)

    return app
