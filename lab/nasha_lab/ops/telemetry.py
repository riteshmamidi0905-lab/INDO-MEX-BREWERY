"""Telemetry capture around REAL agent runs (P1 item 1-2). SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.

Three sources, one record per run:
  1. the existing trace store (state / tool_call / tool_error / policy_retrieved / llm_call / human_decision / final ...), which already carries timestamps;
  2. ExecStack, a context manager that wraps `tools.execute` to time EVERY tool attempt (including failures, which the trace does not time), count retries, and
     host the optional resilience and fault-injection layers;
  3. OpsService, a wrapper around AgentService that times start/resume wall-clock, converts crashes and approval denials into trace events (kind `ops_*`) and
     never changes what the agent decides.
Metric NAMES follow OpenTelemetry conventions (dotted names, attributes, `gen_ai.client.token.usage`), implemented by a small in-process registry. The OTel SDK is
deliberately not a dependency: see docs/OPS-CONTROL-CENTER.md (design note)."""
import json
import time
from collections import defaultdict

from .. import identity as ID, tools as T
from . import LABEL, SCHEMA_VERSION
from .util import quantile

FORBIDDEN_CODES = {"FORBIDDEN_EXTERNAL_ACTION", "UNKNOWN_TOOL", "APPROVAL_REQUIRED", "TAINTED_ARGUMENT"}
NONAUTH_NOTE = "SUPERSEDED"


# ======================================================================================================= metrics registry + structured logs
class MetricsRegistry:
    """Counters, gauges and histograms keyed by (name, sorted attributes). Names are OTel-style; units are in the name suffix or `unit`."""
    def __init__(self):
        self.c, self.g, self.h, self.unit = defaultdict(float), {}, defaultdict(list), {}

    @staticmethod
    def _k(name, attrs): return (name, tuple(sorted((k, str(v)) for k, v in attrs.items())))
    def add(self, name, value=1, unit="1", **attrs): self.c[self._k(name, attrs)] += value; self.unit[name] = unit
    def set(self, name, value, unit="1", **attrs): self.g[self._k(name, attrs)] = value; self.unit[name] = unit
    def record(self, name, value, unit="ms", **attrs): self.h[self._k(name, attrs)].append(value); self.unit[name] = unit

    def snapshot(self):
        out = []
        for (n, a), v in sorted(self.c.items()): out.append(dict(name=n, type="counter", unit=self.unit[n], attributes=dict(a), value=round(v, 4)))
        for (n, a), v in sorted(self.g.items()): out.append(dict(name=n, type="gauge", unit=self.unit[n], attributes=dict(a), value=v))
        for (n, a), v in sorted(self.h.items()):
            out.append(dict(name=n, type="histogram", unit=self.unit[n], attributes=dict(a), count=len(v), sum=round(sum(v), 3), p50=quantile(v, .5), p95=quantile(v, .95), max=max(v)))
        return out


class JsonLogger:
    """Structured JSON log lines (one dict per line). Sink: in-memory list, optional file object. `clock` is injectable for deterministic output."""
    def __init__(self, stream=None, clock=time.time, service="nasha-ops"):
        self.lines, self.stream, self.clock, self.service, self.seq = [], stream, clock, service, 0

    def log(self, level, event, **attrs):
        self.seq += 1
        rec = dict(seq=self.seq, ts=round(self.clock(), 6), level=level, service=self.service, event=event, synthetic=True, **attrs)
        self.lines.append(rec)
        if self.stream: self.stream.write(json.dumps(rec, default=str, sort_keys=True) + "\n")
        return rec

    def info(self, event, **a): return self.log("INFO", event, **a)
    def warn(self, event, **a): return self.log("WARN", event, **a)
    def error(self, event, **a): return self.log("ERROR", event, **a)


