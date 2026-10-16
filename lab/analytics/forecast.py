"""Forecasting baselines with a rolling-origin backtest on SYNTHETIC per-ingredient daily usage.

Because the data are synthetic (a generator with a known weekday pattern and a dated recipe change), forecast accuracy here says NOTHING about
real demand or real forecastability. What this demonstrates is the method: baselines first, honest rolling-origin evaluation, skill versus naive,
paired uncertainty, and interval calibration.
"""
import datetime as dt

import numpy as np

from . import mart
from . import synth

H = 7              # forecast horizon (days)
SEASON = 7
MIN_TRAIN = 28
ORIGINS = [28, 35, 42, 49]
MODELS = ["naive", "seasonal_naive", "moving_average_7", "seasonal_mean", "ses", "holt_winters_add"]


def f_naive(x, h=H): return np.repeat(x[-1], h)
def f_snaive(x, h=H): return np.array([x[len(x) - SEASON + (i % SEASON)] for i in range(h)])
def f_ma7(x, h=H): return np.repeat(x[-7:].mean(), h)


def f_seasonal_mean(x, h=H, weeks=4):
    n = len(x)
    out = []
    for i in range(h):
        idx = [n + i - SEASON * k for k in range(1, weeks + 1) if n + i - SEASON * k >= 0 and n + i - SEASON * k < n]
        out.append(np.mean([x[j] for j in idx]))
    return np.array(out)


def _ses_fit(x):
    best = (None, 1e18)
    for a in np.arange(0.05, 1.0, 0.05):
        l, sse = x[0], 0.0
        for v in x[1:]:
            sse += (v - l) ** 2; l = a * v + (1 - a) * l
        if sse < best[1]: best = (a, sse)
    return best[0]


def f_ses(x, h=H):
    a = _ses_fit(x); l = x[0]
    for v in x[1:]: l = a * v + (1 - a) * l
    return np.repeat(l, h)


def _hw_run(x, a, g):
    m = SEASON
    level = x[:m].mean(); seas = list(x[:m] - level); sse = 0.0; n = len(x)
    for t in range(m, n):
        s = seas[t - m]
        pred = level + s; sse += (x[t] - pred) ** 2
        new_level = a * (x[t] - s) + (1 - a) * level
        seas.append(g * (x[t] - new_level) + (1 - g) * s); level = new_level
    return level, seas, sse


def f_hw(x, h=H):
    best = None
    for a in (0.05, 0.1, 0.2, 0.3, 0.5):
        for g in (0.05, 0.1, 0.3, 0.5):
            level, seas, sse = _hw_run(x, a, g)
            if best is None or sse < best[0]: best = (sse, level, seas)
    _s, level, seas = best; n = len(x)
    return np.array([level + seas[n - SEASON + (i % SEASON)] for i in range(h)])


FUNCS = {"naive": f_naive, "seasonal_naive": f_snaive, "moving_average_7": f_ma7, "seasonal_mean": f_seasonal_mean, "ses": f_ses, "holt_winters_add": f_hw}


def insample_sigma(func, x, start=14):
    """Std of the model's own 1-step-ahead errors inside the training window (used for the nominal 80% interval)."""
    errs = [x[t] - func(x[:t], 1)[0] for t in range(start, len(x))]
    return float(np.std(errs, ddof=1)) if len(errs) > 2 else float("nan")


def series_from_mart(con):
    """Dense daily usage per (site, ingredient): zero-filled over the 56 order days."""
    d0 = synth.START
    rows = con.execute("""SELECT s.site_id, g.ingredient, dd.date, u.theoretical_qty FROM fact_usage_daily u JOIN dim_site s USING(site_key)
                          JOIN dim_ingredient g USING(ingredient_key) JOIN dim_date dd USING(date_key)""").fetchall()
    out = {}
    for s, i, d, q in rows:
        out.setdefault((s, i), np.zeros(synth.N_USAGE_DAYS))[(dt.date.fromisoformat(d) - d0).days] = q
    return out


def backtest(seeds=(1, 2, 3, 4, 5)):
    recs = []     # (seed, site, ingredient, origin, model, actual[7], fcst[7], sigma)
    for seed in seeds:
        con, _ = mart.build(seed)
        for (site, ing), x in sorted(series_from_mart(con).items()):
            for o in ORIGINS:
                train, actual = x[:o], x[o:o + H]
                for m in MODELS:
                    f = FUNCS[m](train)
                    recs.append((seed, site, ing, o, m, actual, f, insample_sigma(FUNCS[m], train)))
    return recs


