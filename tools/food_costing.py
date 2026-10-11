#!/usr/bin/env python3
"""Food costing, allergen and D-54 checks for NASHA recipes (Sprint 9, hardened Sprint 22). Reads food/costing/ingredients.csv and recipes.csv (and ops/finance/dish-economics.csv for
the economics command), all BLANK TEMPLATES until real prices and a real tested recipe exist: this tool never invents a price, a yield or a recipe. Planning support only.
Percent columns here are 0-100 (yield_pct = TOTAL usable fraction after trim AND cooking loss, so cooked_yield_pct is informational and is never applied a second time; waste_pct = extra prep/spoilage waste);
the finance model uses fractions 0-1. A price counts only with a recognised price_class (ACTUAL, SUPPLIER_QUOTE, RETAIL_RECEIPT, ...): blank/UNKNOWN/TEST_FIXTURE prices are NOT costed.
A retail receipt is an R&D price (grade C), not a supplier quote. Frying oil is costed only if it is a recipe ingredient (quantity per portion, e.g. from `oil_allocation`); otherwise it is excluded and the economics command says so.
  python3 tools/food_costing.py            report (empty templates report nothing to cost)
  python3 tools/food_costing.py economics  per-dish FOOD COST -> DIRECT VARIABLE COST -> CONTRIBUTION, kept separate (full operating profit is a fin_model scenario)
  python3 tools/food_costing.py selftest   exercise the logic on in-memory TEST data (never saved)"""
import csv, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fin_model import GRADE, norm, worst   # one provenance vocabulary for costing and finance
ING, REC, DE = "food/costing/ingredients.csv", "food/costing/recipes.csv", "ops/finance/dish-economics.csv"
D54 = re.compile(r"\b(beef|veal|pork|bacon|ham|lard|chorizo|pancetta|prosciutto|sausage|gelatin(?:e)?|tallow|suet|brisket|carnitas|barbacoa|ribeye|steak|jamon|salami|pepperoni|mortadella|manteca|isinglass)(?:s|es)?\b", re.I)   # NO BEEF, NO PORK (D-54); a chef/cultural advisor should own the final list
CONV = {("g", "kg"): 0.001, ("ml", "l"): 0.001, ("kg", "g"): 1000.0, ("l", "ml"): 1000.0}   # recipes are in g/ml, purchases in kg/L; any other mismatch is refused
KNOWN_UNITS = {"g", "kg", "ml", "l", "each", "piece", "oz", "lb"}
ALLERGENS = ("milk", "egg", "peanut", "tree nut", "wheat", "soy", "fish", "shellfish", "sesame")

def num(x):
    try: v = float(x)
    except (ValueError, TypeError): return None
    return v if math.isfinite(v) else None

def analyse(ings, recs):
    out, errs = {}, []
    byid = {i["ingredient_id"]: i for i in ings}
    for i in ings:
        if D54.search(i["name"]): errs.append(f"D-54 VIOLATION: ingredient '{i['name']}' (no beef, no pork)")
    for r in recs:
        d = out.setdefault(r["dish_id"], {"cost": 0.0, "purchase": 0.0, "classes": set(), "allergens": set(), "veg": True, "missing_price": []})
        i = byid.get(r["ingredient_id"])
        if not i: errs.append(f"{r['dish_id']}: unknown ingredient {r['ingredient_id']}"); d["missing_price"].append(f"{r['ingredient_id']} (UNKNOWN INGREDIENT ID; not costed)"); continue
        d["allergens"] |= {a.strip() for a in (i.get("allergens") or "").split("|") if a.strip()}   # collected even when the price cannot be costed
        if (i.get("vegetarian") or "").strip().lower() != "yes": d["veg"] = False
        cls = norm(i.get("price_class"))
        if cls not in GRADE: d["missing_price"].append(f"{i['name']} (price class {cls}: not costed)"); continue
        iu, ru = (i.get("unit") or "").strip().lower(), (r.get("unit") or "").strip().lower()
        if iu not in KNOWN_UNITS or ru not in KNOWN_UNITS or (iu != ru and (ru, iu) not in CONV): d["missing_price"].append(f"{i['name']} (UNIT MISMATCH or unknown unit: ingredient {i.get('unit')!r} vs recipe {r.get('unit')!r}; not costed)"); continue
        price, yld, qty, waste = num(i.get("price_per_unit")), num(i.get("yield_pct") or 100), num(r.get("qty_per_portion")), num(i.get("waste_pct") or 0)
        if None in (price, yld, qty, waste) or price < 0 or qty < 0 or not (1 < yld <= 100) or not (0 <= waste < 100): d["missing_price"].append(f"{i['name']} (missing or invalid price/quantity/yield/waste; yield_pct and waste_pct are 0-100, yield above 1)"); continue
        q = qty * (CONV[(ru, iu)] if iu != ru else 1)
        d["cost"] += q * price / ((yld / 100) * (1 - waste / 100)); d["purchase"] += q * price   # purchase cost = quantity x price; usable cost also pays for trim, cooking loss and waste
        d["classes"].add(cls)
    return out, errs