# ======================================================================================================= execute wrapper
class ExecStack:
    """Context manager replacing `tools.execute` with: sampling( retry/breaker( fault-injection( real execute ))).
    samples: list that receives one dict per logical tool call. Layers are optional and default OFF, so with no arguments this only OBSERVES."""
    def __init__(self, samples=None, retry=None, breaker=None, faults=None, reconcile_drafts=False, naive_draft_retry=False, sleep=time.sleep, clock=time.perf_counter):
        self.samples = samples if samples is not None else []
        self.retry, self.breaker, self.faults, self.reconcile, self.naive, self.sleep, self.clock = retry, breaker, faults, reconcile_drafts, naive_draft_retry, sleep, clock
        self._depth, self._orig = 0, None

    def __enter__(self):
        if self._depth == 0: self._orig = T.execute; T.execute = self._execute
        self._depth += 1; return self

    def __exit__(self, *exc):
        self._depth -= 1
        if self._depth == 0: T.execute = self._orig
        return False

    # ---- one attempt
    def _attempt(self, w, name, args, ctx, attempt):
        f = self.faults
        if f is not None:
            r = f.before(self, w, name, args, ctx, attempt)
            if r is not None: return r
        res = self._orig(w, name, args, ctx)
        if f is not None: res = f.after(self, w, name, args, ctx, res, attempt)
        return res

    def _execute(self, w, name, args, ctx=None):
        ctx = ctx or T.ToolContext(); t0 = self.clock(); spec = T.TOOLS.get(name); perm = spec.permission if spec else None
        attempts, res, retried_codes, circuit_open = 0, None, [], False
        kb_events0 = len(getattr(ctx.kb, "events", None) or []) if name == "get_current_policy" else 0
        pol = self.retry
        while True:
            if self.breaker is not None and not self.breaker.allow(name):
                res = T._err(name, perm or "UNKNOWN", "CIRCUIT_OPEN", f"circuit open for {name}; call not attempted", time.perf_counter(), ctx, args); circuit_open = True; break
            attempts += 1; res = self._attempt(w, name, args, ctx, attempts)
            if self.breaker is not None: self.breaker.record(name, res["ok"] or (res["error"]["code"] not in ("TIMEOUT", "UPSTREAM_FAILURE")))
            if res["ok"] or pol is None or perm not in (T.READ, T.ANALYZE, T.DRAFT): break
            code = res["error"]["code"]
            if code not in pol.retry_on or attempts >= pol.max_attempts: break
            if perm == T.DRAFT:                                          # idempotency: an ambiguous failure may have committed the draft
                if not self.reconcile and not self.naive: break
                from .resilience import existing_draft
                parsed = None
                if not self.reconcile: retried_codes.append(code); self.sleep(pol.delay(attempts) / 1000.0); continue
                parsed = spec.input_model.model_validate(args).model_dump() if args is not None else {}
                did = existing_draft(w, ctx.run_id, "PURCHASE_RECOMMENDATION" if name == "draft_purchase_recommendation" else parsed.get("kind"), parsed)
                if did:
                    res = dict(ok=True, tool=name, permission=perm, error=None, data=dict(draft_id=did, status="DRAFT_NOT_SUBMITTED", notice="reconciled: the draft had already been committed; not re-created"), ms=0.0)
                    retried_codes.append(code); break
            retried_codes.append(code); d = pol.delay(attempts); self.sleep(d / 1000.0)
        s = dict(run_id=ctx.run_id, tool=name, permission=perm, ok=res["ok"], code=(res.get("error") or {}).get("code"), ms=round((self.clock() - t0) * 1000, 2), attempts=attempts,
                 retried=retried_codes, circuit_open=circuit_open)
        d = res.get("data") if res["ok"] else None
        if name == "get_current_policy" and d is not None:
            s["retrieval"] = dict(abstained=bool(d.get("abstained")), n_citations=len(d.get("citations", [])), nonauth=len(d.get("non_authoritative_matches", [])),
                                  nonauth_statuses=sorted({m.get("effective_status") for m in d.get("non_authoritative_matches", [])}), injection=len(d.get("injection_flagged", [])),
                                  cited_statuses=sorted({c.get("effective_status") for c in d.get("citations", [])}), fallback=(len(getattr(ctx.kb, "events", None) or []) > kb_events0) or None)
        if name == "get_supplier_notes_untrusted" and d is not None: s["untrusted"] = dict(ok=d.get("ok"), flags=list(d.get("flags", [])))
        self.samples.append(s)
        return res


# ======================================================================================================= run record
OUTCOME_CATEGORY = {"APPROVED_AND_EXECUTED_IN_SIMULATION": "COMPLETED_ACTION", "APPROVED_ABSTENTION_ACKNOWLEDGED": "COMPLETED_ABSTAIN", "REJECTED_BY_HUMAN_NO_ACTION": "REJECTED",
                    "ESCALATED_NO_DECISION": "ESCALATED", "DUPLICATE_IGNORED": "DUPLICATE", "FAILED_UNKNOWN_EVENT": "FAILED", "FAILED_UNKNOWN_EVENT_TYPE": "FAILED"}
GOOD_CATEGORIES = {"COMPLETED_ACTION", "COMPLETED_ABSTAIN", "REJECTED", "DUPLICATE", "PENDING"}      # a run "succeeds" operationally when it reaches a defined state; wrong decisions are the evaluation's concern


