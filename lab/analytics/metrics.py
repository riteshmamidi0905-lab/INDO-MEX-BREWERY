"""Semantic layer: metric definitions live in metrics.json; this module evaluates them on the mart and on the source tables and reconciles."""
import json
import os

from nasha_lab import world

from . import config as C
from . import synth

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS = {"{{OTHER_FOOD}}": repr(C.OTHER_COST_PCT_OF_PRICE["food"]), "{{FIXED_BEER}}": repr(C.FIXED_UNIT_COST_USD["beer"]), "{{FIXED_NA}}": repr(C.FIXED_UNIT_COST_USD["na"])}
REQUIRED = ["name", "label", "grain", "group_by", "unit", "formula", "owner", "caveats", "additive", "assumption_dependent"]


def load():
    with open(os.path.join(HERE, "metrics.json"), encoding="utf-8") as f:
        return json.load(f)


def _sub(sql):
    for k, v in TOKENS.items():
        sql = sql.replace(k, v)
    return sql


def _lines(con):
    return con.execute("SELECT o.location_id, o.order_date, l.item_id, l.qty, l.unit_price_cents FROM src_fact_order_line l JOIN src_fact_order o USING(order_id)").fetchall()


def _usage_py(con):
    use = synth.usage_by_day([(s, d, i, q) for s, d, i, q, _p in _lines(con)])
    out = {}
    for (site, ing, _day), v in use.items():
        out.setdefault(site, {}); out[site][ing] = out[site].get(ing, 0.0) + v
    return out


def _py(name, con):
    if name == "usage_kg_by_site":
        return {s: sum(v.values()) for s, v in _usage_py(con).items()}
    if name == "contribution_margin_by_site":
        cat = dict(con.execute("SELECT item_id, category FROM src_dim_menu_item"))
        sales, other, fixed = {}, {}, {}
        for s, d, item, q, p in _lines(con):
            c = cat[item]; sales[s] = sales.get(s, 0) + q * p / 100.0
            other[s] = other.get(s, 0) + q * p / 100.0 * C.OTHER_COST_PCT_OF_PRICE.get(c, 0)
            fixed[s] = fixed.get(s, 0) + q * C.FIXED_UNIT_COST_USD.get(c, 0)
        ing = {s: sum(kg * C.COST_PER_KG[i] for i, kg in v.items()) for s, v in _usage_py(con).items()}
        return {s: sales[s] - ing[s] - other[s] - fixed[s] for s in sales}
    if name == "waste_rate_by_site":
        w = {}
        # independent path: re-run the (deterministic) simulation from the source tables
        sim = synth.simulate_inventory(synth.usage_by_day([(s, d, i, q) for s, d, i, q, _p in _lines(con)]), int(con.execute("SELECT v FROM meta WHERE k='seed'").fetchone()[0]))
        for s, _i, _d, _r, q in sim["waste"]:
            w[s] = w.get(s, 0) + q
        u = {s: sum(v.values()) for s, v in _usage_py(con).items()}
        return {s: w.get(s, 0) / u[s] for s in u}
    if name == "count_variance_by_site":
        sim = synth.simulate_inventory(synth.usage_by_day([(s, d, i, q) for s, d, i, q, _p in _lines(con)]), int(con.execute("SELECT v FROM meta WHERE k='seed'").fetchone()[0]))
        use = synth.usage_by_day([(s, d, i, q) for s, d, i, q, _p in _lines(con)])
        waste = {}
        for s, i, d, _r, q in sim["waste"]:
            waste[(s, i, d)] = waste.get((s, i, d), 0) + q
        rec = {}
        for p in sim["pos"]:
            if p["received_day"] is not None:
                rec[(p["site"], p["ingredient"], p["received_day"])] = rec.get((p["site"], p["ingredient"], p["received_day"]), 0) + p["qty_received"]
        snaps = {(s, i, d): q for s, i, d, q in sim["snapshots"]}
        var, exp = {}, {}
        for (s, i, d), q in snaps.items():
            if d == 0:
                continue
            pd_ = d - 7
            e = snaps[(s, i, pd_)] + sum(rec.get((s, i, x), 0) for x in range(pd_ + 1, d + 1)) - sum(use.get((s, i, x), 0) for x in range(pd_, d)) - sum(waste.get((s, i, x), 0) for x in range(pd_, d))
            var[s] = var.get(s, 0) + (q - e); exp[s] = exp.get(s, 0) + e
        return {s: var[s] / exp[s] for s in var}
    if name in ("on_time_by_supplier", "lead_time_by_supplier"):
        sim = synth.simulate_inventory(synth.usage_by_day([(s, d, i, q) for s, d, i, q, _p in _lines(con)]), int(con.execute("SELECT v FROM meta WHERE k='seed'").fetchone()[0]))
        a = {}
        for p in sim["pos"]:
            if p["received_day"] is None:
                continue
            a.setdefault(p["supplier"], []).append(p)
        if name == "on_time_by_supplier":
            return {s: sum(1 for p in v if p["received_day"] <= p["expected_day"]) / len(v) for s, v in a.items()}
        return {s: sum(p["received_day"] - p["order_day"] for p in v) / len(v) for s, v in a.items()}
    raise KeyError(name)


def compute(con, metric, source="mart"):
    """Return {group: value}. source 'mart' evaluates mart_sql; 'raw' evaluates the independent source-side definition."""
    if source == "mart":
        return {g: v for g, v in con.execute(_sub(metric["mart_sql"])).fetchall()}
    if "raw_sql" in metric:
        return {g: v for g, v in con.execute(_sub(metric["raw_sql"])).fetchall()}
    return _py(metric["raw_python"], con)


def reconcile(con, tol=1e-6):
    rows = []
    for m in load()["metrics"]:
        a, b = compute(con, m, "mart"), compute(con, m, "raw")
        keys = sorted(set(a) | set(b))
        worst = max((abs((a.get(k) or 0) - (b.get(k) or 0)) for k in keys), default=0.0)
        rows.append({"metric": m["name"], "groups": len(keys), "max_abs_diff": worst, "ok": set(a) == set(b) and worst <= tol,
                     "mart": {k: a.get(k) for k in keys}, "source": {k: b.get(k) for k in keys}})
    return rows
