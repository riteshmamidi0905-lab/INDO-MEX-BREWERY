"""A SYNTHETIC experiment on mart data with a KNOWN injected effect: does the analysis recover it?

Scenario (SIMULATED): a menu-card placement change for the appetizer 'Mango Habanero Gobi' (legacy id M04) shown to a random half of the synthetic
guests during the last four weeks. Injected truth: each order of a treated guest gains one M04 unit with probability P_ADD; nothing else changes
(orders per guest and all other items have a true effect of ZERO, which makes them honest guardrail / negative-control metrics).
NASHA has no guests and no placement test; this exercises the method (design, power, CUPED, stratification, guardrails, multiplicity), not a result.
"""
import hashlib

import numpy as np
from scipy import stats

from . import mart

P_ADD = 0.10             # injected truth: probability a treated order gains one M04 unit
M04_PRICE_USD = 12.0     # placeholder price from the lab generator
PRE_WEEKS = range(0, 4)
EXP_WEEKS = range(4, 8)
ALPHA = 0.05
METRICS = ["m04_units", "orders", "other_food_units", "spend_usd"]    # primary first; the other three are guardrails / negative controls
Z = lambda p: stats.norm.ppf(p)


def guest_panel(con):
    """Per-guest arrays for the pre and experiment windows, from the mart."""
    q = """SELECT o.guest_key, d.week_index, COUNT(DISTINCT o.order_key),
                  SUM(CASE WHEN i.item_id='M04' THEN l.qty ELSE 0 END), SUM(CASE WHEN i.item_id<>'M04' AND i.category='food' THEN l.qty ELSE 0 END), SUM(l.gross_sales_cents)/100.0
           FROM fact_order o JOIN dim_date d USING(date_key) JOIN fact_order_line l ON l.order_key=o.order_key JOIN dim_menu_item i ON i.item_key=l.item_key
           WHERE o.guest_key<>0 GROUP BY o.guest_key, d.week_index"""
    guests = [g for g, in con.execute("SELECT guest_key FROM dim_guest WHERE guest_key<>0 ORDER BY 1")]
    ix = {g: i for i, g in enumerate(guests)}
    pre = np.zeros((len(guests), 4)); win = np.zeros((len(guests), 4))     # columns follow METRICS: m04_units, orders, other_food_units, spend_usd
    for g, w, n, m04, oth, sp in con.execute(q):
        tgt = pre if w in PRE_WEEKS else win
        tgt[ix[g]] += [m04, n, oth, sp]
    return guests, pre, win


def assign(guests, salt):
    """Deterministic hash assignment at first contact (50/50)."""
    return np.array([int(hashlib.sha256(f"{salt}:{g}".encode()).hexdigest(), 16) % 2 for g in guests])


def inject(win, treat, rng, p_add=P_ADD):
    out = win.copy()
    adds = rng.binomial(win[:, 1].astype(int), p_add) * treat           # extra M04 units for treated guests
    out[:, 0] += adds; out[:, 3] += adds * M04_PRICE_USD
    return out


def _est_unadjusted(y, t):
    y1, y0 = y[t == 1], y[t == 0]
    d = y1.mean() - y0.mean(); se = np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0))
    return d, se


def _est_cuped(y, x, t):
    xc = x - x.mean(); theta = np.cov(y, x, ddof=1)[0, 1] / x.var(ddof=1) if x.var(ddof=1) > 0 else 0.0
    return _est_unadjusted(y - theta * xc, t) + (theta,)


def _est_strat(y, x, t, k=3):
    """Post-stratified difference: strata = terciles of the pre-period covariate; weights = stratum share."""
    qs = np.quantile(x, np.linspace(0, 1, k + 1)[1:-1]); s = np.searchsorted(qs, x, side="right")
    d = v = 0.0
    for j in range(k):
        m = s == j
        if (t[m] == 1).sum() < 2 or (t[m] == 0).sum() < 2: continue
        w = m.mean(); dj, sj = _est_unadjusted(y[m], t[m]); d += w * dj; v += w * w * sj * sj
    return d, np.sqrt(v)


def analyse(pre, post, treat):
    """Return per-metric estimates (unadjusted, CUPED, stratified), p-values, Holm-adjusted p for the guardrail family."""
    res = {}
    for j, name in enumerate(METRICS):
        y, x = post[:, j], pre[:, j]
        d0, s0 = _est_unadjusted(y, treat); d1, s1, th = _est_cuped(y, x, treat); d2, s2 = _est_strat(y, x, treat)
        res[name] = {"unadjusted": {"est": d0, "se": s0}, "cuped": {"est": d1, "se": s1, "theta": th, "var_reduction": 1 - (s1 / s0) ** 2 if s0 > 0 else 0.0},
                     "stratified": {"est": d2, "se": s2}, "pre_post_corr": float(np.corrcoef(y, x)[0, 1])}
        for k in ("unadjusted", "cuped", "stratified"):
            r = res[name][k]; r["p"] = float(2 * (1 - stats.norm.cdf(abs(r["est"] / r["se"])))); r["ci95"] = [r["est"] - 1.96 * r["se"], r["est"] + 1.96 * r["se"]]
    return res


def holm(ps, alpha=ALPHA):
    order = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i]); adj[i] = min(1.0, run)
    return adj


def power_plan(pre, n, p_add=P_ADD):
    """A-priori MDE for the primary metric using the PRE-period sd as the variance proxy (what a planner could know before launch)."""
    sd = pre[:, 0].std(ddof=1)
    per_arm = n / 2
    mde = (Z(1 - ALPHA / 2) + Z(0.8)) * sd * np.sqrt(2 / per_arm)
    return {"pre_period_sd_m04_units": float(sd), "guests": int(n), "per_arm": per_arm, "mde_unadjusted_units": float(mde)}