def build_record(events, run, samples, wall_ms, meta, summary=None):
    """One telemetry record from a run's trace events + tool samples. Pure function of its inputs."""
    ev = events; first = ev[0]["ts"] if ev else None
    kinds = defaultdict(int)
    for e in ev: kinds[e["kind"]] += 1
    rm = next((e for e in ev if e["kind"] == "run_meta"), {})
    prop = next((e for e in reversed(ev) if e["kind"] == "proposal"), {})
    fin = next((e for e in reversed(ev) if e["kind"] == "final"), None)
    hd = [e for e in ev if e["kind"] == "human_decision"]
    ops = [e for e in ev if e["kind"].startswith("ops_")]
    # ---- steps: gap between a state event and the next state/final event; HUMAN_REVIEW is reported as wait, not compute
    steps, human_wait = [], 0.0
    st_idx = [i for i, e in enumerate(ev) if e["kind"] == "state"]
    for n, i in enumerate(st_idx):
        e = ev[i]; end = ev[st_idx[n + 1]]["ts"] if n + 1 < len(st_idx) else (fin["ts"] if fin else e["ts"])
        ms = max(0.0, (end - e["ts"]) * 1000)
        if e["node"] == "HUMAN_REVIEW":
            nxt = next((x for x in ev[i + 1:] if x["kind"] == "human_decision"), None)
            human_wait += ((nxt["ts"] - e["ts"]) * 1000) if nxt else 0.0; ms = 0.0
        steps.append(dict(node=e["node"], ms=round(ms, 3)))
    tools = defaultdict(lambda: dict(calls=0, ok=0, fail=0, codes=defaultdict(int), ms=[], attempts=0))
    for s in samples:
        t = tools[s["tool"]]; t["calls"] += 1; t["ok"] += int(s["ok"]); t["fail"] += int(not s["ok"]); t["ms"].append(s["ms"]); t["attempts"] += s["attempts"]
        if s["code"]: t["codes"][s["code"]] += 1
    tool_out = {k: dict(calls=v["calls"], ok=v["ok"], fail=v["fail"], codes=dict(v["codes"]), ms_max=max(v["ms"]), attempts=v["attempts"]) for k, v in tools.items()}
    ret = dict(hit=0, abstain=0, miss=0, nonauth_matches=0, fallback=0)
    for s in samples:
        if s["tool"] != "get_current_policy": continue
        if not s["ok"]: ret["miss"] += 1; continue
        r = s["retrieval"]; ret["abstain" if r["abstained"] else "hit"] += 1; ret["nonauth_matches"] += r["nonauth"]; ret["fallback"] += int(bool(r["fallback"]))
    llm = [e for e in ev if e["kind"] == "llm_call"]
    llm_ok = [e for e in llm if e.get("ok")]
    planner = dict(type=rm.get("planner_type"), version=rm.get("planner_version"), model=rm.get("model"), llm_calls=len(llm_ok), llm_errors=sum(1 for e in llm if e.get("error")),
                   prompt_tokens=sum(e.get("prompt_tokens", 0) for e in llm_ok), completion_tokens=sum(e.get("completion_tokens", 0) for e in llm_ok), llm_ms=round(sum(e.get("ms", 0) for e in llm_ok), 2),
                   schema_failures=kinds["schema_failure"], planner_failure=bool((summary or {}).get("proposal", {}) and (summary["proposal"] or {}).get("planner_failure")),
                   guardrail_overrides=kinds["guardrail_override"], model_unavailable=any(e.get("error") == "MODEL_UNAVAILABLE" for e in llm))
    outcome = (fin or {}).get("outcome") or (run or {}).get("outcome")
    status = (run or {}).get("status")
    crashed = any(e["kind"] == "ops_run_crashed" for e in ev)
    awaiting = bool(summary and summary.get("awaiting_human"))
    if crashed: cat = "CRASHED"
    elif awaiting: cat = "PENDING"
    elif outcome in OUTCOME_CATEGORY: cat = OUTCOME_CATEGORY[outcome]
    elif status and status.startswith("FAILED"): cat = "FAILED"
    else: cat = "OTHER"
    # ---- approval state machine: pending | approved | rejected | expired | denied | not_required
    if any(e["kind"] == "ops_approval_expired" for e in ev) and awaiting: appr = "expired"
    elif awaiting and any(e["kind"] == "ops_approval_denied" for e in ev): appr = "denied_pending"
    elif awaiting: appr = "pending"
    elif hd and hd[-1].get("decision") == "approve": appr = "approved"
    elif hd and hd[-1].get("decision") == "reject": appr = "rejected"
    elif hd: appr = "other:" + str(hd[-1].get("decision"))
    else: appr = "not_required"
    decision_idx = next((i for i, e in enumerate(ev) if e["kind"] == "human_decision" and e.get("decision") == "approve"), None)
    mut_idx = [i for i, e in enumerate(ev) if e["kind"] == "tool_call" and e.get("permission") == T.MUTATE]
    forb = sum(1 for e in ev if e["kind"] == "tool_error" and e.get("code") in FORBIDDEN_CODES) + kinds["mutation_rejected"]
    last_ts = ev[-1]["ts"] if ev else None
    return dict(
        schema=SCHEMA_VERSION, run_id=(run or {}).get("run_id"), event_id=(run or {}).get("event_id"), family=next((e.get("family") for e in ev if e["kind"] == "state" and e.get("family")), None),
        versions=dict(meta.get("versions", {})), planner=planner, retriever=rm.get("retriever_type"), tool_timeout_s=rm.get("tool_timeout_s"),
        outcome=outcome, outcome_category=cat, ok=cat in GOOD_CATEGORIES, approval=dict(state=appr, ops_events=[e["kind"] + ":" + str(e.get("code", "")) for e in ops]),
        action=prop.get("action"), abstain=bool(prop.get("abstain")), mutating_proposed=len(prop.get("mutating_actions") or []),
        timing=dict(run_ms=round(wall_ms, 3), trace_span_ms=round((last_ts - first) * 1000, 3) if ev else 0.0, human_wait_ms=round(human_wait, 3), steps=steps, llm_ms=planner["llm_ms"]),
        tools=tool_out, tool_calls=len(samples), tool_failures=sum(1 for s in samples if not s["ok"]), tool_retries=sum(s["attempts"] - 1 for s in samples),
        retrieval=ret, safety=dict(forbidden_attempts=forb, mutations_executed=len(mut_idx), approval_boundary_ok=all(decision_idx is not None and i > decision_idx for i in mut_idx),
                                   external_actions=sum(1 for e in ev if e["kind"] == "tool_call" and e.get("permission") == T.EXTERNAL), unsupported_claims_removed=sum(e.get("count", 0) for e in ev if e["kind"] == "unsupported_claims_removed"),
                                   injection_flagged=kinds["injection_flagged"]),
        trace_events=len(ev), label=LABEL)


