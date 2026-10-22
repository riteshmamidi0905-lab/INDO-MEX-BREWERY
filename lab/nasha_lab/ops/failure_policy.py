"""Explicit failure / retry policy (owner decision: retry and fallback are NOT a universal default). SYNTHETIC / SIMULATED / OFFLINE.
Every operation is classified into exactly one of five classes (lab/ops/failure-policy.json); every failure into one of eight failure classes;
`decide()` maps (operation class x failure class) to one of four actions. Unclassified operations fail closed (DO_NOT_RETRY).
Reuses resilience.RetryPolicy (backoff + seeded jitter) and resilience.CircuitBreaker."""
import hashlib
import json
import os
import random
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .. import tools as T
from . import telemetry as TM
from .hardening import Migrator
from .resilience import CircuitBreaker, RetryPolicy, existing_draft
from .util import OPS_DIR, load_json

POLICY_PATH = os.path.join(OPS_DIR, "failure-policy.json")
OP_CLASSES = ("SAFE_TO_RETRY", "SAFE_WITH_IDEMPOTENCY_KEY", "RECONCILE_BEFORE_RETRY", "DO_NOT_RETRY", "HUMAN_REVIEW_REQUIRED")
FAILURE_CLASSES = ("TRANSIENT", "TIMEOUT_AMBIGUOUS", "RATE_LIMIT", "DEPENDENCY_DOWN", "VALIDATION", "AUTH", "PERMANENT", "MALFORMED_RESULT")
ACTIONS = ("RETRY", "RECONCILE_THEN_RETRY", "FAIL_FAST", "DEAD_LETTER")
HEALTH_CLASSES = ("TRANSIENT", "TIMEOUT_AMBIGUOUS", "DEPENDENCY_DOWN")      # failures that say something about the dependency's health (breaker input)


# ------------------------------------------------------------------------------------------------ policy file
@dataclass
class Op:
    name: str; klass: str; side_effects: bool; max_attempts: int = 3; retry_malformed: bool = False; reconciler: Optional[str] = None; breaker: bool = False
    classified: bool = True; rationale: str = ""


class Policy:
    def __init__(self, cfg=None):
        self.cfg = cfg or load_json(POLICY_PATH)
        self.table = self.cfg["decision_table"]
        for k in OP_CLASSES:
            miss = set(FAILURE_CLASSES) - set(self.table.get(k, {}))
            if miss: raise ValueError(f"decision table incomplete for {k}: {sorted(miss)}")
            bad = set(self.table[k].values()) - set(ACTIONS)
            if bad: raise ValueError(f"unknown action(s) {bad}")

    def op(self, name) -> Op:
        o = self.cfg["operations"].get(name)
        if o is None: return Op(name, "DO_NOT_RETRY", True, 1, classified=False, rationale="unclassified operation: fail closed")
        return Op(name, o["class"], o["side_effects"], o.get("max_attempts", 3), o.get("retry_malformed", False), o.get("reconciler"), o.get("breaker", False), True, o.get("rationale", ""))

    def tool(self, name) -> Op:
        o = self.cfg["tools"].get(name)
        if o is None: return Op(name, "DO_NOT_RETRY", True, 1, classified=False, rationale="unclassified tool: fail closed")
        return Op(name, o["class"], o["side_effects"], 3, False, o.get("reconciler"), True, True, o.get("rationale", ""))

    def retry_policy(self, op: Op, seed=0) -> RetryPolicy:
        d = self.cfg["retry_defaults"]
        return RetryPolicy(max_attempts=op.max_attempts, base_ms=d["base_ms"], factor=d["factor"], max_ms=d["max_ms"], jitter=d["jitter"], seed=seed, retry_on=())


def load_policy(path=POLICY_PATH): return Policy(load_json(path))


