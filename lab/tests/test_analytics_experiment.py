"""Experiment: the analysis must recover the injected effect on average, hold its size under A/A, and say so when it is underpowered. SYNTHETIC."""
import numpy as np
import pytest

from analytics import experiment as E


@pytest.fixture(scope="module")
def res():
    return E.run(seed=1, reps=300)


def test_labelled_synthetic_and_limitations_present(res):
    assert res["synthetic"] and "SIMULATED" in res["disclaimer"] and len(res["causal_limitations"]) >= 5


def test_assignment_balanced_and_srm_ok(res):
    d = res["design"]
    assert abs(d["treated"] - d["control"]) < 0.15 * d["guests"] and res["srm_chi2_p"] > 0.01


def test_unbiased_recovery_of_injected_effect_over_repeated_randomisations(res):
    mc = res["monte_carlo_with_effect"]
    truth = mc["truth"]["m04_units"]
    for k in ("unadjusted", "cuped", "stratified"):
        m = mc["metrics"]["m04_units"][k]
        assert abs(m["bias"]) < 0.25 * truth, (k, m)
        assert 0.90 <= m["ci_coverage"] <= 0.99


def test_null_experiment_holds_size(res):
    for k in ("unadjusted", "cuped"):
        for met in E.METRICS:
            assert 0.01 <= res["monte_carlo_null_AA"]["metrics"][met][k]["reject_rate"] <= 0.10


def test_negative_controls_show_no_effect(res):
    mc = res["monte_carlo_with_effect"]["metrics"]
    for met in ("orders", "other_food_units"):
        assert abs(mc[met]["unadjusted"]["bias"]) < 0.1


def test_holm_controls_family_error(res):
    f = res["monte_carlo_null_AA"]["guardrail_family_any_false_positive"]
    assert f["holm_0.05"] <= f["raw_alpha_0.05"] and f["holm_0.05"] <= 0.08


def test_design_is_underpowered_and_report_says_so(res):
    # honest finding: injected effect is well below the a-priori MDE, so power is low
    assert res["truth"]["m04_units_per_treated_guest"] < res["power_plan"]["mde_unadjusted_units"]
    assert res["monte_carlo_with_effect"]["metrics"]["m04_units"]["unadjusted"]["reject_rate"] < 0.6


def test_cuped_helps_only_as_much_as_pre_period_correlates():
    rng = np.random.default_rng(0); x = rng.normal(size=4000); t = rng.integers(0, 2, 4000)
    y = 2 * x + rng.normal(size=4000) + 0.3 * t
    d0, s0 = E._est_unadjusted(y, t); d1, s1, th = E._est_cuped(y, x, t)
    assert s1 < 0.6 * s0 and abs(d1 - 0.3) < 0.15 and abs(th - 2) < 0.2
    y2 = rng.normal(size=4000) + 0.3 * t
    assert abs(E._est_cuped(y2, x, t)[1] / E._est_unadjusted(y2, t)[1] - 1) < 0.05


def test_holm_matches_known_values():
    assert np.allclose(E.holm(np.array([0.01, 0.04, 0.03])), [0.03, 0.06, 0.06])
