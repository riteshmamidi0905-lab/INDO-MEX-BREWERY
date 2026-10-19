"""Read-only cross-system incident reconstruction from NASHA and THE WEIR audit stores.

No policy decision or approval is made here; THE WEIR remains the authority.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Incident:
    correlation_id: str
    events: tuple[dict[str, Any], ...]
    chain_valid: bool
    protected_executions: int
    approvals_consumed: int

def reconstruct(correlation_id: str, *, weir_store: Any, nasha_events: list[dict[str, Any]] | None = None) -> Incident:
    if not isinstance(correlation_id, str) or not correlation_id:
        raise ValueError("correlation_id required")
    valid, _, _ = weir_store.verify_chain()
    if not valid:
        raise RuntimeError("THE WEIR audit chain verification failed")
    events: list[dict[str, Any]] = []
    for event in nasha_events or []:
        if event.get("correlation_id") == correlation_id:
            events.append({"system": "NASHA", **event})
    for event in weir_store.events(session_id=correlation_id):
        events.append({"system": "THE_WEIR", **event})
    events.sort(key=lambda event: (float(event.get("ts", 0)), str(event.get("system"))))
    # Count successful gateway-recorded results and consumed approval events;
    # do not infer execution from an APPROVE decision alone.
    executions = sum(
        1 for event in events if event.get("system") == "THE_WEIR"
        and event.get("kind") == "call.result"
        and not bool(event.get("payload", {}).get("is_error"))\n        and not bool(event.get("payload", {}).get("uncertain"))
    )
    consumed = sum(
        1 for approval in weir_store.list_approvals()
        if approval.session_id == correlation_id and approval.state == "consumed"
    )
    return Incident(correlation_id, tuple(events), True, executions, consumed)
