"""Recipe data model: loads the ingredient master and v1 recipes/sub-recipes from food/recipes and validates them.

Validation is strict on what can be checked mechanically: references, units, cycles, declared vs derived allergens, D-54 (no beef/pork derivatives in
ingredient names), required sections for a dish, honest status labelling. It cannot check that a recipe tastes good, is safe, or is correct: only cooking can.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECIPES = ROOT / "food/recipes"
UNIT_FOR = {"g": "kg", "kg": "kg", "ml": "l", "l": "l", "each": "each"}
ALLERGENS = ("milk", "egg", "fish", "shellfish", "tree_nut", "peanut", "wheat", "soy", "sesame")        # US major food allergens
D54 = re.compile(r"\b(beef|veal|pork|bacon|ham|lard|chorizo|pancetta|prosciutto|sausage|gelatin(?:e)?|tallow|suet|brisket|carnitas|barbacoa|ribeye|steak|jamon|salami|pepperoni|mortadella|manteca)\b", re.I)
DISH_REQUIRED = ("id", "name", "version", "status", "cooking_method", "portion", "components", "sauces", "method", "plating", "equipment", "food_safety", "workflow", "pairing", "photography", "allergens_declared", "dietary", "evidence", "menu_category", "menu_status", "development_status", "target_gross_margin_pct", "research")
OVERCLAIM = re.compile(r"\b(was|were|has been|have been|had been) (cooked|tasted|brewed|tested)\b|\btasted (great|delicious|balanced)\b|\bpanel (scored|found)\b", re.I)
NEGATION = re.compile(r"\b(not|never|nothing|no part|none|nor)\b", re.I)


def overclaims(text):
    """Phrases that read as a cook/taste/test result, ignoring ones in a negated clause ('nothing here has been cooked')."""
    out = []
    for m in OVERCLAIM.finditer(text):
        before = text[max(0, m.start() - 45):m.start()]
        if not NEGATION.search(before):
            out.append(m.group(0))
    return out


class RecipeError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_master(path=None):
    p = Path(path) if path else RECIPES / "ingredients/ingredient-master.json"
    d = json.loads(p.read_text())
    return {i["id"]: i for i in d["ingredients"]}


def load_recipes(directory=None):
    d = Path(directory) if directory else RECIPES / "v1"
    out = {}
    for f in sorted(d.glob("*.v1.json")):
        r = json.loads(f.read_text())
        out[r["id"]] = r
    return out


def iter_lines(recipe):
    """Yield every ingredient/sub-recipe line of a dish or sub-recipe."""
    if recipe["kind"] == "subrecipe":
        yield from recipe["lines"]
    else:
        for c in recipe["components"]:
            yield from c["lines"]


def derived_allergens(rid, recipes, master, _seen=None):
    _seen = _seen or set()
    if rid in _seen:
        raise RecipeError(f"sub-recipe cycle at {rid}")
    out = set()
    for ln in iter_lines(recipes[rid]):
        if "subrecipe" in ln:
            out |= derived_allergens(ln["subrecipe"], recipes, master, _seen | {rid})
        else:
            ing = master[ln["ingredient"]]
            src = master[ing["derived_from"]] if ing.get("derived_from") else ing
            out |= set(ing["allergens"]) | set(src["allergens"])
    return out


def validate(recipes=None, master=None):
    """Return a list of error strings (empty = valid)."""
    recipes = recipes or load_recipes()
    master = master or load_master()
    errs = []
    for ing in master.values():
        if D54.search(ing["name"]):
            errs.append(f"D-54: ingredient '{ing['name']}'")
        if "derived_from" not in ing and not ing.get("price"):
            errs.append(f"ingredient {ing['id']} has no price assumption range")
        if "price" in ing and not (ing["price"]["low"] <= ing["price"]["base"] <= ing["price"]["high"]):
            errs.append(f"ingredient {ing['id']}: price range not ordered")
        if not 0 < ing["yield_pct"] <= 100:
            errs.append(f"ingredient {ing['id']}: yield_pct out of range")
    for rid, r in recipes.items():
        if "PRELIMINARY" not in r["status"].upper() or "NOT COOKED OR TASTED" not in r["status"].upper():
            errs.append(f"{rid}: status must say PRELIMINARY and NOT COOKED OR TASTED")
        blob = json.dumps(r, ensure_ascii=False)
        if overclaims(blob):
            errs.append(f"{rid}: wording claims a cook/taste/test result")
        if re.search(r"\$\s?\d|\bprice\b\s*[:=]\s*\d", blob):
            errs.append(f"{rid}: contains a price (no menu or recipe prices are set, D-86)")
        if r["kind"] == "dish":
            for k in DISH_REQUIRED:
                if k not in r or (k != "allergens_declared" and r[k] in (None, "", [], {})):
                    errs.append(f"{rid}: missing section '{k}'")
            if r.get("menu_category") not in ("appetizer", "main"):
                errs.append(f"{rid}: menu_category must be appetizer or main")
            if not isinstance(r.get("workflow", {}).get("labor_minutes_per_portion"), dict):
                errs.append(f"{rid}: missing prep-time estimate (workflow.labor_minutes_per_portion)")
            if not r.get("method", {}).get("steps"):
                errs.append(f"{rid}: no preparation steps")
        for ln in iter_lines(r):
            q = ln.get("qty")
            if not isinstance(q, (int, float)) or q <= 0:
                errs.append(f"{rid}: bad quantity {ln}")
                continue
            if "subrecipe" in ln:
                if ln["subrecipe"] not in recipes or recipes[ln["subrecipe"]]["kind"] != "subrecipe":
                    errs.append(f"{rid}: unknown sub-recipe {ln['subrecipe']}")
                elif ln["unit"] != "g":
                    errs.append(f"{rid}: sub-recipe line must be in g")
            else:
                ing = master.get(ln["ingredient"])
                if ing is None:
                    errs.append(f"{rid}: unknown ingredient {ln['ingredient']}")
                elif UNIT_FOR.get(ln["unit"]) != ing["unit"]:
                    errs.append(f"{rid}: unit {ln['unit']} incompatible with {ing['id']} ({ing['unit']})")
        try:
            derived = derived_allergens(rid, recipes, master)
            declared = set(r.get("allergens_declared", r.get("allergens_declared", [])))
            if r["kind"] == "dish":
                if not derived <= declared:
                    errs.append(f"{rid}: derived allergens {sorted(derived - declared)} not declared")
                if not declared <= derived | {"wheat"} and declared - derived:
                    errs.append(f"{rid}: declared allergens not derivable from ingredients: {sorted(declared - derived)}")
            elif not derived <= set(r.get("allergens_declared", [])):
                errs.append(f"{rid}: sub-recipe derived allergens {sorted(derived)} not declared")
        except (KeyError, RecipeError) as e:
            errs.append(f"{rid}: {e}")
    return errs
