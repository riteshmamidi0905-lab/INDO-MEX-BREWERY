"""Independent check of the financial model: cases whose expected numbers were worked out BY HAND (written here as literals, not produced by the code), plus mutants that each remove or distort one piece of the arithmetic.
Money is integer cents. The cases are small on purpose: each can be verified with a calculator from the stated inputs. Pure; shared by the tests and the evidence exporter."""
import contextlib

from . import financials as F

P = [{"name": "A", "price_cents": 1000, "unit_cost_cents": 300}]
BASE = {"weekly_orders": 100, "items_per_order": 1, "rent_monthly_cents": 100_000}

# name, assumptions, overrides, budget, expected {field: value}. Working for each:
CASES = [
    # 100 orders x 52/12 = 433.333 units; revenue 433.333 x $10 = 433,333c; variable 433.333 x $3 = 130,000c; contribution 303,333c; fixed 100,000c; operating 203,333c; break-even 100,000 / 700 = 142.857 units.
    # capex 500,000; pre-opening 20,000; working capital 2 x 100,000 + 1 week of inventory (130,000 x 12/52 = 30,000) = 230,000; subtotal 750,000; contingency 10% = 75,000; total 825,000; headroom 2,000,000 - 825,000 = 1,175,000.
    ("base with startup costs", {**BASE, "capex_buildout_cents": 500_000, "preopen_licences_permits_cents": 20_000, "working_capital_months": 2, "opening_inventory_weeks": 1, "contingency_pct": 10}, {}, 2_000_000,
     dict(revenue_cents=433_333, variable_cost_cents=130_000, contribution_cents=303_333, operating_profit_monthly_cents=203_333, breakeven_units_per_month=142.9,
          startup=dict(capex_total_cents=500_000, preopening_total_cents=20_000, subtotal_cents=750_000, contingency_cents=75_000, total_requirement_cents=825_000, headroom_cents=1_175_000, funding_gap_cents=0))),
    # fee 3% of price = 30c; contribution per unit 1000-300-30 = 670c; variable = 433.333 x 330 = 143,000c; fixed 100,000 + 50,000 = 150,000c; operating = 433,333 - 143,000 - 150,000 = 140,333c; break-even 150,000/670 = 223.88 units.
    # capex 400,000; working capital 3 x 150,000 = 450,000; subtotal 850,000; contingency 20% = 170,000; total 1,020,000; budget 500,000 -> gap 520,000.
    ("fees, labour and a funding gap", {**BASE, "variable_overhead_pct": 3, "labor_monthly_cents": 50_000, "capex_equipment_cents": 400_000, "working_capital_months": 3, "contingency_pct": 20}, {}, 500_000,
     dict(revenue_cents=433_333, variable_cost_cents=143_000, operating_profit_monthly_cents=140_333, breakeven_units_per_month=223.9,
          startup=dict(subtotal_cents=850_000, contingency_cents=170_000, total_requirement_cents=1_020_000, headroom_cents=-520_000, funding_gap_cents=520_000))),
    # price +10%, elasticity -1: units = 433.333 x (1 + (-1)(0.10)) = 390; price 1,100c; revenue 429,000c; variable 390 x 300 = 117,000c; contribution 312,000c; operating 212,000c; break-even 100,000 / 800 = 125 units.
    ("a price rise with elasticity -1", {**BASE, "price_elasticity": -1}, {"price_change_pct": 0.10}, 0,
     dict(units_per_month=390.0, revenue_cents=429_000, variable_cost_cents=117_000, contribution_cents=312_000, operating_profit_monthly_cents=212_000, breakeven_units_per_month=125.0)),
    # 10% discount: price 900c; revenue 433.333 x 900 = 390,000c; variable 130,000c; contribution 260,000c; operating 160,000c; break-even 100,000 / 600 = 166.7 units.
    ("a 10 percent discount", {**BASE, "avg_discount_pct": 10}, {}, 0, dict(revenue_cents=390_000, contribution_cents=260_000, operating_profit_monthly_cents=160_000, breakeven_units_per_month=166.7)),
    # cost +30%: unit cost 390c; variable 433.333 x 390 = 169,000c; contribution 264,333c; operating 164,333c; gross margin (1000-390)/1000 = 0.61.
    ("ingredient costs up 30 percent", {**BASE}, {"cost_change_pct": 0.30}, 0, dict(variable_cost_cents=169_000, contribution_cents=264_333, operating_profit_monthly_cents=164_333, gross_margin=0.61))]


def _get(res, path):
    return res[path]


def _check(res, exp):
    bad = []
    for k, v in exp.items():
        if k == "startup":
            bad += [f"startup.{kk}: {res['startup'][kk]} != {vv}" for kk, vv in v.items() if res["startup"][kk] != vv]
        elif k == "gross_margin":
            if abs(res[k] - v) > 1e-4:
                bad.append(f"{k}: {res[k]} != {v}")
        elif isinstance(v, float) and k in ("breakeven_units_per_month", "units_per_month"):
            if res[k] is None or abs(res[k] - v) > 0.051:
                bad.append(f"{k}: {res[k]} != {v}")
        elif abs(res[k] - v) > 1:             # whole cents: one cent of rounding is allowed
            bad.append(f"{k}: {res[k]} != {v}")
    return bad


