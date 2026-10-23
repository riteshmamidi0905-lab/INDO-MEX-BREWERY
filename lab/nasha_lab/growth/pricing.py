"""Pricing engine (capability 5): pure functions over integer-cent inputs, plus an adapter that reads NASHA's existing recipe-costing (`recipes/pricing.py`).
Everything that depends on customer behaviour (price elasticity, bundle uptake) is an ASSUMPTION supplied by the caller and labelled as such in every result; no willingness-to-pay was measured.
Money is integer cents; margins are fractions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    name: str
    price_cents: int
    variable_cost_cents: float          # food + consumables (+ direct labour when the caller wants contribution margin)


def gross_margin(price, cost):
    return (price - cost) / price if price else 0.0


def margin_table(price_cents, cost_cents):
    return dict(price_cents=price_cents, cost_cents=cost_cents, unit_profit_cents=price_cents - cost_cents, margin=gross_margin(price_cents, cost_cents))


def discount_analysis(price_cents, cost_cents, discount_pct):
    """Effect of a percentage discount: new margin and the volume uplift needed to keep TOTAL gross profit unchanged. Returns uplift=None when the discounted price is at or below cost (no uplift can recover it)."""
    p1 = price_cents * (1 - discount_pct / 100.0)
    unit0, unit1 = price_cents - cost_cents, p1 - cost_cents
    return dict(discounted_price_cents=p1, margin_before=gross_margin(price_cents, cost_cents), margin_after=gross_margin(p1, cost_cents) if p1 > 0 else None,
                breakeven_volume_uplift=None if unit1 <= 0 else unit0 / unit1 - 1.0, assumption="uplift is the volume increase needed to hold gross profit; whether it occurs is NOT estimated")


def bundle(items, bundle_discount_pct):
    list_price = sum(i.price_cents for i in items)
    price = list_price * (1 - bundle_discount_pct / 100.0)
    cost = sum(i.variable_cost_cents for i in items)
    return dict(list_price_cents=list_price, bundle_price_cents=price, cost_cents=cost, margin=gross_margin(price, cost), margin_at_list=gross_margin(list_price, cost), saving_cents=list_price - price)


def inflation(price_cents, cost_cents, shocks=(0.0, 0.05, 0.10, 0.20, 0.30)):
    return [dict(shock=s, cost_cents=cost_cents * (1 + s), margin=gross_margin(price_cents, cost_cents * (1 + s))) for s in shocks]


def breakeven_units(fixed_costs_cents, price_cents, variable_cost_cents):
    unit = price_cents - variable_cost_cents
    return None if unit <= 0 else fixed_costs_cents / unit


def sensitivity(base_price_cents, cost_cents, base_units, elasticity, prices):
    """Constant-elasticity demand q = q0 * (p/p0)^e. The ELASTICITY IS AN ASSUMPTION, not an estimate; results are a what-if grid, not a forecast."""
    out = []
    for p in prices:
        q = base_units * (p / base_price_cents) ** elasticity
        out.append(dict(price_cents=p, units=q, revenue_cents=p * q, gross_profit_cents=(p - cost_cents) * q, margin=gross_margin(p, cost_cents)))
    return dict(assumption=f"elasticity {elasticity} is an assumed value, not measured", rows=out, best_price_cents=max(out, key=lambda r: r["gross_profit_cents"])["price_cents"])


def revenue_scenarios(price_cents, cost_cents, base_units, unit_growth=(-0.10, 0.0, 0.10)):
    return [dict(unit_growth=g, units=base_units * (1 + g), revenue_cents=price_cents * base_units * (1 + g), gross_profit_cents=(price_cents - cost_cents) * base_units * (1 + g)) for g in unit_growth]


def nasha_items(cfg=None, scenario="base"):
    """NASHA's concept dishes from the existing economics module (planning-assumption costs, concept prices). Returns {recipe id: dict(price_cents, food_cost_cents, contribution_cost_cents)}."""
    from ..recipes import pricing as P
    out = {}
    for e in P.menu_economics(cfg, scenario):
        out[e["id"]] = dict(name=e["name"], price_cents=round(e["price"] * 100), cost_cents=(e["food_cost"] + e["consumables"]) * 100, contribution_cost_cents=(e["food_cost"] + e["consumables"] + e["direct_labor"]) * 100)
    return out