LAYER_FIELDS = {"price": "menu price per portion", "packaging": "packaging per portion", "fee_pct": "payment/transaction fee (fraction 0-1 of price)", "direct_labor_min": "direct labor minutes per portion", "wage_per_hour": "loaded hourly wage for those minutes (founder labor is NOT zero)", "event_cost_per_portion": "event-specific cost per portion"}
def oil_allocation(oil_in_ml, oil_out_ml, portions):
    """Frying-oil cost driver: oil consumed (measured in minus measured out, ml) per portion fried. Quantity only; add it to the recipe as an oil ingredient to cost it."""
    if not all(math.isfinite(v) for v in (oil_in_ml, oil_out_ml, portions)) or portions <= 0 or oil_in_ml < 0 or oil_out_ml < 0 or oil_out_ml > oil_in_ml: raise ValueError("invalid oil measurements")
    return (oil_in_ml - oil_out_ml) / portions
def layers(food, food_classes, fields):
    """Keeps FOOD COST, DIRECT VARIABLE COST and CONTRIBUTION separate. fields = {name: (value, class)}. Any ingredient or field class outside the recognised grades (UNKNOWN, blank, TEST_FIXTURE), any non-finite or out-of-range value, leaves that layer NOT COMPUTABLE and names what unlocks it. Full operating profit is never computed here."""
    out = {"food_cost": None, "direct_variable_cost": None, "contribution": None, "blocked": []}
    if food is None or not math.isfinite(food) or not food_classes or any(c not in GRADE for c in food_classes): out["blocked"].append("food cost (ingredient prices, quantities or price classes missing/unusable)")
    else: out["food_cost"] = (food, worst(food_classes))
    ok = {k: fields[k] for k in LAYER_FIELDS if k in fields and fields[k][1] in GRADE and math.isfinite(fields[k][0]) and fields[k][0] >= 0 and (k != "fee_pct" or fields[k][0] <= 1)}
    need = [k for k in LAYER_FIELDS if k not in ok]
    out["blocked"] += [LAYER_FIELDS[k] for k in need]
    if out["food_cost"] and not need:
        f = {k: v[0] for k, v in ok.items()}; cls = set(food_classes) | {v[1] for v in ok.values()}
        dv = food + f["packaging"] + f["fee_pct"] * f["price"] + f["direct_labor_min"] / 60 * f["wage_per_hour"] + f["event_cost_per_portion"]
        out["direct_variable_cost"] = (dv, worst(cls)); out["contribution"] = (f["price"] - dv, worst(cls))
    return out
def load(p): return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []

