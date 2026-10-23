"""Versioned pricing configuration and menu economics (D-87).

`food/pricing/price-v2-2026-10-22.json` holds the founder-approved CONCEPT menu prices (house beer glass $9.00, pitcher $31.00, appetizers $13.50, mains $18.50).
They are concept prices, not an operating menu: no restaurant exists. Ingredient costs remain PLANNING ASSUMPTIONS (not supplier quotes, not purchase records).
`food/pricing/price-v1-placeholder.json` is the frozen record of the earlier placeholder prices used by the historical synthetic data set; it is never edited.
Money is carried as integer cents in stored tables and as float dollars only inside this module's cost arithmetic.
"""
import json
from pathlib import Path

from . import bom, costing, model

PRICING = model.ROOT / "food/pricing"
V2 = "price-v2-2026-10-22"
V3 = "price-v3-2026-10-23"
CURRENT = V3
V1 = "price-v1-placeholder"


def load_config(config_id=None):
    config_id = config_id or CURRENT
    return json.loads((PRICING / f"{config_id}.json").read_text())


def price_cents(cfg, menu_category):
    return int(round(cfg["prices_usd"][menu_category] * 100))


def dish_price_cents(cfg, rid, recipes=None):
    recipes = recipes or model.load_recipes()
    return price_cents(cfg, recipes[rid]["menu_category"])


def economics(rid, cfg=None, scenario="base", recipes=None, master=None, shock=None):
    """Per-portion economics at the config price. `shock` = {ingredient category: fractional price change} applied to purchase prices (inflation sensitivity)."""
    cfg = cfg or load_config()
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    if shock:
        master = {k: dict(v, price={s: p * (1 + shock.get(v["category"], 0.0)) for s, p in v["price"].items()}) if "price" in v else v for k, v in master.items()}
    ing = costing.recipe_cost(rid, recipes, master, scenario)["total"]
    a = cfg["cost_assumptions"]
    waste = ing * a["waste_pct"] / 100.0
    consumables = a["consumables_per_portion_usd"]
    r = recipes[rid]
    lab = r["workflow"]["labor_minutes_per_portion"]
    labor = (lab["prep"] + lab["service"]) / 60.0 * a["loaded_labor_usd_per_hour"]
    price = cfg["prices_usd"][r["menu_category"]]
    food = ing + waste
    return {"id": rid, "name": r["name"], "category": r["menu_category"], "scenario": scenario, "price": price, "ingredient_cost": ing, "waste_allowance": waste,
            "food_cost": food, "consumables": consumables, "food_cost_pct": food / price, "gross_profit": price - food - consumables,
            "gross_margin_pct": (price - food - consumables) / price, "direct_labor": labor, "contribution_margin": price - food - consumables - labor,
            "meets_target_margin": (price - food - consumables) / price * 100 >= r["target_gross_margin_pct"]}


def menu_economics(cfg=None, scenario="base", **kw):
    recipes = model.load_recipes()
    return [economics(r["id"], cfg, scenario, recipes, **kw) for r in recipes.values() if r["kind"] == "dish"]


def inflation_table(rid, cfg=None, shocks=(0.0, 0.10, 0.20, 0.30)):
    """Food-cost % when ALL purchased ingredients rise by each shock, and when only protein / dairy rise by it."""
    cfg = cfg or load_config()
    out = []
    for s in shocks:
        allc = {c: s for c in ("protein", "dairy", "produce", "grain", "pantry", "spice", "oil", "aromatic", "herb")}
        out.append({"shock": s, "all": economics(rid, cfg, shock=allc)["food_cost_pct"], "protein_only": economics(rid, cfg, shock={"protein": s})["food_cost_pct"],
                    "dairy_only": economics(rid, cfg, shock={"dairy": s})["food_cost_pct"]})
    return out


def beer_menu(cfg=None):
    cfg = cfg or load_config()
    return cfg["beers"]


def v1_catalog_snapshot():
    """The v1 placeholder prices exactly as the historical simulation catalog defines them (used to prove the frozen record still matches)."""
    from .. import enterprise_sim as es
    return {c[0]: {"name": c[1], "category": c[2], "price_cents": int(c[3])} for c in es.CATALOG}


def bom_rows(cfg=None, recipes=None, master=None):
    """Flat BOM for every dish: (recipe_id, version, ingredient_id, as-purchased qty per portion in purchase units)."""
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    rows = []
    for r in recipes.values():
        if r["kind"] != "dish":
            continue
        for ing, q in sorted(bom.explode(r["id"], recipes, master).items()):
            rows.append((r["id"], r["version"], ing, q, master[ing]["unit"]))
    return rows
