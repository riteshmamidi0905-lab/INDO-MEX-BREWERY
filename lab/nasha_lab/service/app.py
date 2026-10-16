"""create_hardened_app(): the hardened service. Additive to nasha_lab.api.create_app (which is unchanged).

Request path: HardeningMiddleware (request id, trace, drain, size/type limits, IP rate limit, security headers, log, metrics)
  -> route dependency `require(permission)` (bearer token -> principal -> role permission -> per-principal rate limit; deny by default)
  -> handler runs in a bounded worker pool under a per-route deadline
  -> one PostgreSQL transaction: advisory lock on the Idempotency-Key, replay or work, stored response (all or nothing)."""
from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncIterator, Callable, Optional, TypeVar

import psycopg
from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg_pool import PoolClosed, PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import agent, generator, identity as ID, knowledge, tools as T, world as W
from ..ops.failure_policy import decide, load_policy
from . import LABEL, VERSION, schemas as S, store
from .auth import ALL_PERMISSIONS, Principal, TokenService, parse_bearer
from .config import Settings
from .db import Database, Deadline, translate_db_error
from .errors import ERROR_TABLE, ApiError, envelope
from .gateway import BridgedAuthority, ToolGateway
from .middleware import HardeningMiddleware, Runtime
from .migrations import latest_version
from .obs import Hasher, Metrics, Tracer, configure_logging, emit
from .ratelimit import TokenBucketLimiter

R = TypeVar("R")
PUBLIC_PATHS = {"/healthz", "/readyz", "/v1/dev/token"}
ERR = {c: {"model": S.ErrorEnvelope} for c in (400, 401, 403, 404, 409, 413, 415, 422, 429, 500, 502, 503, 504)}
IDEM_HEADER = "Idempotency-Key"


class PostEffectFailure(Exception):
    """The state-changing step succeeded in-process but the database write that records it failed (outcome ambiguous)."""
    def __init__(self, cause: BaseException, run_id: str, tool_args: dict[str, Any]) -> None:
        super().__init__(type(cause).__name__); self.cause, self.run_id, self.tool_args = cause, run_id, tool_args


class Ctx:
    """Everything a request needs; tests reach it through app.state.ctx (fault-injection seams are plain attributes)."""
    def __init__(self, settings: Settings, service: agent.AgentService, db: Database, metrics: Metrics, rt: Runtime, tokens: TokenService, gateway: ToolGateway,
                 log: logging.Logger, tracer: Tracer, hasher: Hasher, executor: ThreadPoolExecutor, principal_limiter: TokenBucketLimiter) -> None:
        self.s, self.service, self.db, self.metrics, self.rt, self.tokens, self.gateway = settings, service, db, metrics, rt, tokens, gateway
        self.log, self.tracer, self.hasher, self.executor, self.principal_limiter = log, tracer, hasher, executor, principal_limiter
        self.policy = load_policy(); self.spool = store.Spool(settings.data_dir)
        self.after_effect_hook: Optional[Callable[[], None]] = None          # test seam: runs after the agent effect, before the DB records it
        self.ready_cache: Optional[tuple[float, dict[str, Any]]] = None
        self.dl_cache: tuple[float, dict[str, int]] = (0.0, {})


def view(row_or_summary: dict[str, Any], *, reconciled: bool = False) -> dict[str, Any]:
    """Public run view from a runs row (never exposes owner, request ids or internal run records)."""
    r = row_or_summary; sm = r["summary"]
    return {"run_id": r["run_id"], "event_id": r["event_id"], "status": r["status"], "awaiting_human": bool(r["awaiting_human"]), "proposal": sm.get("proposal"), "final": sm.get("final"),
            "created_at": r["created_at"].isoformat(), "updated_at": r["updated_at"].isoformat(), "reconciled": reconciled}


