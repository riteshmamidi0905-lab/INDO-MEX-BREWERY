"""SQL access for run state, approvals, audit log, idempotency keys and dead letters. Plain functions over a psycopg connection so the caller owns the transaction
(atomicity is decided by the route, not hidden here). Parameters are always bound, never formatted into SQL."""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Optional

import psycopg
from psycopg.types.json import Jsonb

from .. import tools as T
from ..ops.failure_policy import HINTS, REPLAY
from .errors import ApiError

Conn = "psycopg.Connection[dict[str, Any]]"
Row = dict[str, Any]


def jsonable(x: Any) -> Any: return json.loads(json.dumps(x, default=str))


# ------------------------------------------------------------------------------------------------ schema
def schema_version(c: "psycopg.Connection[dict[str, Any]]") -> int:
    r = c.execute("SELECT to_regclass('schema_migrations') IS NOT NULL AS ok").fetchone()
    if not r or not r["ok"]: return 0
    r = c.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
    return int(r["v"]) if r else 0


# ------------------------------------------------------------------------------------------------ idempotency
def request_hash(method: str, route: str, params: dict[str, Any], body: Any) -> str:
    return hashlib.sha256(json.dumps({"m": method, "r": route, "p": params, "b": body}, sort_keys=True, default=str).encode()).hexdigest()


def idem_lock(c: "psycopg.Connection[dict[str, Any]]", principal: str, key: str) -> None:
    """Serialise concurrent requests with the same (principal, key): the second blocks (bounded by lock_timeout) until the first commits, then sees its stored response."""
    c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"{principal}|{key}",))


def idem_get(c: "psycopg.Connection[dict[str, Any]]", principal: str, key: str, route: str, rhash: str) -> Optional[tuple[int, Any]]:
    r = c.execute("SELECT route, request_hash, response_status, response_body FROM idempotency_keys WHERE principal=%s AND key=%s AND expires_at > now()", (principal, key)).fetchone()
    if r is None: return None
    if r["request_hash"] != rhash or r["route"] != route:
        raise ApiError("IDEMPOTENCY_KEY_REUSED", "this Idempotency-Key was already used with a different request")
    return int(r["response_status"]), r["response_body"]


def idem_put(c: "psycopg.Connection[dict[str, Any]]", principal: str, key: str, route: str, rhash: str, status: int, body: Any, ttl_s: int) -> None:
    c.execute("""INSERT INTO idempotency_keys(principal, key, route, request_hash, response_status, response_body, expires_at)
                 VALUES (%s,%s,%s,%s,%s,%s, now() + make_interval(secs => %s))
                 ON CONFLICT (principal, key) DO UPDATE SET route=EXCLUDED.route, request_hash=EXCLUDED.request_hash, response_status=EXCLUDED.response_status,
                 response_body=EXCLUDED.response_body, created_at=now(), expires_at=EXCLUDED.expires_at WHERE idempotency_keys.expires_at <= now()""",
              (principal, key, route, rhash, status, Jsonb(jsonable(body)), ttl_s))


def idem_purge(c: "psycopg.Connection[dict[str, Any]]") -> int:
    return c.execute("DELETE FROM idempotency_keys WHERE expires_at <= now()").rowcount


# ------------------------------------------------------------------------------------------------ runs and approvals
def insert_run(c: "psycopg.Connection[dict[str, Any]]", *, run_id: str, event_id: str, owner: str, request_id: str, summary: dict[str, Any]) -> None:
    c.execute("INSERT INTO runs(run_id, event_id, owner, status, awaiting_human, request_id, summary) VALUES (%s,%s,%s,%s,%s,%s,%s)",
              (run_id, event_id, owner, summary["status"], bool(summary.get("awaiting_human")), request_id, Jsonb(jsonable(summary))))


def update_run(c: "psycopg.Connection[dict[str, Any]]", run_id: str, summary: dict[str, Any]) -> None:
    c.execute("UPDATE runs SET status=%s, awaiting_human=%s, summary=%s, updated_at=now() WHERE run_id=%s", (summary["status"], bool(summary.get("awaiting_human")), Jsonb(jsonable(summary)), run_id))


def get_run(c: "psycopg.Connection[dict[str, Any]]", run_id: str, *, lock: bool = False) -> Optional[Row]:
    return c.execute("SELECT * FROM runs WHERE run_id=%s" + (" FOR UPDATE" if lock else ""), (run_id,)).fetchone()


def get_run_by_event(c: "psycopg.Connection[dict[str, Any]]", event_id: str) -> Optional[Row]:
    return c.execute("SELECT * FROM runs WHERE event_id=%s AND status NOT IN ('FAILED','DUPLICATE_IGNORED') LIMIT 1", (event_id,)).fetchone()


def list_runs(c: "psycopg.Connection[dict[str, Any]]", *, owner: Optional[str], limit: int, before: Optional[str]) -> list[Row]:
    q, a = "SELECT * FROM runs WHERE true", []
    if owner is not None: q += " AND owner=%s"; a.append(owner)
    if before is not None: q += " AND created_at < (SELECT created_at FROM runs WHERE run_id=%s)"; a.append(before)
    return c.execute(q + " ORDER BY created_at DESC, run_id DESC LIMIT %s", (*a, limit)).fetchall()