def selftest():
    gi = [dict(ingredient_id="a", name="Paneer", category="dairy", unit="kg", price_per_unit="10", yield_pct="100", waste_pct="", allergens="", vegetarian="yes", supplier="TEST", price_source="TEST", price_date="x", notes="", price_class="QUOTE")]
    out, _ = analyse(gi, [dict(dish_id="G", ingredient_id="a", qty_per_portion="100", unit="g", notes="")]); assert abs(out["G"]["cost"] - 1.0) < 1e-9 and out["G"]["classes"] == {"SUPPLIER_QUOTE"}, out   # 100 g of a 10-per-kg item costs 1
    out, _ = analyse(gi, [dict(dish_id="G", ingredient_id="a", qty_per_portion="1", unit="cups", notes="")]); assert out["G"]["missing_price"]   # unknown unit is refused
    ings = [dict(ingredient_id="a", name="Paneer", category="dairy", unit="kg", price_per_unit="10", yield_pct="90", allergens="milk", vegetarian="yes", supplier="TEST", price_source="TEST", price_date="", notes="", price_class="RETAIL RECEIPT"),
            dict(ingredient_id="b", name="Corn tortilla", category="grain", unit="kg", price_per_unit="4", yield_pct="100", allergens="", vegetarian="yes", supplier="TEST", price_source="TEST", price_date="", notes="", price_class="ACTUAL")]
    recs = [dict(dish_id="T", ingredient_id="a", qty_per_portion="0.1", unit="kg", notes=""), dict(dish_id="T", ingredient_id="b", qty_per_portion="0.05", unit="kg", notes="")]
    out, errs = analyse(ings, recs); assert not errs and abs(out["T"]["cost"] - (0.1 * 10 / .9 + 0.05 * 4)) < 1e-9 and out["T"]["veg"] and out["T"]["allergens"] == {"milk"}
    _, errs = analyse(ings + [dict(ings[0], ingredient_id="c", name="Beef birria")], []); assert errs and "D-54" in errs[0]
    for nm in ("Sausages", "Chorizos", "Carnitas", "Isinglass finings"): assert D54.search(nm), nm
    assert not D54.search("Pork-free tortilla".replace("Pork", "Corn")) and not D54.search("Shamrock")
    # blocked inputs: never costed
    for cls in ("", "UNKNOWN", "TEST_FIXTURE", "MAGIC"):
        o, _ = analyse([dict(ings[0], price_class=cls)], [dict(dish_id="X", ingredient_id="a", qty_per_portion="100", unit="g", notes="")]); assert o["X"]["missing_price"] and o["X"]["cost"] == 0, cls
    o, errs = analyse(ings, [dict(dish_id="P", ingredient_id="b", qty_per_portion="100", unit="g", notes=""), dict(dish_id="P", ingredient_id="zzz", qty_per_portion="1", unit="g", notes="")]); assert errs and o["P"]["missing_price"]   # an unknown ingredient id leaves the dish NOT COSTABLE
    for bad in (dict(yield_pct="0.9"), dict(yield_pct="150"), dict(price_per_unit="-4"), dict(waste_pct="100"), dict(price_per_unit="inf"), dict(unit="")):
        o, _ = analyse([dict(ings[1], **bad)], [dict(dish_id="Y", ingredient_id="b", qty_per_portion="100", unit="g", notes="")]); assert o["Y"]["missing_price"], bad   # a fraction typed into a 0-100 column, etc.
    o, _ = analyse(ings, [dict(dish_id="U", ingredient_id="a", qty_per_portion="1", unit="cups", notes="")]); assert o["U"]["allergens"] == {"milk"} and o["U"]["missing_price"]   # allergens kept even when the cost is refused
    # pipeline layers (TEST_FIXTURE numbers: never NASHA economics)
    full = {"price": (10.0, "TEST_FIXTURE"), "packaging": (0.5, "TEST_FIXTURE"), "fee_pct": (0.03, "TEST_FIXTURE"), "direct_labor_min": (3.0, "TEST_FIXTURE"), "wage_per_hour": (20.0, "TEST_FIXTURE"), "event_cost_per_portion": (0.2, "TEST_FIXTURE")}
    lay = layers(3.0, {"TEST_FIXTURE"}, full); assert lay["food_cost"] is None and lay["contribution"] is None   # a fixture never produces a number
    real = {k: (v[0], "ACTUAL") for k, v in full.items()}; lay = layers(3.0, {"SUPPLIER_QUOTE"}, real)
    assert abs(lay["direct_variable_cost"][0] - (3.0 + 0.5 + 0.3 + 1.0 + 0.2)) < 1e-9 and abs(lay["contribution"][0] - (10 - 5.0)) < 1e-9 and lay["contribution"][1] == "A"
    assert layers(3.0, {"RETAIL_RECEIPT"}, real)["contribution"][1] == "C"   # a retail receipt keeps the contribution R&D-grade
    partial = dict(real); del partial["wage_per_hour"]; lay = layers(3.0, {"ACTUAL"}, partial); assert lay["contribution"] is None and lay["food_cost"] and lay["blocked"]
    assert layers(None, set(), real)["food_cost"] is None and layers(1.0, set(), real)["food_cost"] is None and layers(1.0, {""}, real)["food_cost"] is None and layers(float("nan"), {"ACTUAL"}, real)["food_cost"] is None
    assert layers(3.0, {"ACTUAL"}, dict(real, fee_pct=(3.0, "ACTUAL")))["contribution"] is None and layers(3.0, {"ACTUAL"}, dict(real, fee_pct=(float("inf"), "ACTUAL")))["contribution"] is None   # fee is a 0-1 fraction
    assert abs(oil_allocation(2000, 1500, 20) - 25.0) < 1e-9
    for args in ((1000, 1500, 10), (100, float("nan"), 10), (100, 50, float("inf")), (100, 50, 0)):
        try: oil_allocation(*args); raise SystemExit("bad oil inputs accepted")
        except ValueError: pass
    print("food_costing selftest OK (TEST data, not saved)")

