"""Request and response models (the contract). Responses are typed so the OpenAPI document is complete and contract tests can validate real responses."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


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
    schema_version: int
    synthetic: bool = True


class DevTokenIn(Strict):
    sub: str = Field(pattern=r"^[A-Za-z0-9_.:@-]{1,64}$")
    role: Literal["BUYER", "QUALITY_LEAD", "FOUNDER", "READER", "OPERATOR", "AUDITOR"]
    ttl_s: int = Field(900, ge=1, le=3600)


class TokenOut(BaseModel):
    token: str
    token_type: Literal["bearer"] = "bearer"
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
