"""Procurement planning for a launch project, computed from STORED data: the project's financial scenario (units per product per month), the existing recipe bill-of-materials (`recipes/bom.py`, reused),
and the tenant's stored supplier quotes. Pure functions; no purchase order is created, no supplier is contacted, nothing is ordered: the output is a RECOMMENDATION that a person must approve through THE WEIR.
Quote prices are only as real as their price class: SYNTHETIC_QUOTE fixtures are labelled as such in every output, and suppliers with no published price are never ranked."""
import math

from ..recipes import bom, model as RM
from . import pricing as GP

WEEKS_PER_MONTH = 52 / 12


def recipe_map():
    return {it["name"]: rid for rid, it in GP.nasha_items().items()}


def demand(scenario_results, period_weeks):
    """Portions per product for the period, from the scenario's stored units per month."""
    f = period_weeks / WEEKS_PER_MONTH
    return {ln["name"]: ln["units_per_month"] * f for ln in scenario_results["lines"]}


def needs(portions, recipes=None, master=None):
    """Ingredient requirements (as-purchased quantities in purchase units) for the demanded portions. Returns (needs, unmapped product names)."""
    recipes = recipes or RM.load_recipes()
    master = master or RM.load_master()
    rmap, out, unmapped = recipe_map(), {}, []
    for name, n in sorted(portions.items()):
        rid = rmap.get(name)
        if rid is None:
            unmapped.append(name); continue
        for ing, qty in bom.explode(rid, recipes, master).items():
            e = out.setdefault(ing, dict(ingredient_ref=ing, ingredient=master[ing]["name"], unit=master[ing]["unit"], qty=0.0))
            e["qty"] += qty * n
    return out, unmapped


def _valid(p, as_of):
    return p["price_class"] != "NONE_PUBLISHED" and p["unit_price_cents"] is not None and (p["valid_from"] is None or p["valid_from"] <= as_of) and (p["valid_to"] is None or as_of <= p["valid_to"])


def compare(directory, need_map, as_of):
    """Cheapest valid quote per ingredient (whole packs only; ties by lead time then supplier id). Returns (items, per-supplier totals, flags)."""
    items, flags = [], []
    for ing, need in sorted(need_map.items()):
        cands = []
        for s in directory:
            for p in s["products"]:
                if p["ingredient_ref"] == ing and p["unit"] == need["unit"] and _valid(p, as_of):
                    pack = float(p["pack_qty"] or 1)
                    packs = max(1, math.ceil(need["qty"] / pack - 1e-9))
                    buy = packs * pack
                    cands.append(dict(supplier_id=s["id"], supplier=s["name"], verification_status=s["verification_status"], buy_qty=buy, packs=packs, unit_price_cents=float(p["unit_price_cents"]), cost_cents=round(buy * float(p["unit_price_cents"])),
                                      lead_days=p["lead_days"], min_order_cents=p["min_order_cents"] or 0, price_class=p["price_class"], valid_to=str(p["valid_to"]) if p["valid_to"] else None))
        cands.sort(key=lambda c: (c["cost_cents"], c["lead_days"] if c["lead_days"] is not None else 99, c["supplier_id"]))
        if not cands:
            flags.append(dict(kind="no_valid_quote", ingredient=need["ingredient"], message=f"No valid priced quote exists for {need['ingredient']} on the planning date."))
            items.append(dict(ingredient_ref=ing, ingredient=need["ingredient"], unit=need["unit"], need_qty=round(need["qty"], 4), chosen=None, alternatives=0, runner_up=None)); continue
        items.append(dict(ingredient_ref=ing, ingredient=need["ingredient"], unit=need["unit"], need_qty=round(need["qty"], 4), chosen=cands[0], alternatives=len(cands) - 1,
                          runner_up=None if len(cands) < 2 else dict(supplier=cands[1]["supplier"], cost_cents=cands[1]["cost_cents"])))
    totals = {}
    for it in items:
        c = it["chosen"]
        if c:
            t = totals.setdefault(c["supplier_id"], dict(supplier_id=c["supplier_id"], supplier=c["supplier"], cost_cents=0, min_order_cents=0, items=0, price_classes=set()))
            t["cost_cents"] += c["cost_cents"]; t["items"] += 1; t["min_order_cents"] = max(t["min_order_cents"], c["min_order_cents"]); t["price_classes"].add(c["price_class"])
    out = []
    for t in sorted(totals.values(), key=lambda t: t["supplier_id"]):
        t["price_classes"] = sorted(t["price_classes"]); t["below_minimum_order"] = t["cost_cents"] < t["min_order_cents"]
        if t["below_minimum_order"]:
            flags.append(dict(kind="below_minimum_order", supplier=t["supplier"], message=f"{t['supplier']}: planned spend is below its minimum order."))
        out.append(t)
    classes = {c for t in out for c in t["price_classes"]}
    if classes == {"SYNTHETIC_QUOTE"}:
        flags.append(dict(kind="synthetic_prices", message="Every price used is a synthetic fixture. No real supplier price exists, so this is a planning exercise, not a purchasing recommendation."))
    unpriced = [s["name"] for s in directory if s["products"] and all(p["price_class"] == "NONE_PUBLISHED" for p in s["products"])]
    if unpriced:
        flags.append(dict(kind="unpriced_suppliers", message="Not compared (no published prices): " + ", ".join(unpriced) + ". A quote request would be needed; none has been sent."))
    return items, out, flags


