"""Financial model tests: hand-computed oracles, properties, reproducibility and 'results come from stored data'. All figures are SIMULATED projections on stated assumptions."""
import os
from datetime import date

import pytest

from nasha_lab.growth import financials as F

WEEK = 52 / 12


def one(price=2000, cost=500, **a):
    base = dict(weekly_orders=100, items_per_order=1.0, rent_monthly_cents=100_000, startup_capex_cents=1_000_000)
    base.update(a)
    return F.build_inputs([dict(name="Plate", price_cents=price, unit_cost_cents=cost)], base, budget_cents=5_000_000)


def test_unit_economics_and_break_even_match_a_hand_calculation():
    r = F.compute(one())
    units = 100 * WEEK                                       # 433.33 per month
    assert r["units_per_month"] == round(units, 2) and r["revenue_cents"] == round(units * 2000) and r["variable_cost_cents"] == round(units * 500)
    assert r["gross_margin"] == 0.75 and r["contribution_margin"] == 0.75
    assert r["operating_profit_monthly_cents"] == round(units * 1500 - 100_000)                   # 550,000
    assert r["breakeven_units_per_month"] == round(100_000 / 1500, 1) == 66.7
    assert r["breakeven_orders_per_week"] == round(66.667 / WEEK, 1)
    assert r["payback_months"] == round(1_000_000 / (units * 1500 - 100_000), 1) and r["budget_after_capex_cents"] == 4_000_000
    assert r["kind"] == "simulated" and "not actual business performance" in r["disclaimer"]


def test_discount_fees_inflation_and_mix_change_the_margins_as_arithmetic_says():
    inp = F.build_inputs([dict(name="A", price_cents=1000, unit_cost_cents=400, mix=3), dict(name="B", price_cents=2000, unit_cost_cents=1000, mix=1)],
                         dict(weekly_orders=60, items_per_order=1, avg_discount_pct=10, variable_overhead_pct=5, cost_inflation_pct=10))
    r = F.compute(inp); units = 60 * WEEK
    pa, ca = 1000 * 0.9, 400 * 1.1; pb, cb = 2000 * 0.9, 1000 * 1.1
    rev = units * (0.75 * pa + 0.25 * pb); var = units * (0.75 * (ca + pa * 0.05) + 0.25 * (cb + pb * 0.05))
    assert r["revenue_cents"] == round(rev) and r["variable_cost_cents"] == round(var) and r["contribution_cents"] == round(rev - var)
    la = {l["name"]: l for l in r["lines"]}
    assert la["A"]["gross_margin"] == round((pa - ca) / pa, 4) and la["A"]["contribution_margin"] == round((pa - ca - pa * 0.05) / pa, 4) and la["A"]["mix"] == 0.75


def test_price_sensitivity_uses_the_stated_elasticity_and_cost_shocks_lower_margin_monotonically():
    inp = one(price_elasticity=-1.5)
    s = F.sensitivity(inp)
    row = {r["price_change_pct"]: r for r in s["price"]}
    assert row[10.0]["units_per_month"] == round(100 * WEEK * (1 - 0.15), 2) and row[-10.0]["units_per_month"] == round(100 * WEEK * 1.15, 2) and s["elasticity_assumed"] == -1.5
    assert row[0.0]["revenue_cents"] == F.compute(inp)["revenue_cents"]
    margins = [r["gross_margin"] for r in s["cost"]]
    assert margins == sorted(margins, reverse=True) and s["cost"][0]["cost_change_pct"] == 0.0
    profits = [r["operating_profit_monthly_cents"] for r in s["cost"]]
    assert profits == sorted(profits, reverse=True)


def test_at_the_break_even_volume_operating_profit_is_zero_and_losses_report_runway():
    r0 = F.compute(one())
    be_orders = r0["breakeven_orders_per_week"]
    r = F.compute(one(weekly_orders=be_orders))
    assert abs(r["operating_profit_monthly_cents"]) < 0.01 * 100_000 + 200                       # rounding of the break-even figure to 0.1 orders
    loss = F.compute(one(weekly_orders=10, rent_monthly_cents=500_000))
    assert loss["operating_profit_monthly_cents"] < 0 and loss["payback_months"] is None and loss["runway_months_if_loss_making"] == round(4_000_000 / -loss["operating_profit_monthly_cents"], 1)
    broke = F.compute(F.build_inputs([dict(name="P", price_cents=1000, unit_cost_cents=900)], dict(weekly_orders=1, rent_monthly_cents=900_000, startup_capex_cents=6_000_000), budget_cents=5_000_000))
    assert broke["runway_months_if_loss_making"] == 0.0, "capex already exceeds the budget"


def test_scenario_comparison_reports_the_difference_from_the_base():
    base = one()
    rows = F.compare([("Base", base), ("Price +10%", {**base, "price_change_pct": 0.10}), ("Costs +30%", {**base, "cost_change_pct": 0.30})])
    assert rows[0]["profit_vs_base_cents"] == 0 and rows[1]["name"] == "Price +10%" and rows[2]["profit_vs_base_cents"] < 0
    assert rows[1]["profit_vs_base_cents"] == rows[1]["operating_profit_monthly_cents"] - rows[0]["operating_profit_monthly_cents"]


