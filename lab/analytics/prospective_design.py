"""PROSPECTIVE sample-size design for the synthetic M04 placement experiment. SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.

The original experiment (analytics/experiment.py) was deliberately underpowered and stays unchanged as historical evidence; it is NOT retroactively
resized. This module answers a different, forward-looking question: how many synthetic guests PER ARM would a properly sized version of the same
test need? Inputs are the injected effect size and the pre-period SD used in that experiment, plus the observed pre/post correlation for CUPED.

Closed form (two-sided z test, equal arms, alpha = 0.05):
    unadjusted:  n = 2 * (z_{1-alpha/2} + z_{power})^2 * sd^2 / delta^2
    CUPED:       the same with sd^2 replaced by sd^2 * (1 - rho^2)
A seeded, deterministic Monte Carlo (stylised bivariate-normal data with the same sd, rho and delta) then confirms that the chosen n reaches the
target power. No claim about any real business outcome: all inputs come from the simulation.
"""
import math

import numpy as np
from scipy import stats

ALPHA = 0.05
POWERS = (0.80, 0.90)
MC_REPS = 4000
MC_SEED = 20260101
EFFECT_MULTIPLIERS = (0.5, 1.0, 1.5, 2.0, 3.0)      # sensitivity: multiples of the injected effect
SD_MULTIPLIERS = (0.75, 1.0, 1.25)                  # sensitivity: multiples of the pre-period SD
RHO_GRID = (0.0, 0.2, 0.4, 0.6)                     # sensitivity of CUPED to the pre/post correlation
Z = stats.norm.ppf


def n_per_arm(delta, sd, power, rho=0.0, alpha=ALPHA):
    """Closed-form per-arm n (rounded up) for the two-sided z test; CUPED when rho > 0."""
    var = sd ** 2 * (1 - rho ** 2)
    return int(math.ceil(2 * (Z(1 - alpha / 2) + Z(power)) ** 2 * var / delta ** 2))


def analytic_power(n, delta, sd, rho=0.0, alpha=ALPHA):
    se = math.sqrt(2 * sd ** 2 * (1 - rho ** 2) / n)
    z = Z(1 - alpha / 2)
    return float(stats.norm.cdf(delta / se - z) + stats.norm.cdf(-delta / se - z))


def mc_power(n, delta, sd, rho, cuped, reps=MC_REPS, seed=MC_SEED, alpha=ALPHA, chunk=500):
    """Rejection rate of a two-sided z test over `reps` simulated experiments (delta = 0 gives the empirical type I error).

    Stylised data: pre x ~ N(0, sd^2), post y = rho*x + sqrt(1-rho^2)*e + delta*T with e ~ N(0, sd^2), n guests in each arm. CUPED estimates theta
    from the pooled sample (as experiment.py does) and tests y - theta*x."""
    rng = np.random.default_rng(seed)
    rej = 0
    zc = Z(1 - alpha / 2)
    done = 0
    while done < reps:
        m = min(chunk, reps - done)
        x = rng.normal(0, sd, (m, 2 * n))
        e = rng.normal(0, sd, (m, 2 * n))
        y = rho * x + math.sqrt(1 - rho ** 2) * e
        y[:, n:] += delta                                   # second half is the treated arm
        if cuped:
            xc = x - x.mean(axis=1, keepdims=True)
            theta = (xc * (y - y.mean(axis=1, keepdims=True))).sum(axis=1) / (xc ** 2).sum(axis=1)
            y = y - theta[:, None] * xc
        y0, y1 = y[:, :n], y[:, n:]
        d = y1.mean(axis=1) - y0.mean(axis=1)
        se = np.sqrt(y1.var(axis=1, ddof=1) / n + y0.var(axis=1, ddof=1) / n)
        rej += int((np.abs(d / se) > zc).sum())
        done += m
    return rej / reps


def run(delta, sd, rho, original_per_arm, reps=MC_REPS):
    """delta = injected effect (M04 units per treated guest), sd = pre-period SD, rho = observed pre/post correlation (from the experiment)."""
    plan = []
    for p in POWERS:
        for est, r in (("unadjusted", 0.0), ("cuped", rho)):
            n = n_per_arm(delta, sd, p, r)
            mc = mc_power(n, delta, sd, r, est == "cuped", reps)
            plan.append({"target_power": p, "estimator": est, "rho_used": r, "n_per_arm": n, "n_total": 2 * n,
                         "analytic_power_at_n": analytic_power(n, delta, sd, r), "monte_carlo_power_at_n": mc,
                         "monte_carlo_reps": reps, "monte_carlo_se": math.sqrt(mc * (1 - mc) / reps),
                         "reaches_target_within_mc_error": bool(mc >= p - 2.5 * math.sqrt(p * (1 - p) / reps))})
    null_checks = {est: mc_power(n_per_arm(delta, sd, 0.8, r), 0.0, sd, r, est == "cuped", reps, seed=MC_SEED + 1)
                   for est, r in (("unadjusted", 0.0), ("cuped", rho))}
    sens = []
    for em in EFFECT_MULTIPLIERS:
        for sm in SD_MULTIPLIERS:
            d_, s_ = delta * em, sd * sm
            row = {"effect_multiplier": em, "effect_units_per_guest": d_, "sd_multiplier": sm, "sd": s_}
            for p in POWERS:
                row[f"n_per_arm_unadjusted_{int(p * 100)}"] = n_per_arm(d_, s_, p)
                row[f"n_per_arm_cuped_{int(p * 100)}"] = n_per_arm(d_, s_, p, rho)
            sens.append(row)
    rho_sens = [{"rho": r, "n_per_arm_80": n_per_arm(delta, sd, 0.8, r), "n_per_arm_90": n_per_arm(delta, sd, 0.9, r)} for r in RHO_GRID]
    return {
        "synthetic": True,
        "disclaimer": "SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED. Sample sizes for a SIMULATED test on synthetic guests; no real-business outcome is claimed.",
        "inputs": {"alpha_two_sided": ALPHA, "injected_effect_units_per_treated_guest": delta, "pre_period_sd_m04_units": sd, "observed_pre_post_corr": rho,
                   "source": "results/analytics/experiment.json (power_plan, truth, single_run.m04_units.pre_post_corr)"},
        "historical_experiment": {"per_arm": original_per_arm, "analytic_power_unadjusted": analytic_power(original_per_arm, delta, sd),
                                  "status": "deliberately underpowered; kept unchanged as historical evidence; NOT retroactively resized"},
        "plan": plan, "type_I_error_at_planned_n_80": null_checks, "sensitivity": sens, "cuped_rho_sensitivity": rho_sens,
        "assumptions": [
            "Two-sided z test at alpha 0.05, two equal arms, individual guests as the unit of randomisation.",
            "The effect is the injected truth of the simulation (about 0.23 M04 units per treated guest); the SD is the pre-period SD of M04 units per guest, used as the variance proxy for the experiment window.",
            "CUPED reduces the variance by the factor (1 - rho^2), with rho the pre/post correlation observed in the one simulated run; with rho about 0.2 the saving is small.",
            "The Monte Carlo uses stylised bivariate-normal data with the same SD, rho and effect, not the skewed count data of the mart: it confirms the arithmetic and the estimator, not the shape of real data. Heavy tails, repeated visits and clustering would need more guests.",
            "Seeded and deterministic (seed %d, %d repetitions). Monte Carlo standard error of a power estimate is about 0.6 points at 80%%." % (MC_SEED, reps),
            "Not covered: multiple metrics (the Holm family of guardrails), sequential looks, attrition, interference between guests, novelty effects, a real baseline. NASHA has no guests; this is a method exercise."],
    }
