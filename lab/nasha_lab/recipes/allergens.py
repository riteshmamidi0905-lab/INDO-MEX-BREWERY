"""Allergen review derived from the ingredient master (US major allergens + flagged items). A DERIVATION from declared ingredient allergens, not a validation:
blends, processed items and cross-contact need label checks and a qualified allergen reviewer. Never an allergen-free claim."""
from . import model

COLS = model.ALLERGENS


def dish_matrix(recipes=None, master=None):
    recipes = recipes or model.load_recipes()
    master = master or model.load_master()
    rows = []
    for r in recipes.values():
        if r["kind"] != "dish":
            continue
        der = model.derived_allergens(r["id"], recipes, master)
        flags = []
        for ln in model.iter_lines(r):
            ids = [ln["ingredient"]] if "ingredient" in ln else _flat(ln["subrecipe"], recipes)
            for i in ids:
                ing = master[i]
                if ing["vegetarian"] == "check" or "check" in ing["notes"].lower():
                    flags.append(f"{ing['name']}: {ing['notes'] or 'check label'}")
        rows.append({"dish": r["name"], "id": r["id"], **{a: (a in der) for a in COLS}, "declared": sorted(r["allergens_declared"]), "label_checks": sorted(set(flags)), "note": r["allergen_notes"],
                     "claims": "none (no allergen-free, gluten-free or halal claim)"})
    return rows


def _flat(rid, recipes, seen=()):
    out = []
    for ln in model.iter_lines(recipes[rid]):
        out += _flat(ln["subrecipe"], recipes, seen + (rid,)) if "subrecipe" in ln else [ln["ingredient"]]
    return out


def beer_notes(specs):
    """Allergen/ingredient statements for the beers (provisional)."""
    return {b["id"]: {"contains": b["contains"], "no_gluten_free_claim": b["no_gluten_free_claim"]} for b in specs["beers"]}
