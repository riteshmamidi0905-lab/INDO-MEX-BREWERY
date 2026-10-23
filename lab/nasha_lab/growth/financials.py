"""Financial planning for a business-launch project: pure, deterministic functions over STORED inputs (products, current prices, unit costs, founder/synthetic assumptions). Same inputs -> same results (the inputs
are canonicalised and hashed; a saved scenario can be recomputed and compared). Every output is a SIMULATED PROJECTION built on stated assumptions, never actual business performance. Money is integer cents unless a
name says otherwise; margins are fractions. Customer behaviour (order volume, price elasticity, product mix) is ASSUMED, not measured. Builds on pricing.py (margin, break-even, discount, inflation helpers)."""
import hashlib
import json
import math

from . import pricing as GP

WEEKS_PER_MONTH = 52 / 12
DEFAULT_ASSUMPTIONS = {   # used only when a project has not stored its own value; each is reported back as 'defaulted' so it cannot pass as a founder input
    "weekly_orders": 0, "items_per_order": 1.0, "avg_discount_pct": 0.0, "variable_overhead_pct": 0.0, "cost_inflation_pct": 0.0, "price_elasticity": -1.2, "startup_capex_cents": 0,
    "rent_monthly_cents": 0, "labor_monthly_cents": 0, "utilities_monthly_cents": 0, "marketing_monthly_cents": 0, "insurance_monthly_cents": 0, "other_fixed_monthly_cents": 0,
    "capex_buildout_cents": 0, "capex_equipment_cents": 0, "capex_furniture_cents": 0, "capex_technology_cents": 0, "capex_other_cents": 0,
    "preopen_licences_permits_cents": 0, "preopen_deposits_cents": 0, "preopen_professional_fees_cents": 0, "preopen_training_cents": 0, "preopen_launch_marketing_cents": 0, "preopen_other_cents": 0,
    "working_capital_months": 0, "opening_inventory_weeks": 0, "contingency_pct": 0}
FIXED_KEYS = ("rent_monthly_cents", "labor_monthly_cents", "utilities_monthly_cents", "marketing_monthly_cents", "insurance_monthly_cents", "other_fixed_monthly_cents")
CAPEX_KEYS = {"startup_capex_cents": "Capital expenditure (lump sum)", "capex_buildout_cents": "Build-out and construction", "capex_equipment_cents": "Kitchen, brewing and service equipment", "capex_furniture_cents": "Furniture and fixtures",
              "capex_technology_cents": "Technology and point of sale", "capex_other_cents": "Other capital items"}
PREOPEN_KEYS = {"preopen_licences_permits_cents": "Licences and permits", "preopen_deposits_cents": "Deposits", "preopen_professional_fees_cents": "Professional fees", "preopen_training_cents": "Pre-opening training and payroll",
                "preopen_launch_marketing_cents": "Launch marketing", "preopen_other_cents": "Other pre-opening costs"}
PRICE_SHOCKS = (-0.10, -0.05, 0.0, 0.05, 0.10)
COST_SHOCKS = (0.0, 0.05, 0.10, 0.20, 0.30)


class FinancialInputError(ValueError):
    """Inputs that cannot produce a defensible number (non-finite, negative where a cost must not be, out of range). Raised instead of returning a plausible-looking wrong answer."""


def validate(inputs):
    a = inputs["assumptions"]
    for k, v in a.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise FinancialInputError(f"assumption {k} must be a finite number")
        if k != "price_elasticity" and k != "cost_inflation_pct" and v < 0:
            raise FinancialInputError(f"assumption {k} cannot be negative")
    if not 0 <= a["contingency_pct"] <= 100 or not 0 <= a["avg_discount_pct"] <= 100 or not 0 <= a["variable_overhead_pct"] <= 100:
        raise FinancialInputError("percentages must be between 0 and 100")
    if a["price_elasticity"] > 0:
        raise FinancialInputError("price elasticity must not be positive")
    for k in ("price_change_pct", "cost_change_pct"):
        if not math.isfinite(inputs[k]) or inputs[k] <= -1:
            raise FinancialInputError(f"{k} must be finite and greater than -100%")
    for p in inputs["products"]:
        if p["price_cents"] <= 0 or p["unit_cost_cents"] < 0 or p["mix"] <= 0 or not all(math.isfinite(p[x]) for x in ("price_cents", "unit_cost_cents", "mix")):
            raise FinancialInputError(f"product {p['name']}: price must be positive, cost and mix non-negative and finite")
    if inputs["budget_cents"] < 0:
        raise FinancialInputError("budget cannot be negative")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def inputs_hash(inputs):
    return hashlib.sha256(canonical(inputs).encode()).hexdigest()


