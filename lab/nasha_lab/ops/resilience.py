"""Resilience primitives (P2: GAP-01 timeouts/retries/backoff with idempotency, GAP-04 retriever fallback, GAP-10 rate limiting).
SYNTHETIC / SIMULATED. Pure, clock-injectable, seeded, so every behaviour is testable without sleeping."""
import json
import random
import time
from dataclasses import dataclass

TRANSIENT_CODES = ("TIMEOUT", "UPSTREAM_FAILURE")


@dataclass
class RetryPolicy:
    """Bounded exponential backoff with seeded jitter. delay(n) is the sleep BEFORE attempt n+1 (n = attempts already made)."""
    max_attempts: int = 3; base_ms: float = 20.0; factor: float = 2.0; max_ms: float = 200.0; jitter: float = 0.25; seed: int = 0
    retry_on: tuple = TRANSIENT_CODES

    def delay(self, attempts_made, rng=None):
        rng = rng or random.Random(self.seed * 1000 + attempts_made)
        d = min(self.max_ms, self.base_ms * self.factor ** (attempts_made - 1))
        return round(d * (1 + self.jitter * (2 * rng.random() - 1)), 3)

    def schedule(self):
        """The nominal (jittered) sleeps in milliseconds between attempts, for documentation and tests."""
        return [self.delay(n) for n in range(1, self.max_attempts)]


class CircuitBreaker:
    """Per-key breaker: CLOSED -> OPEN after `threshold` consecutive failures -> HALF_OPEN after `reset_s` (one probe) -> CLOSED on success."""
    def __init__(self, threshold=3, reset_s=5.0, clock=time.monotonic):
        self.threshold, self.reset_s, self.clock = threshold, reset_s, clock
        self.fails, self.opened_at, self.probe = {}, {}, {}

    def state(self, key):
        if key in self.opened_at:
            return "HALF_OPEN" if self.clock() - self.opened_at[key] >= self.reset_s else "OPEN"
        return "CLOSED"

    def allow(self, key):
        s = self.state(key)
        if s == "CLOSED": return True
        if s == "HALF_OPEN" and not self.probe.get(key): self.probe[key] = True; return True
        return False

    def record(self, key, ok):
        if ok:
            self.fails[key] = 0; self.opened_at.pop(key, None); self.probe.pop(key, None); return
        self.fails[key] = self.fails.get(key, 0) + 1
        if self.fails[key] >= self.threshold or key in self.probe:
            self.opened_at[key] = self.clock(); self.probe.pop(key, None)


def call_with_retry(fn, policy: RetryPolicy, *, is_failure, sleep=time.sleep, breaker=None, key="k"):
    """Generic bounded retry. fn() -> result; is_failure(result) -> error code or None.
    Returns (result, attempts, sleeps_ms, circuit_open). A circuit breaker (optional) short-circuits without calling fn."""
    sleeps, attempts = [], 0
    while True:
        if breaker is not None and not breaker.allow(key): return None, attempts, sleeps, True
        attempts += 1; result = fn(); code = is_failure(result)
        if breaker is not None: breaker.record(key, code is None)
        if code is None or code not in policy.retry_on or attempts >= policy.max_attempts: return result, attempts, sleeps, False
        d = policy.delay(attempts); sleeps.append(d); sleep(d / 1000.0)


def existing_draft(world, run_id, kind, payload):
    """Reconcile a draft after an AMBIGUOUS failure (the call timed out but may have committed): has the same draft (run, kind, exact payload) already been stored?"""
    want = json.dumps(payload, default=str)
    for r in world.q("SELECT draft_id, payload FROM drafts WHERE run_id=? AND kind=?", run_id, kind):
        if r["payload"] == want: return r["draft_id"]
    return None


