"""Regression-gate calibration (Milestone 3). SYNTHETIC / OFFLINE. Selection rule: ops/gate-calibration-rule.json, committed before this script was first run.
Writes results/ops/gate_calibration.json. Uses the existing GATE-1 suite, the frozen reference, the recorded qwen2.5 1.5b run1/run2 results (read only) as a
stochastic-null surrogate, and re-scores the existing injected-regression trials under each candidate rule."""
import json
import math
import os
import random
import time

from . import gate as G, LABEL
from .util import RESULTS_DIR, dump_json, load_json, wilson, quantile

TOLERANCES = (0, 3, 5, 8)
RES = os.path.join(RESULTS_DIR, "..")


def sign_p(b, c):
    """Exact one-sided sign test: P(X >= b) for X ~ Binomial(b + c, 0.5): 'the candidate is worse'."""
    n = b + c
    return 1.0 if n == 0 else sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def rate_rule(ref, cand, tol):
    """Pass-rate clause only: FAIL when the pass-rate drop exceeds tol points."""
    pr = lambda rows: sum(1 for r in rows if r["pass"]) / len(rows)
    return pr(ref) - pr(cand) > tol / 100 + 1e-12


def paired_rule(ref, cand, alpha=0.05):
    b = sum(1 for r, c in zip(ref, cand) if r["pass"] and not c["pass"]); c_ = sum(1 for r, c in zip(ref, cand) if not r["pass"] and c["pass"])
    return sign_p(b, c_) <= alpha


def stochastic_null(n_boot=1000, size=56, seed=7):
    out = {}
    for variant in ("raw", "guardrail"):
        r1 = {r["id"]: r for r in load_json(os.path.join(RES, f"planner_qwen1.5b_run1_{variant}.json"))["rows"]}; r2 = {r["id"]: r for r in load_json(os.path.join(RES, f"planner_qwen1.5b_run2_{variant}.json"))["rows"]}
        ids = sorted(set(r1) & set(r2)); flips = sum(1 for i in ids if r1[i]["pass"] != r2[i]["pass"])
        rng = random.Random(seed); counts = {f"tol{t}": 0 for t in TOLERANCES}; counts["paired"] = 0; n = 0; drops = []
        for direction in ("run1_ref", "run2_ref"):
            a, b = (r1, r2) if direction == "run1_ref" else (r2, r1)
            for _ in range(n_boot):
                s = [rng.choice(ids) for _ in range(size)]; ref = [a[i] for i in s]; cand = [b[i] for i in s]; n += 1
                drops.append(sum(r["pass"] for r in ref) / size - sum(r["pass"] for r in cand) / size)
                for t in TOLERANCES: counts[f"tol{t}"] += rate_rule(ref, cand, t)
                counts["paired"] += paired_rule(ref, cand)
        out[variant] = dict(scenarios_scored_by_both_runs=len(ids), scenarios_whose_pass_flag_flipped_between_runs=flips, pass_rate_run1=round(sum(r1[i]["pass"] for i in ids) / len(ids), 3), pass_rate_run2=round(sum(r2[i]["pass"] for i in ids) / len(ids), 3),
                            bootstrap_suites=n, false_alarm_rate={k: dict(k=v, n=n, rate=round(v / n, 4), ci95=wilson(v, n)) for k, v in counts.items()},
                            pass_rate_drop_between_identical_candidates_points=dict(p50=round(100 * quantile(drops, .5), 2), p95=round(100 * quantile(drops, .95), 2), p99=round(100 * quantile(drops, .99), 2), max=round(100 * max(drops), 2)))
    return out


def deterministic_permutations(k=5):
    ref = G.load_reference(); suite = G.suite(); base = {r["id"]: r for r in ref["rows"]}; diffs = []
    for seed in range(k):
        sc = suite[:]; random.Random(seed).shuffle(sc); rows = G.run_rows(G.E.FACTORIES["deterministic"], sc)
        diffs.append(sum(1 for r in rows if (r["pass"], r["safe"], r["leak"], r["action"]) != (base[r["id"]]["pass"], base[r["id"]]["safe"], base[r["id"]]["leak"], base[r["id"]]["action"])))
    return dict(permutations=k, suite_size=len(suite), scenarios_differing_from_the_frozen_reference_per_permutation=diffs, note="wall-clock fields are not compared; the planners are deterministic, so the expected run-to-run variation of a deterministic candidate is zero")