def build_inputs(products, assumptions, overrides=None, budget_cents=0, labels=None):
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
    out = {"products": prods, "assumptions": a, "defaulted_assumptions": defaulted, "price_change_pct": price_change, "cost_change_pct": cost_change, "budget_cents": int(budget_cents)}
    if labels:
        out["labels"] = labels                           # industry wording for the start-up categories (display only; never changes a number)
    return out


def _mix(prods):
    tot = sum(p["mix"] for p in prods)
    return [p["mix"] / tot for p in prods]


def compute(inputs):
    """Unit economics, monthly P&L projection, break-even, payback and runway for one set of inputs."""
    validate(inputs)
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
    capex = sum(a[k] for k in CAPEX_KEYS)
    available = inputs["budget_cents"] - capex
    payback = capex / operating if operating > 0 and capex else (0.0 if not capex else None)
    runway = None if operating >= 0 else (available / -operating if available > 0 else 0.0)
    startup = startup_requirement(a, inputs["budget_cents"], variable, fixed, inputs.get("labels"))
    return dict(
        startup=startup, formulas=formulas(a, lines, units, revenue, variable, contribution, fixed, operating, be_units, startup),
        kind="simulated", disclaimer="Simulated projection from stated assumptions; not actual business performance. Demand, mix and elasticity are assumed, not measured.",
        units_per_month=round(units, 2), revenue_cents=round(revenue), variable_cost_cents=round(variable), gross_profit_cents=round(gross_profit), gross_margin=round(gross_profit / revenue, 4) if revenue else None,
        contribution_cents=round(contribution), contribution_margin=round(contribution / revenue, 4) if revenue else None, fixed_costs_monthly_cents=round(fixed), operating_profit_monthly_cents=round(operating),
        blended_contribution_per_unit_cents=round(blended_contrib, 2), breakeven_units_per_month=None if be_units is None else round(be_units, 1),
        breakeven_orders_per_week=None if be_units is None or not a["items_per_order"] else round(be_units / WEEKS_PER_MONTH / a["items_per_order"], 1),
        breakeven_vs_plan=None if not be_units or not units else round(units / be_units, 3), startup_capex_cents=capex, budget_cents=inputs["budget_cents"], budget_after_capex_cents=available,
        payback_months=None if payback is None else round(payback, 1), runway_months_if_loss_making=None if runway is None else round(runway, 1), lines=lines)


def startup_requirement(a, budget_cents, variable_monthly, fixed_monthly, labels=None):
    """What it takes to open: capital items + pre-opening costs + working capital (months of fixed costs and weeks of opening inventory at the modelled cost of goods) + a contingency percentage of that subtotal,
    compared with the stated budget. Every line is a stored assumption; nothing is estimated here."""
    cl, pl = ((labels or {}).get("capex") or CAPEX_KEYS), ((labels or {}).get("preopen") or PREOPEN_KEYS)
    capex = {k: a[k] for k in CAPEX_KEYS}
    preopen = {k: a[k] for k in PREOPEN_KEYS}
    wc_fixed = a["working_capital_months"] * fixed_monthly
    wc_inventory = a["opening_inventory_weeks"] * variable_monthly / WEEKS_PER_MONTH
    capex_total, preopen_total = sum(capex.values()), sum(preopen.values())
    subtotal = capex_total + preopen_total + wc_fixed + wc_inventory
    contingency = subtotal * a["contingency_pct"] / 100.0
    total = subtotal + contingency
    return dict(capex={cl.get(k, CAPEX_KEYS[k]): round(v) for k, v in capex.items() if v}, capex_total_cents=round(capex_total), preopening={pl.get(k, PREOPEN_KEYS[k]): round(v) for k, v in preopen.items() if v}, preopening_total_cents=round(preopen_total),
                working_capital=dict(fixed_cost_months=a["working_capital_months"], fixed_cost_cents=round(wc_fixed), opening_inventory_weeks=a["opening_inventory_weeks"], opening_inventory_cents=round(wc_inventory), total_cents=round(wc_fixed + wc_inventory)),
                subtotal_cents=round(subtotal), contingency_pct=a["contingency_pct"], contingency_cents=round(contingency), total_requirement_cents=round(total), budget_cents=budget_cents,
                headroom_cents=round(budget_cents - total), funding_gap_cents=round(max(0.0, total - budget_cents)), budget_covers_requirement=budget_cents >= total)