def run_cases():
    out = []
    for name, assumptions, ov, budget, exp in CASES:
        res = F.compute(F.build_inputs(P, assumptions, ov, budget))
        bad = _check(res, exp)
        out.append(dict(name=name, expected_fields=len(exp) + (len(exp["startup"]) - 1 if "startup" in exp else 0), mismatches=bad, ok=not bad))
    return out


def invariants():
    """Relations that must hold for any inputs: the startup total adds up, the headroom is budget minus requirement, and identical inputs give identical results and hashes."""
    res = F.run(F.build_inputs(P, CASES[0][1], {}, 2_000_000))
    st = res["results"]["startup"]
    r2 = F.run(F.build_inputs(P, dict(reversed(list(CASES[0][1].items()))), {}, 2_000_000))
    return {"total = subtotal + contingency": st["total_requirement_cents"] == st["subtotal_cents"] + st["contingency_cents"], "headroom = budget - total": st["headroom_cents"] == st["budget_cents"] - st["total_requirement_cents"],
            "subtotal = capital + pre-opening + working capital": st["subtotal_cents"] == st["capex_total_cents"] + st["preopening_total_cents"] + st["working_capital"]["total_cents"],
            "same inputs give the same results and hash": res == r2 and res["inputs_hash"] == r2["inputs_hash"]}


# ---------------------------------------------------------------------------------------------- mutants
@contextlib.contextmanager
def _patched(**kv):
    old = {k: getattr(F, k) for k in kv}
    try:
        for k, v in kv.items():
            setattr(F, k, v)
        yield
    finally:
        for k, v in old.items():
            setattr(F, k, v)


def _startup_variant(kind):
    real = F.startup_requirement
    def f(a, budget, variable_monthly, fixed_monthly):
        if kind == "contingency_on_capex_only":
            r = real(dict(a, contingency_pct=0), budget, variable_monthly, fixed_monthly)
            c = round(r["capex_total_cents"] * a["contingency_pct"] / 100.0)
            return dict(r, contingency_cents=c, total_requirement_cents=r["subtotal_cents"] + c, headroom_cents=round(budget - r["subtotal_cents"] - c), funding_gap_cents=round(max(0.0, r["subtotal_cents"] + c - budget)))
        if kind == "working_capital_ignores_months":
            return real(dict(a, working_capital_months=0), budget, variable_monthly, fixed_monthly)
        if kind == "inventory_uses_month_not_week":
            return real(dict(a, opening_inventory_weeks=a["opening_inventory_weeks"] * F.WEEKS_PER_MONTH), budget, variable_monthly, fixed_monthly)
        if kind == "headroom_sign_flipped":
            r = real(a, budget, variable_monthly, fixed_monthly)
            return dict(r, headroom_cents=-r["headroom_cents"], funding_gap_cents=round(max(0.0, budget - r["total_requirement_cents"])))
        if kind == "preopening_dropped":
            return real({**a, **{k: 0 for k in F.PREOPEN_KEYS}}, budget, variable_monthly, fixed_monthly)
        return real(a, budget, variable_monthly, fixed_monthly)
    return f


def _compute_variant(kind):
    real = F.compute
    def f(inputs):
        a = dict(inputs["assumptions"])
        if kind == "elasticity_ignored":
            a["price_elasticity"] = 0.0
        if kind == "discount_ignored":
            a["avg_discount_pct"] = 0.0
        if kind == "fixed_costs_ignored":
            for k in F.FIXED_KEYS:
                a[k] = 0
        if kind == "fees_ignored":
            a["variable_overhead_pct"] = 0.0
        return real({**inputs, "assumptions": a})
    return f


MUTANTS = {
    "contingency_on_capex_only": ("contingency applies to the whole start-up subtotal", lambda: _patched(startup_requirement=_startup_variant("contingency_on_capex_only"))),
    "working_capital_ignores_months": ("working capital holds months of fixed costs", lambda: _patched(startup_requirement=_startup_variant("working_capital_ignores_months"))),
    "inventory_uses_month_not_week": ("opening inventory is weeks of cost of goods", lambda: _patched(startup_requirement=_startup_variant("inventory_uses_month_not_week"))),
    "headroom_sign_flipped": ("headroom is budget minus requirement", lambda: _patched(startup_requirement=_startup_variant("headroom_sign_flipped"))),
    "preopening_dropped": ("pre-opening costs are part of the requirement", lambda: _patched(startup_requirement=_startup_variant("preopening_dropped"))),
    "elasticity_ignored": ("a price change moves demand by the stated elasticity", lambda: _patched(compute=_compute_variant("elasticity_ignored"))),
    "discount_ignored": ("the average discount lowers the price received", lambda: _patched(compute=_compute_variant("discount_ignored"))),
    "fixed_costs_ignored": ("fixed costs reduce operating profit and set break-even", lambda: _patched(compute=_compute_variant("fixed_costs_ignored"))),
    "fees_ignored": ("payment and platform fees are variable costs", lambda: _patched(compute=_compute_variant("fees_ignored")))}


def run_mutants():
    base_bad = sum(not c["ok"] for c in run_cases()) + sum(not v for v in invariants().values())
    out = []
    for name, (removes, patch) in MUTANTS.items():
        with patch():
            bad = sum(not c["ok"] for c in run_cases()) + sum(not v for v in invariants().values())
        out.append(dict(name=name, removes=removes, failures_on_mutant=bad, killed=bad > base_bad))
    return dict(baseline_failures=base_bad, mutants=out)