# --------------------------------------------------------------------------------------------------- GAP-04: retriever fallback
class ResilientKB:
    """Wraps a KnowledgeBase. If the configured (hybrid) retriever raises, answer from the LEXICAL retriever (BM25) instead: bounded retries first, a breaker
    so a dead retriever is not hammered, and every degradation is recorded in `events`. The status-aware answer logic (abstain, non-authoritative exclusion,
    injection scan) is the SAME code path: only the candidate generator changes, so authority rules are not bypassed."""
    def __init__(self, kb, policy=None, breaker=None, sleep=time.sleep, fallback="bm25"):
        self._kb, self.sleep, self.fallback = kb, sleep, fallback
        self.policy = policy or RetryPolicy(max_attempts=2, base_ms=5, max_ms=20, retry_on=("RETRIEVER_ERROR",))
        self.breaker = breaker or CircuitBreaker(2, 30.0)
        self.events = []; self.mode = "primary"

    def __getattr__(self, name): return getattr(self._kb, name)

    def _try(self, method, *a, **kw):
        def fn():
            try: return getattr(self._kb, method)(*a, **kw)
            except Exception as e: return _Err(f"{type(e).__name__}: {e}"[:160])
        res, attempts, _sleeps, open_ = call_with_retry(fn, self.policy, is_failure=lambda r: "RETRIEVER_ERROR" if isinstance(r, _Err) else None, sleep=self.sleep, breaker=self.breaker, key="retriever")
        if open_ or isinstance(res, _Err):
            self.events.append(dict(kind="retriever_fallback", from_retriever=self._kb.default, to=self.fallback, reason="circuit_open" if open_ else res.msg, attempts=attempts)); self.mode = "fallback"
            out = getattr(self._kb, method)(*a, **dict(kw, retriever=self.fallback))
            return dict(out, retriever_fallback=self.fallback) if method == "ask" else out
        self.mode = "primary"; return res

    def ask(self, question, **kw): return self._try("ask", question, **kw)
    def search(self, query, **kw): return self._try("search", query, **kw)


class _Err:
    def __init__(self, msg): self.msg = msg


# --------------------------------------------------------------------------------------------------- GAP-10: rate limiting
class RateLimiter:
    """Token bucket per client key. Clock-injectable. `capacity` tokens, refilled at `refill_per_s`."""
    def __init__(self, capacity=20, refill_per_s=10.0, clock=time.monotonic):
        self.capacity, self.refill, self.clock, self.b = capacity, refill_per_s, clock, {}

    def take(self, key, cost=1.0):
        now = self.clock(); tokens, last = self.b.get(key, (float(self.capacity), now))
        tokens = min(self.capacity, tokens + (now - last) * self.refill)
        if tokens >= cost: self.b[key] = (tokens - cost, now); return True, 0.0
        self.b[key] = (tokens, now); return False, round((cost - tokens) / self.refill, 3)


class RateLimitMiddleware:
    """Pure-ASGI middleware. Answers 429 with the lab's error envelope and Retry-After. /health and /ready are exempt (probes must not be throttled).
    Client key = X-Client-Id header, else the peer address. NOT a DoS defence: in-process, per-instance state, no distributed limit, trusting a client-supplied id."""
    EXEMPT = ("/health", "/ready")

    def __init__(self, app, limiter: RateLimiter, on_limit=None):
        self.app, self.limiter, self.on_limit = app, limiter, on_limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] in self.EXEMPT: return await self.app(scope, receive, send)
        hdr = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        key = hdr.get("x-client-id") or (scope.get("client") or ("anon", 0))[0]
        ok, wait = self.limiter.take(key)
        if ok: return await self.app(scope, receive, send)
        if self.on_limit: self.on_limit(key, scope["path"])
        body = json.dumps({"error": {"code": "RATE_LIMITED", "message": f"too many requests; retry after {wait}s", "request_id": hdr.get("x-request-id", "")}}).encode()
        await send({"type": "http.response.start", "status": 429, "headers": [(b"content-type", b"application/json"), (b"retry-after", str(max(1, int(wait + 0.999))).encode()), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


def with_rate_limit(app, limiter=None, on_limit=None):
    """Wrap an existing FastAPI app (api.create_app) WITHOUT modifying api.py; returns the wrapped ASGI app."""
    return RateLimitMiddleware(app, limiter or RateLimiter(), on_limit)
