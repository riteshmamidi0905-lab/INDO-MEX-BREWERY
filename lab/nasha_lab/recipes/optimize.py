"""Recipe-cost levers and supplier-price sensitivity (D-88). ANALYSIS, not instructions: every lever states its quality impact; no lever is applied to a recipe.

Principle (founder, D-88): never cut quality just to reach a margin target. Portion levers are bounded by a quality floor (no more than -5% of the primary protein without a tasting),
and the ORIGINAL costing scenario is always returned alongside for comparison. All prices are planning assumptions or SYNTHETIC quotes.
"""
import copy

from . import costing, model, pricing, suppliers

QUALITY_FLOOR_PROTEIN_SCALE = 0.95


def primary_protein(rid, recipes=None, master=None):
    recipes, master = recipes or model.load_recipes(), master or model.load_master()
    drivers, _ = costing.top_drivers(rid, recipes, master, n=999)
    prot = [d for d in drivers if master[d["ingredient"]]["category"] == "protein"]
    return prot[0]["ingredient"] if prot else None


def _variant(rid, cfg, recipes, master, protein_scale=1.0, yield_pct=None, price_map=None, waste_pct=None):
    r2, m2, c2 = copy.deepcopy(recipes), copy.deepcopy(master), copy.deepcopy(cfg)
    prot = primary_protein(rid, recipes, master)
    if protein_scale != 1.0 and prot:
        for comp in r2[rid]["components"]:
            for ln in comp["lines"]:
                if ln.get("ingredient") == prot:
                    ln["qty"] *= protein_scale
    if yield_pct is not None and prot:
        m2[prot]["yield_pct"] = yield_pct
    for k, v in (price_map or {}).items():
        if k in m2 and "price" in m2[k]:
            m2[k]["price"] = {s: v for s in m2[k]["price"]}
    if waste_pct is not None:
        c2["cost_assumptions"]["waste_pct"] = waste_pct
    return pricing.economics(rid, c2, "base", r2, m2)


def cheapest_prices(quotes, shocks=None):
    """{ingredient: lowest unit price among SYNTHETIC quotes}, optionally with per-supplier price shocks {supplier_id: +fraction}. Also returns who supplies each."""
    best = {}
    for q in quotes:
        p = q["unit_price"] * (1 + (shocks or {}).get(q["supplier_id"], 0.0))
        if q["ingredient_id"] not in best or (p, q["supplier_id"]) < best[q["ingredient_id"]][:2]:
            best[q["ingredient_id"]] = (p, q["supplier_id"])
    return best


def levers(rid, cfg=None, recipes=None, master=None, quotes=None):
    """Rows of {lever, setting, food_cost, gross_margin_pct, margin_delta_pts, quality_impact, note} for one dish. The first row is the ORIGINAL scenario (kept for comparison)."""
    cfg, recipes, master = cfg or pricing.load_config(), recipes or model.load_recipes(), master or model.load_master()
    quotes = quotes or suppliers.load()["quotes"]
    base = pricing.economics(rid, cfg, "base", recipes, master)
    rows = [("original", "planning-assumption base prices, as costed", base, "none", "baseline retained for comparison (D-88)")]
    prot = primary_protein(rid, recipes, master)
    for s in (0.90, 0.95, 1.05):
        floor = s < QUALITY_FLOOR_PROTEIN_SCALE
        rows.append(("portion", f"{prot} x{s:.2f}", _variant(rid, cfg, recipes, master, protein_scale=s), "BELOW QUALITY FLOOR: needs tasting; do not apply" if floor else ("tasting needed" if s != 1 else "none"),
                     "bounded by the quality floor (-5% protein)" if not floor else "shown for information only"))
    if prot:
        y0 = master[prot]["yield_pct"]
        for y in sorted({min(100, y0 + 5), min(100, y0 + 10)}):
            if y > y0:
                rows.append(("yield", f"{prot} yield {y0}% -> {y}%", _variant(rid, cfg, recipes, master, yield_pct=y), "none if cut spec/supplier delivers it",
                             f"pre-trimmed spec is cost-neutral up to a +{(y / y0 - 1) * 100:.0f}% price premium per kg"))
    best = cheapest_prices(quotes)
    rows.append(("supplier", "cheapest valid SYNTHETIC quote per ingredient", _variant(rid, cfg, recipes, master, price_map={k: v[0] for k, v in best.items()}), "none if specs are equivalent",
                 "synthetic quotes only; real quotes and spec equivalence needed"))
    for w in (3.0, 7.0):
        rows.append(("waste", f"waste allowance {w:.0f}%", _variant(rid, cfg, recipes, master, waste_pct=w), "none", "operational (portion control, prep discipline, holding)"))
    b = base["gross_margin_pct"]
    return [{"dish": rid, "lever": l, "setting": s, "food_cost": e["food_cost"], "gross_margin_pct": e["gross_margin_pct"], "margin_delta_pts": (e["gross_margin_pct"] - b) * 100, "quality_impact": q, "note": n}
            for l, s, e, q, n in rows]


def protein_grams_for_margin(rid, target_pct, cfg=None, recipes=None, master=None):
    """INFORMATION ONLY: primary-protein scale at which the planning gross margin equals target (linear in grams). Not a recommendation."""
    cfg, recipes, master = cfg or pricing.load_config(), recipes or model.load_recipes(), master or model.load_master()
    e0, e1 = pricing.economics(rid, cfg, "base", recipes, master), _variant(rid, cfg, recipes, master, protein_scale=0.9)
    slope = (e1["gross_margin_pct"] - e0["gross_margin_pct"]) / -0.1
    return 1.0 + (target_pct / 100 - e0["gross_margin_pct"]) / slope if slope else None


def supplier_sensitivity(shock=0.15, cfg=None, recipes=None, master=None, quotes=None):
    """Dish cost when each supplier's quoted prices rise by `shock`, under cheapest-quote sourcing (a supplier that is no longer cheapest loses the line). Also reports cost share."""
    cfg, recipes, master = cfg or pricing.load_config(), recipes or model.load_recipes(), master or model.load_master()
    quotes = quotes or suppliers.load()["quotes"]
    sup_ids = sorted({q["supplier_id"] for q in quotes})
    base_best = cheapest_prices(quotes)
    out = []
    for rid, r in recipes.items():
        if r["kind"] != "dish":
            continue
        base = _variant(rid, cfg, recipes, master, price_map={k: v[0] for k, v in base_best.items()})
        for s in sup_ids:
            sh = cheapest_prices(quotes, {s: shock})
            e = _variant(rid, cfg, recipes, master, price_map={k: v[0] for k, v in sh.items()})
            flat, tot = costing.top_drivers(rid, recipes, master, n=999)
            share = sum(d["cost"] for d in flat if base_best.get(d["ingredient"], (0, None))[1] == s) / tot if tot else 0.0
            out.append({"supplier_id": s, "dish": rid, "base_food_cost": base["food_cost"], "shocked_food_cost": e["food_cost"], "delta_pct": e["food_cost"] / base["food_cost"] - 1, "share_of_cost": share})
    return out
