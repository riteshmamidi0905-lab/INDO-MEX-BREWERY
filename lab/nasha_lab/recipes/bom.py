"""Bill-of-materials explosion: dish -> raw ingredients in PURCHASE units (kg, l, each), as-purchased (AP) quantities after yield and sub-recipes."""
from . import costing, model

SIM_ITEM_TO_RECIPE = {"M01": "chicken-65-totopos", "M02": "paneer-tikka-taco", "M04": "mango-habanero-gobi", "M05": "butter-chicken-quesadilla"}


def explode(rid, recipes=None, master=None):
    """{ingredient_id: AP quantity per ONE portion in the ingredient's purchase unit}."""
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    out = {}

    def walk(rec_id, factor):
        for ln in model.iter_lines(recipes[rec_id]):
            if "subrecipe" in ln:
                walk(ln["subrecipe"], factor * ln["qty"] / recipes[ln["subrecipe"]]["batch_yield_g"])
                continue
            ing = master[ln["ingredient"]]
            qty = ln["qty"] * costing.TO_PURCHASE[ln["unit"]] * factor
            if ing.get("derived_from"):
                src, qty = ing["derived_from"], qty / (ing["yield_pct"] / 100.0)
                out[src] = out.get(src, 0.0) + qty / (master[src]["yield_pct"] / 100.0)
            else:
                out[ing["id"]] = out.get(ing["id"], 0.0) + qty / (ing["yield_pct"] / 100.0)

    walk(rid, 1.0)
    return out


def bom_table(recipes=None, master=None, mapping=None):
    mapping = mapping or SIM_ITEM_TO_RECIPE
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    return {item: explode(rid, recipes, master) for item, rid in mapping.items()}
