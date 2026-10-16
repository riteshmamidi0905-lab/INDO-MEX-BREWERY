"""P3 product case: the numbers the case relies on are re-derived from the committed result files (SYNTHETIC, same author, nothing re-run)."""
import hashlib
import json
from pathlib import Path

import pytest

from product_case import analysis as A

LAB = Path(__file__).resolve().parents[1]
R = LAB / "results"


@pytest.fixture(scope="module")
def built():
    return A.build_all()


def _j(name):
    return json.loads((R / name).read_text())


def test_committed_analysis_json_equals_a_fresh_derivation(built):
    committed = json.loads((LAB / "product_case" / "results" / "analysis.json").read_text())
    assert json.loads(json.dumps(built, sort_keys=True)) == committed


def test_analysis_never_writes_into_the_frozen_results_directory():
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in R.glob("*.json")}
    A.build_all()
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in R.glob("*.json")}
    assert before == after


def test_headline_numbers_quoted_in_the_case_match_the_result_files():
    d = _j("planner_deterministic.json")["overall"]
    assert (d["pass_rate"]["k"], d["pass_rate"]["n"]) == (259, 259) and d["latency_ms_p50"] == 65.5
    q = _j("planner_qwen1.5b_run2_raw.json")["overall"]
    assert (q["pass_rate"]["k"], q["pass_rate"]["n"]) == (5, 140)
    assert q["latency_ms_p50"] == 28031.7 and q["external_actions"] == 0 and q["llm_calls"] == 426
    q7 = _j("planner_qwen7b_raw.json")["overall"]
    assert (q7["pass_rate"]["k"], q7["pass_rate"]["n"]) == (10, 35) and q7["latency_ms_p50"] == 151524.4
    ts = _j("tool_schema_result.json")
    assert (ts["rows"][0]["required_tools"]["k"], ts["rows"][1]["required_tools"]["k"], ts["n"]) == (22, 67, 140)
    assert ts["rows"][0]["wrong_silent_no_action"] == 30
    assert ts["by_event_family"]["POLICY"]["action_ts1"] == 22 and ts["by_event_family"]["POLICY"]["action_ts2"] == 10
    assert _j("ext1_planner_deterministic.json")["probes"]["pass_rate"]["k"] == 0
    p2 = _j("ext1_planner_deterministic_poq2.json")
    assert (p2["probes"]["pass_rate"]["k"], p2["probes"]["pass_rate"]["n"]) == (8, 8)


def test_the_30_silent_all_clears_are_all_inventory_events(built):
    f = built["families"]["qwen1.5b_raw"]
    assert f["INVENTORY"]["silent_all_clear"] == 30 and f["INVENTORY"]["need_action"] == 59
    assert f["DATA_QUALITY"]["silent_all_clear"] == 0 and f["POLICY"]["silent_all_clear"] == 0
    # the independent count in the tool-schema result file agrees with the sum across families
    assert sum(f[k]["silent_all_clear"] for k in f) == _j("tool_schema_result.json")["rows"][0]["wrong_silent_no_action"] == 30


def test_envelope_and_control_have_zero_silent_all_clears_and_say_how_wide_the_interval_is(built):
    for key in ("deterministic", "qwen1.5b_guardrail", "qwen7b_raw", "qwen7b_guardrail"):
        assert built["families"][key]["INVENTORY"]["silent_all_clear"] == 0
    lo, hi = built["families"]["deterministic"]["INVENTORY"]["silent_ci95"]
    assert lo == 0.0 and hi < 0.04                                   # 0/119 on same-author scenarios
    assert built["families"]["qwen7b_raw"]["INVENTORY"]["silent_ci95"][1] > 0.15   # 0/16 cannot exclude a 15% miss rate


def test_the_suite_is_almost_all_actionable_so_false_alarms_are_barely_measured(built):
    s = built["no_action_share"]
    assert (s["n"], s["expected_exactly_no_action"]) == (259, 8)
    assert built["families"]["qwen1.5b_raw"]["INVENTORY"]["healthy_n"] == 4


def test_d54_policy_family_direction_of_errors(built):
    p = built["policy_direction"]
    assert p["deterministic"] == {"acceptable": 82, "n": 82}
    r = p["qwen1.5b_raw"]
    assert r["n"] == 42 and r["acceptable"] == 22
    assert r["leans_toward_confirm_where_oracle_required_abstain_or_reject"] == 5
    assert r["rejects_where_oracle_allowed_only_abstain_or_confirm"] == 12
    assert "leans_toward_confirm_where_oracle_required_abstain_or_reject" not in p["qwen1.5b_guardrail"]


def test_latency_ratios_are_order_of_magnitude(built):
    L = built["latency"]
    assert 300 < L["ratio_1_5b_over_det_259"] < 600 and L["ratio_7b_over_det_259"] > 2000


def test_wilson_interval_reference_values():
    assert A.wilson(0, 140)[0] == 0.0 and A.wilson(0, 140)[1] == pytest.approx(0.027, abs=0.002)
    assert A.wilson(30, 59) == pytest.approx((0.384, 0.632), abs=0.002)
    assert A.wilson(0, 0) == (None, None)


def test_nonai_baseline_lexicon_gap_is_pinned_not_hidden(built):
    """KNOWN GAP of the non-AI baseline (existence probe, not a rate): beef/pork derivatives outside the 14-token lexicon return NO_POLICY_SIGNAL.
    If the lexicon is extended this test must be updated deliberately (and docs/product/03 and 06 with it)."""
    s = built["lexicon_probe"]["summary"]
    assert s["in_lexicon_prohibited"] == "5/5" and s["out_of_lexicon_not_flagged"] == "10/10" and s["benign_prohibited"] == "0/4"
