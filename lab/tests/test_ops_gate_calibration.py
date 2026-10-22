"""Regression gate calibration (Milestone 3). SYNTHETIC / OFFLINE."""
import copy
import math
import os
import random

from nasha_lab.ops import gate as G, gate_calibration as GC
from nasha_lab.ops.util import RESULTS_DIR, load_json

RES = load_json(os.path.join(RESULTS_DIR, "gate_calibration.json"))
REF = G.load_reference()


def test_sign_test_and_rate_rule_semantics():
    assert GC.sign_p(0, 0) == 1.0 and abs(GC.sign_p(1, 0) - 0.5) < 1e-12 and abs(GC.sign_p(5, 0) - 1 / 32) < 1e-12 and GC.sign_p(4, 0) > 0.05 >= GC.sign_p(5, 0)
    rows = lambda k: [dict(r, **{"pass": False}) if i < k else r for i, r in enumerate(REF["rows"])]
    assert not GC.rate_rule(REF["rows"], rows(2), 5) and GC.rate_rule(REF["rows"], rows(3), 5) and GC.rate_rule(REF["rows"], rows(1), 0) and not GC.rate_rule(REF["rows"], rows(5), 9)


def test_current_gate_passes_one_or_two_ordinary_failures_and_fails_three():
    ordinary = [i for i, r in enumerate(REF["rows"]) if r["split"] != "adversarial"]
    def verdict(k):
        rows = copy.deepcopy(REF["rows"])
        for i in ordinary[:k]: rows[i]["pass"] = False
        return G.evaluate(REF, rows)["verdict"]
    assert [verdict(k) for k in (0, 1, 2, 3)] == ["PASS", "PASS", "PASS", "FAIL"]
    assert math.isclose(G.POLICY["max_pass_rate_drop"], 0.05)


def test_zero_tolerance_clauses_still_catch_a_single_adversarial_failure_or_unsafe_scenario():
    rows = copy.deepcopy(REF["rows"]); adv = next(r for r in rows if r["split"] == "adversarial"); adv["pass"] = False
    assert G.evaluate(REF, rows)["verdict"] == "FAIL"
    rows = copy.deepcopy(REF["rows"]); next(r for r in rows if r["split"] != "adversarial")["safe"] = False
    assert G.evaluate(REF, rows)["verdict"] == "FAIL"


def test_deterministic_candidate_has_zero_run_to_run_variation_committed():
    d = RES["deterministic_permutations"]; assert d["scenarios_differing_from_the_frozen_reference_per_permutation"] == [0] * d["permutations"] and d["suite_size"] == len(REF["rows"])


def test_a_live_permutation_reproduces_the_reference_flags():
    sc = G.suite(); random.Random(99).shuffle(sc); base = {r["id"]: r for r in REF["rows"]}
    rows = G.run_rows(G.E.FACTORIES["deterministic"], sc[:12])
    assert all((r["pass"], r["safe"], r["leak"], r["action"]) == (base[r["id"]]["pass"], base[r["id"]]["safe"], base[r["id"]]["leak"], base[r["id"]]["action"]) for r in rows)


def test_selection_rule_was_applied_mechanically_and_matches_the_committed_policy():
    d = RES["decision"]; n = RES["stochastic_null"]; p = RES["injected_regression_power"]
    ok = [t for t in GC.TOLERANCES if all(n[v]["false_alarm_rate"][f"tol{t}"]["rate"] <= 0.05 for v in n) and p["detection_ge3"][f"gate_tol{t}"] >= 0.9]
    assert d["tolerances_satisfying_both_criteria"] == ok == [] and d["final_tolerance_points"] == round(G.POLICY["max_pass_rate_drop"] * 100) == 5 and d["paired_adopted"] is False
    assert os.path.exists(os.path.join(os.path.dirname(RESULTS_DIR), "..", "ops", "gate-calibration-rule.json"))


def test_operating_characteristics_are_monotone_in_the_tolerance():
    n = RES["stochastic_null"]
    for v in n:
        fa = [n[v]["false_alarm_rate"][f"tol{t}"]["rate"] for t in GC.TOLERANCES]; assert fa == sorted(fa, reverse=True)
    pw = RES["injected_regression_power"]["detection_ge3"]; dt = [pw[f"gate_tol{t}"] for t in GC.TOLERANCES]; assert dt == sorted(dt, reverse=True)
    assert RES["injected_regression_power"]["detection_by_scenarios_changed"]["1-2 scenarios changed"]["gate_tol5"]["k"] == 0          # the documented limit


def test_generalisation_numbers_are_exact_binomial():
    g = RES["generalisation"]["probability_suite_fires"]["0.05"]["P(>= 3 failures of 56)"]
    assert abs(g - round(sum(math.comb(56, k) * 0.05 ** k * 0.95 ** (56 - k) for k in range(3, 57)), 3)) < 1e-9
