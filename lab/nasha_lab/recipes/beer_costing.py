"""PRELIMINARY beer production costing and beverage margins (D-88). Every number is a PLANNING ASSUMPTION computed from the concept formulations in beer_specs and the
assumption file food/pricing/beer-cost-assumptions.v1.json. Nothing has been brewed, measured or purchased: these are NOT verified production costs.

Serving sizes are the founder's provisional concept sizes (glass 16 US fl oz, pitcher 60 US fl oz) stored exactly from fl oz; real glassware capacity, headspace and fill
lines need physical validation. Excise tax, TABC/TTB fees, equipment depreciation and serving labor are excluded (see `excluded` in the assumption file).
"""
import json

from .. import beer_specs
from . import model, pricing

SCEN = ("low", "base", "high")
ASSUMP = pricing.PRICING / "beer-cost-assumptions.v1.json"


def assumptions():
    return json.loads(ASSUMP.read_text())


def serving_ml(cfg, size):
    """Exact millilitres of a serving, computed from fl oz (never from a rounded mL figure)."""
    sv = cfg["serving_volumes"]
    return sv[size]["fl_oz"] * sv["oz_to_ml"]


def _price(a, key, scen):
    return a["ingredient_prices_usd_per_kg"][key][SCEN.index(scen)]


def batch_ingredients(beer_id, a=None):
    """[(item, kg, usd_per_kg_by_scenario)] for one pilot batch (100 L into the fermenter)."""
    a = a or assumptions()
    specs = {b["id"]: b for b in beer_specs.specs()["beers"]}
    b, ra, n = specs[beer_id], a["recipe_assumptions"], a["batch"]["pilot_batch_l"] / 100.0
    master = model.load_master()
    rows = [(f"{k} (grist)", kg, {s: _price(a, k, s) for s in SCEN}) for k, kg in b["grist_kg"].items()]
    rows.append(("yeast", ra["yeast_g_per_100_l"][beer_id] / 1000.0 * n, {s: _price(a, "yeast", s) for s in SCEN}))
    if beer_id == "badshah":
        rows.append(("bittering hops", b["bittering_hops"]["grams_for_objective"] / 1000.0, {s: _price(a, "bittering hops (noble-type)", s) for s in SCEN}))
    else:
        rows.append(("bittering hops", ra["amba_haze_bittering_g_per_100_l"] * n / 1000.0, {s: _price(a, "aroma/dry hops (IPA-type)", s) for s in SCEN}))
        rows.append(("dry hops", ra["amba_haze_dry_hop_g_per_l"] * a["batch"]["pilot_batch_l"] / 1000.0, {s: _price(a, "aroma/dry hops (IPA-type)", s) for s in SCEN}))
        rows.append(("mango puree", b["mango_puree"]["kg_per_100_l"] * n, {s: master["i-mango-puree"]["price"][s] for s in SCEN}))
    return rows


def batch_cost(beer_id, scen="base", a=None):
    a = a or assumptions()
    ing = sum(kg * p[scen] for _, kg, p in batch_ingredients(beer_id, a))
    over = sum(v[SCEN.index(scen)] for v in a["overheads_usd_per_batch"].values())
    labor = a["labor"]["brewer_hours_per_batch"] * a["labor"]["loaded_usd_per_hour"]
    return {"ingredients": ing, "overheads": over, "labor": labor, "total_ex_labor": ing + over, "total": ing + over + labor}


def economics(beer_id, size, scen="base", cfg=None, a=None):
    cfg, a = cfg or pricing.load_config(), a or assumptions()
    bc = batch_cost(beer_id, scen, a)
    packaged_l = a["batch"]["pilot_batch_l"] * a["batch"]["packaged_fraction"]
    ml = serving_ml(cfg, size)
    litres_charged = ml / 1000.0 / (1 - a["batch"]["service_waste_pct"] / 100.0)
    price = cfg["prices_usd"]["beer_glass" if size == "glass" else "beer_pitcher"]
    cost_ex, cost_all = bc["total_ex_labor"] / packaged_l * litres_charged, bc["total"] / packaged_l * litres_charged
    return {"beer": beer_id, "size": size, "scenario": scen, "volume_ml": ml, "price": price, "cost_ex_labor": cost_ex, "cost_with_brew_labor": cost_all,
            "margin_ex_labor_pct": (price - cost_ex) / price, "margin_with_brew_labor_pct": (price - cost_all) / price, "cost_per_packaged_litre_with_labor": bc["total"] / packaged_l,
            "price_per_litre": price / (ml / 1000.0), "status": "PRELIMINARY PLANNING ESTIMATE - NOT A VERIFIED PRODUCTION COST"}


def pitcher_vs_glass(cfg=None):
    """Pitcher (60 oz) vs buying the same volume in glasses (16 oz): the price per litre and the implied volume discount."""
    cfg = cfg or pricing.load_config()
    g, p = cfg["prices_usd"]["beer_glass"], cfg["prices_usd"]["beer_pitcher"]
    glasses = serving_ml(cfg, "pitcher") / serving_ml(cfg, "glass")
    return {"glasses_per_pitcher": glasses, "glass_equivalent_price": glasses * g, "pitcher_price": p, "discount_pct": 1 - p / (glasses * g)}


def all_rows(cfg=None):
    cfg = cfg or pricing.load_config()
    return [economics(b["id"], s, sc, cfg) for b in cfg["beers"] for s in ("glass", "pitcher") for sc in SCEN]
