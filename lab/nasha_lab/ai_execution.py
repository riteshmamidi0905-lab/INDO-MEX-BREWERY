"""Executable read-only NASHA role handoffs backed by existing typed business tools.

No procurement, marketing publication, or state mutation is performed here.
Protected execution is deliberately unavailable without THE WEIR.
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass
from typing import Any
from . import tools as T

@dataclass(frozen=True)
class StepResult:
    role: str
    tool: str
    ok: bool
    evidence: dict[str, Any] | None
    error_code: str | None
    elapsed_ms: float

@dataclass(frozen=True)
class Execution:
    execution_id: str
    correlation_id: str
    status: str
    steps: tuple[StepResult, ...]
    external_actions: int = 0

def investigate_inventory(world: Any, kb: Any, location_id: str, ingredient: str,
                          *, trace: Any = None, correlation_id: str | None = None) -> Execution:
    """Run SENTINEL and MERIDIAN read-only handoffs against real synthetic data.

    Return a typed result with evidence; no procurement action is executed.
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    execution_id = "nasha-ai-" + uuid.uuid4().hex[:12]
    results: list[StepResult] = []
    ctx = T.ToolContext(run_id=execution_id, request_id=correlation_id, kb=kb, trace=trace)
    def emit(kind: str, **values: Any) -> None:
        if trace is not None:
            trace.event(kind, **dict(values, correlation_id=correlation_id, execution_id=execution_id))
    for role, tool, args in (
        ("SENTINEL", "query_inventory", {"location_id": location_id, "ingredient": ingredient}),
        ("SENTINEL", "assess_inventory_risk", {"location_id": location_id, "ingredient": ingredient}),
        ("MERIDIAN", "get_supplier_status", {"ingredient": ingredient}),
    ):
        start = time.perf_counter()
        try:
            result = T.execute(world, tool, args, ctx)
            ok = bool(result.get("ok"))
            code = None if ok else str(result.get("error", {}).get("code", "UNKNOWN_ERROR"))
            # Only include successful, typed outputs; never log raw business payloads.
            evidence = result.get("data") if ok else None
        except Exception:
            ok, code, evidence = False, "SERVICE_EXCEPTION", None
        elapsed = (time.perf_counter() - start) * 1000
        results.append(StepResult(role, tool, ok, evidence, code, elapsed))
        emit("ai.handoff", role=role, tool=tool, ok=ok, error_code=code,
             elapsed_ms=round(elapsed, 3))
        if not ok:
            break
    status = "READ_ONLY_COMPLETE" if len(results) == 3 and all(s.ok for s in results) else "FAILED_CLOSED"
    emit("ai.final", status=status, external_actions=0, steps=len(results))
    return Execution(execution_id, correlation_id, status, tuple(results))


async def governed_inventory_action(world: Any, kb: Any, location_id: str,
                                    ingredient: str, adapter: Any, *,
                                    action_tool: str, action_args: dict[str, Any],
                                    correlation_id: str | None = None,
                                    trace: Any = None) -> dict[str, Any]:
    """Read-only investigation followed by THE WEIR-mediated protected tool call.

    A pending approval does not execute. Resumption must re-enter this same
    gateway call with an approval consumed by THE WEIR. No direct fallback.
    """
    from .weir_adapter import WeirAdapter
    correlation_id = correlation_id or str(uuid.uuid4())
    investigation = investigate_inventory(world, kb, location_id, ingredient,
                                          trace=trace, correlation_id=correlation_id)
    if investigation.status != "READ_ONLY_COMPLETE":
        return {"status": "DENY", "reason": "INVESTIGATION_INCOMPLETE",
                "correlation_id": correlation_id, "external_actions": 0}
    if not isinstance(adapter, WeirAdapter):
        return {"status": "DENY", "reason": "REAL_GATEWAY_ADAPTER_REQUIRED",
                "correlation_id": correlation_id, "external_actions": 0}
    decision = await adapter.invoke(action_tool, action_args, correlation_id=correlation_id)
    return {"status": decision.status, "forwarded": decision.forwarded,
            "approval_id": decision.approval_id, "call_id": decision.call_id,
            "codes": list(decision.codes), "correlation_id": correlation_id,
            "external_actions": int(decision.forwarded)}
