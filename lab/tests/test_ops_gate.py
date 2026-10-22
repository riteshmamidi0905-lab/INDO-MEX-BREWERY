"""Regression gate: policy logic, injected regressions, committed reference, rollback drill. SYNTHETIC / OFFLINE EVALUATION."""
import os
import pytest
from nasha_lab import eval_planners as E
from nasha_lab.ops import gate as G, versions as V
from nasha_lab.ops.util import RESULTS_DIR, load_json


def row(i, passed=True, safe=True, leak=False, split="dev"): return dict(id=i, split=split, family="f", **{"pass": passed}, safe=safe, leak=leak, action="A")


REF = dict(rows=[row(f"s{i}", split="adversarial" if i < 5 else "dev") for i in range(20)])


def test_identical_candidate_passes_and_pass_rate_drop_fails():
    assert G.evaluate(REF, REF["rows"])["verdict"] == "PASS"
    one = [dict(r) for r in REF["rows"]]; one[10]["pass"] = False
    assert G.evaluate(REF, one)["verdict"] == "PASS", "one dev scenario (5%) is exactly at the tolerance: the gate is deliberately NOT sensitive to a single failure"
    two = [dict(r) for r in one]; two[11]["pass"] = False; g = G.evaluate(REF, two); assert g["verdict"] == "FAIL" and "pass rate fell" in g["reasons"][0]


def test_any_adversarial_regression_or_new_unsafe_scenario_fails_regardless_of_rate():
    c = [dict(r) for r in REF["rows"]]; c[0]["pass"] = False; assert "adversarial" in " ".join(G.evaluate(REF, c)["reasons"])
    c = [dict(r) for r in REF["rows"]]; c[12]["safe"] = False; assert "UNSAFE" in " ".join(G.evaluate(REF, c)["reasons"])
    c = [dict(r) for r in REF["rows"]]; c[13]["leak"] = True; assert "leak" in " ".join(G.evaluate(REF, c)["reasons"])


def test_missing_scenarios_fail_the_gate():
    assert G.evaluate(REF, REF["rows"][:-2])["verdict"] == "FAIL"


def test_committed_reference_matches_the_suite():
    ref = G.load_reference(); sc = G.suite()
    assert ref["n"] == len(sc) == len(ref["rows"]) and [r["id"] for r in ref["rows"]] == [s.id for s in sc] and ref["pass_rate"] == 1.0
    assert ref["scenario_ids_sha"] == G.sha([s.id for s in sc], 16) and G.sha(ref["rows"], 16) == ref["rows_sha"]


def test_degraded_planner_is_caught_on_a_small_real_suite():
    sc = G.suite()[:20]
    ref = dict(rows=G.run_rows(E.FACTORIES["deterministic"], sc)); assert all(r["pass"] for r in ref["rows"])
    for mode in ("no_action", "drop_evidence"):
        g = G.evaluate(ref, G.run_rows(G.degraded_factory(1.0, 0, mode), sc)); assert g["verdict"] == "FAIL", mode
    assert G.evaluate(ref, G.run_rows(E.FACTORIES["rule-model"], sc))["verdict"] == "PASS"


def test_assembled_degraded_rows_equal_a_real_partial_degradation_run():
    sc = G.suite()[:12]; clean = G.run_rows(E.FACTORIES["deterministic"], sc); full = G.run_rows(G.degraded_factory(1.0, 0, "no_action"), sc)
    real = G.run_rows(G.degraded_factory(0.5, 7, "no_action"), sc); asm = G.assemble_degraded(clean, full, sc, 0.5, 7, "no_action")
    assert [r["pass"] for r in asm] == [r["pass"] for r in real] and [r["action"] for r in asm] == [r["action"] for r in real]


def test_committed_gate_results_are_consistent():
    r = load_json(os.path.join(RESULTS_DIR, "regression_gate.json"))
    assert r["assembly_equivalence_check"]["identical_pass_flags"] and r["control"]["false_alarms"] == 0
    assert r["severity_curve"]["1.0"]["detection"]["rate"] == 1.0 and r["severity_curve"]["0.05"]["detection"]["rate"] < 1.0, "the curve must show the honest miss at low severity"
    assert r["named_candidates"]["worst-case"]["verdict"] == "FAIL" and r["named_candidates"]["rule-model"]["verdict"] == "PASS"


def test_version_registry_matches_live_code_and_corpus():
    reg = V.load_registry(); assert V.drift(reg) == [], "code, prompt, tool schema or corpus changed without registering a new version (python -m nasha_lab.ops.versions register)"
    assert reg["active"] == "v1" and {v["version_id"] for v in reg["versions"]} >= {"v1", "v2", "v3", "v4-recorded"}
    v1 = next(v for v in reg["versions"] if v["version_id"] == "v1"); assert v1["eval_snapshot"]["reference_rows_sha"] == G.load_reference()["rows_sha"]


def test_recorded_only_version_cannot_be_activated():
    r = V.Registry(V.load_registry())
    with pytest.raises(ValueError): r.activate("v4-recorded")


def test_committed_rollback_drill_shows_catch_and_rollback():
    d = load_json(os.path.join(RESULTS_DIR, "rollback_drill.json")); s = d["summary"]
    assert s["gate_caught_bad_candidate"] and s["safe_candidate_allowed"] and s["rolled_back_to"] == "v1" and s["post_rollback_gate"] == "PASS"
    assert d["incidents"][0]["cls"] == "EVAL_REGRESSION" and d["incidents"][0]["status"] == "RESOLVED" and d["incidents"][0]["runbook_id"] == "RB-EVAL-REGRESSION"


def test_gate_suite_ids_are_unique_and_cover_every_split():
    sc = G.suite(); ids = [s.id for s in sc]
    assert len(ids) == len(set(ids)), "FC-07 lesson: new evaluation sets must use unique ids"
    assert {s.split for s in sc} == {"dev", "heldout", "adversarial"}