# ======================================================================================================= service wrapper
class OpsService:
    """Wrap an AgentService. All calls run under ExecStack. Crashes become FAILED runs with an `ops_run_crashed` event (so the event can be re-processed),
    authentication/authorisation failures become `ops_approval_*` events, and an ops-level approval TTL (DESIGN TARGET) expires stale pending reviews."""
    def __init__(self, svc, *, stack=None, registry=None, logger=None, versions=None, clock=time.time, approval_ttl_s=900.0):
        self.svc, self.stack = svc, stack or ExecStack()
        self.registry, self.log, self.versions, self.clock, self.approval_ttl_s = registry or MetricsRegistry(), logger or JsonLogger(clock=clock), versions or {}, clock, approval_ttl_s
        self.wall = defaultdict(float); self.opened = {}; self.run_ids = []

    # ---- helpers
    def _ops_event(self, run_id, kind, **data):
        r = self.svc.store.run(run_id)
        self.svc.store.trace(run_id, (r or {}).get("request_id", "")).event(kind, **data)

    def _find_crashed(self, event_id):
        row = self.svc.store.con.execute("SELECT run_id FROM agent_runs WHERE event_id=? AND status='RUNNING' ORDER BY created DESC LIMIT 1", (event_id,)).fetchone()
        return row[0] if row else None

    def start(self, event_id, request_id=""):
        t0 = time.perf_counter()
        try:
            with self.stack: s = self.svc.start(event_id, request_id)
        except Exception as e:                                         # a crash inside the graph: the existing code leaves the run RUNNING, which blocks re-processing of the event
            rid = self._find_crashed(event_id)
            self.wall[rid] += (time.perf_counter() - t0) * 1000
            if rid:
                self._ops_event(rid, "ops_run_crashed", error=type(e).__name__, detail=str(e)[:160]); self.svc.store.set_status(rid, "FAILED", "CRASHED", finished=True)
                if rid not in self.run_ids: self.run_ids.append(rid)
            self.log.error("run.crashed", run_id=rid, event_id=event_id, error=type(e).__name__, detail=str(e)[:160])
            return dict(run=self.svc.store.run(rid) if rid else None, awaiting_human=False, proposal=None, final=None, status="FAILED", crashed=True, error=type(e).__name__)
        rid = s["run"]["run_id"]; self.wall[rid] += (time.perf_counter() - t0) * 1000
        if rid not in self.run_ids: self.run_ids.append(rid)
        if s["awaiting_human"]: self.opened[rid] = self.clock()
        self.log.info("run.started", run_id=rid, event_id=event_id, status=s["status"])
        return s

    def summary(self, run_id): return self.svc.summary(run_id)
    def dev_session(self, reviewer_id="founder"): return self.svc.dev_session(reviewer_id)

    def reopen(self, run_id):
        """Recovery action for an expired pending approval: restart its TTL (a person re-opens the review)."""
        self.opened[run_id] = self.clock(); self._ops_event(run_id, "ops_approval_reopened"); self.log.info("approval.reopened", run_id=run_id)

    def resume(self, run_id, decision, session=None):
        now = self.clock()
        if run_id in self.opened and now - self.opened[run_id] > self.approval_ttl_s:
            self._ops_event(run_id, "ops_approval_expired", code="APPROVAL_TTL", age_s=round(now - self.opened[run_id], 1), ttl_s=self.approval_ttl_s)
            self.log.warn("approval.expired", run_id=run_id, age_s=round(now - self.opened[run_id], 1))
            raise ID.AuthError("APPROVAL_EXPIRED", f"pending review older than {self.approval_ttl_s}s (design target)")
        t0 = time.perf_counter()
        try:
            with self.stack: s = self.svc.resume(run_id, decision, session)
        except ID.AuthError as e:
            kind = "ops_approval_expired" if e.code == "EXPIRED" else "ops_approval_denied"
            if self.svc.store.run(run_id): self._ops_event(run_id, kind, code=e.code, decision=str(decision.get("decision"))[:30])
            self.log.warn("approval.denied" if kind.endswith("denied") else "approval.expired", run_id=run_id, code=e.code)
            raise
        except Exception as e:
            self.wall[run_id] += (time.perf_counter() - t0) * 1000
            self._ops_event(run_id, "ops_run_crashed", error=type(e).__name__, detail=str(e)[:160]); self.svc.store.set_status(run_id, "FAILED", "CRASHED", finished=True)
            self.log.error("run.crashed", run_id=run_id, error=type(e).__name__); raise
        self.wall[run_id] += (time.perf_counter() - t0) * 1000
        if not s["awaiting_human"]: self.opened.pop(run_id, None)
        else: self.opened[run_id] = self.clock()
        self.log.info("run.resumed", run_id=run_id, decision=decision.get("decision"), status=s["status"])
        return s

    def record(self, run_id):
        run = self.svc.store.run(run_id)
        try: summ = self.svc.summary(run_id)
        except Exception: summ = None
        samples = [s for s in self.stack.samples if s["run_id"] == run_id]
        return build_record(self.svc.store.events(run_id), run, samples, self.wall[run_id], dict(versions=self.versions), summ)

    def records(self): return [self.record(r) for r in self.run_ids]


