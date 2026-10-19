"""Secret-minimizing correlation ledger for offline specialist workflows.

Stores identifiers, event types, and payload digests only. No input/output
bodies, supplier data, free text or access tokens are written to the ledger.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib
import json
import time

@dataclass(frozen=True)
class AuditEvent:
    seq: int
    correlation_id: str
    role: str
    kind: str
    payload_sha256: str
    duration_ms: float

class AuditLedger:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, *, correlation_id: str, role: str, kind: str,
               payload: Any = None, duration_ms: float = 0.0) -> AuditEvent:
        if not correlation_id or not role or not kind:
            raise ValueError("audit identity fields required")
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()
        row=AuditEvent(len(self._events)+1,correlation_id,role,kind,digest,round(duration_ms,3))
        self._events.append(row)
        return row

    def reconstruct(self, correlation_id: str) -> tuple[AuditEvent,...]:
        return tuple(row for row in self._events if row.correlation_id==correlation_id)

    def verify(self, correlation_id: str, *, required: tuple[str,...]) -> bool:
        rows=self.reconstruct(correlation_id)
        if not rows or [r.seq for r in rows]!=sorted(r.seq for r in rows):
            return False
        return all(kind in {r.kind for r in rows} for kind in required)
