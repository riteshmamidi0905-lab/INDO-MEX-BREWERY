"""Demand forecasting and labor analytics over the published warehouse (SYNTHETIC data).

Three forecasters on a daily series, all pure numpy: seasonal-naive (same weekday last week), seasonal-mean (mean of the last 4 same weekdays) and
additive Holt-Winters with weekly seasonality (smoothing parameters picked by grid search on the training window only). Evaluation is a rolling-origin
backtest (no look-ahead): for each origin, fit on data before it, forecast the next `horizon` days, score against what actually happened.
The simulator has weekly seasonality by construction, so good scores here mean the method recovers a known structure, not that real demand is forecastable.
"""
import numpy as np
import pandas as pd

from . import analytics

SEASON = 7


def seasonal_naive(y, h):
    y = np.asarray(y, float)
    return np.array([y[len(y) - SEASON + (i % SEASON)] for i in range(h)])


def seasonal_mean(y, h, k=4):
    y = np.asarray(y, float)
    k = min(k, len(y) // SEASON)
    prof = np.mean([y[len(y) - SEASON * (j + 1): len(y) - SEASON * j] for j in range(k)], axis=0)
    return np.array([prof[i % SEASON] for i in range(h)])


def _hw_fit(y, a, b, g):
    n = len(y)
    level = np.mean(y[:SEASON])
    trend = (np.mean(y[SEASON:2 * SEASON]) - np.mean(y[:SEASON])) / SEASON
    seas = list(y[:SEASON] - level)
    sse = 0.0
    for t in range(SEASON, n):
        s = seas[t - SEASON]
        pred = level + trend + s
        sse += (y[t] - pred) ** 2
        new_level = a * (y[t] - s) + (1 - a) * (level + trend)
        trend = b * (new_level - level) + (1 - b) * trend
        seas.append(g * (y[t] - new_level) + (1 - g) * s)
        level = new_level
    return level, trend, seas, sse


def holt_winters(y, h):
    y = np.asarray(y, float)
    if len(y) < 3 * SEASON:
        return seasonal_naive(y, h)
    best = None
    for a in (.1, .3, .5):
        for b in (.01, .05):
            for g in (.1, .3):
                r = _hw_fit(y, a, b, g)
                if best is None or r[3] < best[3]:
                    best = r
    level, trend, seas, _ = best
    n = len(y)
    return np.array([level + (i + 1) * trend + seas[n - SEASON + (i % SEASON)] for i in range(h)])


METHODS = {"seasonal_naive": seasonal_naive, "seasonal_mean_4w": seasonal_mean, "holt_winters_weekly": holt_winters}


def backtest(y, horizon=28, origins=4, min_train=8 * SEASON):
    """Rolling origin, step = horizon. Returns {method: {"wape":..,"mae":..,"bias":..}} and the number of origins used."""
    y = np.asarray(y, float)
    res = {m: {"abs": 0.0, "act": 0.0, "err": 0.0} for m in METHODS}
    used = 0
    for k in range(origins):
        end = len(y) - horizon * k
        start = end - horizon
        if start < min_train:
            break
        used += 1
        train, act = y[:start], y[start:end]
        for m, f in METHODS.items():
            p = f(train, horizon)
            res[m]["abs"] += np.abs(p - act).sum(); res[m]["act"] += act.sum(); res[m]["err"] += (p - act).sum()
    n = used * horizon
    return {m: {"wape": r["abs"] / r["act"] if r["act"] else None, "mae": r["abs"] / n if n else None, "bias": r["err"] / n if n else None} for m, r in res.items()}, used


def daily_series(con, location_id=None):
    analytics._require_published(con)
    where, par = ("WHERE location_id=?", (location_id,)) if location_id else ("", ())
    df = pd.read_sql_query(f"SELECT date, sum(orders) orders, sum(net_cents) net_cents, sum(actual_labor_hours) actual_h, sum(scheduled_labor_hours) sched_h, sum(labor_cost_cents) labor_cents FROM mart_daily_location {where} GROUP BY date ORDER BY date", con, params=par)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").asfreq("D").fillna(0)


def forecast_report(con, horizon=28):
    """Company-level and top-3-site forecast with backtests; best method chosen by WAPE on the backtest only."""
    out = {}
    sites = [r[0] for r in con.execute("SELECT location_id FROM mart_daily_location GROUP BY 1 ORDER BY sum(orders) DESC LIMIT 3")]
    for key in ["company"] + sites:
        df = daily_series(con, None if key == "company" else key)
        y = df["orders"].to_numpy()
        # drop leading days before the series starts (site not open yet)
        nz = np.nonzero(y)[0]
        y = y[nz[0]:] if len(nz) else y
        bt, used = backtest(y, horizon)
        ok = {m: v for m, v in bt.items() if v["wape"] is not None}
        best = min(ok, key=lambda m: ok[m]["wape"]) if ok else None
        fc = METHODS[best](y, horizon) if best else np.zeros(horizon)
        out[key] = {"history_days": int(len(y)), "backtest_origins": used, "backtest": bt, "best": best, "last_date": str(df.index[-1].date()),
                    "forecast": [round(float(v), 1) for v in fc], "history_tail": [float(v) for v in y[-56:]]}
    return out


def labor_report(con):
    """Labor analytics: scheduled vs actual hours, labor %, productivity by weekday, outlier site-days. Placeholder wages (see DATA-PLATFORM.md)."""
    analytics._require_published(con)
    d = pd.read_sql_query("SELECT date, month, location_id, format, orders, net_cents, scheduled_labor_hours sched, actual_labor_hours act, labor_cost_cents lc, labor_pct_of_sales lp, sales_per_labor_hour_cents spl FROM mart_daily_location", con)
    d["dow"] = pd.to_datetime(d.date).dt.day_name()
    d["var_h"] = d.act - d.sched
    d["var_pct"] = d.var_h / d.sched.where(d.sched > 0)
    by_site = d.groupby("location_id").agg(sched=("sched", "sum"), act=("act", "sum"), net=("net_cents", "sum"), lc=("lc", "sum"), orders=("orders", "sum")).reset_index()
    by_site["var_pct"] = (by_site.act - by_site.sched) / by_site.sched
    by_site["labor_pct"] = by_site.lc / by_site.net
    by_site["orders_per_labor_hr"] = by_site.orders / by_site.act
    dow = d.groupby("dow").agg(net=("net_cents", "sum"), act=("act", "sum"), orders=("orders", "sum")).reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]).reset_index()
    dow["sales_per_labor_hr_cents"] = dow.net / dow.act
    dow["orders_per_labor_hr"] = dow.orders / dow.act
    thr = d.lp.quantile(.95)
    outl = d[d.lp >= thr].sort_values("lp", ascending=False).head(15)[["date", "location_id", "orders", "net_cents", "act", "lp"]]
    heat = d.groupby(["location_id", "month"]).apply(lambda g: g.lc.sum() / g.net_cents.sum() if g.net_cents.sum() else np.nan, include_groups=False).unstack("month")
    return {"by_site": by_site, "dow": dow, "outliers": outl, "p95_labor_pct": float(thr), "heat": heat, "company_var_pct": float((d.act.sum() - d.sched.sum()) / d.sched.sum())}


def labor_plan(fc_orders, orders_per_labor_hr):
    """Scenario, not a schedule: hours needed to serve forecast orders at the historical productivity of the last 8 weeks."""
    return [round(float(o) / orders_per_labor_hr, 1) for o in fc_orders]
