"""One error envelope and a stable error-code table. The table is a contract: tests/snapshots/p5_error_codes.json pins it.

Every code carries its HTTP status, the failure class from ops.failure_policy it maps to, and what a client may do next (`client_retry`):
  never | after_retry_after | same_idempotency_key | reconcile_first | after_human_review"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ErrorSpec:
    status: int
    failure_class: str      # one of ops.failure_policy.FAILURE_CLASSES
    client_retry: str


ERROR_TABLE: dict[str, ErrorSpec] = {
    "AUTH_REQUIRED": ErrorSpec(401, "AUTH", "never"),
    "AUTH_INVALID_TOKEN": ErrorSpec(401, "AUTH", "never"),
    "AUTH_TOKEN_EXPIRED": ErrorSpec(401, "AUTH", "never"),
    "FORBIDDEN": ErrorSpec(403, "AUTH", "never"),
    "ROLE_NOT_PERMITTED": ErrorSpec(403, "AUTH", "never"),
    "NOT_FOUND": ErrorSpec(404, "PERMANENT", "never"),
    "ROUTE_NOT_FOUND": ErrorSpec(404, "PERMANENT", "never"),
    "METHOD_NOT_ALLOWED": ErrorSpec(405, "VALIDATION", "never"),
    "MALFORMED_BODY": ErrorSpec(400, "VALIDATION", "never"),
    "INVALID_REQUEST": ErrorSpec(422, "VALIDATION", "never"),
    "UNSUPPORTED_MEDIA_TYPE": ErrorSpec(415, "VALIDATION", "never"),
    "PAYLOAD_TOO_LARGE": ErrorSpec(413, "VALIDATION", "never"),
    "IDEMPOTENCY_KEY_REQUIRED": ErrorSpec(400, "VALIDATION", "never"),
    "IDEMPOTENCY_KEY_INVALID": ErrorSpec(400, "VALIDATION", "never"),
    "IDEMPOTENCY_KEY_REUSED": ErrorSpec(422, "VALIDATION", "never"),
    "IDEMPOTENCY_BUSY": ErrorSpec(409, "TRANSIENT", "same_idempotency_key"),
    "CONFLICT_STATE": ErrorSpec(409, "VALIDATION", "never"),
    "EVENT_ALREADY_PROCESSED": ErrorSpec(409, "VALIDATION", "never"),
    "RUN_NOT_RESUMABLE": ErrorSpec(409, "PERMANENT", "never"),
    "UNKNOWN_EVENT": ErrorSpec(404, "PERMANENT", "never"),
    "RATE_LIMITED": ErrorSpec(429, "RATE_LIMIT", "after_retry_after"),
    "DEADLINE_EXCEEDED": ErrorSpec(504, "TIMEOUT_AMBIGUOUS", "same_idempotency_key"),
    "TOOL_TIMEOUT": ErrorSpec(504, "TIMEOUT_AMBIGUOUS", "after_retry_after"),
    "UPSTREAM_FAILURE": ErrorSpec(502, "TRANSIENT", "after_retry_after"),
    "UPSTREAM_MALFORMED": ErrorSpec(502, "MALFORMED_RESULT", "never"),
    "DEPENDENCY_UNAVAILABLE": ErrorSpec(503, "DEPENDENCY_DOWN", "after_retry_after"),
    "DB_UNAVAILABLE": ErrorSpec(503, "DEPENDENCY_DOWN", "after_retry_after"),
    "DB_TIMEOUT": ErrorSpec(504, "TIMEOUT_AMBIGUOUS", "same_idempotency_key"),
    "DB_POOL_EXHAUSTED": ErrorSpec(503, "DEPENDENCY_DOWN", "after_retry_after"),
    "SCHEMA_MISMATCH": ErrorSpec(503, "DEPENDENCY_DOWN", "never"),
    "NOT_READY": ErrorSpec(503, "DEPENDENCY_DOWN", "after_retry_after"),
    "SHUTTING_DOWN": ErrorSpec(503, "DEPENDENCY_DOWN", "after_retry_after"),
    "DECISION_AMBIGUOUS": ErrorSpec(500, "TIMEOUT_AMBIGUOUS", "after_human_review"),
    "INTERNAL_ERROR": ErrorSpec(500, "PERMANENT", "never"),
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, *, retry_after_s: Optional[float] = None, details: Optional[Mapping[str, Any]] = None, status: Optional[int] = None) -> None:
        super().__init__(f"{code}: {message}")
        if code not in ERROR_TABLE: raise KeyError(f"unregistered error code {code}")
        self.code, self.message, self.retry_after_s, self.details = code, message, retry_after_s, dict(details or {})
        self.status = status or ERROR_TABLE[code].status

    @property
    def spec(self) -> ErrorSpec: return ERROR_TABLE[self.code]


def envelope(code: str, message: str, request_id: str, *, details: Optional[Mapping[str, Any]] = None, retry_after_s: Optional[float] = None) -> dict[str, Any]:
    spec = ERROR_TABLE[code]
    err: dict[str, Any] = {"code": code, "message": message, "request_id": request_id, "failure_class": spec.failure_class, "client_retry": spec.client_retry}
    if retry_after_s is not None: err["retry_after_s"] = round(retry_after_s, 3)
    if details: err["details"] = dict(details)
    return {"error": err}


def error_table_snapshot() -> dict[str, dict[str, Any]]:
    return {c: {"status": s.status, "failure_class": s.failure_class, "client_retry": s.client_retry} for c, s in sorted(ERROR_TABLE.items())}