# ------------------------------------------------------------------------------------------------ classification
def classify_failure(code, side_effects, policy=None):
    """Error code -> failure class. TIMEOUT is ambiguous only if the operation has side effects. Unknown codes: ambiguous if side effects, else permanent."""
    m = (policy or _default()).cfg["error_code_map"]
    if code is None: return "PERMANENT"
    if str(code).startswith("AUTH_") or str(code) in ("EXPIRED", "FORBIDDEN"): return "AUTH"
    v = m.get(code)
    if v is None: return "TIMEOUT_AMBIGUOUS" if side_effects else "PERMANENT"
    if v == "TIMEOUT_AMBIGUOUS_IF_SIDE_EFFECTS_ELSE_TRANSIENT": return "TIMEOUT_AMBIGUOUS" if side_effects else "TRANSIENT"
    return v


_DEF = []
def _default():
    if not _DEF: _DEF.append(load_policy())
    return _DEF[0]


@dataclass
class Decision:
    action: str; reason: str; may_retry: bool = False        # may_retry: for RECONCILE_THEN_RETRY, whether a retry is allowed if the effect is found absent


def decide(op_class, failure_class, *, attempts_made=1, max_attempts=3, has_key=True, can_reconcile=True, budget_ok=True, side_effects=True, policy=None) -> Decision:
    """The decision function. Pure. See docs/FAILURE-POLICY.md for the table and guards."""
    p = policy or _default()
    if op_class not in OP_CLASSES or failure_class not in FAILURE_CLASSES: return Decision("DEAD_LETTER", "unknown class: fail closed")
    base = p.table[op_class][failure_class]
    room = attempts_made < max_attempts and budget_ok
    if base == "RETRY":
        if op_class == "SAFE_WITH_IDEMPOTENCY_KEY" and not has_key: return Decision("DEAD_LETTER", "no idempotency key: a retry could double-apply")
        if not room: return Decision("DEAD_LETTER" if side_effects else "FAIL_FAST", "retry limit reached" if attempts_made >= max_attempts else "retry budget exhausted")
        return Decision("RETRY", "retry with backoff", True)
    if base == "RECONCILE_THEN_RETRY":
        if not can_reconcile: return Decision("DEAD_LETTER", "effect cannot be verified (no reconciler)")
        return Decision("RECONCILE_THEN_RETRY", "read whether the effect happened first", room)
    return Decision(base, {"FAIL_FAST": "failure will not be fixed by repeating or is not safe to repeat", "DEAD_LETTER": "outcome unknown or human decision needed"}[base])


# ------------------------------------------------------------------------------------------------ budget
class RetryBudget:
    """Retries may add at most `ratio` x requests (+ a floor of `min_retries`) on top of first attempts, so a failing dependency is not amplified."""
    def __init__(self, ratio=0.2, min_retries=3): self.ratio, self.min, self.requests, self.retries = ratio, min_retries, 0, 0
    def on_request(self): self.requests += 1
    def can_retry(self): return self.retries < self.min + self.ratio * self.requests
    def spend(self): self.retries += 1


# ------------------------------------------------------------------------------------------------ store: dead letters + idempotency ledger
def _m1(c):
    c.execute("""CREATE TABLE ops_dead_letters(dl_id TEXT PRIMARY KEY, created TEXT, correlation_id TEXT, run_id TEXT, operation TEXT, tool TEXT, op_class TEXT, failure_code TEXT,
                 failure_class TEXT, attempts INTEGER, reason TEXT, args_hash TEXT, args_json TEXT, status TEXT, replay_instructions TEXT, resolution TEXT)""")
def _m2(c): c.execute("CREATE TABLE ops_idempotency(key TEXT PRIMARY KEY, operation TEXT, result_json TEXT, hits INTEGER DEFAULT 0)")
STORE_MIGRATIONS = [(1, "create ops_dead_letters", _m1), (2, "create ops_idempotency", _m2)]

REPLAY = {
    "DO_NOT_RETRY": "Do NOT re-run the call blindly: the first attempt may have committed. 1) Inspect the target state ({hint}). 2) If the effect is present, resolve this record as ALREADY_APPLIED. "
                    "3) If absent, have a reviewer re-issue the action through the normal approval flow (a NEW approval bound to args_hash {h}). 4) resolve_dead_letter() with the outcome.",
    "RECONCILE_BEFORE_RETRY": "Reconcile first ({hint}); retry only if the effect is absent. Then resolve this record.",
    "SAFE_WITH_IDEMPOTENCY_KEY": "Replay is safe ONLY with the same idempotency key (see correlation_id / args_hash {h}); a replay with a new key can double-apply. Then resolve this record.",
    "SAFE_TO_RETRY": "The operation has no side effects: re-run it once the dependency is healthy, then resolve this record.",
    "HUMAN_REVIEW_REQUIRED": "A person must inspect what executed and what did not ({hint}), decide, and resolve this record. Nothing is replayed automatically."}
