"""FastAPI service over the lab. Typed models, one error contract, request ids, structured JSON logs, OpenAPI.
Every route has a consumer: the agent UI/tests (runs, review, traces), operators (inventory, quality), and analysts (knowledge)."""
import json
import logging
import time
import uuid
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import agent, identity as ID, knowledge, tools as T, world as W

log = logging.getLogger("nasha.api")


class ErrorBody(BaseModel):
    code: str; message: str; request_id: str

class ErrorEnvelope(BaseModel):
    error: ErrorBody

class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=300)

class RunIn(BaseModel):
    event_id: str = Field(pattern=r"^EV-[A-Z]\d+$")

class LoginIn(BaseModel):
    reviewer_id: str = Field(min_length=2, max_length=40); passcode: str = Field(min_length=4, max_length=80)

class DecisionIn(BaseModel):
    note: str = Field(default="", max_length=300)

class ReviewIn(BaseModel):
    decision: Literal["approve", "reject", "edit", "request_more_evidence"]
    note: str = Field(default="", max_length=300); edits: Optional[dict[str, Any]] = None


def create_app(service: Optional[agent.AgentService] = None, world=None, kb=None) -> FastAPI:
    app = FastAPI(title="NASHA Enterprise AI Lab", version="0.2.0",
                  description="SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED. A human-supervised operations agent over synthetic NASHA data.")
    if service is None:
        world = world or W.build_world(1)[0]; kb = kb or knowledge.default_kb(); service = agent.AgentService(world, kb)
    app.state.service, app.state.world, app.state.kb = service, service.rt.world, service.rt.kb

    def err(request, status, code, message):
        rid = getattr(request.state, "request_id", "-")
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "request_id": rid}}, headers={"X-Request-ID": rid})

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or "req-" + uuid.uuid4().hex[:10]
        request.state.request_id = rid; t0 = time.perf_counter()
        try:
            resp = await call_next(request)
        except Exception:
            log.exception(json.dumps({"event": "unhandled", "request_id": rid, "path": request.url.path}))
            return err(request, 500, "INTERNAL_ERROR", "internal error")
        resp.headers["X-Request-ID"] = rid
        log.info(json.dumps({"event": "request", "request_id": rid, "method": request.method, "path": request.url.path, "status": resp.status_code, "ms": round((time.perf_counter() - t0) * 1000, 1)}))
        return resp

    @app.exception_handler(RequestValidationError)
    async def on_validation(request, exc): return err(request, 422, "INVALID_REQUEST", "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())[:300])

    @app.exception_handler(HTTPException)
    async def on_http(request, exc): return err(request, exc.status_code, exc.detail if isinstance(exc.detail, str) and exc.detail.isupper() else "HTTP_ERROR", str(exc.detail))

    def tool(request, name, args, status_map=None):
        ctx = T.ToolContext(run_id="api", request_id=request.state.request_id, kb=app.state.kb)
        res = T.execute(app.state.world, name, args, ctx)
        if not res["ok"]:
            code = res["error"]["code"]; st = {"NOT_FOUND": 404, "INVALID_ARGUMENTS": 422, "TIMEOUT": 504, "REJECTED": 409}.get(code, 502)
            raise _Raise(st, code, res["error"]["message"])
        return res["data"]

    class _Raise(HTTPException):
        def __init__(self, st, code, msg): super().__init__(st, detail=msg); self.code = code

    @app.exception_handler(_Raise)
    async def on_raise(request, exc): return err(request, exc.status_code, exc.code, str(exc.detail))

    error_responses = {404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 502: {"model": ErrorEnvelope}, 504: {"model": ErrorEnvelope}}

    @app.get("/health")
    def health(): return {"status": "ok", "synthetic": True}

    @app.get("/ready")
    def ready(request: Request):
        n = app.state.world.q("SELECT COUNT(*) n FROM fact_order")[0]["n"]
        ok = n > 0 and len(app.state.kb.chunks) > 0
        if not ok: raise _Raise(503, "NOT_READY", "world or knowledge base empty")
        return {"status": "ready", "orders": n, "knowledge_chunks": len(app.state.kb.chunks), "tools_registered": len(T.TOOLS), "mcp_tools": 9}

    @app.get("/events")
    def events(): return {"events": [dict(e, payload=json.loads(e["payload"])) for e in app.state.world.q("SELECT * FROM operational_incidents ORDER BY event_id")]}

    @app.get("/inventory/{ingredient}", responses=error_responses)
    def inventory(request: Request, ingredient: str, location_id: str = Query(pattern=r"^L\d{2}$")): return tool(request, "query_inventory", dict(location_id=location_id, ingredient=ingredient))

    @app.get("/quality/findings", responses=error_responses)
    def findings(request: Request, rule: Optional[str] = None, limit: int = Query(20, ge=1, le=100)): return tool(request, "list_quality_findings", dict(rule=rule, limit=limit))

    @app.get("/quality/findings/{finding_id}", responses=error_responses)
    def finding(request: Request, finding_id: int): return tool(request, "get_quality_finding", dict(finding_id=finding_id))

    @app.post("/knowledge/search", responses=error_responses)
    def k_search(request: Request, body: T.SearchIn): return tool(request, "search_nasha_knowledge", body.model_dump())

    @app.post("/knowledge/ask", responses=error_responses)
    def k_ask(request: Request, body: AskIn): return tool(request, "get_current_policy", dict(question=body.question))

    @app.post("/agent/runs", status_code=201, responses=error_responses)
    def start(request: Request, body: RunIn):
        s = app.state.service.start(body.event_id, request.state.request_id)
        if s["status"] in ("DUPLICATE_IGNORED",): return JSONResponse(status_code=200, content=json.loads(json.dumps(s, default=str)))
        if s["status"].startswith("FAILED"): raise _Raise(404, "UNKNOWN_EVENT", f"no event {body.event_id}")
        return s

    @app.get("/agent/runs/{run_id}", responses=error_responses)
    def get_run(run_id: str):
        s = app.state.service.summary(run_id)
        if s is None: raise _Raise(404, "NOT_FOUND", f"no run {run_id}")
        return s

    def bearer(request):
        h = request.headers.get("Authorization", "")
        return h[7:] if h.lower().startswith("bearer ") else None

    def decide(request, run_id, payload):
        try: return app.state.service.resume(run_id, payload, session=bearer(request))
        except KeyError: raise _Raise(404, "NOT_FOUND", f"no run {run_id}")
        except RuntimeError as e: raise _Raise(409, "NOT_AWAITING_REVIEW", str(e))
        except ID.AuthError as e:
            raise _Raise(403 if e.code in ("ROLE_NOT_PERMITTED",) else 401, e.code, e.message or e.code)

    @app.post("/auth/session", responses=error_responses)
    def login(body: LoginIn):
        try: return {"token": app.state.service.rt.authority.login(body.reviewer_id, body.passcode), "token_type": "bearer"}
        except ID.AuthError as e: raise _Raise(401, e.code, "invalid reviewer id or passcode")

    @app.get("/auth/me", responses=error_responses)
    def me(request: Request):
        try: i = app.state.service.rt.authority.identify(bearer(request)); return {"reviewer_id": i.id, "role": i.role}
        except ID.AuthError as e: raise _Raise(401, e.code, e.message or e.code)

    @app.post("/agent/runs/{run_id}/approve", responses=error_responses)
    def approve(request: Request, run_id: str, body: DecisionIn): return decide(request, run_id, dict(decision="approve", note=body.note))

    @app.post("/agent/runs/{run_id}/reject", responses=error_responses)
    def reject(request: Request, run_id: str, body: DecisionIn): return decide(request, run_id, dict(decision="reject", note=body.note))

    @app.post("/agent/runs/{run_id}/review", responses=error_responses)
    def review(request: Request, run_id: str, body: ReviewIn): return decide(request, run_id, body.model_dump())

    @app.get("/traces/{run_id}", responses=error_responses)
    def trace(run_id: str):
        if app.state.service.store.run(run_id) is None: raise _Raise(404, "NOT_FOUND", f"no run {run_id}")
        return {"run_id": run_id, "events": app.state.service.store.events(run_id)}

    @app.get("/traces/{run_id}/record", responses=error_responses)
    def trace_record(run_id: str):
        from . import experiments
        if app.state.service.store.run(run_id) is None: raise _Raise(404, "NOT_FOUND", f"no run {run_id}")
        return experiments.run_record(app.state.service.store.events(run_id))

    @app.get("/review", include_in_schema=False)
    def review_ui():
        import os
        from fastapi.responses import HTMLResponse
        html = open(os.path.join(os.path.dirname(__file__), "ui", "review.html"), encoding="utf-8").read()
        return HTMLResponse(html, headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'", "X-Content-Type-Options": "nosniff"})

    return app