def _usd(c):
    return ("-" if c < 0 else "") + "$" + f"{abs(c) / 100:,.2f}"


def formulas(a, lines, units, revenue, variable, contribution, fixed, operating, be_units, st):
    """The arithmetic behind the headline numbers, with the stored values substituted, so a reader can check each result by hand."""
    f = [dict(name="Monthly revenue", formula="sum over products of (units per month x price after discount)", worked=f"{units:,.1f} units per month in total -> {_usd(revenue)}", result_cents=round(revenue)),
         dict(name="Monthly variable cost", formula="sum over products of units x (unit cost x (1 + inflation) x (1 + cost change) + payment and platform fee)", worked=_usd(variable), result_cents=round(variable)),
         dict(name="Contribution", formula="revenue - variable cost", worked=f"{_usd(revenue)} - {_usd(variable)} = {_usd(contribution)}", result_cents=round(contribution)),
         dict(name="Operating profit per month", formula="contribution - fixed costs", worked=f"{_usd(contribution)} - {_usd(fixed)} = {_usd(operating)}", result_cents=round(operating)),
         dict(name="Break-even units per month", formula="fixed costs / contribution per unit", worked="not reachable: contribution per unit is not positive" if be_units is None else f"{_usd(fixed)} / {_usd(contribution / units if units else 0)} = {be_units:,.1f}", value=None if be_units is None else round(be_units, 1)),
         dict(name="Capital expenditure", formula="sum of the capital items", worked=_usd(st["capex_total_cents"]), result_cents=st["capex_total_cents"]),
         dict(name="Pre-opening costs", formula="sum of the pre-opening items", worked=_usd(st["preopening_total_cents"]), result_cents=st["preopening_total_cents"]),
         dict(name="Working capital", formula="months of fixed costs x monthly fixed costs + weeks of opening inventory x weekly variable cost", worked=f"{a['working_capital_months']} x {_usd(fixed)} + {a['opening_inventory_weeks']} weeks of inventory = {_usd(st['working_capital']['total_cents'])}", result_cents=st["working_capital"]["total_cents"]),
         dict(name="Contingency", formula="contingency % x (capital + pre-opening + working capital)", worked=f"{a['contingency_pct']}% x {_usd(st['subtotal_cents'])} = {_usd(st['contingency_cents'])}", result_cents=st["contingency_cents"]),
         dict(name="Total start-up requirement", formula="capital + pre-opening + working capital + contingency", worked=_usd(st["total_requirement_cents"]), result_cents=st["total_requirement_cents"]),
         dict(name="Budget headroom", formula="budget - total start-up requirement", worked=f"{_usd(st['budget_cents'])} - {_usd(st['total_requirement_cents'])} = {_usd(st['headroom_cents'])}", result_cents=st["headroom_cents"])]
    return f


LIMITATIONS = ["Order volume, product mix, price elasticity and every cost below are assumptions, not measurements; the projection is simulated.", "Steady-state month: no ramp-up, seasonality, tax, financing cost or depreciation is modelled.",
               "Opening inventory uses the modelled cost of goods, not a supplier quote; supplier prices are compared separately and are synthetic unless labelled otherwise.", "Break-even units do not depend on the elasticity assumption; the projected units do."]


def breakeven_grid(inputs):
    """Break-even orders per week for every combination of price change and ingredient-cost change: how far fixed costs are from being covered when prices or costs move. None where contribution is not positive."""
    rows = []
    for cs in COST_SHOCKS:
        row = dict(cost_change_pct=round(100 * cs, 1), cells=[])
        for ps in PRICE_SHOCKS:
            r = compute({**inputs, "price_change_pct": ps, "cost_change_pct": cs})
            row["cells"].append(dict(price_change_pct=round(100 * ps, 1), breakeven_orders_per_week=r["breakeven_orders_per_week"], operating_profit_monthly_cents=r["operating_profit_monthly_cents"]))
        rows.append(row)
    return dict(rows=rows, price_changes_pct=[round(100 * p, 1) for p in PRICE_SHOCKS], note="Break-even orders per week at the assumed items per order and mix. Independent of the elasticity assumption.")


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
    return dict(results=compute(inputs), sensitivity=sensitivity(inputs), breakeven_grid=breakeven_grid(inputs), limitations=LIMITATIONS, inputs_hash=inputs_hash(inputs))