HINTS = {"adjust_inventory_record": "SELECT * FROM inventory_movements WHERE kind='ADJUSTMENT' for the location/ingredient, compare qty_delta and date",
         "flag_record_for_review": "SELECT * FROM review_queue WHERE run_id=<run> and kind='RECORD_REVIEW', compare payload", "release_draft": "SELECT status FROM drafts WHERE draft_id=<id>",
         "draft_purchase_recommendation": "SELECT * FROM drafts WHERE run_id=<run> AND kind='PURCHASE_RECOMMENDATION'", "draft_review_ticket": "SELECT * FROM drafts WHERE run_id=<run>",
         "human_approval_execute_step": "agent_runs status and the run's trace events for mutation attempts"}


class OpsStore:
    """SQLite ops store for dead letters (the manual-recovery / human queue) and the idempotency ledger. Pass a file path to persist; versioned with the Migrator."""
    def __init__(self, path=":memory:", clock=time.time):
        self.path, self.clock = path, clock
        self.con = sqlite3.connect(path); self.mig = Migrator(self.con, STORE_MIGRATIONS); self.mig.migrate()

    def add_dead_letter(self, *, correlation_id, run_id="", operation, tool=None, op_class, failure_code, failure_class, attempts, reason, args=None):
        h = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:16]
        dl = "DL-" + hashlib.sha256(f"{correlation_id}|{operation}|{tool}|{h}".encode()).hexdigest()[:10]          # keyed: replaying the same failure converges to one record
        hint = HINTS.get(tool or operation, "inspect the target state for this operation")
        instr = REPLAY[op_class].format(hint=hint, h=h)
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.clock()))
        self.con.execute("INSERT INTO ops_dead_letters VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(dl_id) DO UPDATE SET attempts=excluded.attempts, reason=excluded.reason",
                         (dl, created, correlation_id, run_id, operation, tool, op_class, failure_code, failure_class, attempts, reason, h, json.dumps(T.redact(args or {}), default=str), "OPEN", instr, None))
        return self.get(dl)

    def get(self, dl_id):
        r = self.con.execute("SELECT * FROM ops_dead_letters WHERE dl_id=?", (dl_id,))
        row = r.fetchone(); return dict(zip([c[0] for c in r.description], row)) if row else None

    def list(self, status="OPEN"):
        r = self.con.execute("SELECT * FROM ops_dead_letters WHERE status=? ORDER BY created, dl_id", (status,)); cols = [c[0] for c in r.description]
        return [dict(zip(cols, x)) for x in r.fetchall()]

    def resolve_dead_letter(self, dl_id, status, note):
        if status not in ("ALREADY_APPLIED", "REPLAYED", "DISCARDED"): raise ValueError("status must be ALREADY_APPLIED, REPLAYED or DISCARDED")
        self.con.execute("UPDATE ops_dead_letters SET status=?, resolution=? WHERE dl_id=?", (status, note, dl_id))

    # ---- idempotency ledger: the first completed result for a key is stored and returned for every later call with that key
    def run_once(self, key, operation, fn):
        row = self.con.execute("SELECT result_json FROM ops_idempotency WHERE key=?", (key,)).fetchone()
        if row:
            self.con.execute("UPDATE ops_idempotency SET hits=hits+1 WHERE key=?", (key,)); return json.loads(row[0]), True
        res = fn(key)
        self.con.execute("INSERT OR IGNORE INTO ops_idempotency(key, operation, result_json) VALUES(?,?,?)", (key, operation, json.dumps(res, default=str)))
        return res, False


# ------------------------------------------------------------------------------------------------ generic runner
@dataclass
class Outcome:
    ok: bool; value: Any = None; code: Optional[str] = None; message: str = ""; retry_after_ms: Optional[float] = None


