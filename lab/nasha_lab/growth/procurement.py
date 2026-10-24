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


def needs_from_requirements(requirements, period_weeks):
    """Needs stated explicitly by the project (equipment, services, consumables): a one-time requirement is needed once; a per-week requirement is needed every week of the period. Industry-agnostic: this is how a studio or
    any business without recipes says what it must buy. Returns {ref: need}."""
    out = {}
    for r in requirements or []:
        qty = float(r["qty"]) * (period_weeks if r["recurrence"] == "per_week" else 1)
        e = out.setdefault(r["ref"], dict(ingredient_ref=r["ref"], ingredient=r["name"], unit=r["unit"], qty=0.0, recurrence=r["recurrence"], kind=r["kind"]))
        e["qty"] += qty
    return out


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
            e = out.setdefault(ing, dict(ingredient_ref=ing, ingredient=master[ing]["name"], unit=master[ing]["unit"], qty=0.0, recurrence="per_week", kind="consumable"))
            e["qty"] += qty * n
    return out, unmapped


def _valid(p, as_of):
    return p["price_class"] != "NONE_PUBLISHED" and p["unit_price_cents"] is not None and (p["valid_from"] is None or p["valid_from"] <= as_of) and (p["valid_to"] is None or as_of <= p["valid_to"])


def compare(directory, need_map, as_of):
    """Cheapest valid quote per ingredient (whole packs only; ties by lead time, then supplier NAME, then id: ids are random per database). Returns (items, per-supplier totals, flags)."""
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
        # Tie-break (documented, deterministic across databases): cheapest whole-pack cost, then shortest lead time, then supplier NAME, and only then the id. Ids are random per database, so an id-first tie-break
        # made the supplier listing order (and, with exact ties, the chosen supplier) differ between two otherwise identical environments.
        cands.sort(key=lambda c: (c["cost_cents"], c["lead_days"] if c["lead_days"] is not None else 99, c["supplier"], c["supplier_id"]))
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
    for t in sorted(totals.values(), key=lambda t: (t["supplier"], t["supplier_id"])):         # by name first: ids are random per database
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


def replenishment(items, period_weeks, safety_pct=20.0):
    """Inventory planning from the same stored data: weekly usage, the chosen supplier's lead time, a reorder point (usage over the lead time plus a stated safety margin) and the number of weeks one order covers.
    The safety margin is an ASSUMPTION (default 20%), not a measured service level."""
    out = []
    for it in items:
        c = it["chosen"]
        if not c or it.get("recurrence", "per_week") != "per_week":
            continue                                   # a one-time purchase (equipment) has no weekly usage to plan a reorder point for
        weekly = it["need_qty"] / period_weeks
        lead = c["lead_days"] or 0
        out.append(dict(ingredient=it["ingredient"], unit=it["unit"], weekly_usage=round(weekly, 3), lead_days=lead, reorder_point=round(weekly * lead / 7 * (1 + safety_pct / 100), 3),
                        order_qty=c["buy_qty"], weeks_covered=round(c["buy_qty"] / weekly, 2) if weekly else None, supplier=c["supplier"]))
    return sorted(out, key=lambda r: (r["weeks_covered"] if r["weeks_covered"] is not None else 1e9, r["ingredient"]))


def price_effect(items, period_weeks):
    """What the supplier choice is worth: the planned spend at the cheapest valid quotes versus buying each ingredient from its second-cheapest valid quote (where there is one), and the monthly equivalent.
    Arithmetic on stored quotes only; the price classes involved are listed so a synthetic comparison cannot pass as a real saving."""
    chosen = sum(i["chosen"]["cost_cents"] for i in items if i["chosen"])
    second = sum((i["runner_up"]["cost_cents"] if i["runner_up"] else i["chosen"]["cost_cents"]) for i in items if i["chosen"])
    single = sum(1 for i in items if i["chosen"] and not i["runner_up"])
    classes = sorted({i["chosen"]["price_class"] for i in items if i["chosen"]})
    month = WEEKS_PER_MONTH / period_weeks
    return dict(chosen_total_cents=chosen, second_choice_total_cents=second, difference_cents=second - chosen, monthly_equivalent_difference_cents=round((second - chosen) * month), items_with_only_one_valid_quote=single,
                price_classes=classes, is_real_saving=False if "SYNTHETIC_QUOTE" in classes else None,
                note="Compares the cheapest valid quote with the next cheapest for each ingredient. " + ("Every price used is a synthetic fixture, so this is an illustration, not a saving." if classes == ["SYNTHETIC_QUOTE"] else "Quotes of different price classes are not interchangeable; check each before relying on the difference."))


def plan(directory, scenario_results, period_weeks, as_of, requirements=(), use_recipes=True):
    """The needs come from the project's explicit requirements and, for an industry that cooks (use_recipes), from the recipe bill of materials for the scenario's demand. Same comparison, same independent re-derivation."""
    portions, unmapped, need_map, sources = {}, [], {}, []
    if use_recipes and scenario_results:
        portions = demand(scenario_results, period_weeks)
        need_map, unmapped = needs(portions); sources.append("recipes")
    if requirements:
        for ref, n in needs_from_requirements(requirements, period_weeks).items():
            if ref in need_map and need_map[ref]["unit"] == n["unit"]:
                need_map[ref]["qty"] += n["qty"]
            else:
                need_map[ref] = n
        sources.append("requirements")
    items, totals, flags = compare(directory, need_map, as_of)
    kinds = {r: (n.get("recurrence", "per_week"), n.get("kind", "consumable")) for r, n in need_map.items()}
    for it in items:
        it["recurrence"], it["kind"] = kinds.get(it["ingredient_ref"], ("per_week", "consumable"))
    if unmapped:
        flags.append(dict(kind="unmapped_products", message="No recipe for: " + ", ".join(unmapped)))
    return dict(needs_from=sources, period_weeks=period_weeks, as_of=str(as_of), portions={k: round(v, 1) for k, v in portions.items()}, items=items, price_effect=price_effect(items, period_weeks), replenishment=replenishment(items, period_weeks), replenishment_assumption="safety margin 20% (assumed)", supplier_totals=totals, total_cost_cents=sum(t["cost_cents"] for t in totals), flags=flags,
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
    pe = plan.get("price_effect")
    if pe is not None and (pe["chosen_total_cents"] != total or pe["difference_cents"] != pe["second_choice_total_cents"] - pe["chosen_total_cents"] or pe["difference_cents"] < 0):
        problems.append("price effect does not reconcile with the chosen quotes")
    return problems


def digest(plan):
    """Fingerprint of exactly what a person approves: the period, every chosen quote (supplier, packs, cost) and the total. The planning date is excluded; what the quotes say on that date is what is included."""
    import hashlib
    import json
    core = dict(period_weeks=plan["period_weeks"], total=plan["total_cost_cents"], items=[[i["ingredient_ref"], (i["chosen"] or {}).get("supplier_id"), (i["chosen"] or {}).get("packs"), (i["chosen"] or {}).get("cost_cents")] for i in plan["items"]])
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