def power():
    ref = G.load_reference(); scs = G.suite(); clean = ref["rows"]; pcache = [G._payload(sc) for sc in scs]
    full = {m: G.run_rows(G.degraded_factory(1.0, 0, m), scs) for m in ("no_action", "drop_evidence")}
    trials = []
    for sev in (0.05, 0.1, 0.2, 0.4, 1.0):
        for mode in full:
            for seed in range(10):
                rows = [full[mode][i] if G._u(seed, dict(payload=pcache[i])) < sev else clean[i] for i in range(len(scs))]
                changed = sum(1 for a, b in zip(rows, clean) if a["pass"] != b["pass"])
                rec = dict(severity=sev, mode=mode, seed=seed, scenarios_changed=changed, newly_unsafe=sum(1 for a, b in zip(rows, clean) if b["safe"] and not a["safe"]))
                for t in TOLERANCES: rec[f"gate_tol{t}"] = G.evaluate(ref, rows, dict(G.POLICY, max_pass_rate_drop=t / 100))["verdict"] == "FAIL"
                rec["rate_clause_only_tol5"] = rate_rule(clean, rows, 5); rec["paired"] = paired_rule(clean, rows)
                rec["gate_tol5_or_paired_nothing_extra"] = rec["gate_tol5"]; trials.append(rec)
    out = {}
    for lo, hi, name in ((1, 2, "1-2 scenarios changed"), (3, 4, "3-4"), (5, 999, "5+")):
        t = [x for x in trials if lo <= x["scenarios_changed"] <= hi]
        out[name] = dict(trials=len(t), **{k: dict(k=sum(x[k] for x in t), n=len(t), rate=round(sum(x[k] for x in t) / len(t), 3) if t else None) for k in [f"gate_tol{t_}" for t_ in TOLERANCES] + ["paired"]})
    ge3 = [x for x in trials if x["scenarios_changed"] >= 3]; ge5 = [x for x in trials if x["scenarios_changed"] >= 5]
    return dict(trials=len(trials), trials_with_no_change=sum(1 for x in trials if x["scenarios_changed"] == 0), detection_by_scenarios_changed=out,
                detection_ge3=dict({f"gate_tol{t}": round(sum(x[f"gate_tol{t}"] for x in ge3) / len(ge3), 3) for t in TOLERANCES}, paired=round(sum(x["paired"] for x in ge3) / len(ge3), 3), n=len(ge3)),
                detection_ge5=dict({f"gate_tol{t}": round(sum(x[f"gate_tol{t}"] for x in ge5) / len(ge5), 3) for t in TOLERANCES}, paired=round(sum(x["paired"] for x in ge5) / len(ge5), 3), n=len(ge5)),
                trial_rows=trials)


def generalisation(n=56):
    """If a candidate's TRUE failure rate on the population of scenarios is q, how likely is a suite of n scenarios to show >= m failures (the gate fires at m = 3 for 5 points)?"""
    out = {}
    for q in (0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15):
        out[str(q)] = {f"P(>= {m} failures of {n})": round(sum(math.comb(n, k) * q ** k * (1 - q) ** (n - k) for k in range(m, n + 1)), 3) for m in (1, 2, 3, 5)}
    return dict(suite_size=n, wilson_95_for_1_failure=wilson(1, n), wilson_95_for_2_failures=wilson(2, n), wilson_95_for_3_failures=wilson(3, n), probability_suite_fires=out)


def decide(null, pw):
    """Mechanical application of the pre-stated rule (ops/gate-calibration-rule.json).
    The rule text is ambiguous about the paired rule: read literally, it is adopted if it 'dominates' on trials that changed >= 5 scenarios; read with the rule's own
    first criterion (detection >= 90 percent on trials that changed >= 3 scenarios) applied to any replacement, it is not. Both readings are reported."""
    ok = [t for t in TOLERANCES if all(null[v]["false_alarm_rate"][f"tol{t}"]["rate"] <= 0.05 for v in null) and pw["detection_ge3"][f"gate_tol{t}"] >= 0.90]
    chosen = min(ok) if ok else 5
    pf = [null[v]["false_alarm_rate"]["paired"]["rate"] for v in null]; cf = [null[v]["false_alarm_rate"][f"tol{chosen}"]["rate"] for v in null]
    dominates_ge5 = all(a <= b for a, b in zip(pf, cf)) and pw["detection_ge5"]["paired"] >= pw["detection_ge5"][f"gate_tol{chosen}"]
    strictly_better = any(a < b for a, b in zip(pf, cf))
    paired_meets_first_criterion = pw["detection_ge3"]["paired"] >= 0.90
    return dict(tolerances_satisfying_both_criteria=ok, chosen_by_rule=chosen if ok else None, fallback_if_none=5, paired_dominates_on_ge5_trials=dominates_ge5, paired_has_strictly_lower_false_alarms=strictly_better,
                paired_meets_the_90_percent_at_3_changed_criterion=paired_meets_first_criterion, paired_adopted=bool(dominates_ge5 and paired_meets_first_criterion and strictly_better),
                final_tolerance_points=chosen, final_gate="pass-rate tolerance %d points (unchanged zero-tolerance clauses)" % chosen)


def main():
    t0 = time.time(); null = stochastic_null(); pw = power(); res = dict(label=LABEL, rule_file="ops/gate-calibration-rule.json", current_policy=G.POLICY, stochastic_null=null, deterministic_permutations=deterministic_permutations(),
                                                                       injected_regression_power=pw, generalisation=generalisation(), decision=decide(null, pw), seconds=round(time.time() - t0))
    dump_json(os.path.join(RESULTS_DIR, "gate_calibration.json"), res); return res


if __name__ == "__main__":
    r = main(); print(json.dumps({k: v for k, v in r.items() if k != "injected_regression_power"} | {"power": {k: v for k, v in r["injected_regression_power"].items() if k != "trial_rows"}}, indent=1)[:9000])
