"""Regenerate every analytics results file under lab/results/analytics/.   cd lab && python -m analytics.run_all

All numbers in lab/docs/ANALYTICS-*.md come from these files (docs are rendered from them by analytics/render_docs.py).
SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.
"""
import json
import os

import numpy as np

from . import config as C, difficult, dqf, experiment, forecast, library, mart, mart_checks as MC, metrics as M
from nasha_lab import generator

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "analytics")
BANNER = "SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED"


def _clean(o):
    if isinstance(o, dict): return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, float): return round(o, 6)
    return o


def write(name, obj):
    os.makedirs(OUT, exist_ok=True)
    obj = {"_banner": BANNER, "_config_hash": C.config_hash(), **obj}
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(_clean(obj), f, indent=1, sort_keys=False, ensure_ascii=False); f.write("\n")


def margin_sensitivity(con):
    rows = con.execute("""
      WITH s AS (SELECT item_key, SUM(qty) u, SUM(gross_sales_cents)/100.0 sales FROM fact_order_line GROUP BY 1),
      r AS (SELECT b.item_key, SUM(b.kg_per_unit*g.assumed_cost_per_kg) c FROM bridge_item_ingredient b JOIN dim_ingredient g USING(ingredient_key) GROUP BY 1)
      SELECT i.item_id || ' ' || i.item_name, i.category, s.sales, s.u, s.u*COALESCE(r.c,0) + s.sales*CASE i.category WHEN 'food' THEN %s ELSE 0 END
             + s.u*CASE i.category WHEN 'beer' THEN %s WHEN 'na' THEN %s ELSE 0 END
      FROM s JOIN dim_menu_item i USING(item_key) LEFT JOIN r USING(item_key)""" % (C.OTHER_COST_PCT_OF_PRICE["food"], C.FIXED_UNIT_COST_USD["beer"], C.FIXED_UNIT_COST_USD["na"])).fetchall()
    out = {}
    for mult in C.COGS_SENSITIVITY:
        ranked = sorted(rows, key=lambda r: -(r[2] - mult * r[4]))
        out[str(mult)] = [{"item": r[0], "category": r[1], "units": r[3], "sales_usd": round(r[2], 2), "margin_usd": round(r[2] - mult * r[4], 2), "margin_pct": round(100 * (r[2] - mult * r[4]) / r[2], 1)} for r in ranked]
    base = [x["item"] for x in out["1.0"]]
    return {"cost_multipliers": list(C.COGS_SENSITIVITY), "ranking_by_multiplier": out,
            "ranking_identical_across_multipliers": all([x["item"] for x in out[str(m)]] == base for m in C.COGS_SENSITIVITY),
            "top3_identical_across_multipliers": all([x["item"] for x in out[str(m)]][:3] == base[:3] for m in C.COGS_SENSITIVITY),
            "note": "Costs are ASSUMPTIONS; this tests only whether the ORDER of items is sensitive to a uniform +/-25% change in all assumed costs."}


def recovery_checks(con):
    """Can the mart analyses recover the properties the simulation injected? Scored candidly, including where they do not."""
    rows = con.execute("""SELECT s.site_id, g.ingredient, SUM(f.variance_qty), SUM(f.usage_since_prev), SUM(f.expected_on_hand) FROM fact_inventory_snapshot f
        JOIN dim_site s USING(site_key) JOIN dim_ingredient g USING(ingredient_key) WHERE f.prev_date_key<>0 GROUP BY 1,2""").fetchall()
    pairs = [{"site": r[0], "ingredient": r[1], "net_variance_kg": r[2], "usage_kg": r[3], "variance_pct_of_usage": r[2] / r[3] if r[3] else None} for r in rows]
    big = [p for p in pairs if p["usage_kg"] >= 20]
    def rank(lst, site, ing):
        lst = sorted(lst, key=lambda p: p["variance_pct_of_usage"]); return 1 + [(p["site"], p["ingredient"]) for p in lst].index((site, ing))
    shrink = {"injected": "L03 goat, unlogged shrink = %.0f%% of daily usage" % (100 * C.INJECTED_SHRINK[0][2]),
              "observed_variance_pct_of_usage": next(p["variance_pct_of_usage"] for p in pairs if (p["site"], p["ingredient"]) == ("L03", "goat")),
              "rank_most_negative_all_24_pairs": rank(pairs, "L03", "goat"), "pairs_total": len(pairs),
              "rank_most_negative_pairs_with_usage_ge_20kg": rank(big, "L03", "goat"), "pairs_with_usage_ge_20kg": len(big),
              "most_negative_five_all": [(p["site"], p["ingredient"], round(p["variance_pct_of_usage"], 4), round(p["usage_kg"], 1)) for p in sorted(pairs, key=lambda p: p["variance_pct_of_usage"])[:5]]}
    sup = con.execute("""SELECT s.supplier_id, 1.0*SUM(p.days_late<=0)/COUNT(*), COUNT(*) FROM fact_po_line p JOIN dim_supplier s USING(supplier_key) WHERE p.status='RECEIVED' GROUP BY 1 ORDER BY 2""").fetchall()
    late = {"injected_late_probability": C.SUPPLIER_LATE_PROB, "observed_on_time_rate_worst_first": [(a, round(b, 3), n) for a, b, n in sup],
            "worst_two_match_injected_worst_two": {a for a, _b, _n in sup[:2]} == {"S03", "S05"}}
    masa = con.execute("""SELECT d.date >= ? AS after_change, SUM(u.theoretical_qty) / COUNT(DISTINCT d.date) AS kg_per_day_all_sites FROM fact_usage_daily u
        JOIN dim_ingredient g USING(ingredient_key) JOIN dim_date d USING(date_key) WHERE g.ingredient='corn masa' GROUP BY 1 ORDER BY 1""", (C.MENU_CHANGE_DATE,)).fetchall()
    multi = []
    for sd in range(1, 6):
        c2, _ = mart.build(sd)
        r2 = c2.execute("""SELECT s.site_id, g.ingredient, SUM(f.variance_qty)/SUM(f.usage_since_prev), SUM(f.usage_since_prev) FROM fact_inventory_snapshot f JOIN dim_site s USING(site_key)
            JOIN dim_ingredient g USING(ingredient_key) WHERE f.prev_date_key<>0 GROUP BY 1,2 HAVING SUM(f.usage_since_prev)>=20 ORDER BY 3""").fetchall()
        multi.append({"seed": sd, "rank_of_L03_goat_among_pairs_ge_20kg": 1 + [(r[0], r[1]) for r in r2].index(("L03", "goat")), "pairs": len(r2)})
    shrink["multi_seed_rank_pairs_ge_20kg"] = multi
    return {"unlogged_shrink_recovery": shrink, "late_supplier_recovery": late, "corn_masa_kg_per_day_before_after_recipe_change": [(bool(a), round(b, 3)) for a, b in masa]}


