"""Conservative triage of near-duplicate findings.

A matching basket and time window alone never establishes transaction identity.
This classifier is deliberately separate from the frozen v1 benchmark.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Candidate:
    order_id: str
    location_id: str
    timestamp: datetime
    basket: tuple

@dataclass(frozen=True)
class Assessment:
    decision: str
    candidates: tuple[str, ...]
    reason: str

def assess(order: Candidate, others: list[Candidate], *, window_seconds: float = 1.0) -> Assessment:
    """No independent transaction identity is available in this dataset.

    The order_id is a row identifier, not a payment/transaction identifier.
    Return review, never a confirmed duplicate, for plausible collisions.
    """
    if not order.order_id or not order.location_id or not isinstance(order.timestamp, datetime):
        return Assessment("REQUIRES_REVIEW", (), "missing required identifier or timestamp")
    if window_seconds < 0:
        raise ValueError("negative window")
    matches = sorted({
        other.order_id for other in others
        if other.order_id and other.order_id != order.order_id
        and other.location_id == order.location_id
        and other.basket == order.basket
        and isinstance(other.timestamp, datetime)
        and abs((other.timestamp - order.timestamp).total_seconds()) <= window_seconds
    })
    if matches:
        return Assessment("REQUIRES_REVIEW", tuple(matches),
                          "basket and timestamp are insufficient to establish transaction identity")
    return Assessment("NO_CANDIDATE", (), "no matching transaction within the window")
