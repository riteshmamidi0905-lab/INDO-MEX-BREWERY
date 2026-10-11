#!/usr/bin/env python3
"""Food costing, allergen and D-54 checks for NASHA recipes (Sprint 9). Reads food/costing/ingredients.csv and recipes.csv, both BLANK TEMPLATES until real
supplier prices and a real tested recipe exist: this tool never invents a price, a yield or a recipe. Planning support only; not a tested recipe.
  python3 tools/food_costing.py            report (empty templates report nothing to cost)
  python3 tools/food_costing.py selftest   exercise the logic on in-memory TEST data (never saved)"""
import csv, os, re, sys
ING, REC = "food/costing/ingredients.csv", "food/costing/recipes.csv"
D54 = re.compile(r"\b(beef|veal|pork|bacon|ham|lard|chorizo|pancetta|prosciutto|sausage|gelatin(?:e)?)\b", re.I)   # NO BEEF, NO PORK (D-54)
ALLERGENS = ("milk", "egg", "peanut", "tree nut", "wheat", "soy", "fish", "shellfish", "sesame")

def analyse(ings, recs):
    out, errs = {}, []
    byid = {i["ingredient_id"]: i for i in ings}
    for i in ings:
        if D54.search(i["name"]): errs.append(f"D-54 VIOLATION: ingredient '{i['name']}' (no beef, no pork)")
    for r in recs:
        i = byid.get(r["ingredient_id"])
        if not i: errs.append(f"{r['dish_id']}: unknown ingredient {r['ingredient_id']}"); continue
        d = out.setdefault(r["dish_id"], {"cost": 0.0, "allergens": set(), "veg": True, "missing_price": []})
        try:
            price, yld, qty = float(i["price_per_unit"]), float(i["yield_pct"] or 100) / 100, float(r["qty_per_portion"])
            d["cost"] += qty * price / yld
        except ValueError: d["missing_price"].append(i["name"])
        d["allergens"] |= {a.strip() for a in i["allergens"].split("|") if a.strip()}
        if (i["vegetarian"] or "").strip().lower() != "yes": d["veg"] = False
    return out, errs

def load(p): return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []

def selftest():
    ings = [dict(ingredient_id="a", name="Paneer", category="dairy", unit="kg", price_per_unit="10", yield_pct="90", allergens="milk", vegetarian="yes", supplier="TEST", price_source="TEST", price_date="", notes=""),
            dict(ingredient_id="b", name="Corn tortilla", category="grain", unit="kg", price_per_unit="4", yield_pct="100", allergens="", vegetarian="yes", supplier="TEST", price_source="TEST", price_date="", notes="")]
    recs = [dict(dish_id="T", ingredient_id="a", qty_per_portion="0.1", unit="kg", notes=""), dict(dish_id="T", ingredient_id="b", qty_per_portion="0.05", unit="kg", notes="")]
    out, errs = analyse(ings, recs); assert not errs and abs(out["T"]["cost"] - (0.1 * 10 / .9 + 0.05 * 4)) < 1e-9 and out["T"]["veg"] and out["T"]["allergens"] == {"milk"}
    _, errs = analyse(ings + [dict(ings[0], ingredient_id="c", name="Beef birria")], []); assert errs and "D-54" in errs[0]
    print("food_costing selftest OK (TEST data, not saved)")

if len(sys.argv) > 1 and sys.argv[1] == "selftest": selftest(); sys.exit(0)
ings, recs = load(ING), load(REC); out, errs = analyse(ings, recs)
if not ings: print("No ingredient prices recorded yet: nothing to cost (no price is ever invented).")
for d, v in out.items(): print(f"{d}: cost/portion {v['cost']:.2f} (missing prices: {v['missing_price'] or 'none'}); allergens {sorted(v['allergens']) or 'none recorded'}; vegetarian as recorded: {v['veg']}")
for e in errs: print("FAIL", e)
sys.exit(1 if errs else 0)
