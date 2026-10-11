#!/usr/bin/env python3
"""Menu engineering (Kasavana-Smith style) from REAL sales data only (Sprint 14). Input: ops/menu-engineering/sales.csv with columns
item,units_sold,price,food_cost_per_unit (header only today). Never generates or assumes sales. Planning tool.
  python3 tools/menu_engineering.py            report
  python3 tools/menu_engineering.py selftest
Classes: STAR (high popularity, high margin), PLOWHORSE (high pop, low margin), PUZZLE (low pop, high margin), DOG (low, low).
Popularity threshold = 70% of average mix share (classic rule of thumb); margin threshold = weighted-average unit contribution margin."""
import csv, os, sys
F = "ops/menu-engineering/sales.csv"
def classify(rows):
    rows = [dict(r, units=float(r["units_sold"]), price=float(r["price"]), cost=float(r["food_cost_per_unit"])) for r in rows]
    tot = sum(r["units"] for r in rows)
    if not rows or tot <= 0: return []
    for r in rows: r["cm"] = r["price"] - r["cost"]; r["mix"] = r["units"] / tot
    avg_cm = sum(r["cm"] * r["units"] for r in rows) / tot; thr = 0.7 / len(rows)
    for r in rows:
        r["class"] = ("STAR" if r["cm"] >= avg_cm else "PLOWHORSE") if r["mix"] >= thr else ("PUZZLE" if r["cm"] >= avg_cm else "DOG")
        r["food_cost_pct"] = round(r["cost"] / r["price"] * 100, 1)
    return rows
def selftest():
    t = [dict(item="a", units_sold=100, price=10, food_cost_per_unit=3), dict(item="b", units_sold=100, price=10, food_cost_per_unit=8), dict(item="c", units_sold=5, price=12, food_cost_per_unit=3), dict(item="d", units_sold=5, price=9, food_cost_per_unit=8)]
    c = {r["item"]: r["class"] for r in classify(t)}; assert c == {"a":"STAR","b":"PLOWHORSE","c":"PUZZLE","d":"DOG"}, c
    print("selftest ok on in-memory TEST data (never saved)")
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest(); sys.exit()
    r = list(csv.DictReader(open(F, encoding="utf-8"))) if os.path.exists(F) else []
    if not r: print("NO SALES DATA: nothing to classify (no sales exist; none are invented)."); sys.exit()
    for x in classify(r): print(x["item"], x["class"], f"CM {x['cm']:.2f}", f"cost {x['food_cost_pct']}%")