def observe(registry: MetricsRegistry, rec, model_label=None):
    """Feed one run record into the OTel-style registry."""
    pl = rec["planner"]["type"] or "unknown"
    registry.add("nasha.agent.run.count", 1, outcome_category=rec["outcome_category"], planner=pl)
    registry.record("nasha.agent.run.duration", rec["timing"]["run_ms"], planner=pl)
    for s in rec["timing"]["steps"]: registry.record("nasha.agent.step.duration", s["ms"], node=s["node"])
    for t, v in rec["tools"].items():
        registry.add("nasha.tool.call.count", v["ok"], tool=t, status="ok"); registry.add("nasha.tool.call.count", v["fail"], tool=t, status="error")
        for c, n in v["codes"].items(): registry.add("nasha.tool.call.errors", n, tool=t, error_code=c)
    for k in ("hit", "abstain", "miss"): registry.add("nasha.retrieval.count", rec["retrieval"][k], result=k)
    mdl = rec["planner"]["model"] or "none"
    registry.add("gen_ai.client.token.usage", rec["planner"]["prompt_tokens"], unit="{token}", **{"gen_ai.token.type": "input", "gen_ai.request.model": mdl})
    registry.add("gen_ai.client.token.usage", rec["planner"]["completion_tokens"], unit="{token}", **{"gen_ai.token.type": "output", "gen_ai.request.model": mdl})
    registry.add("nasha.approval.count", 1, state=rec["approval"]["state"])
