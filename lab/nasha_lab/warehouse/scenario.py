"""Versioned pricing + recipe SCENARIO layered on the published warehouse (SYNTHETIC; D-87).

Chain:  menu item -> recipe (version) -> ingredient -> supplier quote -> inventory -> order -> cost -> analytics.

The scenario adds `scn_*` tables to the warehouse database. It NEVER modifies or deletes dim_/fact_/mart_ tables, so the historical placeholder-price simulation is
preserved byte-for-byte. New revenue figures are a RESTATEMENT: the same simulated quantities valued at the approved concept prices (price-v2-2026-10-22).
No demand response to the new prices is modelled (no elasticity), pitchers are not simulated, and nothing here is NASHA revenue: no restaurant operates.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from . import analytics, db, forecast
from ..recipes import beer_costing, bom, menu as menu_defs, model, optimize, pricing, suppliers, synth_ops

SQL = Path(__file__).with_name("scenario_models") / "10_scn_derived.sql"
SCENARIO_ID = "scn-price-v3-menu-d88"
BASE_TABLES = ["scn_pricing", "scn_sim_item_map", "scn_menu_definition", "scn_menu_item", "scn_ingredient", "scn_supplier", "scn_supplier_quote", "scn_recipe_bom", "scn_calendar", "scn_inventory_week", "scn_injected_anomaly", "scn_supplier_note", "scn_serving", "scn_beer_economics", "scn_cost_lever", "scn_supplier_sensitivity"]
DERIVED_TABLES = ["scn_depletion_day", "scn_depletion_week", "scn_item_month", "scn_menu_profitability_month", "scn_variance_week", "scn_menu_engineering"]
PY_TABLES = ["scn_variance_flag", "scn_demand_forecast", "scn_forecast_backtest", "scn_procurement_reco", "scn_scenario_run"]
ALL_TABLES = BASE_TABLES + DERIVED_TABLES + PY_TABLES
DDL = {
    "scn_pricing": "config_id TEXT, price_key TEXT, kind TEXT, price_cents INTEGER, status TEXT",
    "scn_sim_item_map": "sim_item_id TEXT, menu_item_id TEXT, v1_price_cents INTEGER, effective_price_cents INTEGER, price_basis TEXT",
    "scn_menu_definition": "menu_id TEXT, sim_item_id TEXT, menu_item_id TEXT, role TEXT, provisional INTEGER, status TEXT",
    "scn_menu_item": "menu_item_id TEXT, name TEXT, menu_category TEXT, recipe_id TEXT, recipe_version TEXT, menu_status TEXT, price_cents INTEGER, unit_food_cost_cents REAL, unit_consumables_cents REAL, price_config TEXT",
    "scn_ingredient": "ingredient_id TEXT, name TEXT, category TEXT, unit TEXT, yield_pct REAL, base_unit_price REAL, price_class TEXT",
    "scn_supplier": "supplier_id TEXT, name TEXT, kind TEXT, synthetic INTEGER",
    "scn_supplier_quote": "quote_id TEXT, supplier_id TEXT, ingredient_id TEXT, unit_price REAL, pack_qty REAL, lead_days INTEGER, min_order_usd REAL, valid_from TEXT, valid_to TEXT, price_class TEXT",
    "scn_recipe_bom": "recipe_id TEXT, recipe_version TEXT, ingredient_id TEXT, ap_qty_per_portion REAL, unit TEXT",
    "scn_calendar": "date_key INTEGER, week INTEGER",
    "scn_inventory_week": "location_id TEXT, week INTEGER, ingredient_id TEXT, opening_qty REAL, receipts_qty REAL, closing_counted_qty REAL",
    "scn_injected_anomaly": "location_id TEXT, ingredient_id TEXT, kind TEXT, start_week INTEGER, weeks INTEGER, magnitude REAL",
    "scn_supplier_note": "supplier_id TEXT, note TEXT, trust TEXT",
    "scn_serving": "size TEXT, fl_oz REAL, volume_ml REAL, status TEXT",
    "scn_beer_economics": "beer_id TEXT, size TEXT, scenario TEXT, volume_ml REAL, price_cents INTEGER, cost_ex_labor_cents REAL, cost_with_brew_labor_cents REAL, margin_ex_labor_pct REAL, margin_with_brew_labor_pct REAL, status TEXT",
    "scn_cost_lever": "menu_item_id TEXT, lever TEXT, setting TEXT, food_cost_cents REAL, gross_margin_pct REAL, margin_delta_pts REAL, quality_impact TEXT, note TEXT",
    "scn_supplier_sensitivity": "supplier_id TEXT, menu_item_id TEXT, base_food_cost_cents REAL, shocked_food_cost_cents REAL, delta_pct REAL, share_of_cost REAL",
    "scn_variance_flag": "location_id TEXT, week INTEGER, ingredient_id TEXT, variance_pct REAL, baseline_pct REAL, excess_pct REAL, pattern TEXT, severity TEXT",
    "scn_demand_forecast": "location_id TEXT, ingredient_id TEXT, day_ahead INTEGER, forecast_qty REAL, method TEXT",
    "scn_forecast_backtest": "location_id TEXT, ingredient_id TEXT, method TEXT, wape REAL, origins INTEGER",
    "scn_procurement_reco": "reco_id TEXT, location_id TEXT, ingredient_id TEXT, need_qty REAL, on_hand_qty REAL, order_qty REAL, unit TEXT, supplier_id TEXT, quote_id TEXT, est_cost_usd REAL, cheapest_alt TEXT, price_class TEXT, status TEXT, rationale TEXT, inputs_hash TEXT",
    "scn_scenario_run": "scenario_id TEXT, pricing_config TEXT, prior_pricing_config TEXT, recipe_set_sha TEXT, quotes_sha TEXT, seed INTEGER, notes TEXT",
}


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _create(con, name):
    con.execute(f"DROP TABLE IF EXISTS {name}")
    con.execute(f"CREATE TABLE {name} ({DDL[name]})")


def _insert(con, name, rows):
    if not rows:
        return
    n = len(DDL[name].split(","))
    con.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * n)})", rows)


def run_sql_script(con, sql):
    for st in [s for s in sql.split(";\n") if s.strip() and not s.strip().startswith("--") or "CREATE" in s]:
        con.execute(st)


def build(wh_path, config_id=None, seed=7, anomalies="default", quotes=None, supplier_notes=None):
    """Rebuild every scn_ table from the published warehouse. Idempotent and deterministic for a fixed warehouse, config and seed."""
    con = db.connect(wh_path)
    analytics._require_published(con)
    config_id = config_id or pricing.CURRENT
    cfg = pricing.load_config(config_id)
    recipes, master = model.load_recipes(), model.load_master()
    qfile = quotes or suppliers.load()                 # a tenant may supply its own SYNTHETIC quote set (different seed / missing suppliers)
    for t in ALL_TABLES:
        con.execute(f"DROP TABLE IF EXISTS {t}")
    for t in BASE_TABLES + PY_TABLES:
        _create(con, t)
    # ---- prices (v2 approved + frozen v1 record) and sim item map
    _insert(con, "scn_pricing", [(config_id, k, "category_price", int(round(v * 100)), cfg["status"]) for k, v in cfg["prices_usd"].items()] +
            [(config_id, f"{g}_volume_ml", "serving_volume", None, cfg["serving_volumes"][g]["status"]) for g in ("glass", "pitcher")] +
            [("price-v1-placeholder", k, "sim_item_price", v["price_cents"], "FROZEN HISTORICAL PLACEHOLDER") for k, v in json.loads((pricing.PRICING / "price-v1-placeholder.json").read_text())["items"].items()])
    v1 = pricing.v1_catalog_snapshot()
    menu_name, to_recipe = synth_ops.menu_for(wh_path)               # the definition the warehouse was generated with; "historical" reproduces the pre-D-90 scenario
    mdef = menu_defs.load(menu_name)
    if menu_name == "historical":
        to_recipe = cfg["menu_item_mapping_to_sim"]
    px = {r[0]: (r[1], r[2]) for r in con.execute("SELECT item_id, list_price_cents, name FROM dim_product")}
    v1 = {k: v for k, v in v1.items() if k in px}                      # only items that exist in this warehouse (a "current" warehouse has no M03 / Goat Birria)
    for slot in to_recipe:
        v1.setdefault(slot, {"name": px[slot][1], "category": "food", "price_cents": int(px[slot][0])})
    beers = {b["sim_item_id"]: b for b in cfg["beers"]}
    rows = []
    for item, v in v1.items():
        if item in to_recipe:
            cat = recipes[to_recipe[item]]["menu_category"]
            rows.append((item, to_recipe[item], v["price_cents"], pricing.price_cents(cfg, cat), "v2_approved"))
        elif item in beers:
            rows.append((item, None, v["price_cents"], pricing.price_cents(cfg, "beer_glass"), "v2_approved"))
        else:
            rows.append((item, None, v["price_cents"], v["price_cents"], "v1_placeholder_carried"))
    _insert(con, "scn_sim_item_map", rows)
    _insert(con, "scn_menu_definition", [(mdef["menu_id"], i["sim_item_id"], i["menu_item_id"], i.get("role", "core5"), int(bool(i.get("provisional"))), "PROVISIONAL: not cooked or tested; costing is a desk estimate" if i.get("provisional") else "active (concept)") for i in mdef["items"]])
    sv = cfg["serving_volumes"]
    _insert(con, "scn_serving", [(k, sv[k]["fl_oz"], sv[k]["fl_oz"] * sv["oz_to_ml"], sv[k]["status"]) for k in ("glass", "pitcher")])
    _insert(con, "scn_beer_economics", [(r["beer"], r["size"], r["scenario"], r["volume_ml"], int(round(r["price"] * 100)), r["cost_ex_labor"] * 100, r["cost_with_brew_labor"] * 100,
                                         r["margin_ex_labor_pct"], r["margin_with_brew_labor_pct"], r["status"]) for r in beer_costing.all_rows(cfg)])
    qf = qfile
    _insert(con, "scn_cost_lever", [(r["dish"], r["lever"], r["setting"], r["food_cost"] * 100, r["gross_margin_pct"], r["margin_delta_pts"], r["quality_impact"], r["note"])
                                    for rid, rr in recipes.items() if rr["kind"] == "dish" for r in optimize.levers(rid, cfg, recipes, master, qf["quotes"])])
    _insert(con, "scn_supplier_sensitivity", [(r["supplier_id"], r["dish"], r["base_food_cost"] * 100, r["shocked_food_cost"] * 100, r["delta_pct"], r["share_of_cost"])
                                              for r in optimize.supplier_sensitivity(0.15, cfg, recipes, master, qf["quotes"])])
    # ---- menu items, recipes, BOM, ingredients, suppliers
    mi = []
    for r in recipes.values():
        if r["kind"] != "dish":
            continue
        e = pricing.economics(r["id"], cfg, "base", recipes, master)
        mi.append((r["id"], r["name"], r["menu_category"], r["id"], r["version"], r["menu_status"], pricing.price_cents(cfg, r["menu_category"]), round(e["food_cost"] * 100, 4), round(e["consumables"] * 100, 4), config_id))
    _insert(con, "scn_menu_item", mi)
    _insert(con, "scn_recipe_bom", pricing.bom_rows(cfg, recipes, master))
    _insert(con, "scn_ingredient", [(i["id"], i["name"], i["category"], i["unit"], i["yield_pct"], (i["price"]["base"] if "price" in i else None), "PLANNING_ASSUMPTION") for i in master.values()
                                         if menu_name == "historical" or not i.get("retired")])      # D-90: a current-state scenario carries no retired ingredient (the master file keeps it as history)
    notes = supplier_notes if supplier_notes is not None else {s["supplier_id"]: f"Synthetic delivery note for {s['name']}: standard weekly delivery window; minimum order applies to broadline distributors." for s in qfile["suppliers"]}
    _insert(con, "scn_supplier_note", [(sid, note, "untrusted") for sid, note in sorted(notes.items())])
    _insert(con, "scn_supplier", [(s["supplier_id"], s["name"], s["kind"], 1) for s in qfile["suppliers"]])
    _insert(con, "scn_supplier_quote", [(q["quote_id"], q["supplier_id"], q["ingredient_id"], q["unit_price"], q["pack_qty"], q["lead_days"], q["min_order_usd"], q["valid_from"], q["valid_to"], q["price_class"]) for q in qfile["quotes"]])
    # ---- calendar (week index consistent with synth_ops.weekly_sales) and synthetic inventory counts
    first = synth_ops.first_sales_date(wh_path)
    cal = [(int(k), (pd.Timestamp(d) - pd.Timestamp(first)).days // 7) for k, d in con.execute("SELECT date_key, date FROM dim_date ORDER BY 1")]
    _insert(con, "scn_calendar", cal)
    ops = synth_ops.generate(wh_path, seed=seed, **({} if anomalies == "default" else {"anomalies": anomalies}))
    _insert(con, "scn_inventory_week", [(r["site"], r["week"], r["ingredient"], r["opening"], r["receipts"], r["closing_counted"]) for r in ops["rows"]])
    _insert(con, "scn_injected_anomaly", [(a.site, a.ingredient, a.kind, a.start_week, a.weeks, a.magnitude) for a in ops["anomalies"]])
    con.commit()
    # ---- derived SQL
    for t in DERIVED_TABLES:
        con.execute(f"DROP TABLE IF EXISTS {t}")
    run_sql_script(con, SQL.read_text())
    con.commit()
    # ---- python-derived: variance flags, demand forecast, procurement recommendations
    flags = detect_variance(con)
    _insert(con, "scn_variance_flag", flags)
    fc, bt = forecast_ingredient_demand(con)
    _insert(con, "scn_demand_forecast", fc)
    _insert(con, "scn_forecast_backtest", bt)
    recos = recommend_procurement(con, qfile["quotes"])
    _insert(con, "scn_procurement_reco", recos)
    _insert(con, "scn_scenario_run", [(SCENARIO_ID, config_id, "price-v1-placeholder (historical simulation); lineage v2-2026-10-22", sha([recipes, master]), sha(qfile), seed,
                                       "Restatement of the historical simulation at approved concept prices; no demand response; pitchers not simulated; synthetic quotes only; beer costs are preliminary planning estimates at provisional serving sizes; Goat Birria retired (D-88) so its historical sales carry the v1 placeholder price and have no BOM")])
    con.commit()
    out = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ALL_TABLES}
    con.close()
    return out


# ------------------------------------------------------------------ variance / waste detection
def detect_variance(con, min_excess=0.08, mad_k=4.0):
    """Flag site-ingredient-weeks whose usage exceeds theoretical by much more than that series' own typical loss. Uses ONLY measured counts and receipts (never the injected truth).
    pattern: spike (1 week) | persistent (>= 3 consecutive flagged weeks) | recurring; severity by excess."""
    df = pd.read_sql_query("SELECT location_id, week, ingredient_id, variance_pct FROM scn_variance_week WHERE variance_pct IS NOT NULL ORDER BY 1,3,2", con)
    out = []
    for (loc, ing), g in df.groupby(["location_id", "ingredient_id"], sort=True):
        v = g["variance_pct"].to_numpy(float)
        med = float(np.median(v))
        mad = max(0.01, float(np.median(np.abs(v - med)) * 1.4826))
        hit = (v - med > max(min_excess, mad_k * mad))
        weeks = g["week"].to_numpy()
        runs, i = [], 0
        while i < len(hit):
            if hit[i]:
                j = i
                while j + 1 < len(hit) and hit[j + 1] and weeks[j + 1] == weeks[j] + 1:
                    j += 1
                runs.append((i, j))
                i = j + 1
            else:
                i += 1
        for a, b in runs:
            pat = "persistent" if b - a + 1 >= 3 else ("spike" if b == a else "short_run")
            for k in range(a, b + 1):
                ex = float(v[k] - med)
                out.append((loc, int(weeks[k]), ing, float(v[k]), med, ex, pat, "high" if ex > 0.3 else ("medium" if ex > 0.15 else "low")))
    return out


def score_detection(con):
    """Recall/precision of the variance flags against the injected anomalies (evaluation only; the detector never reads scn_injected_anomaly)."""
    inj = set()
    for loc, ing, kind, s, n, m in con.execute("SELECT * FROM scn_injected_anomaly"):
        inj |= {(loc, ing, w) for w in range(s, s + n)}
    got = {(r[0], r[1], r[2]) for r in con.execute("SELECT location_id, ingredient_id, week FROM scn_variance_flag")}
    tp = len(inj & got)
    return {"injected_cells": len(inj), "flagged_cells": len(got), "true_positive": tp, "recall": tp / len(inj) if inj else None, "precision": tp / len(got) if got else None, "false_positive_cells": len(got - inj)}


# ------------------------------------------------------------------ ingredient demand forecast
def forecast_ingredient_demand(con, horizon=14, top_n=None):
    """Daily theoretical ingredient demand per site, forecast with the best of three methods chosen by rolling-origin backtest (same methods and rules as the sales forecast).
    Demand = unit forecast x BOM implicitly: the series is already sales x BOM. Returns (forecast rows, backtest rows)."""
    df = pd.read_sql_query("SELECT location_id, date, ingredient_id, theoretical_qty FROM scn_depletion_day", con)
    if df.empty:
        return [], []
    df["date"] = pd.to_datetime(df["date"])
    lo, hi = df["date"].min(), df["date"].max()
    idx = pd.date_range(lo, hi, freq="D")
    fc, bt = [], []
    for (loc, ing), g in df.groupby(["location_id", "ingredient_id"], sort=True):
        y = g.set_index("date")["theoretical_qty"].reindex(idx, fill_value=0.0).to_numpy(float)
        nz = np.nonzero(y)[0]
        if len(nz) == 0:
            continue
        y = y[nz[0]:]
        res, used = forecast.backtest(y, horizon=horizon, origins=3, min_train=8 * forecast.SEASON)
        ok = {m: r for m, r in res.items() if r["wape"] is not None}
        if ok:
            best = min(ok, key=lambda m: (ok[m]["wape"], m))
            for m, r in ok.items():
                bt.append((loc, ing, m, round(r["wape"], 6), used))
        else:
            best = "seasonal_mean_4w" if len(y) >= 4 * forecast.SEASON else "seasonal_naive"
        if len(y) < forecast.SEASON:
            continue
        p = forecast.METHODS[best](y, horizon)
        fc += [(loc, ing, k + 1, float(max(0.0, v)), best) for k, v in enumerate(p)]
    return fc, bt


# ------------------------------------------------------------------ procurement recommendations (PROPOSALS ONLY)
def recommend_procurement(con, quotes, cover_days=7, safety=0.10):
    master = model.load_master()
    last = {(r[0], r[1]): r[2] for r in con.execute("SELECT location_id, ingredient_id, closing_counted_qty FROM scn_inventory_week w WHERE week = (SELECT max(week) FROM scn_inventory_week x WHERE x.location_id = w.location_id AND x.ingredient_id = w.ingredient_id)")}
    need = {}
    for loc, ing, k, q, m in con.execute("SELECT location_id, ingredient_id, day_ahead, forecast_qty, method FROM scn_demand_forecast WHERE day_ahead <= ?", (cover_days,)):
        need[(loc, ing)] = need.get((loc, ing), 0.0) + q
    out = []
    for (loc, ing), n in sorted(need.items()):
        target = n * (1 + safety)
        on_hand = last.get((loc, ing), 0.0)
        gap = target - on_hand
        if gap <= 1e-9:
            continue
        ranked = suppliers.compare(quotes, ing, gap, on="2026-10-22")
        if not ranked:
            continue
        best = ranked[0]
        inputs = {"loc": loc, "ing": ing, "need": round(n, 6), "on_hand": round(on_hand, 6), "cover_days": cover_days, "safety": safety, "quote": best["quote_id"]}
        rationale = {"rule": "reorder = forecast demand for the cover window x (1+safety) minus last counted on-hand; whole packs from the cheapest valid SYNTHETIC quote",
                     "alternatives": [{"supplier_id": r["supplier_id"], "cost": r["cost"]} for r in ranked[1:3]]}
        out.append((f"R-{sha(inputs)}", loc, ing, round(n, 6), round(on_hand, 6), best["buy_qty"], master[ing]["unit"], best["supplier_id"], best["quote_id"], best["cost"],
                    ranked[1]["supplier_id"] if len(ranked) > 1 else None, best["price_class"], "PROPOSED", json.dumps(rationale, sort_keys=True), sha(inputs)))
    return out