def test_results_are_reproducible_and_inputs_are_hashed_canonically():
    a, b = one(), one()
    assert F.run(a) == F.run(b) and F.inputs_hash(a) == F.inputs_hash(b)
    assert F.inputs_hash(one(weekly_orders=101)) != F.inputs_hash(a)
    shuffled = dict(a, products=list(reversed(a["products"])))
    assert F.inputs_hash(shuffled) != "" and F.compute(shuffled) == F.compute(a)


def test_defaults_are_reported_so_they_cannot_pass_as_founder_inputs_and_bad_inputs_are_refused():
    inp = F.build_inputs([dict(name="P", price_cents=1000, unit_cost_cents=300)], dict(weekly_orders=10))
    assert "price_elasticity" in inp["defaulted_assumptions"] and "weekly_orders" not in inp["defaulted_assumptions"]
    with pytest.raises(ValueError):
        F.build_inputs([dict(name="P", price_cents=1000, unit_cost_cents=300)], {}, overrides={"nonsense": 1})
    with pytest.raises(ValueError):
        F.build_inputs([dict(name="P", price_cents=None, unit_cost_cents=300)], {})


# ---------------------------------------------------------------- results come from STORED data
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
from nasha_lab.growth import launch_seed as LS, schema as S, seed as SD, service as SV
from nasha_lab.warehouse import pg_hardening as H


@pytest.fixture(scope="module")
def stored(tmp_path_factory):
    if os.environ.get("NASHA_PG_DSN"):
        dsn = os.environ["NASHA_PG_DSN"]; srv = None
    else:
        try:
            import pixeltable_pgserver as pg
            srv = pg.get_server(str(tmp_path_factory.mktemp("pgdata")), cleanup_mode="stop"); dsn = srv.get_uri()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute('DROP SCHEMA IF EXISTS "growth_fin" CASCADE'); c.execute('CREATE SCHEMA "growth_fin"')
    H.migrate(dsn, "growth_fin", specs=S.migrations("growth_fin"))
    SV.provision(dsn, "growth_fin", "tenant-nasha", "t", "hospitality", [("ada", "Ada", "OWNER"), ("ana", "Ana", "ANALYST"), ("vic", "Vic", "VIEWER")])
    s = SV.GrowthService(dsn, "growth_fin", "tenant-nasha", "ada"); SD.seed_nasha(s, None, with_accounts=False); ids = LS.seed_nasha_launch(s, today=date(2026, 10, 23))
    yield s, ids, dsn
    s.close()
    if srv: srv.cleanup()


def test_scenarios_are_computed_from_stored_products_prices_and_assumptions_and_a_saved_scenario_recomputes_identically(stored):
    s, ids, dsn = stored
    pid = ids["project"]
    prev = s.preview_scenario(pid)
    econ = s.product_economics()
    assert len(prev["inputs"]["products"]) == len(econ) == 15 and {p["name"] for p in prev["inputs"]["products"]} == {e["name"] for e in econ}
    ov = s.project_overview(pid)
    assert prev["inputs"]["assumptions"]["weekly_orders"] == next(a["value"] for a in ov["assumptions"] if a["key"] == "weekly_orders") and prev["inputs"]["defaulted_assumptions"] == []
    sid = s.save_scenario(pid, "Base case")
    saved = s.get_scenario(sid)
    again = F.run(saved["inputs"])
    assert again["results"] == saved["results"]["results"] and again["inputs_hash"] == saved["inputs_hash"] == F.inputs_hash(saved["inputs"]), "a saved scenario can be recomputed exactly from its stored inputs"
    assert saved["results"]["results"]["kind"] == "simulated"
    # change a STORED assumption: the result changes (nothing is hard-coded)
    s.set_assumption(pid, "weekly_orders", "Guest orders per week", 800, "orders", "founder", "founder revised")
    after = s.preview_scenario(pid)
    assert after["results"]["revenue_cents"] > prev["results"]["revenue_cents"] and after["inputs_hash"] != prev["inputs_hash"]
    s.set_assumption(pid, "weekly_orders", "Guest orders per week", 650, "orders", "synthetic_assumption", None)
    # change a STORED price: margins change
    pr = s.preview_scenario(pid, overrides={"cost_change_pct": 0.30})
    assert pr["results"]["gross_margin"] < prev["results"]["gross_margin"]


def test_unit_costs_and_prices_in_the_projection_equal_the_stored_values(stored):
    s, ids, _ = stored
    prev = s.preview_scenario(ids["project"])
    econ = {e["name"]: e for e in s.product_economics()}
    for l in prev["results"]["lines"]:
        e = econ[l["name"]]
        disc = prev["inputs"]["assumptions"]["avg_discount_pct"] / 100
        assert l["price_cents"] == round(e["price_cents"] * (1 - disc), 2) and l["unit_cost_cents"] == round(e["unit_cost_cents"], 2)
    assert prev["results"]["gross_margin"] > 0.5 and prev["results"]["breakeven_units_per_month"] > 0


def test_roles_may_view_but_only_owner_and_analyst_save_scenarios(stored):
    s, ids, dsn = stored
    v = SV.GrowthService(dsn, "growth_fin", "tenant-nasha", "vic")
    assert v.preview_scenario(ids["project"]) is not None
    with pytest.raises(SV.Denied):
        v.save_scenario(ids["project"], "nope")
    v.close()
    a = SV.GrowthService(dsn, "growth_fin", "tenant-nasha", "ana")
    assert a.save_scenario(ids["project"], "Analyst scenario", overrides={"price_change_pct": 0.05})
    a.close()
