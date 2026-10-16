"""Seeded trials of the explicit failure policy vs. the 'retry everything' default the owner rejected. SYNTHETIC / SIMULATED / OFFLINE.
Same fault seams as GAP-01 (faultlib.FaultPlan). The committed GAP-01 result in reliability_gaps.json is left untouched as the pre-policy baseline;
this module writes results/ops/failure_policy_trials.json. Nothing was tuned after looking at results: limits come from failure-policy.json."""
import sys
from . import faultlib as FL, faults as F, runner as R, telemetry as TM, failure_policy as FP
from .resilience import RetryPolicy, CircuitBreaker
import os
from .util import RESULTS_DIR, dump_json, rate
from . import LABEL


class NaiveAllStack(TM.ExecStack):
    """The rejected rule: retry EVERY operation, including mutations, on timeout/upstream errors/malformed results, up to 3 attempts."""
    def __init__(self, **kw): super().__init__(retry=None, **kw)

    def _execute(self, w, name, args, ctx=None):
        ctx = ctx or TM.T.ToolContext(); res = None
        for n in range(3):
            res = TM.ExecStack._execute(self, w, name, args, ctx)
            if res["ok"] or res["error"]["code"] not in ("TIMEOUT", "UPSTREAM_FAILURE", "MALFORMED_RESULT"): break
        return res


def _n(env, sql, rid): return env.world.q(sql, rid)[0]["n"]


def _dsc():
    return [s for s in F.pool(["INVENTORY"]) if "DRAFT_PURCHASE_RECOMMENDATION" in s.expected["action"]][:10]


def _dq():
    return [s for s in F.pool(["DATA_QUALITY"])][:10]


def trial_draft_ambiguous():
    out = {}
    mk = {"no_retry": lambda: TM.ExecStack(faults=FL.FaultPlan(commit_then_timeout={"draft_purchase_recommendation"})),
          "naive_retry": lambda: TM.ExecStack(faults=FL.FaultPlan(commit_then_timeout={"draft_purchase_recommendation"}), retry=RetryPolicy(max_attempts=3, base_ms=1, max_ms=2), naive_draft_retry=True),
          "reconcile_then_retry_execstack": lambda: TM.ExecStack(faults=FL.FaultPlan(commit_then_timeout={"draft_purchase_recommendation"}), retry=RetryPolicy(max_attempts=3, base_ms=1, max_ms=2), reconcile_drafts=True),
          "failure_policy": lambda: FP.PolicyStack(store=FP.OpsStore(), sleep=lambda s: None, faults=FL.FaultPlan(commit_then_timeout={"draft_purchase_recommendation"}))}
    for arm, f in mk.items():
        dup = ok = n = dl = 0
        for sc in _dsc():
            env = R.make_env(sc, "deterministic", stack=f()); rid, _ = R.drive(env, decisions=[]); n += 1
            cnt = _n(env, "SELECT COUNT(*) n FROM drafts WHERE kind='PURCHASE_RECOMMENDATION' AND run_id=?", rid); dup += int(cnt > 1)
            ok += int(env.ops.record(rid)["action"] == "DRAFT_PURCHASE_RECOMMENDATION")
            if arm == "failure_policy": dl += len(env.ops.stack.runner.store.list())
        out[arm] = dict(runs=n, runs_with_duplicate_drafts=dup, runs_reaching_the_draft_proposal=ok, **({"open_dead_letters": dl} if arm == "failure_policy" else {}))
    return out


def trial_mutation_ambiguous():
    """Approved MUTATE_SIMULATION (flag_record_for_review) whose first attempt commits and then reports TIMEOUT."""
    out = {}
    mk = {"no_retry": lambda: TM.ExecStack(faults=FL.FaultPlan(commit_then_timeout={"flag_record_for_review"})),
          "retry_everything": lambda: NaiveAllStack(faults=FL.FaultPlan(commit_then_timeout={"flag_record_for_review"})),
          "failure_policy": lambda: FP.PolicyStack(store=FP.OpsStore(), sleep=lambda s: None, faults=FL.FaultPlan(commit_then_timeout={"flag_record_for_review"}))}
    for arm, f in mk.items():
        dup = n = dl = attempts = blocked = 0
        for sc in _dq():
            st = f(); env = R.make_env(sc, "deterministic", stack=st); rid, _ = R.drive(env); n += 1
            cnt = _n(env, "SELECT COUNT(*) n FROM review_queue WHERE kind='RECORD_REVIEW' AND run_id=?", rid); dup += int(cnt > 1)
            attempts += sum(s["attempts"] for s in st.samples if s["run_id"] == rid and s["tool"] == "flag_record_for_review")
            blocked += sum(1 for e in env.svc.store.events(rid) if e['kind'] == 'tool_error' and 'REPLAYED' in str(e.get('message')))
            if arm == "failure_policy": dl += len(st.runner.store.list())
        out[arm] = dict(runs=n, runs_with_duplicate_review_items=dup, retries_refused_by_single_use_grant=blocked, total_attempts_on_the_mutation=attempts, **({"open_dead_letters": dl} if arm == "failure_policy" else {}))
    return out


