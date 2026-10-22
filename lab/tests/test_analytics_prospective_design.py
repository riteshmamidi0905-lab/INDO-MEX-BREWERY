"""Prospective design: closed form vs seeded Monte Carlo; the original experiment is unchanged and labelled as historical."""
import json
import os

import pytest

from analytics import prospective_design as P, render_docs as RD

EXP = RD.R("experiment")
DELTA = EXP["truth"]["m04_units_per_treated_guest"]
SD = EXP["power_plan"]["pre_period_sd_m04_units"]
RHO = EXP["single_run"]["m04_units"]["pre_post_corr"]


def test_closed_form_known_values():
    assert P.n_per_arm(DELTA, SD, 0.8) == 955 and P.n_per_arm(DELTA, SD, 0.9) == 1279
    assert P.n_per_arm(DELTA, SD, 0.8, RHO) < 955 and P.n_per_arm(DELTA, SD, 0.9, RHO) < 1279
    assert abs(P.analytic_power(955, DELTA, SD) - 0.8) < 0.002


@pytest.mark.parametrize("power", [0.8, 0.9])
@pytest.mark.parametrize("cuped", [False, True])
def test_closed_form_agrees_with_monte_carlo(power, cuped):
    rho = RHO if cuped else 0.0
    n = P.n_per_arm(DELTA, SD, power, rho)
    mc = P.mc_power(n, DELTA, SD, rho, cuped)
    assert abs(mc - P.analytic_power(n, DELTA, SD, rho)) < 0.025
    assert mc >= power - 0.015


def test_monte_carlo_is_deterministic_and_null_holds_alpha():
    assert P.mc_power(200, DELTA, SD, 0.0, False, reps=300) == P.mc_power(200, DELTA, SD, 0.0, False, reps=300)
    assert abs(P.mc_power(955, 0.0, SD, 0.0, False, seed=5) - 0.05) < 0.02


def test_committed_results_match_and_original_experiment_is_underpowered():
    res = RD.R("prospective_design")
    assert all(x["reaches_target_within_mc_error"] for x in res["plan"])
    assert res["historical_experiment"]["analytic_power_unadjusted"] < 0.3
    assert res["inputs"]["injected_effect_units_per_treated_guest"] == pytest.approx(DELTA, abs=1e-5)
    assert "NOT retroactively resized" in res["historical_experiment"]["status"]
    doc = open(os.path.join(RD.DOCS, "ANALYTICS-EVALUATION.md"), encoding="utf-8").read()
    assert "ANALYTICS-PROSPECTIVE-DESIGN.md" in doc and "not retroactively resized" in doc
    assert EXP["power_plan"]["per_arm"] == 170.5   # the original experiment is unchanged