def main():
    con, info = mart.build(C.SEED)
    q = lambda s: con.execute(s).fetchall()
    tables = [t for t, in q("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'dim_%' OR name LIKE 'fact_%' OR name LIKE 'bridge_%') ORDER BY 1")]
    write("mart_summary.json", {"seed": C.SEED, "row_counts": {t: q(f"SELECT COUNT(*) FROM {t}")[0][0] for t in tables},
        "reconciliation": {k: {"left": a, "right": b, "equal": a == b} for k, (a, b) in MC.reconciliation(con).items()},
        "orphan_foreign_keys": {k: v for k, v in sorted(MC.orphan_counts(con).items())}, "grain_duplicates": MC.grain_duplicates(con), "scd2_problems": MC.scd2_problems(con),
        "order_lines_outside_scd2_window": MC.order_lines_outside_scd2_window(con), "injected_defect_count": len(info["injected_defects"]),
        "simulation_truth": info["simulation_truth"], "menu_change_date_assumption": C.MENU_CHANGE_DATE, "menu_change_date_label": C._MENU_CHANGE_DATE_LABEL, "assumptions_file": "lab/analytics/config.py"})
    rec = M.reconcile(con)
    write("metrics_reconciliation.json", {"metrics_file": "lab/analytics/metrics.json", "all_ok": all(r["ok"] for r in rec),
        "rows": [{k: r[k] for k in ("metric", "groups", "max_abs_diff", "ok", "mart", "source")} for r in rec]})
    qs = []
    for qd in library.load_all():
        cols, rows = library.run(con, qd["id"])
        qs.append({"id": qd["id"], "title": qd["title"], "question": qd["question"], "technique": qd["technique"], "expected_shape": qd["expected_shape"], "rows": len(rows), "columns": cols, "first_rows": rows[:3]})
    write("sql_library.json", {"queries": qs, "count": len(qs)})
    dcs = []
    mf = difficult.manifest()
    for d in difficult.case_dirs():
        cols, rows = difficult.run_trap(d)
        name = os.path.basename(d)
        dcs.append({"case": name, "public_files": sorted(os.listdir(d)), "trap_query_executes": True, "trap_rows_returned": len(rows),
                    "removed_private_key_files": sorted(k.split("/")[1] for k in mf if k.startswith(name + "/"))})
    write("difficult_cases.json", {"cases": dcs, "count": len(dcs), "manifest_entries": len(mf),
          "note": "Answer keys (solution.sql, expected.json, explanation.md) are private and not in this repository; see analytics/difficult_cases/README.md."})
    seeds = range(1, 11)
    sc = dqf.score(seeds)
    raw, _ = generator.generate(C.SEED, C.DEFECTS_PER_TYPE, menu_version=C.MENU_VERSION_SOURCE)
    write("dq_evaluation.json", {"framework": "lab/analytics/dqf.py (SQL rules over the raw landing zone)", "score": sc, "clean_data_false_alarms": dqf.clean_run(range(1, 6)),
        "lab_rules_for_comparison": dqf.lab_rules_score(seeds), "novel_defect_probe": dqf.novel_probe(), "freshness": dqf.freshness(dqf.landing_db(raw)),
        "row_conservation": dqf.reconciliation(raw),
        "caveat": "Injected defects are simple by construction and the same author wrote generator, defects and rules; recall of 1.0 shows the rules do what they were written to do, not that they would find defects in real data."})
    write("forecast_backtest.json", forecast.run())
    write("experiment.json", experiment.run(seed=1, reps=1000))
    write("margin_sensitivity.json", margin_sensitivity(con))
    write("recovery_checks.json", recovery_checks(con))
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
