"""Typed NASHA -> THE WEIR gateway adapter.

Requires a real mcp_weir.gateway.Gateway instance already configured with
a pinned policy and a NASHA MCP upstream. This adapter never calls a local
tool implementation, and never treats a pending approval as execution.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time
import uuid

@dataclass(frozen=True)
class WeirResult:
    correlation_id: str
    tool: str
    status: str
    forwarded: bool
    approval_id: str | None
    call_id: str | None
    codes: tuple[str, ...]
    elapsed_ms: float

class WeirAdapter:
    """All calls use THE WEIR's actual Gateway.call_tool_detailed path."""

    def __init__(self, gateway: Any, session: Any, *, allowed_tools: frozenset[str],
                 trace: Any = None):
        if gateway is None or session is None:
            raise ValueError("gateway and session are mandatory; fail closed")
        self.gateway = gateway
        self.session = session
        self.allowed_tools = frozenset(allowed_tools)
        self.trace = trace

    async def invoke(self, tool: str, args: dict[str, Any], *,
                     correlation_id: str | None = None) -> WeirResult:
        correlation_id = correlation_id or str(uuid.uuid4())
        start = time.perf_counter()
        def emit(kind: str, **data: Any) -> None:
            if self.trace is not None:
                self.trace.event(kind, correlation_id=correlation_id, **data)
        if not isinstance(tool, str) or tool not in self.allowed_tools or not isinstance(args, dict):
            emit("weir.decision", tool=str(tool)[:100], status="DENY", reason="UNAUTHORIZED_TOOL")
            return WeirResult(correlation_id, str(tool), "DENY", False, None, None,
                              ("UNAUTHORIZED_TOOL",), (time.perf_counter()-start)*1000)
        # Never catch and re-issue a protected operation. Retries must be explicitly
        # authorized by the caller and use THE WEIR's own approval consumption.
        try:
            outcome = await self.gateway.call_tool_detailed(self.session, tool, args)
            forwarded = bool(outcome.forwarded) and not bool(outcome.result.get("isError"))
            status = "ALLOW" if forwarded else ("APPROVE" if outcome.approval_id else "DENY")
            result = WeirResult(correlation_id, tool, status, forwarded,
                                outcome.approval_id, outcome.call_id,
                                tuple(outcome.codes), (time.perf_counter()-start)*1000)
        except Exception:
            # Avoid leaking exception payloads (which may contain upstream secrets).
            result = WeirResult(correlation_id, tool, "DENY", False, None, None,
                                ("GATEWAY_UNAVAILABLE",), (time.perf_counter()-start)*1000)
        emit("weir.decision", tool=tool, status=result.status, forwarded=result.forwarded,
             call_id=result.call_id, approval_id=result.approval_id, codes=list(result.codes),
             elapsed_ms=round(result.elapsed_ms, 3))
        return result
