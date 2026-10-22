"""Statistics for product experiments plus a deterministic synthetic experiment portfolio.

SYNTHETIC. Outcomes are simulated from the warehouse's measured baseline with an INJECTED true effect, so the right answer is known and the
analysis can be graded honestly. The portfolio deliberately contains a clear win, an underpowered (inconclusive) test, a null result, a harmful
change, and a broken randomization (sample-ratio mismatch) that must be rejected. Nothing here is a claim about real customers."""
import hashlib
import math

import numpy as np
from scipy import stats


def assign(member_id, exp_id, p_treat=0.5):
    h = int(hashlib.sha256(f"{exp_id}|{member_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "treatment" if h < p_treat else "control"


def two_proportion(x1, n1, x0, n0, alpha=0.05):
    """Treatment (x1/n1) vs control (x0/n0): difference, Wald CI, z-test p."""
    p1, p0 = x1 / n1, x0 / n0
    se = math.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    d = p1 - p0
    z = d / se if se else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    h = stats.norm.ppf(1 - alpha / 2) * se
    return {"diff": d, "ci": (d - h, d + h), "p": p, "control_rate": p0, "treatment_rate": p1}


def welch(a, b, alpha=0.05):
    """a=treatment values, b=control values."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a.mean() - b.mean()
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t, p = stats.ttest_ind(a, b, equal_var=False)
    h = stats.norm.ppf(1 - alpha / 2) * se
    return {"diff": d, "ci": (d - h, d + h), "p": float(p), "control_mean": b.mean(), "treatment_mean": a.mean()}


def srm_check(n_treat, n_control, expected_ratio=0.5, alpha=0.001):
    """Sample-ratio mismatch: chi-square goodness of fit against the planned split. A failure means do not trust the experiment."""
    n = n_treat + n_control
    chi2 = (n_treat - n * expected_ratio) ** 2 / (n * expected_ratio) + (n_control - n * (1 - expected_ratio)) ** 2 / (n * (1 - expected_ratio))
    p = 1 - stats.chi2.cdf(chi2, 1)
    return {"chi2": chi2, "p": p, "ok": p >= alpha}


def n_per_arm(p0, mde_abs, alpha=0.05, power=0.8):
    p1 = p0 + mde_abs
    pb = (p0 + p1) / 2
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return math.ceil(((za * math.sqrt(2 * pb * (1 - pb)) + zb * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2) / mde_abs ** 2)


PORTFOLIO = [  # id, title, injected absolute effect on the 30-day repeat rate, members per arm, arm split, note
    ("E1", "Reorder nudge in the app (clear win, adequately powered)", +0.040, 12000, 0.5, "true effect +4.0 points"),
    ("E2", "Rewards-points banner (real but small effect, underpowered)", +0.008, 1500, 0.5, "true effect +0.8 points with a sample too small to see it"),
    ("E3", "New welcome email subject (no effect)", 0.0, 8000, 0.5, "null by construction"),
    ("E4", "Aggressive discount reminder (harmful)", -0.030, 9000, 0.5, "true effect -3.0 points"),
    ("E5", "Menu-card redesign (randomization bug)", +0.020, 7000, 0.62, "assignment bug: a 62/38 split when 50/50 was planned"),
]


def run_portfolio(base_rate, seed=11):
    rng = np.random.default_rng(seed)
    out = []
    for eid, title, eff, n, split, note in PORTFOLIO:
        nt = int(2 * n * split)
        nc = 2 * n - nt
        xt = int(rng.binomial(nt, min(max(base_rate + eff, 0), 1)))
        xc = int(rng.binomial(nc, base_rate))
        res = two_proportion(xt, nt, xc, nc)
        srm = srm_check(nt, nc, 0.5)
        sig = res["p"] < 0.05
        lo, hi = res["ci"]
        if not srm["ok"]:
            verdict = "REJECT: sample-ratio mismatch; the result cannot be trusted whatever the p-value"
        elif sig and res["diff"] > 0:
            verdict = "WIN: significant improvement"
        elif sig and res["diff"] < 0:
            verdict = "HARM: significant decline; roll back"
        else:
            need = n_per_arm(base_rate, max(abs(eff), 0.01))
            verdict = f"INCONCLUSIVE: the interval includes zero ({lo:+.3f} to {hi:+.3f}); about {need:,} per arm are needed to detect {max(abs(eff), 0.01):.3f}" if eff != 0 else "NO EFFECT detected (consistent with the null)"
        out.append({"id": eid, "title": title, "n_treatment": nt, "n_control": nc, "base_rate": round(base_rate, 4), "injected_effect": eff, "observed_diff": round(res["diff"], 4),
                    "ci95": [round(lo, 4), round(hi, 4)], "p": round(res["p"], 4), "srm_p": round(srm["p"], 6), "srm_ok": srm["ok"], "verdict": verdict, "note": note})
    return out