def main():
    if sys.argv[1:] == ["selftest"]: selftest(); return 0
    ings, recs = load(ING), load(REC); out, errs = analyse(ings, recs)
    if sys.argv[1:] == ["economics"]:   # cost path for each dish: purchase -> usable/portion food cost -> direct variable cost -> contribution
        de, seen = {}, {}
        for r in load(DE):
            c = norm(r.get("provenance_class")); v = num(r.get("value")); key = (r["dish_id"], r["field"]); seen[key] = seen.get(key, 0) + 1
            if v is not None and c in GRADE and r["field"] in LAYER_FIELDS: de.setdefault(r["dish_id"], {})[r["field"]] = (v, c)
        for (dish, field), n in seen.items():
            if n > 1: de.get(dish, {}).pop(field, None); print(f"WARNING: {dish}/{field} appears {n} times in dish-economics.csv; ignored until it is unique")
        for dish in sorted({r["dish_id"] for r in recs} | set(de)):
            d = out.get(dish); food = d["cost"] if d and not d["missing_price"] else None
            lay = layers(food, d["classes"] if d else set(), de.get(dish, {}))
            print(f"{dish}: FOOD COST " + (f"{lay['food_cost'][0]:.2f} (input grade {lay['food_cost'][1]}; purchase cost before yield {d['purchase']:.2f})" if lay["food_cost"] else "NOT COMPUTABLE") + " | DIRECT VARIABLE COST " + (f"{lay['direct_variable_cost'][0]:.2f} (grade {lay['direct_variable_cost'][1]})" if lay["direct_variable_cost"] else "NOT COMPUTABLE") + " | CONTRIBUTION " + (f"{lay['contribution'][0]:.2f} (grade {lay['contribution'][1]})" if lay["contribution"] else "NOT COMPUTABLE") + " | FULL OPERATING PROFIT not computed per dish (fin_model scenario) | frying oil counted only if it is a recipe ingredient")
            if lay["blocked"]: print("   unlocks: " + "; ".join(lay["blocked"][:7]))
        return 1 if errs else 0
    if not ings: print("No ingredient prices recorded yet: nothing to cost (no price is ever invented).")
    for dish, v in out.items():
        rd = any(GRADE.get(c, "F") != "A" for c in v["classes"])
        print(f"{dish}: " + (f"cost/portion {v['cost']:.2f} (ingredients only; no labour; purchase price / usable yield / waste kept separate)" + (" INCLUDES NON-QUOTE/NON-ACTUAL PRICES (retail receipt or reference): R&D planning only, not investor financials" if rd else "") if not v['missing_price'] else f"NOT COSTABLE ({len(v['missing_price'])} ingredient prices/quantities missing; no partial cost is reported)") + f" (missing: {v['missing_price'] or 'none'}); allergens {sorted(v['allergens']) or 'none recorded'}; vegetarian as recorded: {v['veg']}")
    for e in errs: print("FAIL", e)
    return 1 if errs else 0
if __name__ == "__main__": sys.exit(main())
