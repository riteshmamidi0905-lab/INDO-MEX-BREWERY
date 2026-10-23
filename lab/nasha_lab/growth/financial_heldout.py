"""HELD-OUT financial cases: separate from the development cases in financial_eval. Each expected number was worked out by hand (the working is in the comments) BEFORE the code was run against it, and the cases use shapes the
development cases do not (two products with unequal mix, a membership-style price list, a funded start-up plan, a loss-making unfunded project). Run once; any later change to financials.py that moves them is visible here.
Money in whole cents (one cent of rounding allowed); decimals to 0.05. Small and author-worked: they test the arithmetic, not the realism of any plan."""
from . import financials as F

P = [{"name": "Membership", "price_cents": 7900, "unit_cost_cents": 1800, "mix": 2}, {"name": "Class pack", "price_cents": 14900, "unit_cost_cents": 2500, "mix": 1}]
BASE = {"weekly_orders": 60, "items_per_order": 1, "rent_monthly_cents": 300_000, "labor_monthly_cents": 500_000}
CASES = [
    # 60 x 52/12 = 260 units/month, shares 2/3 and 1/3: revenue 173.333 x 7,900 + 86.667 x 14,900 = 2,660,667c; variable 312,000 + 216,667 = 528,667c; contribution 2,132,000c; fixed 800,000c; operating 1,332,000c;
    # break-even 800,000 / (2,132,000/260 = 8,200) = 97.56 units = 22.5 orders a week; gross margin 2,132,000 / 2,660,667 = 0.8013
    ("two products, unequal mix", BASE, {}, 0, dict(units_per_month=260.0, revenue_cents=2_660_667, variable_cost_cents=528_667, contribution_cents=2_132_000, operating_profit_monthly_cents=1_332_000, breakeven_units_per_month=97.6, breakeven_orders_per_week=22.5, gross_margin=0.8013)),
    # +5% price with elasticity -0.5: units 260 x 0.975 = 253.5; prices x 1.05 x 0.9 (10% discount) = x 0.945, average price 9,670.5; revenue 2,451,472c; variable 253.5 x 2,033.33 = 515,450c; contribution 1,936,022c; operating 1,136,022c
    ("a price rise, a discount and elasticity", {**BASE, "price_elasticity": -0.5, "avg_discount_pct": 10}, {"price_change_pct": 0.05}, 0, dict(units_per_month=253.5, revenue_cents=2_451_472, variable_cost_cents=515_450, contribution_cents=1_936_022, operating_profit_monthly_cents=1_136_022)),
    # capital 2.8M + 3.2M + 0.8M + 0.6M = 7.4M; pre-opening 1.8M + 0.2M = 2.0M; working capital 2 x 800,000 + 2 weeks of cost of goods (528,667 x 12/52 = 122,000 a week) = 1,600,000 + 244,000 = 1,844,000;
    # subtotal 11,244,000; contingency 8% = 899,520; total 12,143,520; headroom 18,000,000 - 12,143,520 = 5,856,480; no gap
    ("a funded start-up plan", {**BASE, "capex_buildout_cents": 2_800_000, "capex_equipment_cents": 3_200_000, "capex_furniture_cents": 800_000, "capex_technology_cents": 600_000, "preopen_deposits_cents": 1_800_000, "preopen_licences_permits_cents": 200_000,
                                "working_capital_months": 2, "opening_inventory_weeks": 2, "contingency_pct": 8}, {}, 18_000_000,
     dict(startup=dict(capex_total_cents=7_400_000, preopening_total_cents=2_000_000, subtotal_cents=11_244_000, contingency_cents=899_520, total_requirement_cents=12_143_520, headroom_cents=5_856_480, funding_gap_cents=0))),
]
# one product, 10 orders a week: 43.33 units; revenue 342,333c; variable 78,000c; contribution 264,333c; fixed 800,000c; operating -535,667c; break-even 800,000 / 6,100 = 131.1 units = 30.3 orders a week; no capital so payback 0;
# loss-making with a 3,000,000c budget: runway 3,000,000 / 535,667 = 5.6 months
LOSS = ("a loss-making project with a small budget", {"weekly_orders": 10, "items_per_order": 1, "rent_monthly_cents": 800_000}, {}, 3_000_000,
        dict(units_per_month=43.3, revenue_cents=342_333, variable_cost_cents=78_000, contribution_cents=264_333, operating_profit_monthly_cents=-535_667, breakeven_units_per_month=131.1, breakeven_orders_per_week=30.3, runway_months_if_loss_making=5.6))


def _check(res, exp):
    bad = []
    for k, v in exp.items():
        if k == "startup":
            bad += [f"startup.{kk}: {res['startup'][kk]} != {vv}" for kk, vv in v.items() if abs(res["startup"][kk] - vv) > 1]
        elif k == "gross_margin":
            if abs(res[k] - v) > 1e-4:
                bad.append(f"{k}: {res[k]} != {v}")
        elif isinstance(v, float) and abs(v) < 1000 and k not in ("revenue_cents",):
            if res[k] is None or abs(res[k] - v) > 0.051:
                bad.append(f"{k}: {res[k]} != {v}")
        elif abs(res[k] - v) > 1:
            bad.append(f"{k}: {res[k]} != {v}")
    return bad


def run():
    out = []
    for name, a, ov, budget, exp in CASES + [LOSS]:
        prods = P if name != LOSS[0] else P[:1]
        res = F.compute(F.build_inputs(prods, a, ov, budget))
        bad = _check(res, exp)
        out.append(dict(name=name, fields=len(exp) + (len(exp["startup"]) - 1 if "startup" in exp else 0), mismatches=bad, ok=not bad))
    return out