def trial_transient_timeout():
    out = {}
    for arm in ("no_retry", "failure_policy", "retry_everything"):
        ok = n = att = 0
        for seed in range(20):
            r = F.rng_for("gap01", seed); sc = r.choice(F.pool(["INVENTORY"])); tools = sorted(set(sc.expected["required"]) - F.EVIDENCE_TOOLS_EXCLUDED)
            if not tools: continue
            tool = r.choice(tools); ca = F.clean_twin(sc)[0]; plan = FL.FaultPlan(transient={tool: dict(fail_first=1, code="TIMEOUT")})
            st = {"no_retry": lambda: TM.ExecStack(faults=plan), "failure_policy": lambda: FP.PolicyStack(store=FP.OpsStore(), sleep=lambda s: None, faults=plan), "retry_everything": lambda: NaiveAllStack(faults=plan)}[arm]()
            env = R.make_env(sc, "deterministic", stack=st); rid, _ = R.drive(env, decisions=[]); n += 1; ok += int(env.ops.record(rid)["action"] == ca)
            att += sum(s["attempts"] for s in st.samples if s["run_id"] == rid)
        out[arm] = dict(runs=n, action_equals_clean=rate(ok, n), total_tool_attempts=att)
    return out


def trial_permanent_failures():
    """Failures that repetition cannot fix: malformed tool result, and a persistent tool timeout. Count wasted attempts."""
    out = {}
    for fault in ("malformed", "slow"):
        for arm in ("failure_policy", "retry_everything"):
            n = att = escal = 0
            for seed in range(20):
                r = F.rng_for("pol_" + fault, seed); sc = r.choice(F.pool()); tools = sorted(set(sc.expected["required"]) - F.EVIDENCE_TOOLS_EXCLUDED)
                if not tools: continue
                tool = r.choice(tools)
                st = FP.PolicyStack(store=FP.OpsStore(), sleep=lambda s: None) if arm == "failure_policy" else NaiveAllStack(sleep=lambda s: None)
                env = R.make_env(sc, "deterministic", stack=st, faults={**dict(sc.faults), tool: fault}, timeout_s=0.05); rid, _ = R.drive(env, decisions=[]); n += 1
                ss = [s for s in st.samples if s["run_id"] == rid and s["tool"] == tool]; att += sum(s["attempts"] for s in ss); escal += int(F.conservative(env.ops.record(rid)["action"] or ""))
            out[f"{'malformed_result' if fault == 'malformed' else 'persistent_timeout'}/{arm}"] = dict(runs=n, attempts=att, runs_ending_conservative=escal)
    return out


def trial_breaker_and_budget():
    br = CircuitBreaker(3, 999); st = FP.PolicyStack(store=FP.OpsStore(), breaker=br, sleep=lambda s: None); sc = F.pool(["INVENTORY"])[0]
    tool = sorted(set(sc.expected["required"]) - F.EVIDENCE_TOOLS_EXCLUDED)[0]; rows = []
    for k in range(6):
        env = R.make_env(sc, "deterministic", stack=st, faults={**dict(sc.faults), tool: "error"}); rid, _ = R.drive(env, decisions=[])
        s = [x for x in st.samples if x["run_id"] == rid and x["tool"] == tool][0]; rows.append(dict(run=k, code=s["code"], attempts=s["attempts"], circuit_open=s["circuit_open"]))
    b = st.runner.budget
    return dict(calls=rows, breaker_state=br.state(tool), budget=dict(requests=b.requests, retries=b.retries))


def main():
    res = dict(label=LABEL, experiment="failure-policy trials (sequential, seeded; policy limits from ops/failure-policy.json, not tuned after results)",
               draft_ambiguous_timeout=trial_draft_ambiguous(), mutation_ambiguous_timeout=trial_mutation_ambiguous(), transient_timeout_first_attempt=trial_transient_timeout(),
               unfixable_failures=trial_permanent_failures(), breaker_and_budget=trial_breaker_and_budget())
    dump_json(os.path.join(RESULTS_DIR, "failure_policy_trials.json"), res); return res


if __name__ == "__main__":
    import json; print(json.dumps(main(), indent=1)[:6000])