def metrics(rows):
    a = np.concatenate([r[5] for r in rows]); f = np.concatenate([r[6] for r in rows])
    ae = np.abs(f - a); nz = a > 1e-9
    return {"n_forecasts": len(rows), "MAE": float(ae.mean()), "WAPE": float(ae.sum() / a.sum()), "MAPE_pct_nonzero_days": float(100 * (ae[nz] / a[nz]).mean()),
            "bias_pct_of_actual": float(100 * (f - a).sum() / a.sum()), "zero_actual_days": int((~nz).sum())}


def interval_coverage(rows, z=1.2816):
    hit = tot = 0; width = []
    for r in rows:
        s = r[7]
        if not np.isfinite(s): continue
        lo, hi = r[6] - z * s, r[6] + z * s
        hit += int(((r[5] >= lo) & (r[5] <= hi)).sum()); tot += len(r[5]); width.append(float((hi - lo).mean()))
    return {"nominal": 0.80, "empirical": round(hit / tot, 4), "mean_width": round(float(np.mean(width)), 4), "points": tot}


def paired_bootstrap(recs, model, base, n_boot=2000, seed=7):
    """Bootstrap over (seed, series, origin) units: difference in WAPE (model - base); negative = model better."""
    key = lambda r: (r[0], r[1], r[2], r[3])
    a = {key(r): r for r in recs if r[4] == model}; b = {key(r): r for r in recs if r[4] == base}
    ks = sorted(a)
    ea = np.array([np.abs(a[k][6] - a[k][5]).sum() for k in ks]); eb = np.array([np.abs(b[k][6] - b[k][5]).sum() for k in ks]); act = np.array([a[k][5].sum() for k in ks])
    rng = np.random.default_rng(seed); diffs = []
    for _ in range(n_boot):
        i = rng.integers(0, len(ks), len(ks)); diffs.append((ea[i].sum() - eb[i].sum()) / act[i].sum())
    obs = (ea.sum() - eb.sum()) / act.sum()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"wape_diff_vs_" + base: round(float(obs), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)], "units": len(ks),
            "win_rate_units": round(float((ea < eb).mean()), 4)}


def run(seeds=(1, 2, 3, 4, 5)):
    recs = backtest(seeds)
    out = {"synthetic": True, "disclaimer": "SYNTHETIC usage series from the lab generator; forecast accuracy says nothing about real demand.",
           "design": {"horizon_days": H, "origins": ORIGINS, "min_train_days": MIN_TRAIN, "seeds": list(seeds), "series_per_seed": 24, "models": MODELS,
                      "note": "expanding-window rolling origin; 4 origins per series; units are NOT independent across origins of one series"},
           "overall": {}, "by_ingredient_wape": {}, "paired_vs_naive": {}, "paired_vs_seasonal_naive": {}, "interval_80": {}}
    for m in MODELS:
        rows = [r for r in recs if r[4] == m]
        out["overall"][m] = {k: round(v, 4) if isinstance(v, float) else v for k, v in metrics(rows).items()}
        out["interval_80"][m] = interval_coverage(rows)
        out["by_ingredient_wape"][m] = {ing: round(metrics([r for r in rows if r[2] == ing])["WAPE"], 4) for ing in sorted({r[2] for r in rows})}
        if m != "naive": out["paired_vs_naive"][m] = paired_bootstrap(recs, m, "naive")
        if m != "seasonal_naive": out["paired_vs_seasonal_naive"][m] = paired_bootstrap(recs, m, "seasonal_naive")
    # structural break: corn masa series contains the dated recipe change (M04 loses its tortilla on the SCD2 change date)
    pre = [r for r in recs if r[2] == "corn masa" and r[3] == 49]
    out["recipe_change_note"] = {"origin_49_corn_masa_wape": {m: round(metrics([r for r in pre if r[4] == m])["WAPE"], 4) for m in MODELS},
                                 "comment": "origin 49 (forecast days 49-55) is entirely after the 2026-04-13 recipe change (day 42); origin 35/42 windows straddle or precede it"}
    best = min(MODELS, key=lambda m: out["overall"][m]["WAPE"])
    out["best_by_wape"] = best
    return out
