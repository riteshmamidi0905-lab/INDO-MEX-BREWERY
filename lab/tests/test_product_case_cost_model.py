"""P3 product case: the expected-cost model is deterministic, its properties hold, and the decision rule is applied mechanically."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from product_case import cost_model as C

LAB = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built():
    return C.build_all()


def test_committed_cost_model_json_equals_a_fresh_run(built):
    committed = json.loads((LAB / "product_case" / "results" / "cost_model.json").read_text())
    assert json.loads(json.dumps(built, sort_keys=True)) == committed


def test_seeded_sensitivity_is_reproducible_and_seed_dependent():
    a, b = C.sensitivity(draws=2000, seed=1), C.sensitivity(draws=2000, seed=1)
    c = C.sensitivity(draws=2000, seed=2)
    assert a == b and a != c


def test_rules_cost_increases_with_the_cost_of_a_silent_miss():
    p = C.Params()
    costs = [C.cost_rules(replace(p, c_miss=x))["total"] for x in (50, 500, 5000)]
    assert costs == sorted(costs) and len(set(costs)) == 3


def test_an_add_only_second_opinion_cannot_help_if_the_rules_have_no_gap_or_the_model_catches_nothing():
    p = C.Params()
    for f_add in (0.0, 0.05, 0.3):
        assert C.cost_hybrid(replace(p, g=0.0), f_add)["total"] >= C.cost_rules(replace(p, g=0.0))["total"]
        assert C.cost_hybrid(replace(p, b=0.0), f_add)["total"] >= C.cost_rules(replace(p, b=0.0))["total"]


def test_raw_small_model_never_wins_anywhere_in_the_stated_ranges(built):
    for mode in ("pess", "opt"):
        assert built["sensitivity"][mode]["win_share"]["llm15_raw"] == 0.0
    assert all(r["winner"] != "best_llm_planner" for r in built["grid"])


def test_central_case_numbers_are_internally_consistent(built):
    cc = built["central_case"]
    for v in cc["cost"].values():
        assert v["total"] == pytest.approx(v["miss"] + v["review"] + v["rework"] + v["false_alarm"], abs=0.5)
    assert cc["cost"]["llm15_raw"]["miss"] > 5 * cc["cost"]["rules_only"]["miss"]


def test_breakeven_c_miss_is_a_real_threshold(built):
    for mode, f in (("optimistic", 0.05),):
        be = C.breakeven_c_miss(None, mode)
        p = C.Params()
        assert C.cost_hybrid(replace(p, c_miss=be * 1.05), f)["total"] < C.cost_rules(replace(p, c_miss=be * 1.05))["total"]
        assert C.cost_hybrid(replace(p, c_miss=be * 0.95), f)["total"] > C.cost_rules(replace(p, c_miss=be * 0.95))["total"]
    assert built["breakeven_c_miss_hybrid_vs_rules"]["pessimistic"] > built["breakeven_c_miss_hybrid_vs_rules"]["optimistic"]


def test_decision_rule_is_applied_mechanically(built):
    v = built["verdict"]
    assert v["llm_planner"].startswith("recommendation stands")
    assert v["hybrid_add_only"].startswith("CONDITIONAL")
    fake = {"pess": {"win_share": {"rules_only": 0.1, "llm15_raw": 0, "llm15_envelope": 0.6, "llm7_raw": 0, "llm7_envelope": 0, "hybrid_add_only": 0.3}},
            "opt": {"win_share": {"rules_only": 0.1, "llm15_raw": 0, "llm15_envelope": 0.6, "llm7_raw": 0, "llm7_envelope": 0, "hybrid_add_only": 0.3}}}
    assert C.verdict(fake)["llm_planner"] == "REVERSE the recommendation"


def test_drafting_break_even_shape():
    d = C.drafting_breakeven(3.0, 2.0, 0.5, 200.0)
    assert d["saving_per_message"] == 0.5 and d["break_even_undetected_error_rate"] == 0.0025
    assert C.drafting_breakeven(3.0, 3.0, 0.5, 200.0)["break_even_undetected_error_rate"] == 0.0