def monte_carlo(pre, win, reps=500, p_add=P_ADD, seed=11):
    """Re-randomise and re-inject `reps` times on the same guest panel. Finite-population truth = p_add * mean(window orders)."""
    rng = np.random.default_rng(seed); n = len(pre)
    truth = {"m04_units": p_add * win[:, 1].mean(), "orders": 0.0, "other_food_units": 0.0, "spend_usd": p_add * win[:, 1].mean() * M04_PRICE_USD}
    rec = {m: {k: {"est": [], "cover": [], "reject": []} for k in ("unadjusted", "cuped", "stratified")} for m in METRICS}
    fam_any_raw = fam_any_holm = 0
    for _ in range(reps):
        t = rng.integers(0, 2, n)
        if t.sum() < 5 or t.sum() > n - 5: continue
        post = inject(win, t, rng, p_add); r = analyse(pre, post, t)
        for m in METRICS:
            for k in ("unadjusted", "cuped", "stratified"):
                e = r[m][k]; rec[m][k]["est"].append(e["est"]); rec[m][k]["cover"].append(e["ci95"][0] <= truth[m] <= e["ci95"][1]); rec[m][k]["reject"].append(e["p"] < ALPHA)
        fam = [r[m]["cuped"]["p"] for m in METRICS[1:]]
        fam_any_raw += any(p < ALPHA for p in fam); fam_any_holm += any(a < ALPHA for a in holm(np.array(fam)))
    out = {"reps": reps, "p_add": p_add, "truth": truth, "metrics": {}}
    for m in METRICS:
        out["metrics"][m] = {}
        for k in ("unadjusted", "cuped", "stratified"):
            e = np.array(rec[m][k]["est"])
            out["metrics"][m][k] = {"mean_est": float(e.mean()), "bias": float(e.mean() - truth[m]), "sd_est": float(e.std(ddof=1)),
                                    "ci_coverage": float(np.mean(rec[m][k]["cover"])), "reject_rate": float(np.mean(rec[m][k]["reject"]))}
    out["guardrail_family_any_false_positive"] = {"raw_alpha_0.05": fam_any_raw / reps, "holm_0.05": fam_any_holm / reps}
    return out


def run(seed=1, reps=500):
    con, _ = mart.build(seed)
    guests, pre, win = guest_panel(con)
    n = len(guests)
    treat = assign(guests, f"exp-{seed}")
    rng = np.random.default_rng(1000 + seed)
    post = inject(win, treat, rng)
    res = analyse(pre, post, treat)
    fam = np.array([res[m]["cuped"]["p"] for m in METRICS[1:]]); adj = holm(fam)
    for m, a in zip(METRICS[1:], adj): res[m]["holm_adjusted_p_cuped"] = float(a)
    exp_orders = float(win[:, 1].mean())
    truth_primary = P_ADD * exp_orders
    srm_p = float(stats.chisquare([int((treat == 1).sum()), int((treat == 0).sum())]).pvalue)
    plan = power_plan(pre, n)
    mc_effect, mc_null = monte_carlo(pre, win, reps, P_ADD), monte_carlo(pre, win, reps, 0.0, seed=12)
    primary = res["m04_units"]
    recovered = {k: bool(primary[k]["ci95"][0] <= truth_primary <= primary[k]["ci95"][1]) for k in ("unadjusted", "cuped", "stratified")}
    return {
        "synthetic": True, "disclaimer": "SIMULATED experiment on synthetic guests with an injected effect. No real guests, no real placement test.",
        "design": {"unit": "synthetic guest (dim_guest), assigned 50/50 by seeded hash at first contact", "pre_weeks": [0, 3], "experiment_weeks": [4, 7], "guests": n,
                   "treated": int(treat.sum()), "control": int((treat == 0).sum()), "primary_metric": "m04_units per guest in the experiment window",
                   "guardrails_negative_controls": METRICS[1:], "multiplicity": "primary tested alone at 0.05; the 3 guardrail metrics are a Holm-corrected family at 0.05",
                   "injected_effect": f"each order of a treated guest gains one M04 unit with probability {P_ADD}; all else unchanged"},
        "srm_chi2_p": srm_p, "power_plan": plan,
        "truth": {"m04_units_per_treated_guest": truth_primary, "mean_window_orders_per_guest": exp_orders, "spend_usd_per_treated_guest": truth_primary * M04_PRICE_USD},
        "single_run": {m: res[m] for m in METRICS}, "primary_ci_contains_truth": recovered,
        "monte_carlo_with_effect": mc_effect, "monte_carlo_null_AA": mc_null,
        "causal_limitations": [
            "Randomisation is simulated; the 'effect' is whatever the injection code says. Recovering it proves the ANALYSIS is unbiased on this data-generating process, not that any real menu change works.",
            "No guests exist: guest ids come from a seeded assignment process (config.GUEST_*). Real repeat-visit dynamics, interference between guests at one table, novelty effects and seasonality are absent.",
            "The effect is on a single appetizer count; cannibalisation, margin and long-run retention are not modelled, so the experiment cannot say whether the change is good for the business.",
            "Only 4 weeks and a few hundred guests: heavy tails, repeated visits per guest and new guests arriving after assignment are handled crudely (new guests have a pre-period covariate of zero).",
            "Monte Carlo coverage is relative to the finite-population truth of this guest panel (fixed baseline behaviour, random assignment and injection), i.e. randomisation inference, not a superpopulation claim.",
            "Same author wrote the injection and the analysis (no independent review)."],
    }
