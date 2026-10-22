"""SYNTHETIC ingredient-level operations generated from the warehouse's real (simulated) sales: deliveries, weekly counts and measured usage per site, with
INJECTED, KNOWN anomalies so detectors can be scored. Nothing here is a real transaction, supplier, price or loss.

Theoretical usage = units sold x BOM. Actual usage = theoretical x (1 + baseline loss) + injected anomalies. A system only SEES counts and receipts, so
measured usage = opening + receipts - closing (count noise included) : the variance detector works from that, never from the hidden truth.
"""
import hashlib
import sqlite3
from dataclasses import dataclass

import numpy as np

from . import bom as BOM, model


@dataclass(frozen=True)
class Anomaly:
    site: str
    ingredient: str
    kind: str                 # over_portion | spike | unrecorded_transfer
    start_week: int
    weeks: int
    magnitude: float          # fractional change of actual usage


def first_sales_date(wh_path):
    """First calendar date with a sale of any of the five Core 5 items: defines week 0 for the scenario calendar and the synthetic counts."""
    con = sqlite3.connect(f"file:{wh_path}?mode=ro", uri=True)
    r = con.execute("""SELECT min(d.date) FROM fact_order_line f JOIN dim_date d USING(date_key) JOIN dim_product p USING(product_key) WHERE p.item_id IN ('M01','M02','M03','M04','M05')""").fetchone()[0]
    con.close()
    return r


def weekly_sales(wh_path):
    """(week_index -> {site: {item: units}}) for the five Core 5 sim items, week 0 = first week with sales."""
    con = sqlite3.connect(f"file:{wh_path}?mode=ro", uri=True)
    rows = con.execute("""SELECT d.date, l.location_id, p.item_id, sum(f.qty) FROM fact_order_line f JOIN dim_date d USING(date_key) JOIN dim_location l USING(location_key)
                          JOIN dim_product p USING(product_key) WHERE p.item_id IN ('M01','M02','M03','M04','M05') GROUP BY 1,2,3""").fetchall()
    con.close()
    import datetime as dt
    first = min(dt.date.fromisoformat(r[0]) for r in rows)
    out = {}
    for d, site, item, q in rows:
        wk = (dt.date.fromisoformat(d) - first).days // 7
        out.setdefault(wk, {}).setdefault(site, {}).setdefault(item, 0)
        out[wk][site][item] += q
    return out


def _rng(seed, *tags):
    h = hashlib.sha256(("|".join(map(str, (seed,) + tags))).encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(h[:8], "big")))


def generate(wh_path, seed=7, anomalies=None, baseline_loss=0.04, count_noise=0.006, recipes=None, master=None):
    """Returns dict(rows=[...], anomalies=[...]); each row = site, week, ingredient, theoretical, measured, receipts, opening, closing (purchase units)."""
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    table = BOM.bom_table(recipes, master)
    sales = weekly_sales(wh_path)
    weeks = sorted(sales)
    sites = sorted({s for w in sales.values() for s in w})
    if anomalies is None:
        anomalies = default_anomalies(sites, weeks, table)
    inj = {}
    for a in anomalies:
        for w in range(a.start_week, a.start_week + a.weeks):
            inj[(a.site, a.ingredient, w)] = inj.get((a.site, a.ingredient, w), 0.0) + a.magnitude
    rows = []
    for site in sites:
        stock = {}
        for w in weeks:
            units = sales[w].get(site, {})
            if not units:
                continue
            theo = {}
            for item, u in units.items():
                for ing, q in table[item].items():
                    theo[ing] = theo.get(ing, 0.0) + u * q
            for ing, t in theo.items():
                r = _rng(seed, site, ing, w)
                actual = t * (1 + max(-0.02, r.normal(baseline_loss, 0.015))) * (1 + inj.get((site, ing, w), 0.0))
                opening = stock.get(ing)
                if opening is None:
                    opening = actual * 1.5                                    # first count: about 1.5 weeks of cover
                receipts = actual * max(0.5, r.normal(1.0, 0.04))            # ordered to meet use, +/- 4%
                closing = max(0.0, opening + receipts - actual)
                counted = closing + r.normal(0, count_noise * max(t, 1e-9))   # counting noise
                stock[ing] = closing                                          # physical stock carries the TRUE closing forward
                rows.append({"site": site, "week": w, "ingredient": ing, "theoretical": t, "receipts": receipts, "opening": opening, "closing_counted": counted,
                             "measured": opening + receipts - counted})
    return {"rows": rows, "anomalies": anomalies, "weeks": weeks, "sites": sites, "synthetic": True}


def default_anomalies(sites, weeks, table):
    """A fixed, documented set of injected problems (deterministic): used to score detection recall and false positives."""
    if len(sites) < 3 or len(weeks) < 20:
        return []
    heavy = lambda item: max(table[item], key=table[item].get)               # the dominant ingredient of an item (largest AP quantity)
    return [Anomaly(sites[0], "i-goat-bone-in", "over_portion", weeks[len(weeks) // 3], 6, 0.20),
            Anomaly(sites[1], "i-chicken-thigh", "spike", weeks[len(weeks) // 2], 1, 0.70),
            Anomaly(sites[2], "i-paneer", "unrecorded_transfer", weeks[len(weeks) * 2 // 3], 4, 0.25)]
