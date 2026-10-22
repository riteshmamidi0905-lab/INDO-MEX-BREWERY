"""Preliminary food-cost model. Every price is a PLANNING ASSUMPTION range (low/base/high), not a supplier quote and not a menu price; every yield is a typical
factor to be measured. No menu price exists (D-86): `implied_price` is arithmetic (cost / target food-cost %), never a recommendation.

Cost of a line = quantity (edible/EP) / ingredient yield x unit price. A sub-recipe line costs batch cost x qty / batch yield (grams). Derived ingredients
(hung curd) take the price of their source divided by their yield.
"""
from . import model

SCENARIOS = ("low", "base", "high")
TO_PURCHASE = {"g": 0.001, "kg": 1.0, "ml": 0.001, "l": 1.0, "each": 1.0}


def unit_price(ing, master, scenario):
    """Price per purchase unit of one AS-PURCHASED unit (before yield)."""
    if ing.get("derived_from"):
        src = master[ing["derived_from"]]
        return unit_price(src, master, scenario) / (ing["yield_pct"] / 100.0)
    return ing["price"][scenario]


def line_cost(ln, recipes, master, scenario, _stack=()):
    if "subrecipe" in ln:
        sr = recipes[ln["subrecipe"]]
        batch = recipe_cost(sr["id"], recipes, master, scenario, _stack)["total"]
        return batch * ln["qty"] / sr["batch_yield_g"]
    ing = master[ln["ingredient"]]
    qty = ln["qty"] * TO_PURCHASE[ln["unit"]]
    y = 1.0 if ing.get("derived_from") else ing["yield_pct"] / 100.0
    return qty / y * unit_price(ing, master, scenario)


def recipe_cost(rid, recipes=None, master=None, scenario="base", _stack=()):
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    if rid in _stack:
        raise model.RecipeError(f"cycle at {rid}")
    r = recipes[rid]
    rows = []
    for ln in model.iter_lines(r):
        c = line_cost(ln, recipes, master, scenario, _stack + (rid,))
        rows.append({"item": ln.get("ingredient") or ln["subrecipe"], "qty": ln["qty"], "unit": ln["unit"], "cost": c})
    total = sum(x["cost"] for x in rows)
    for x in rows:
        x["share"] = x["cost"] / total if total else 0.0
    return {"id": rid, "scenario": scenario, "total": total, "lines": rows}


def dish_summary(rid, recipes=None, master=None, waste_pct=0.0, target_food_cost_pct=30.0):
    """Cost per portion in the three price scenarios, with an optional waste allowance, and the arithmetic implied price (NOT a menu price)."""
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    out = {"id": rid, "name": recipes[rid]["name"], "waste_pct": waste_pct}
    for sc in SCENARIOS:
        c = recipe_cost(rid, recipes, master, sc)["total"] * (1 + waste_pct / 100.0)
        out[sc] = round(c, 3)
    out["implied_price_at_target_pct"] = {"target_food_cost_pct": target_food_cost_pct, **{sc: round(out[sc] / (target_food_cost_pct / 100.0), 2) for sc in SCENARIOS}}
    out["price_status"] = "NO MENU PRICE SET (D-86); implied prices are arithmetic only"
    return out


def top_drivers(rid, recipes=None, master=None, scenario="base", n=5):
    """Largest cost lines after flattening sub-recipes into raw ingredients (the real cost drivers)."""
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    flat = {}

    def walk(rec_id, factor, stack):
        r = recipes[rec_id]
        for ln in model.iter_lines(r):
            if "subrecipe" in ln:
                walk(ln["subrecipe"], factor * ln["qty"] / recipes[ln["subrecipe"]]["batch_yield_g"], stack + (rec_id,))
            else:
                flat[ln["ingredient"]] = flat.get(ln["ingredient"], 0.0) + factor * line_cost(ln, recipes, master, scenario)
    walk(rid, 1.0, ())
    total = sum(flat.values())
    rows = sorted(flat.items(), key=lambda kv: -kv[1])[:n]
    return [{"ingredient": k, "name": master[k]["name"], "cost": round(v, 4), "share": round(v / total, 3)} for k, v in rows], total


def sensitivity(rid, recipes=None, master=None, shock=0.20):
    """Cost change if ONE ingredient's price rises by `shock` (default +20%), ranked: where price risk concentrates."""
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    drivers, total = top_drivers(rid, recipes, master, n=999)
    return [{"ingredient": d["ingredient"], "name": d["name"], "delta": round(d["cost"] * shock, 4), "delta_pct_of_dish": round(d["share"] * shock * 100, 2)} for d in drivers]


def all_dishes(recipes=None, master=None, **kw):
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    return [dish_summary(r["id"], recipes, master, **kw) for r in recipes.values() if r["kind"] == "dish"]