def insert_approval(c: "psycopg.Connection[dict[str, Any]]", *, run_id: str, decision: str, reviewer: str, role: str, note: str, result_status: str, request_id: str) -> None:
    c.execute("INSERT INTO approvals(run_id, decision, reviewer, role, note, result_status, request_id) VALUES (%s,%s,%s,%s,%s,%s,%s)", (run_id, decision, reviewer, role, note, result_status, request_id))


def count_approvals(c: "psycopg.Connection[dict[str, Any]]", run_id: str) -> int:
    r = c.execute("SELECT count(*) AS n FROM approvals WHERE run_id=%s", (run_id,)).fetchone()
    return int(r["n"]) if r else 0


# ------------------------------------------------------------------------------------------------ audit
def audit(c: "psycopg.Connection[dict[str, Any]]", *, request_id: str, principal_hash: str, action: str, resource: str, outcome: str, detail: Optional[dict[str, Any]] = None) -> None:
    c.execute("INSERT INTO audit_log(request_id, principal_hash, action, resource, outcome, detail) VALUES (%s,%s,%s,%s,%s,%s)",
              (request_id, principal_hash, action, resource, outcome, Jsonb(jsonable(T.redact(detail or {})))))


def list_audit(c: "psycopg.Connection[dict[str, Any]]", limit: int) -> list[Row]:
    return c.execute("SELECT audit_id, at, request_id, principal_hash, action, resource, outcome, detail FROM audit_log ORDER BY audit_id DESC LIMIT %s", (limit,)).fetchall()


# ------------------------------------------------------------------------------------------------ dead letters
def dead_letter_record(*, correlation_id: str, run_id: str, operation: str, tool: Optional[str], op_class: str, failure_code: Optional[str], failure_class: str,
                       attempts: int, reason: str, args: Optional[dict[str, Any]]) -> Row:
    """Same identity and replay instructions as ops.failure_policy.OpsStore: replaying the same failure converges to one record."""
    h = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:16]
    dl = "DL-" + hashlib.sha256(f"{correlation_id}|{operation}|{tool}|{h}".encode()).hexdigest()[:10]
    hint = HINTS.get(tool or operation, "inspect the target state for this operation")
    return dict(dl_id=dl, correlation_id=correlation_id, run_id=run_id, operation=operation, tool=tool, op_class=op_class, failure_code=failure_code, failure_class=failure_class,
                attempts=attempts, reason=reason[:300], args_hash=h, args_json=jsonable(T.redact(args or {})), replay_instructions=REPLAY[op_class].format(hint=hint, h=h))


def insert_dead_letter(c: "psycopg.Connection[dict[str, Any]]", r: Row) -> Row:
    c.execute("""INSERT INTO dead_letters(dl_id, correlation_id, run_id, operation, tool, op_class, failure_code, failure_class, attempts, reason, args_hash, args_json, replay_instructions)
                 VALUES (%(dl_id)s,%(correlation_id)s,%(run_id)s,%(operation)s,%(tool)s,%(op_class)s,%(failure_code)s,%(failure_class)s,%(attempts)s,%(reason)s,%(args_hash)s,%(args_json)s,%(replay_instructions)s)
                 ON CONFLICT (dl_id) DO UPDATE SET attempts=EXCLUDED.attempts, reason=EXCLUDED.reason""", dict(r, args_json=Jsonb(r["args_json"])))
    return r


def list_dead_letters(c: "psycopg.Connection[dict[str, Any]]", status: str, limit: int) -> list[Row]:
    return c.execute("SELECT * FROM dead_letters WHERE status=%s ORDER BY created_at, dl_id LIMIT %s", (status, limit)).fetchall()


def resolve_dead_letter(c: "psycopg.Connection[dict[str, Any]]", dl_id: str, status: str, note: str, by: str) -> Optional[Row]:
    return c.execute("UPDATE dead_letters SET status=%s, resolution=%s, resolved_by=%s WHERE dl_id=%s AND status='OPEN' RETURNING *", (status, note, by, dl_id)).fetchone()


def dead_letter_counts(c: "psycopg.Connection[dict[str, Any]]") -> dict[str, int]:
    return {r["status"]: int(r["n"]) for r in c.execute("SELECT status, count(*) AS n FROM dead_letters GROUP BY status").fetchall()}


class Spool:
    """Append-only JSONL fallback for dead letters when the database itself is the failure. Replayed (idempotently, keyed by dl_id) once the database is back."""
    def __init__(self, directory: str) -> None:
        self.path = os.path.join(directory, "dead-letter-spool.jsonl")

    def append(self, r: Row) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f: f.write(json.dumps(dict(r, spooled_at=time.time()), default=str, sort_keys=True) + "\n")

    def drain(self, c: "psycopg.Connection[dict[str, Any]]") -> int:
        if not os.path.exists(self.path): return 0
        n = 0
        with open(self.path, encoding="utf-8") as f: lines = [x for x in f.read().splitlines() if x.strip()]
        for line in lines:
            r = json.loads(line); r.pop("spooled_at", None); insert_dead_letter(c, r); n += 1
        return n

    def clear(self) -> None:
        if os.path.exists(self.path): os.replace(self.path, self.path + ".replayed")