def plan(directory, scenario_results, period_weeks, as_of):
    portions = demand(scenario_results, period_weeks)
    need_map, unmapped = needs(portions)
    items, totals, flags = compare(directory, need_map, as_of)
    if unmapped:
        flags.append(dict(kind="unmapped_products", message="No recipe for: " + ", ".join(unmapped)))
    return dict(period_weeks=period_weeks, as_of=str(as_of), portions={k: round(v, 1) for k, v in portions.items()}, items=items, supplier_totals=totals, total_cost_cents=sum(t["cost_cents"] for t in totals), flags=flags,
                disclaimer="Recommendation only. No order was placed and no supplier was contacted.")


def check_plan(directory, plan, as_of):
    """Independent re-derivation (brute force, separate arithmetic): every chosen quote exists, is valid on the date, is the cheapest valid whole-pack option, and every cost and total adds up."""
    problems = []
    flat = [(s, p) for s in directory for p in s["products"]]
    total = 0
    for it in plan["items"]:
        ch = it["chosen"]
        options = []
        for s, p in flat:
            if p["ingredient_ref"] == it["ingredient_ref"] and p["unit"] == it["unit"] and _valid(p, as_of):
                packs = max(1, math.ceil(round(it["need_qty"] / float(p["pack_qty"] or 1), 6)))
                options.append((round(packs * float(p["pack_qty"] or 1) * float(p["unit_price_cents"])), s["id"]))
        if ch is None:
            if options:
                problems.append(f"{it['ingredient']}: a valid quote exists but none was chosen")
            continue
        if not options:
            problems.append(f"{it['ingredient']}: the chosen quote is not valid on {as_of}"); continue
        best = min(options)[0]
        if abs(ch["cost_cents"] - best) > 1:
            problems.append(f"{it['ingredient']}: chosen cost {ch['cost_cents']} is not the cheapest valid option {best}")
        total += ch["cost_cents"]
    if total != plan["total_cost_cents"] or total != sum(t["cost_cents"] for t in plan["supplier_totals"]):
        problems.append("totals do not add up")
    return problems


def digest(plan):
    """Fingerprint of exactly what a person approves: the period, every chosen quote (supplier, packs, cost) and the total. The planning date is excluded; what the quotes say on that date is what is included."""
    import hashlib
    import json
    core = dict(period_weeks=plan["period_weeks"], total=plan["total_cost_cents"], items=[[i["ingredient_ref"], (i["chosen"] or {}).get("supplier_id"), (i["chosen"] or {}).get("packs"), (i["chosen"] or {}).get("cost_cents")] for i in plan["items"]])
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