def create_hardened_app(settings: Settings, *, service: Optional[agent.AgentService] = None, db: Optional[Database] = None, log_stream: Any = None,
                        clock: Callable[[], float] = time.monotonic, tool_executor: Optional[Callable[..., dict[str, Any]]] = None) -> FastAPI:
    log = configure_logging(settings.log_level, log_stream)
    metrics, hasher = Metrics(), Hasher(settings.log_salt.get_secret_value().encode() if settings.log_salt else None)
    tracer = Tracer(log)
    if service is None:
        w = W.build_world(settings.world_seed, menu_version=generator.CURRENT_MENU_VERSION, po_coverage=W.CURRENT_PO_COVERAGE)[0]
        os.makedirs(settings.data_dir, exist_ok=True)
        from .. import trace as TR
        service = agent.AgentService(w, knowledge.default_kb(), store=TR.Store(os.path.join(settings.data_dir, "runs.db")), checkpoint_path=os.path.join(settings.data_dir, "checkpoints.db"),
                                     authority=BridgedAuthority.dev())
    database = db or Database(settings, metrics, clock=clock)
    tokens = TokenService(settings.signing_keys(), settings.jwt_active_kid, settings.jwt_issuer, settings.jwt_audience, leeway_s=settings.jwt_leeway_s, max_ttl_s=settings.token_max_ttl_s)
    ip_lim = TokenBucketLimiter(settings.rate_ip_capacity, settings.rate_ip_refill_per_s, max_keys=settings.rate_table_max, clock=clock)
    pr_lim = TokenBucketLimiter(settings.rate_principal_capacity, settings.rate_principal_refill_per_s, max_keys=settings.rate_table_max, clock=clock)
    rt = Runtime(max_body=settings.max_body_bytes, ip_limiter=ip_lim, metrics=metrics, tracer=tracer, log=log, hasher=hasher, proxy_hops=settings.trusted_proxy_hops)
    gateway = ToolGateway(service.rt.world, service.rt.kb, metrics, executor=tool_executor, timeout_s=settings.tool_timeout_s)
    ex = ThreadPoolExecutor(max_workers=settings.worker_threads, thread_name_prefix="nasha-work")
    ctx = Ctx(settings, service, database, metrics, rt, tokens, gateway, log, tracer, hasher, ex, pr_lim)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database.open()
        ok = await asyncio.get_running_loop().run_in_executor(ex, database.wait_ready, settings.db_pool_timeout_s)
        if not ok:
            if settings.require_db_at_start:
                database.close()
                raise RuntimeError("database unavailable at start and NASHA_SVC_REQUIRE_DB_AT_START is true; refusing to start")
            emit(log, logging.WARNING, "starting_degraded", detail="database unavailable at start; /readyz will report 503 until it is reachable")
        emit(log, logging.INFO, "started", detail=f"env={settings.env} version={VERSION} latest_schema={latest_version()}")
        try:
            yield
        finally:
            rt.draining = True                                        # graceful shutdown: refuse new work, let in-flight requests finish
            deadline = time.monotonic() + settings.shutdown_grace_s
            while rt.inflight > 0 and time.monotonic() < deadline: await asyncio.sleep(0.05)
            emit(log, logging.INFO, "stopping", count=rt.inflight)
            ex.shutdown(wait=False, cancel_futures=True)
            database.close()

    app = FastAPI(title="NASHA Enterprise AI Lab: hardened service", version=VERSION, lifespan=lifespan,
                  description=f"{LABEL}. A hardened API layer over the lab agent: signed-token auth, roles, rate limits, deadlines, idempotency, PostgreSQL state.",
                  docs_url="/docs" if settings.docs_enabled else None, redoc_url=None, openapi_url="/openapi.json" if settings.docs_enabled else None)
    app.state.ctx = ctx
    app.add_middleware(HardeningMiddleware, rt=rt)
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=["GET", "POST"],
                           allow_headers=["Authorization", "Content-Type", IDEM_HEADER, "X-Request-ID"], max_age=600)

    # ------------------------------------------------------------------------------------------------ errors
    def rid_of(request: Request) -> str: return str(request.scope.get("state", {}).get("request_id", "-"))

    def err_response(request: Request, e: ApiError) -> JSONResponse:
        request.scope.setdefault("state", {})["error_code"] = e.code
        h = {}
        if e.retry_after_s is not None: h["Retry-After"] = str(max(1, int(e.retry_after_s + 0.999)))
        if e.code == "AUTH_REQUIRED" or e.code.startswith("AUTH_INVALID") or e.code == "AUTH_TOKEN_EXPIRED": h["WWW-Authenticate"] = "Bearer"
        metrics.inc("nasha_errors_total", help="error envelopes by code", code=e.code)
        return JSONResponse(status_code=e.status, content=envelope(e.code, e.message, rid_of(request), details=e.details, retry_after_s=e.retry_after_s), headers=h)

    @app.exception_handler(ApiError)
    async def on_api_error(request: Request, e: ApiError) -> JSONResponse: return err_response(request, e)

    @app.exception_handler(psycopg.Error)
    async def on_pg(request: Request, e: psycopg.Error) -> JSONResponse: return err_response(request, translate_db_error(e))

    @app.exception_handler(PoolTimeout)
    async def on_pool_timeout(request: Request, e: PoolTimeout) -> JSONResponse: return err_response(request, translate_db_error(e))

    @app.exception_handler(PoolClosed)
    async def on_pool_closed(request: Request, e: PoolClosed) -> JSONResponse: return err_response(request, translate_db_error(e))

    @app.exception_handler(StarletteHTTPException)
    async def on_http(request: Request, e: StarletteHTTPException) -> JSONResponse:
        m = {404: ("ROUTE_NOT_FOUND", "no such route"), 405: ("METHOD_NOT_ALLOWED", "method not allowed"), 413: ("PAYLOAD_TOO_LARGE", f"request body exceeds {settings.max_body_bytes} bytes")}
        code, msg = m.get(e.status_code, ("INVALID_REQUEST", "request rejected"))
        return err_response(request, ApiError(code, msg))

    @app.exception_handler(RequestValidationError)
    async def on_validation(request: Request, e: RequestValidationError) -> JSONResponse:
        # authentication comes first: an unauthenticated caller learns nothing about the request schema
        try:
            if request.url.path not in PUBLIC_PATHS and request.url.path.startswith("/v1/"): authenticate(request)
        except ApiError as ae:
            return err_response(request, ae)
        errs = e.errors()
        if any(x["type"] in ("json_invalid", "model_attributes_type") for x in errs): return err_response(request, ApiError("MALFORMED_BODY", "request body is not valid JSON"))
        det = [{"loc": ".".join(str(p) for p in x["loc"]), "msg": str(x["msg"])[:120], "type": x["type"]} for x in errs[:10]]        # never echo the input value
        return err_response(request, ApiError("INVALID_REQUEST", "request validation failed", details={"errors": det}))

    # ------------------------------------------------------------------------------------------------ auth + authorization
    bearer = HTTPBearer(auto_error=False, description="Signed JWT (HS256, kid header). SYNTHETIC tokens only.")

    def authenticate(request: Request) -> Principal:
        try:
            p = tokens.verify(parse_bearer(request.headers.get("authorization")))
        except ApiError as e:
            metrics.inc("nasha_auth_failures_total", help="authentication failures", reason=e.code)
            raise
        request.scope.setdefault("state", {})["principal_hash"] = hasher(p.sub)
        return p

    def require(permission: str) -> Callable[..., Any]:
        assert permission in ALL_PERMISSIONS, f"unknown permission {permission}"

        async def dep(request: Request, _creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> Principal:
            p = authenticate(request)
            if not p.can(permission):
                metrics.inc("nasha_auth_failures_total", help="authentication failures", reason="FORBIDDEN")
                raise ApiError("FORBIDDEN", "this role may not perform this action")
            ok, wait = pr_lim.take(p.sub)
            if not ok:
                metrics.inc("nasha_rate_limited_total", help="requests refused by the rate limiter", scope="principal")
                raise ApiError("RATE_LIMITED", "too many requests for this principal", retry_after_s=max(wait, 0.001))
            return p
        dep.__nasha_permission__ = permission          # type: ignore[attr-defined]
        return dep

    def idem_key(request: Request) -> str:
        k = request.headers.get(IDEM_HEADER)
        if not k: raise ApiError("IDEMPOTENCY_KEY_REQUIRED", f"{IDEM_HEADER} header is required for this endpoint")
        if not store_key_ok(k): raise ApiError("IDEMPOTENCY_KEY_INVALID", f"{IDEM_HEADER} must be 8-128 characters of [A-Za-z0-9_.:-]")
        return k

    def store_key_ok(k: str) -> bool:
        import re
        return re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", k) is not None

    # ------------------------------------------------------------------------------------------------ execution helpers
    async def offload(fn: Callable[[Deadline], R], seconds: float) -> R:
        """Run blocking work in the bounded pool under a deadline. On timeout the caller gets 504 and the work is told to stop before it commits."""
        dl = Deadline(seconds)
        cv = contextvars.copy_context()
        fut = asyncio.get_running_loop().run_in_executor(ex, lambda: cv.run(fn, dl))
        try:
            return await asyncio.wait_for(fut, timeout=seconds)
        except asyncio.TimeoutError:
            dl.cancel(); metrics.inc("nasha_deadline_exceeded_total", help="requests that hit their deadline")
            raise ApiError("DEADLINE_EXCEEDED", f"the request exceeded its {seconds:g}s deadline", retry_after_s=1.0) from None

    async def idempotent(request: Request, p: Principal, key: str, route: str, params: dict[str, Any], body: Any, seconds: float,
                         work: Callable[[Any, Deadline], tuple[int, Any]], after_fail: Optional[Callable[[ApiError], None]] = None) -> JSONResponse:
        rhash = store.request_hash(request.method, route, params, body)
        rid = rid_of(request)

        def job(dl: Deadline) -> tuple[int, Any, bool]:
            try:
                with tracer.span("db.tx", route=route), database.tx(dl) as conn:
                    store.idem_lock(conn, p.sub, key)
                    hit = store.idem_get(conn, p.sub, key, route, rhash)
                    if hit is not None: return hit[0], hit[1], True
                    status, payload = work(conn, dl)
                    store.idem_put(conn, p.sub, key, route, rhash, status, payload, settings.idempotency_ttl_s)
                    return status, payload, False
            except PostEffectFailure as pe:
                raise ambiguous_decision(pe, rid, p) from None
            except ApiError as ae:
                if after_fail: after_fail(ae)
                raise
        status, payload, replay = await offload(job, seconds)
        if replay: metrics.inc("nasha_idempotent_replays_total", help="responses served from the idempotency store")
        return JSONResponse(status_code=status, content=payload, headers={"Idempotent-Replay": "true"} if replay else {})

    def ambiguous_decision(pe: PostEffectFailure, rid: str, p: Principal) -> ApiError:
        """The approval executed in-process but the database could not record it. Policy: HUMAN_REVIEW_REQUIRED + timeout-ambiguous -> DEAD_LETTER."""
        op = ctx.policy.op("human_approval_execute_step")
        d = decide(op.klass, "TIMEOUT_AMBIGUOUS", attempts_made=1, max_attempts=op.max_attempts, has_key=True, can_reconcile=False, side_effects=True, policy=ctx.policy)
        rec = store.dead_letter_record(correlation_id=rid, run_id=pe.run_id, operation=op.name, tool=None, op_class=op.klass, failure_code=type(pe.cause).__name__,
                                       failure_class="TIMEOUT_AMBIGUOUS", attempts=1, reason=f"decision executed but not recorded: {type(pe.cause).__name__}", args=pe.tool_args)
        try:
            with database.tx() as c: store.insert_dead_letter(c, rec)
        except Exception:
            ctx.spool.append(rec); metrics.inc("nasha_dead_letter_spooled_total", help="dead letters written to the local spool because the database was unavailable")
        metrics.inc("nasha_dead_letters_created_total", help="dead letters created", action=d.action)
        emit(log, logging.ERROR, "decision_ambiguous", request_id=rid, principal=hasher(p.sub), code="DECISION_AMBIGUOUS", detail=rec["dl_id"])
        return ApiError("DECISION_AMBIGUOUS", "the decision was executed but could not be recorded; a dead-letter record was created for human review", details={"dead_letter": rec["dl_id"], "run_id": pe.run_id})

    def sanitize(request: Request) -> None: return None

    # ------------------------------------------------------------------------------------------------ probes
    @app.get("/healthz", response_model=S.Live, tags=["ops"], summary="Liveness: cheap, no dependencies")
    async def healthz() -> dict[str, Any]: return {"status": "ok", "synthetic": True}

    def readiness() -> dict[str, Any]:
        now = time.monotonic()
        if ctx.ready_cache and now - ctx.ready_cache[0] < 1.0 and not rt.draining: return ctx.ready_cache[1]
        checks: dict[str, dict[str, Any]] = {}; version = 0
        try:
            with database.tx(Deadline(settings.db_pool_timeout_s)) as c:
                checks["db"] = {"ok": True, "detail": "reachable"}
                version = store.schema_version(c)
        except ApiError as e:
            checks["db"] = {"ok": False, "detail": e.code}
        want = latest_version()
        if "ok" in checks["db"] and checks["db"]["ok"]:
            if version == want or (version > want and settings.allow_newer_schema): checks["schema"] = {"ok": True, "detail": f"version {version}"}
            elif version < want: checks["schema"] = {"ok": False, "detail": f"SCHEMA_OLDER: database {version}, build needs {want}; run the migration job"}
            else: checks["schema"] = {"ok": False, "detail": f"SCHEMA_NEWER: database {version}, build supports {want}"}
        else: checks["schema"] = {"ok": False, "detail": "not checked: database unavailable"}
        try:
            n = service.rt.world.q("SELECT COUNT(*) n FROM fact_order")[0]["n"]
            checks["agent"] = {"ok": bool(n > 0 and len(service.rt.kb.chunks) > 0), "detail": "world and knowledge base loaded"}
        except Exception as e:
            checks["agent"] = {"ok": False, "detail": type(e).__name__}
        checks["draining"] = {"ok": not rt.draining, "detail": "accepting traffic" if not rt.draining else "shutting down"}
        res = {"checks": checks, "schema_version": version}
        if all(v["ok"] for v in checks.values()) and os.path.exists(ctx.spool.path):
            try:
                with database.tx() as c: n = ctx.spool.drain(c)
                ctx.spool.clear(); emit(log, logging.INFO, "spool_replayed", count=n)
            except Exception:
                pass
        ctx.ready_cache = (now, res)
        return res

    @app.get("/readyz", response_model=S.Ready, responses={503: {"model": S.ErrorEnvelope}}, tags=["ops"], summary="Readiness: database, schema version, agent, drain state")
    async def readyz(request: Request) -> JSONResponse:
        res = await offload(lambda dl: readiness(), settings.default_deadline_s)
        failed = [k for k, v in res["checks"].items() if not v["ok"]]
        if failed:
            code = "SHUTTING_DOWN" if failed == ["draining"] else ("SCHEMA_MISMATCH" if failed == ["schema"] else ("DB_UNAVAILABLE" if "db" in failed else "NOT_READY"))
            return err_response(request, ApiError("NOT_READY" if code == "NOT_READY" else code, "not ready: " + ", ".join(failed), retry_after_s=2.0, details={"failed": failed, "checks": res["checks"]}))
        return JSONResponse({"status": "ready", "checks": res["checks"], "schema_version": res["schema_version"], "synthetic": True})

    @app.get("/metrics", response_class=PlainTextResponse, responses={401: {"model": S.ErrorEnvelope}, 403: {"model": S.ErrorEnvelope}}, tags=["ops"], summary="Prometheus text metrics (OPERATOR token)",
             include_in_schema=settings.metrics_enabled)
    async def prom(request: Request, _p: Principal = Depends(require("metrics:read"))) -> PlainTextResponse:
        if not settings.metrics_enabled: raise ApiError("ROUTE_NOT_FOUND", "metrics are disabled")

        def collect(dl: Deadline) -> None:
            st = database.stats()
            for k, v in st.items(): metrics.set("nasha_db_pool", v, help="connection pool state", state=k)
            metrics.set("nasha_inflight_requests", rt.inflight, help="requests being served")
            metrics.set("nasha_rate_limiter_keys", ip_lim.size(), help="tracked rate-limit keys", scope="ip")
            metrics.set("nasha_rate_limiter_keys", pr_lim.size(), help="tracked rate-limit keys", scope="principal")
            metrics.set("nasha_build_info", 1, help="build information", version=VERSION)
            up, ver = 0, 0
            counts: dict[str, int] = {}
            try:
                now = time.monotonic()
                with database.tx(Deadline(1.0)) as c:
                    ver = store.schema_version(c); up = 1
                    if now - ctx.dl_cache[0] > 5: ctx.dl_cache = (now, store.dead_letter_counts(c))
                    counts = ctx.dl_cache[1]
            except ApiError:
                counts = ctx.dl_cache[1]
            metrics.set("nasha_db_up", up, help="1 if the database answered the scrape")
            metrics.set("nasha_schema_version", ver, help="applied schema version")
            for stname in ("OPEN", "ALREADY_APPLIED", "REPLAYED", "DISCARDED"): metrics.set("nasha_dead_letters", counts.get(stname, 0), help="dead-letter records by status", status=stname)
        await offload(collect, settings.default_deadline_s)
        return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")

    # ------------------------------------------------------------------------------------------------ dev token issuer (tests / dev only)
    if settings.dev_token_issuer:
        @app.post("/v1/dev/token", response_model=S.TokenOut, responses=ERR, tags=["dev"], summary="DEV/TEST ONLY token issuer (absent unless NASHA_SVC_DEV_TOKEN_ISSUER=true and env is dev/test)")
        async def dev_token(body: S.DevTokenIn) -> dict[str, Any]:
            return {"token": tokens.issue(body.sub, body.role, body.ttl_s), "token_type": "bearer", "expires_in": body.ttl_s}

    # ------------------------------------------------------------------------------------------------ read-only tool routes
    async def tool_route(request: Request, name: str, args: dict[str, Any]) -> dict[str, Any]:
        rid = rid_of(request)

        def job(dl: Deadline) -> dict[str, Any]:
            with tracer.span("tool." + name):
                data, attempts = gateway.call(name, args, rid, dl)
            return {"data": data, "attempts": attempts}
        return await offload(job, settings.default_deadline_s)

    @app.get("/v1/events", response_model=S.EventList, responses=ERR, tags=["tools"], summary="List operational incidents (synthetic)")
    async def events(request: Request, _p: Principal = Depends(require("tools:read"))) -> dict[str, Any]:
        def job(dl: Deadline) -> dict[str, Any]:
            return {"events": [{"event_id": e["event_id"], "payload": json.loads(e["payload"])} for e in service.rt.world.q("SELECT * FROM operational_incidents ORDER BY event_id")]}
        return await offload(job, settings.default_deadline_s)

    @app.get("/v1/inventory/{ingredient}", response_model=S.ToolData, responses=ERR, tags=["tools"])
    async def inventory(request: Request, ingredient: str = Path(min_length=2, max_length=40, pattern=r"^[A-Za-z][A-Za-z0-9 _-]*$"), location_id: str = Query(pattern=r"^L\d{2}$"),
                        _p: Principal = Depends(require("tools:read"))) -> dict[str, Any]:
        return await tool_route(request, "query_inventory", dict(location_id=location_id, ingredient=ingredient))

    @app.get("/v1/quality/findings", response_model=S.ToolData, responses=ERR, tags=["tools"])
    async def findings(request: Request, rule: Optional[str] = Query(None, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$"), limit: int = Query(20, ge=1, le=100),
                       _p: Principal = Depends(require("tools:read"))) -> dict[str, Any]:
        return await tool_route(request, "list_quality_findings", dict(rule=rule, limit=limit))

    @app.post("/v1/knowledge/ask", response_model=S.ToolData, responses=ERR, tags=["tools"], summary="Read-only policy question (POST because of the body; no Idempotency-Key needed)")
    async def ask(request: Request, body: S.AskIn, _p: Principal = Depends(require("tools:read"))) -> dict[str, Any]:
        return await tool_route(request, "get_current_policy", dict(question=body.question))

    # ------------------------------------------------------------------------------------------------ runs
    def can_see(p: Principal, row: dict[str, Any]) -> bool: return row["owner"] == p.sub or p.can("runs:read_all")

    @app.post("/v1/runs", status_code=201, response_model=S.RunView, responses=ERR, tags=["runs"], summary="Start an agent run for an event (Idempotency-Key required)")
    async def start_run(request: Request, body: S.RunStartIn, p: Principal = Depends(require("runs:create")), key: str = Depends(idem_key)) -> JSONResponse:
        rid = rid_of(request)

        def work(c: Any, dl: Deadline) -> tuple[int, Any]:
            c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 1))", ("event:" + body.event_id,))        # one start per event across instances and keys
            existing = store.get_run_by_event(c, body.event_id)
            if existing is not None:
                raise ApiError("EVENT_ALREADY_PROCESSED", "a run already exists for this event", details={"run_id": existing["run_id"]} if can_see(p, existing) else None)
            if not service.rt.world.q("SELECT 1 FROM operational_incidents WHERE event_id=?", body.event_id): raise ApiError("UNKNOWN_EVENT", f"no event {body.event_id}")
            prior = service.store.active_run_for(body.event_id)
            reconciled = prior is not None
            with tracer.span("agent.start"):
                if prior is not None: summary = service.summary(prior[0])          # RECONCILE_BEFORE_RETRY: an earlier attempt started the run but the database never recorded it
                else: summary = service.start(body.event_id, rid)
            if summary is None or str(summary["status"]).startswith("FAILED"): raise ApiError("UNKNOWN_EVENT", f"event {body.event_id} could not be processed")
            run_id = summary["run"]["run_id"]
            store.insert_run(c, run_id=run_id, event_id=body.event_id, owner=p.sub, request_id=rid, summary=summary)
            store.audit(c, request_id=rid, principal_hash=hasher(p.sub), action="run.start", resource=run_id, outcome="ok", detail={"event_id": body.event_id, "reconciled": reconciled})
            row = store.get_run(c, run_id)
            assert row is not None
            return 201, view(row, reconciled=reconciled)
        return await idempotent(request, p, key, "POST /v1/runs", {}, body.model_dump(), settings.run_deadline_s, work)

    async def read_db(fn: Callable[[Any], R], seconds: Optional[float] = None) -> R:
        def job(dl: Deadline) -> R:
            with database.tx(dl) as c: return fn(c)
        return await offload(job, seconds or settings.default_deadline_s)

    @app.get("/v1/runs", response_model=S.RunList, responses=ERR, tags=["runs"], summary="List runs (own runs; all runs with runs:read_all)")
    async def list_runs(request: Request, limit: int = Query(20, ge=1, le=100), before: Optional[str] = Query(None, pattern=r"^run-[0-9a-f]{10}$"),
                        p: Principal = Depends(require("runs:read_own"))) -> dict[str, Any]:
        owner = None if p.can("runs:read_all") else p.sub
        rows = await read_db(lambda c: store.list_runs(c, owner=owner, limit=limit, before=before))
        return {"runs": [view(r) for r in rows], "next_before": rows[-1]["run_id"] if len(rows) == limit else None}

    @app.get("/v1/runs/{run_id}", response_model=S.RunView, responses=ERR, tags=["runs"])
    async def get_run(request: Request, run_id: str = Path(pattern=r"^run-[0-9a-f]{10}$"), p: Principal = Depends(require("runs:read_own"))) -> dict[str, Any]:
        row = await read_db(lambda c: store.get_run(c, run_id))
        if row is None or not can_see(p, row): raise ApiError("NOT_FOUND", f"no run {run_id}")      # same answer for "absent" and "not yours": no enumeration
        return view(row)

    def decision_route(decision: str) -> Callable[..., Any]:
        async def handler(request: Request, body: S.DecisionIn, run_id: str = Path(pattern=r"^run-[0-9a-f]{10}$"), p: Principal = Depends(require("runs:decide")), key: str = Depends(idem_key)) -> JSONResponse:
            rid = rid_of(request)

            def work(c: Any, dl: Deadline) -> tuple[int, Any]:
                row = store.get_run(c, run_id, lock=True)
                if row is None: raise ApiError("NOT_FOUND", f"no run {run_id}")
                state = service.summary(run_id)
                if state is None: raise ApiError("RUN_NOT_RESUMABLE", "the agent no longer holds this run's state; it cannot be resumed")
                if not row["awaiting_human"]: raise ApiError("CONFLICT_STATE", f"run {run_id} is not awaiting a human decision (status {row['status']})")
                if not state["awaiting_human"]:
                    # DB says awaiting, the agent says decided: an earlier attempt executed but never recorded (it dead-lettered). Bring the record in line, do not execute again.
                    store.update_run(c, run_id, state)
                    store.audit(c, request_id=rid, principal_hash=hasher(p.sub), action="run.reconcile", resource=run_id, outcome="reconciled", detail={"status": state["status"]})
                    env = envelope("CONFLICT_STATE", "this run was already decided by an earlier attempt; the record has been reconciled, nothing was executed again", rid, details={"status": state["status"]})
                    return 409, env
                tool_args = {"run_id": run_id, "decision": decision}
                try:
                    with tracer.span("agent.resume"):
                        summary = service.resume(run_id, dict(decision=decision, note=body.note), session=ID.Identity(p.sub, p.role))
                except KeyError: raise ApiError("NOT_FOUND", f"no run {run_id}") from None
                except RuntimeError as e: raise ApiError("CONFLICT_STATE", str(e)[:200]) from None
                except ID.AuthError as e:
                    if e.code == "ROLE_NOT_PERMITTED": raise ApiError("ROLE_NOT_PERMITTED", "this role may not approve this action") from None
                    raise ApiError("FORBIDDEN", "not permitted") from None
                except Exception as e:
                    raise PostEffectFailure(e, run_id, tool_args) from None          # the effect may or may not have happened
                try:                                                                 # from here the effect has happened in-process
                    if ctx.after_effect_hook: ctx.after_effect_hook()
                    store.insert_approval(c, run_id=run_id, decision=decision, reviewer=p.sub, role=p.role, note=body.note, result_status=summary["status"], request_id=rid)
                    store.update_run(c, run_id, summary)
                    store.audit(c, request_id=rid, principal_hash=hasher(p.sub), action="run." + decision, resource=run_id, outcome="ok", detail={"status": summary["status"]})
                    out = store.get_run(c, run_id)
                    assert out is not None
                    return 200, view(out)
                except Exception as e:
                    raise PostEffectFailure(e, run_id, tool_args) from None

            def denied(ae: ApiError) -> None:
                if ae.code in ("ROLE_NOT_PERMITTED", "FORBIDDEN"):
                    try:
                        with database.tx() as c: store.audit(c, request_id=rid, principal_hash=hasher(p.sub), action="run." + decision, resource=run_id, outcome="denied", detail={"code": ae.code})
                    except ApiError: pass
            return await idempotent(request, p, key, f"POST /v1/runs/{{run_id}}/{decision}", {"run_id": run_id}, body.model_dump(), settings.run_deadline_s, work, after_fail=denied)
        return handler

    for _d, _label in (("approve", "Approve the pending proposal (role-checked; Idempotency-Key required)"), ("reject", "Reject the pending proposal (Idempotency-Key required)")):
        app.add_api_route(f"/v1/runs/{{run_id}}/{_d}", decision_route(_d), methods=["POST"], response_model=S.RunView, responses=ERR, tags=["runs"], summary=_label, name=f"{_d}_run")

    # ------------------------------------------------------------------------------------------------ dead letters + audit
    def dl_view(r: dict[str, Any]) -> dict[str, Any]:
        return {k: (r[k].isoformat() if k == "created_at" else r[k]) for k in S.DeadLetterView.model_fields}

    @app.get("/v1/dead-letters", response_model=S.DeadLetterList, responses=ERR, tags=["ops"], summary="Open dead letters (OPERATOR)")
    async def dead_letters(request: Request, status: str = Query("OPEN", pattern=r"^(OPEN|ALREADY_APPLIED|REPLAYED|DISCARDED)$"), limit: int = Query(50, ge=1, le=200),
                           _p: Principal = Depends(require("deadletters:read"))) -> dict[str, Any]:
        rows = await read_db(lambda c: store.list_dead_letters(c, status, limit))
        return {"dead_letters": [dl_view(r) for r in rows]}

    @app.post("/v1/dead-letters/{dl_id}/resolve", response_model=S.DeadLetterView, responses=ERR, tags=["ops"], summary="Resolve a dead letter after a person checked the target state")
    async def resolve(request: Request, body: S.ResolveIn, dl_id: str = Path(pattern=r"^DL-[0-9a-f]{10}$"), p: Principal = Depends(require("deadletters:resolve")), key: str = Depends(idem_key)) -> JSONResponse:
        rid = rid_of(request)

        def work(c: Any, dl: Deadline) -> tuple[int, Any]:
            r = store.resolve_dead_letter(c, dl_id, body.status, body.note, hasher(p.sub))
            if r is None: raise ApiError("NOT_FOUND", f"no open dead letter {dl_id}")
            store.audit(c, request_id=rid, principal_hash=hasher(p.sub), action="deadletter.resolve", resource=dl_id, outcome=body.status)
            return 200, dl_view(r)
        return await idempotent(request, p, key, "POST /v1/dead-letters/{dl_id}/resolve", {"dl_id": dl_id}, body.model_dump(), settings.default_deadline_s, work)

    @app.get("/v1/audit", response_model=S.AuditList, responses=ERR, tags=["ops"], summary="Recent audit entries (OPERATOR or AUDITOR)")
    async def audit_list(request: Request, limit: int = Query(50, ge=1, le=200), _p: Principal = Depends(require("audit:read"))) -> dict[str, Any]:
        rows = await read_db(lambda c: store.list_audit(c, limit))
        return {"entries": [dict(r, at=r["at"].isoformat()) for r in rows]}

    assert_all_routes_protected(app)
    app.openapi_schema = None
    return app


def assert_all_routes_protected(app: FastAPI) -> None:
    """Deny by default, enforced at start-up: every route except the explicit public set must depend on `require(permission)`."""
    from fastapi.routing import APIRoute
    bad: list[str] = []
    for r in app.routes:
        if not isinstance(r, APIRoute) or r.path in PUBLIC_PATHS: continue
        if not any(getattr(d.call, "__nasha_permission__", None) for d in r.dependant.dependencies): bad.append(r.path)
    if bad: raise RuntimeError(f"routes without an authorization dependency: {sorted(bad)}")
