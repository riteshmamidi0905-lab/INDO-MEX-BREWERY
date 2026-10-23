"""Financial planning for a business-launch project: pure, deterministic functions over STORED inputs (products, current prices, unit costs, founder/synthetic assumptions). Same inputs -> same results (the inputs
are canonicalised and hashed; a saved scenario can be recomputed and compared). Every output is a SIMULATED PROJECTION built on stated assumptions, never actual business performance. Money is integer cents unless a
name says otherwise; margins are fractions. Customer behaviour (order volume, price elasticity, product mix) is ASSUMED, not measured. Builds on pricing.py (margin, break-even, discount, inflation helpers)."""
import hashlib
import json

from . import pricing as GP

WEEKS_PER_MONTH = 52 / 12
DEFAULT_ASSUMPTIONS = {   # used only when a project has not stored its own value; each is reported back as 'defaulted' so it cannot pass as a founder input
    "weekly_orders": 0, "items_per_order": 1.0, "avg_discount_pct": 0.0, "variable_overhead_pct": 0.0, "cost_inflation_pct": 0.0, "price_elasticity": -1.2, "startup_capex_cents": 0,
    "rent_monthly_cents": 0, "labor_monthly_cents": 0, "utilities_monthly_cents": 0, "marketing_monthly_cents": 0, "insurance_monthly_cents": 0, "other_fixed_monthly_cents": 0}
FIXED_KEYS = ("rent_monthly_cents", "labor_monthly_cents", "utilities_monthly_cents", "marketing_monthly_cents", "insurance_monthly_cents", "other_fixed_monthly_cents")
PRICE_SHOCKS = (-0.10, -0.05, 0.0, 0.05, 0.10)
COST_SHOCKS = (0.0, 0.05, 0.10, 0.20, 0.30)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def inputs_hash(inputs):
    return hashlib.sha256(canonical(inputs).encode()).hexdigest()


def build_inputs(products, assumptions, overrides=None, budget_cents=0):
    """products: [{name, price_cents, unit_cost_cents, mix (optional weight)}] from the stored products and current prices; assumptions: {key: value} from stored project assumptions;
    overrides: {key: value} for a what-if (price_change_pct, cost_change_pct and any assumption key). Returns the full, explicit input document that compute() consumes."""
    a = dict(DEFAULT_ASSUMPTIONS)
    defaulted = sorted(k for k in a if k not in assumptions)
    a.update({k: v for k, v in assumptions.items() if k in a})
    ov = dict(overrides or {})
    price_change, cost_change = float(ov.pop("price_change_pct", 0.0)), float(ov.pop("cost_change_pct", 0.0))
    for k, v in ov.items():
        if k not in a:
            raise ValueError(f"unknown override {k}")
        a[k] = v
    prods = sorted(({"name": p["name"], "price_cents": int(p["price_cents"]), "unit_cost_cents": float(p["unit_cost_cents"]), "mix": float(p.get("mix") or 1.0)} for p in products if p.get("price_cents") and p.get("unit_cost_cents") is not None),
                   key=lambda p: p["name"])
    if not prods:
        raise ValueError("a financial scenario needs at least one product with a current price and a unit cost")
    return {"products": prods, "assumptions": a, "defaulted_assumptions": defaulted, "price_change_pct": price_change, "cost_change_pct": cost_change, "budget_cents": int(budget_cents)}


def _mix(prods):
    tot = sum(p["mix"] for p in prods)
    return [p["mix"] / tot for p in prods]