@dataclass
class Reconciled:
    state: str; value: Any = None          # 'found' | 'absent' | 'unknown'


@dataclass
class RunResult:
    ok: bool; value: Any; code: Optional[str]; attempts: int; delays_ms: list; actions: list; failure_classes: list
    dead_letter: Optional[dict] = None; circuit_open: bool = False; reconciled: bool = False; stop_reason: str = ""


class PolicyRunner:
    def __init__(self, policy=None, store=None, budget=None, breaker=None, sleep=time.sleep, seed=0, events=None):
        self.policy, self.store = policy or _default(), store or OpsStore()
        self.budget, self.breaker, self.sleep, self.seed = budget or RetryBudget(), breaker or CircuitBreaker(3, 30.0), sleep, seed
        self.events = events if events is not None else []

    def run(self, op: Op, attempt: Callable[[int], Outcome], *, key=None, reconcile: Optional[Callable[[], Reconciled]] = None, correlation_id="", run_id="", args=None, tool=None, breaker_key=None) -> RunResult:
        rp = self.policy.retry_policy(op, seed=self.seed + int(hashlib.sha256(f"{correlation_id}|{op.name}".encode()).hexdigest()[:6], 16))
        bk = breaker_key or op.name; use_breaker = op.breaker
        attempts, delays, actions, fcs = 0, [], [], []
        self.budget.on_request()

        def dead(out, fc, reason):
            dl = self.store.add_dead_letter(correlation_id=correlation_id or "none", run_id=run_id, operation=op.name, tool=tool, op_class=op.klass, failure_code=out.code, failure_class=fc, attempts=attempts, reason=reason, args=args)
            self.events.append(dict(event="dead_letter", op=op.name, dl_id=dl["dl_id"], reason=reason)); return dl

        while True:
            if use_breaker and not self.breaker.allow(bk):
                actions.append("FAIL_FAST"); fcs.append("DEPENDENCY_DOWN"); return RunResult(False, None, "CIRCUIT_OPEN", attempts, delays, actions, fcs, circuit_open=True, stop_reason="circuit open: not attempted")
            attempts += 1
            try: out = attempt(attempts)
            except Exception as e: out = Outcome(False, None, getattr(e, "code", None) or ("TIMEOUT" if isinstance(e, TimeoutError) else "UPSTREAM_FAILURE"), str(e)[:160])
            fc = None if out.ok else classify_failure(out.code, op.side_effects, self.policy)
            if use_breaker: self.breaker.record(bk, out.ok or fc not in HEALTH_CLASSES)
            if out.ok: return RunResult(True, out.value, None, attempts, delays, actions, fcs)
            fcs.append(fc)
            eff = "TRANSIENT" if (fc == "MALFORMED_RESULT" and op.retry_malformed) else fc
            d = decide(op.klass, eff, attempts_made=attempts, max_attempts=op.max_attempts, has_key=key is not None, can_reconcile=reconcile is not None,
                       budget_ok=self.budget.can_retry(), side_effects=op.side_effects, policy=self.policy)
            actions.append(d.action)
            if d.action == "FAIL_FAST": return RunResult(False, out.value, out.code, attempts, delays, actions, fcs, stop_reason=d.reason)
            if d.action == "DEAD_LETTER": return RunResult(False, out.value, out.code, attempts, delays, actions, fcs, dead_letter=dead(out, fc, f"{out.code}: {d.reason}"), stop_reason=d.reason)
            if d.action == "RECONCILE_THEN_RETRY":
                try: rec = reconcile()
                except Exception: rec = Reconciled("unknown")
                if rec.state == "found": return RunResult(True, rec.value, None, attempts, delays, actions, fcs, reconciled=True)
                if rec.state != "absent": return RunResult(False, out.value, out.code, attempts, delays, actions, fcs, dead_letter=dead(out, fc, f"{out.code}: reconciliation inconclusive"), stop_reason="reconciliation inconclusive")
                if not d.may_retry: return RunResult(False, out.value, out.code, attempts, delays, actions, fcs, stop_reason="effect confirmed absent; retry limit or budget reached")
            self.budget.spend()
            dl = rp.delay(attempts)
            if fc == "RATE_LIMIT": dl = max(dl, out.retry_after_ms or 0, self.policy.cfg["retry_defaults"]["rate_limit_floor_ms"])
            delays.append(dl); self.sleep(dl / 1000.0)


