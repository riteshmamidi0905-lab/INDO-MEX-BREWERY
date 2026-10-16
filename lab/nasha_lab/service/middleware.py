"""Pure-ASGI hardening middleware: request id and trace context, drain on shutdown, body-size and content-type limits, per-IP rate limit, security headers,
access log and metrics, and one last-resort handler so an unexpected exception still produces the error envelope (never a stack trace or a plain-text 500)."""
from __future__ import annotations

import json
import logging
import re
import secrets
import time
from typing import Any, Awaitable, Callable, MutableMapping, Optional

from fastapi import HTTPException

from .errors import ApiError, envelope
from .obs import Hasher, Metrics, Tracer, emit
from .ratelimit import TokenBucketLimiter

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
RID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
PROBES = ("/healthz", "/readyz")
KNOWN_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
SECURITY_HEADERS = [(b"x-content-type-options", b"nosniff"), (b"cache-control", b"no-store"), (b"referrer-policy", b"no-referrer"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"), (b"cross-origin-resource-policy", b"same-origin")]


class _TooLarge(HTTPException):
    def __init__(self) -> None: super().__init__(status_code=413, detail="payload too large")


class Runtime:
    """Mutable facts the middleware needs; owned by the app."""
    def __init__(self, *, max_body: int, ip_limiter: TokenBucketLimiter, metrics: Metrics, tracer: Tracer, log: logging.Logger, hasher: Hasher, proxy_hops: int) -> None:
        self.max_body, self.ip_limiter, self.metrics, self.tracer, self.log, self.hasher, self.proxy_hops = max_body, ip_limiter, metrics, tracer, log, hasher, proxy_hops
        self.draining, self.inflight = False, 0


def client_ip(scope: Scope, hops: int) -> str:
    peer = (scope.get("client") or ("unknown", 0))[0]
    if hops <= 0: return str(peer)
    for k, v in scope.get("headers", []):
        if k == b"x-forwarded-for":
            parts = [p.strip() for p in v.decode("latin-1").split(",") if p.strip()]
            if len(parts) >= hops: return parts[-hops][:64]
    return str(peer)


class HardeningMiddleware:
    def __init__(self, app: Any, rt: Runtime) -> None:
        self.app, self.rt = app, rt

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http": return await self.app(scope, receive, send)
        rt = self.rt; t0 = time.perf_counter()
        hdr = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        rid = hdr.get("x-request-id", "")
        rid = rid if RID_RE.match(rid) else "req-" + secrets.token_hex(8)
        trace_id, span_id, _ = rt.tracer.start(hdr.get("traceparent"))
        scope.setdefault("state", {})["request_id"] = rid
        scope["state"]["trace_id"] = trace_id
        path = scope["path"]; state: dict[str, Any] = {"status": 500, "started": False}
        ip = client_ip(scope, rt.proxy_hops)
        out_headers = [(b"x-request-id", rid.encode()), (b"traceparent", f"00-{trace_id}-{span_id}-01".encode())] + SECURITY_HEADERS

        async def send_wrapped(msg: MutableMapping[str, Any]) -> None:
            if msg["type"] == "http.response.start":
                state["status"], state["started"] = msg["status"], True
                msg = dict(msg); have = {k.lower() for k, _ in msg.get("headers", [])}
                msg["headers"] = list(msg.get("headers", [])) + [h for h in out_headers if h[0] not in have]
            await send(msg)

        async def reply(err: ApiError) -> None:
            body = json.dumps(envelope(err.code, err.message, rid, details=err.details, retry_after_s=err.retry_after_s)).encode()
            h = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
            if err.retry_after_s is not None: h.append((b"retry-after", str(max(1, int(err.retry_after_s + 0.999))).encode()))
            await send_wrapped({"type": "http.response.start", "status": err.status, "headers": h})
            await send_wrapped({"type": "http.response.body", "body": body})

        received = 0

        async def limited_receive() -> MutableMapping[str, Any]:
            nonlocal received
            m = await receive()
            if m["type"] == "http.request":
                received += len(m.get("body", b""))
                if received > rt.max_body: raise _TooLarge()
            return m

        rt.inflight += 1
        try:
            err: Optional[ApiError] = None
            if rt.draining and path not in PROBES: err = ApiError("SHUTTING_DOWN", "the service is shutting down", retry_after_s=2.0)
            elif path not in PROBES:
                ok, wait = rt.ip_limiter.take(ip)
                if not ok:
                    rt.metrics.inc("nasha_rate_limited_total", help="requests refused by the rate limiter", scope="ip")
                    err = ApiError("RATE_LIMITED", "too many requests from this address", retry_after_s=max(wait, 0.001))
            if err is None:
                cl = hdr.get("content-length")
                if cl is not None and not cl.isdigit(): err = ApiError("MALFORMED_BODY", "invalid Content-Length")
                elif cl is not None and int(cl) > rt.max_body: err = ApiError("PAYLOAD_TOO_LARGE", f"request body exceeds {rt.max_body} bytes")
                elif scope["method"] in ("POST", "PUT", "PATCH") and (int(cl or 0) > 0 or "transfer-encoding" in hdr) and not hdr.get("content-type", "").lower().startswith("application/json"):
                    err = ApiError("UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json")
            if err is not None: await reply(err)
            else:
                try:
                    await self.app(scope, limited_receive, send_wrapped)
                except _TooLarge:
                    if not state["started"]: await reply(ApiError("PAYLOAD_TOO_LARGE", f"request body exceeds {rt.max_body} bytes"))
                except Exception as e:                                   # last resort: never leak details
                    tb = e.__traceback__
                    while tb is not None and tb.tb_next is not None: tb = tb.tb_next
                    where = f"{tb.tb_frame.f_code.co_filename.rsplit('/', 1)[-1]}:{tb.tb_lineno}:{tb.tb_frame.f_code.co_name}" if tb else None      # location only, never values
                    emit(rt.log, logging.ERROR, "unhandled_exception", request_id=rid, trace_id=trace_id, method=scope["method"], kind=type(e).__name__, where=where)
                    if not state["started"]: await reply(ApiError("INTERNAL_ERROR", "internal error"))
        finally:
            rt.inflight -= 1
            route = getattr(scope.get("route"), "path", None) or "unmatched"
            dur = time.perf_counter() - t0; status = state["status"]
            method = scope["method"] if scope["method"] in KNOWN_METHODS else "OTHER"          # client-chosen method tokens must not create metric series
            rt.metrics.inc("nasha_http_requests_total", help="HTTP requests", method=method, route=route, status=status)
            rt.metrics.observe("nasha_http_request_duration_seconds", dur, help="HTTP request latency in seconds", method=method, route=route)
            if status >= 400: rt.metrics.inc("nasha_http_errors_total", help="HTTP error responses", status=status)
            emit(rt.log, logging.INFO if status < 500 else logging.ERROR, "request", request_id=rid, trace_id=trace_id, span_id=span_id, method=method, route=route, status=status,
                 ms=round(dur * 1000, 2), principal=scope["state"].get("principal_hash"), ip_hash=rt.hasher(ip), code=scope["state"].get("error_code"))