def compute(inputs):
    """Unit economics, monthly P&L projection, break-even, payback and runway for one set of inputs."""
    a, prods = inputs["assumptions"], inputs["products"]
    w = _mix(prods)
    pc, cc = inputs["price_change_pct"], inputs["cost_change_pct"]
    infl = a["cost_inflation_pct"] / 100.0
    elasticity = float(a["price_elasticity"])
    base_units = a["weekly_orders"] * a["items_per_order"] * WEEKS_PER_MONTH
    units = max(0.0, base_units * (1 + elasticity * pc))                         # ASSUMED demand response to a price change
    disc = a["avg_discount_pct"] / 100.0
    lines, revenue, variable, gross_profit = [], 0.0, 0.0, 0.0
    for p, share in zip(prods, w):
        price = p["price_cents"] * (1 + pc) * (1 - disc)
        cost = p["unit_cost_cents"] * (1 + infl) * (1 + cc)
        fee = price * a["variable_overhead_pct"] / 100.0
        n = units * share
        lines.append(dict(name=p["name"], price_cents=round(price, 2), unit_cost_cents=round(cost, 2), gross_margin=round(GP.gross_margin(price, cost), 4), contribution_per_unit_cents=round(price - cost - fee, 2),
                          contribution_margin=round((price - cost - fee) / price, 4) if price else 0.0, mix=round(share, 4), units_per_month=round(n, 2)))
        revenue += n * price; variable += n * (cost + fee); gross_profit += n * (price - cost)
    contribution = revenue - variable
    fixed = sum(a[k] for k in FIXED_KEYS)
    operating = contribution - fixed
    blended_contrib = contribution / units if units else 0.0
    be_units = fixed / blended_contrib if blended_contrib > 0 else None
    capex = a["startup_capex_cents"]
    available = inputs["budget_cents"] - capex
    payback = capex / operating if operating > 0 and capex else (0.0 if not capex else None)
    runway = None if operating >= 0 else (available / -operating if available > 0 else 0.0)
    return dict(
        kind="simulated", disclaimer="Simulated projection from stated assumptions; not actual business performance. Demand, mix and elasticity are assumed, not measured.",
        units_per_month=round(units, 2), revenue_cents=round(revenue), variable_cost_cents=round(variable), gross_profit_cents=round(gross_profit), gross_margin=round(gross_profit / revenue, 4) if revenue else None,
        contribution_cents=round(contribution), contribution_margin=round(contribution / revenue, 4) if revenue else None, fixed_costs_monthly_cents=round(fixed), operating_profit_monthly_cents=round(operating),
        blended_contribution_per_unit_cents=round(blended_contrib, 2), breakeven_units_per_month=None if be_units is None else round(be_units, 1),
        breakeven_orders_per_week=None if be_units is None or not a["items_per_order"] else round(be_units / WEEKS_PER_MONTH / a["items_per_order"], 1),
        breakeven_vs_plan=None if be_units is None or not units else round(units / be_units, 3), startup_capex_cents=capex, budget_cents=inputs["budget_cents"], budget_after_capex_cents=available,
        payback_months=None if payback is None else round(payback, 1), runway_months_if_loss_making=None if runway is None else round(runway, 1), lines=lines)


def sensitivity(inputs):
    """Price sensitivity (with the stated elasticity) and cost-change effect, each recomputed through compute() so every cell is a full scenario."""
    price_rows = []
    for s in PRICE_SHOCKS:
        r = compute({**inputs, "price_change_pct": s})
        price_rows.append(dict(price_change_pct=round(100 * s, 1), units_per_month=r["units_per_month"], revenue_cents=r["revenue_cents"], operating_profit_monthly_cents=r["operating_profit_monthly_cents"], gross_margin=r["gross_margin"]))
    cost_rows = []
    for s in COST_SHOCKS:
        r = compute({**inputs, "cost_change_pct": s})
        cost_rows.append(dict(cost_change_pct=round(100 * s, 1), gross_margin=r["gross_margin"], contribution_margin=r["contribution_margin"], operating_profit_monthly_cents=r["operating_profit_monthly_cents"],
                              breakeven_units_per_month=r["breakeven_units_per_month"]))
    return dict(price=price_rows, cost=cost_rows, elasticity_assumed=inputs["assumptions"]["price_elasticity"])


def compare(named_inputs):
    """named_inputs: [(name, inputs)] -> side-by-side key results with the difference from the first (the base)."""
    rows = []
    for name, inp in named_inputs:
        r = compute(inp)
        rows.append(dict(name=name, **{k: r[k] for k in ("units_per_month", "revenue_cents", "gross_margin", "contribution_margin", "operating_profit_monthly_cents", "breakeven_units_per_month", "payback_months")}))
    base = rows[0]
    for r in rows:
        r["profit_vs_base_cents"] = r["operating_profit_monthly_cents"] - base["operating_profit_monthly_cents"]
    return rows


def run(inputs):
    """The stored form of a scenario: results plus sensitivity, with the hash of the exact inputs."""
    return dict(results=compute(inputs), sensitivity=sensitivity(inputs), inputs_hash=inputs_hash(inputs))