# ------------------------------------------------------------------------------------------------ tool executor (drop-in for ExecStack)
def _reconciler_for(spec, name, op, w, args, ctx):
    if op.reconciler == "draft":
        parsed = spec.input_model.model_validate(args).model_dump()
        def r():
            did = existing_draft(w, ctx.run_id, "PURCHASE_RECOMMENDATION" if name == "draft_purchase_recommendation" else parsed.get("kind"), parsed)
            if did: return Reconciled("found", dict(ok=True, tool=name, permission=spec.permission, error=None, data=dict(draft_id=did, status="DRAFT_NOT_SUBMITTED", notice="reconciled: the draft had already been committed; not re-created"), ms=0.0))
            return Reconciled("absent")
        return r
    if op.reconciler == "release_draft":
        parsed = spec.input_model.model_validate(args).model_dump()
        def r():
            row = w.q("SELECT status FROM drafts WHERE draft_id=?", parsed["draft_id"])
            if not row: return Reconciled("unknown")
            if row[0]["status"] == "APPROVED_FOR_HUMAN_PROCUREMENT_REVIEW":
                return Reconciled("found", dict(ok=True, tool=name, permission=spec.permission, error=None, data=dict(draft_id=parsed["draft_id"], status="APPROVED_FOR_HUMAN_PROCUREMENT_REVIEW", notice="reconciled: already released; not re-applied"), ms=0.0))
            return Reconciled("absent")
        return r
    return None


class PolicyStack(TM.ExecStack):
    """ExecStack whose retry behaviour is the explicit failure policy instead of 'retry READ/ANALYZE/DRAFT on transient codes'. Same fault-injection and sampling seams."""
    def __init__(self, policy=None, store=None, budget=None, breaker=None, sleep=time.sleep, seed=0, **kw):
        super().__init__(retry=None, breaker=None, sleep=sleep, **kw)
        self.runner = PolicyRunner(policy, store, budget, breaker, sleep, seed); self.policy = self.runner.policy

    def _execute(self, w, name, args, ctx=None):
        ctx = ctx or T.ToolContext(); spec = T.TOOLS.get(name); op = self.policy.tool(name); t0 = self.clock()
        real = self.samples; scratch = []; box = {}

        def attempt(n):
            self.samples = scratch
            try: res = TM.ExecStack._execute(self, w, name, args, ctx)
            finally: self.samples = real
            box["res"] = res
            return Outcome(res["ok"], res, None if res["ok"] else res["error"]["code"], "" if res["ok"] else res["error"]["message"])

        rec = _reconciler_for(spec, name, op, w, args, ctx) if (spec is not None and op.reconciler and args is not None) else None
        rr = self.runner.run(op, attempt, reconcile=rec, correlation_id=ctx.request_id or ctx.run_id, run_id=ctx.run_id, args=args, tool=name, breaker_key=name)
        if rr.circuit_open: res = T._err(name, spec.permission if spec else "UNKNOWN", "CIRCUIT_OPEN", f"circuit open for {name}; call not attempted", time.perf_counter(), ctx, args)
        elif rr.reconciled: res = rr.value
        else: res = box["res"]
        s = dict(scratch[-1]) if scratch else dict(run_id=ctx.run_id, tool=name, permission=spec.permission if spec else None)
        s.update(run_id=ctx.run_id, tool=name, permission=spec.permission if spec else None, ok=res["ok"], code=(res.get("error") or {}).get("code"), ms=round((self.clock() - t0) * 1000, 2), attempts=rr.attempts,
                 retried=[f for f, x in zip(rr.failure_classes, rr.actions) if x in ("RETRY", "RECONCILE_THEN_RETRY")],
                 circuit_open=rr.circuit_open, policy=dict(op_class=op.klass, actions=rr.actions, failure_classes=rr.failure_classes, reconciled=rr.reconciled, dead_letter=(rr.dead_letter or {}).get("dl_id"), stop=rr.stop_reason))
        real.append(s)
        return res
