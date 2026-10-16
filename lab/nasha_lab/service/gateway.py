"""Bridges the service to the lab's tools and agent under the explicit failure policy (ops.failure_policy).

* ToolGateway: read tools run through PolicyRunner, so retries happen ONLY where the policy classes the tool SAFE_TO_RETRY; every attempt is bounded by the
  request deadline; a failure becomes an ApiError whose code and client-retry advice come from the error table.
* BridgedAuthority: lets the already-authenticated JWT principal reach AgentService.resume without a second login (the agent's signed approval grant still
  records the reviewer and still enforces the per-tool role policy)."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from .. import identity as ID, tools as T
from ..ops.failure_policy import Outcome, Policy, PolicyRunner, RetryBudget, classify_failure, load_policy
from ..ops.resilience import CircuitBreaker
from .db import Deadline
from .errors import ApiError
from .obs import Metrics

TOOL_ERROR_MAP: dict[str, str] = {
    "NOT_FOUND": "NOT_FOUND", "INVALID_ARGUMENTS": "INVALID_REQUEST", "REJECTED": "CONFLICT_STATE", "TIMEOUT": "TOOL_TIMEOUT",
    "UPSTREAM_FAILURE": "UPSTREAM_FAILURE", "RETRIEVER_ERROR": "UPSTREAM_FAILURE", "MALFORMED_RESULT": "UPSTREAM_MALFORMED", "CIRCUIT_OPEN": "DEPENDENCY_UNAVAILABLE",
    "DEADLINE": "DEADLINE_EXCEEDED",
}


class BridgedAuthority(ID.Authority):
    def identify(self, session: Any) -> ID.Identity:
        if isinstance(session, ID.Identity): return session
        return super().identify(session)


class _NoStore:
    """PolicyRunner needs a dead-letter sink. Read tools are SAFE_TO_RETRY (no side effects) and never dead-letter, so this refuses loudly if that ever changes."""
    def add_dead_letter(self, **kw: Any) -> dict[str, Any]: raise RuntimeError("a read-only gateway must not dead-letter")


class ToolGateway:
    def __init__(self, world: Any, kb: Any, metrics: Metrics, *, policy: Optional[Policy] = None, clock: Callable[[], float] = time.monotonic,
                 executor: Optional[Callable[..., dict[str, Any]]] = None, timeout_s: float = 2.0) -> None:
        self.world, self.kb, self.metrics, self.timeout_s = world, kb, metrics, timeout_s
        self.policy = policy or load_policy()
        self.budget = RetryBudget(ratio=0.2, min_retries=3)
        self.breaker = CircuitBreaker(3, 10.0, clock=clock)
        self._execute = executor            # test seam; None = tools.execute looked up at call time (so fault injection by monkeypatch works)
        self._lock = threading.Lock()

    def call(self, name: str, args: dict[str, Any], request_id: str, deadline: Deadline) -> tuple[dict[str, Any], int]:
        op = self.policy.tool(name)
        box: dict[str, Any] = {}

        def attempt(n: int) -> Outcome:
            if deadline.remaining() <= 0 or deadline.cancelled: return Outcome(False, None, "DEADLINE", "request deadline passed")
            ctx = T.ToolContext(run_id="api", request_id=request_id, kb=self.kb, timeout_s=max(0.05, min(self.timeout_s, deadline.remaining())))
            fn = self._execute or T.execute
            res: dict[str, Any] = fn(self.world, name, args, ctx)
            box["res"] = res
            return Outcome(bool(res["ok"]), res, None if res["ok"] else res["error"]["code"], "" if res["ok"] else res["error"]["message"])

        def sleep(s: float) -> None: time.sleep(min(s, deadline.remaining()))

        runner = PolicyRunner(self.policy, _NoStore(), self.budget, self.breaker, sleep)        # type: ignore[arg-type]
        rr = runner.run(op, attempt, correlation_id=request_id, args=args, tool=name, breaker_key=name)
        self.metrics.inc("nasha_tool_calls_total", help="tool calls by outcome", tool=name, outcome="ok" if rr.ok else (rr.code or "error"))
        if rr.attempts > 1: self.metrics.inc("nasha_tool_retries_total", rr.attempts - 1, help="tool retries taken under the explicit policy", tool=name)
        if rr.ok: return box["res"]["data"], rr.attempts
        code = rr.code or "UPSTREAM_FAILURE"
        err = (box.get("res") or {}).get("error") or {}
        api_code = TOOL_ERROR_MAP.get(code, "UPSTREAM_FAILURE")
        fc = classify_failure(code, op.side_effects, self.policy)
        msg = str(err.get("message", "tool failed"))[:200] if api_code in ("NOT_FOUND", "INVALID_REQUEST", "CONFLICT_STATE") else f"tool {name} failed ({code})"
        raise ApiError(api_code, msg, retry_after_s=1.0 if api_code in ("TOOL_TIMEOUT", "UPSTREAM_FAILURE", "DEPENDENCY_UNAVAILABLE") else None,
                       details={"tool": name, "attempts": rr.attempts, "policy_failure_class": fc, "policy_actions": rr.actions})
