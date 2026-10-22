"""Request and response models (the contract). Responses are typed so the OpenAPI document is complete and contract tests can validate real responses."""
from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class Strict(BaseModel):
    """Request bodies: unknown fields are refused, and free text may not carry control characters (NUL cannot be stored in PostgreSQL text, and the others only help log forging)."""
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def _no_control_chars(cls, v: Any) -> Any:
        if isinstance(v, str) and CONTROL_RE.search(v): raise ValueError("control characters are not allowed")
        return v


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    failure_class: str
    client_retry: str
    retry_after_s: Optional[float] = None
    details: Optional[dict[str, Any]] = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class Live(BaseModel):
    status: Literal["ok"]
    synthetic: bool = True


class CheckResult(BaseModel):
    ok: bool
    detail: str = ""


class Ready(BaseModel):
    status: Literal["ready"]
    checks: dict[str, CheckResult]
    synthetic: bool = True


class DevTokenIn(Strict):
    sub: str = Field(pattern=r"^[A-Za-z0-9_.:@-]{1,64}$")
    role: Literal["BUYER", "QUALITY_LEAD", "FOUNDER", "READER", "OPERATOR", "AUDITOR"]
    ttl_s: int = Field(900, ge=1, le=3600)


class TokenOut(BaseModel):
    token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  (OAuth token-type label, not a secret)
    expires_in: int


class RunStartIn(Strict):
    event_id: str = Field(pattern=r"^EV-[A-Z]\d+$")


class DecisionIn(Strict):
    note: str = Field(default="", max_length=300)


class RunView(BaseModel):
    run_id: str
    event_id: str
    status: str
    awaiting_human: bool
    proposal: Optional[dict[str, Any]] = None
    final: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str
    reconciled: bool = False


class RunList(BaseModel):
    runs: list[RunView]
    next_before: Optional[str] = None


class ToolData(BaseModel):
    data: dict[str, Any]
    attempts: int


class AskIn(Strict):
    question: str = Field(min_length=3, max_length=300)


class EventOut(BaseModel):
    event_id: str
    payload: dict[str, Any]


class EventList(BaseModel):
    events: list[EventOut]


class DeadLetterView(BaseModel):
    dl_id: str
    created_at: str
    correlation_id: str
    run_id: str
    operation: str
    tool: Optional[str] = None
    op_class: str
    failure_code: Optional[str] = None
    failure_class: str
    attempts: int
    reason: str
    status: str
    replay_instructions: str
    resolution: Optional[str] = None


class DeadLetterList(BaseModel):
    dead_letters: list[DeadLetterView]


class ResolveIn(Strict):
    status: Literal["ALREADY_APPLIED", "REPLAYED", "DISCARDED"]
    note: str = Field(min_length=3, max_length=300)


class AuditEntry(BaseModel):
    audit_id: int
    at: str
    request_id: str
    principal_hash: str
    action: str
    resource: str
    outcome: str
    detail: dict[str, Any]


class AuditList(BaseModel):
    entries: list[AuditEntry]
