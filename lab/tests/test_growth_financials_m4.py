"""Financial intelligence (Milestone 4): start-up cost categories, working capital, contingency, break-even grid, formulas with substituted numbers, supplier price effect, input validation and failure behaviour.
Expected numbers come from hand calculations written in financial_eval.py before the code was run against them. SYNTHETIC data only; every result is a simulated projection."""
import math
from datetime import date

import pytest

from nasha_lab.growth import financial_eval as E, financials as F, procurement as PRC

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, demo as DM

A = "tenant-nasha"


def test_every_hand_calculated_case_matches_to_the_cent():
    bad = [(c["name"], c["mismatches"]) for c in E.run_cases() if not c["ok"]]
    assert not bad, bad


def test_structural_invariants_hold_and_identical_inputs_give_identical_results():
    assert all(E.invariants().values()), [k for k, v in E.invariants().items() if not v]


def test_each_financial_mutant_is_caught():
    m = E.run_mutants()
    assert m["baseline_failures"] == 0 and len(m["mutants"]) >= 9 and all(x["killed"] for x in m["mutants"]), [x["name"] for x in m["mutants"] if not x["killed"]]


def test_the_formulas_shown_to_the_user_report_exactly_the_numbers_that_were_calculated():
    res = F.compute(F.build_inputs(E.P, E.CASES[0][1], {}, 2_000_000))
    by = {f["name"]: f for f in res["formulas"]}
    assert by["Monthly revenue"]["result_cents"] == res["revenue_cents"] and by["Contribution"]["result_cents"] == res["contribution_cents"]
    assert by["Operating profit per month"]["result_cents"] == res["operating_profit_monthly_cents"] and by["Total start-up requirement"]["result_cents"] == res["startup"]["total_requirement_cents"]
    assert by["Break-even units per month"]["value"] == res["breakeven_units_per_month"] and by["Budget headroom"]["result_cents"] == res["startup"]["headroom_cents"]
    assert "$1,000.00 / $7.00" in by["Break-even units per month"]["worked"] and "10% x $7,500.00 = $750.00" in by["Contingency"]["worked"]
    assert F.LIMITATIONS and all("assum" in x.lower() or "model" in x.lower() or "supplier" in x.lower() or "break-even" in x.lower() for x in F.LIMITATIONS)
    assert res["kind"] == "simulated" and "not actual business performance" in res["disclaimer"]


@pytest.mark.parametrize("assumptions,overrides,budget", [
    ({"weekly_orders": float("nan")}, {}, 0), ({"weekly_orders": float("inf")}, {}, 0), ({"rent_monthly_cents": -1}, {}, 0), ({"contingency_pct": 101}, {}, 0), ({"avg_discount_pct": 120}, {}, 0),
    ({"price_elasticity": 0.5}, {}, 0), ({}, {"price_change_pct": -1.0}, 0), ({}, {"cost_change_pct": float("nan")}, 0), ({}, {}, -5), ({"working_capital_months": -2}, {}, 0)])
def test_inputs_that_cannot_give_a_defensible_number_are_refused_not_computed(assumptions, overrides, budget):
    with pytest.raises(F.FinancialInputError):
        F.compute(F.build_inputs(E.P, {**E.BASE, **assumptions}, overrides, budget))


def test_a_scenario_with_no_priced_product_or_an_unknown_override_is_refused():
    with pytest.raises(ValueError):
        F.build_inputs([], E.BASE, {}, 0)
    with pytest.raises(ValueError):
        F.build_inputs(E.P, E.BASE, {"profit_multiplier": 3}, 0)
    with pytest.raises(F.FinancialInputError):
        F.compute(F.build_inputs([{"name": "Free", "price_cents": 0, "unit_cost_cents": 5}], E.BASE, {}, 0) if False else {**F.build_inputs(E.P, E.BASE, {}, 0), "products": [{"name": "Free", "price_cents": 0, "unit_cost_cents": 5.0, "mix": 1.0}]})


def test_break_even_grid_moves_the_right_way_and_shows_unreachable_cells_as_none():
    inp = F.build_inputs([{"name": "Thin", "price_cents": 1000, "unit_cost_cents": 750}], {**E.BASE, "rent_monthly_cents": 200_000}, {}, 0)
    g = F.breakeven_grid(inp)
    rows = {r["cost_change_pct"]: [c["breakeven_orders_per_week"] for c in r["cells"]] for r in g["rows"]}
    base = rows[0.0]
    assert all(b is not None for b in base) and base == sorted(base, reverse=True), "a higher price needs fewer orders to break even"
    col = [rows[k][2] for k in sorted(rows) if rows[k][2] is not None]
    assert col == sorted(col), "higher ingredient cost needs more orders"
    assert 750 * 1.30 > 1000 * 0.90 and rows[30.0][0] is None, "at +30% cost (975c) and -10% price (900c) the unit loses money, so break-even is unreachable"
    assert "elasticity" in g["note"]


def test_supplier_price_effect_is_arithmetic_on_stored_quotes_and_never_a_real_saving_when_synthetic():
    def it(ref, chosen, runner=None, cls="SYNTHETIC_QUOTE"):
        return dict(ingredient_ref=ref, chosen=dict(cost_cents=chosen, price_class=cls), runner_up=None if runner is None else dict(cost_cents=runner))
    pe = PRC.price_effect([it("a", 1000, 1300), it("b", 500, 500), it("c", 200)], 4)
    assert pe["chosen_total_cents"] == 1700 and pe["second_choice_total_cents"] == 2000 and pe["difference_cents"] == 300 and pe["items_with_only_one_valid_quote"] == 1
    assert pe["monthly_equivalent_difference_cents"] == round(300 * (52 / 12) / 4) and pe["is_real_saving"] is False and "synthetic" in pe["note"].lower()
    assert PRC.price_effect([it("a", 1000, 1300, "SUPPLIER_QUOTE")], 4)["is_real_saving"] is None


# ---------------------------------------------------------------- HTTP: the stored model end to end
@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import pixeltable_pgserver as pg
    root = tmp_path_factory.mktemp("gfin")
    try:
        srv = pg.get_server(str(root / "pg"), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    dsn = srv.get_uri()
    envs = DM.build(root / "d", dsn, schema="growth_fin", with_warehouse=False, today=date(2026, 10, 23))
    yield TestClient(GA.create_growth_app(envs, as_of=date(2026, 10, 23))), envs
    srv.cleanup()


def H(envs, u):
    return {"Authorization": "Bearer " + envs[A].authority.login(u, f"{A}-{u}-dev-passcode")}


def pid(world):
    c, envs = world
    return c.get(f"/v1/tenants/{A}/projects", headers=H(envs, "ada")).json()["items"][0]["id"]


def test_the_flagship_startup_requirement_is_computed_from_stored_assumptions_and_shows_a_funding_gap(world):
    c, envs = world
    r = c.post(f"/v1/tenants/{A}/projects/{pid(world)}/scenarios/preview", json={}, headers=H(envs, "vic")).json()
    st, res = r["results"]["startup"], r["results"]
    assert st["capex_total_cents"] == 42_000_000 and st["preopening_total_cents"] == 8_300_000 and st["working_capital"]["fixed_cost_months"] == 2
    assert st["total_requirement_cents"] == st["subtotal_cents"] + st["contingency_cents"] and st["headroom_cents"] == 60_000_000 - st["total_requirement_cents"]
    assert st["funding_gap_cents"] > 0 and st["budget_covers_requirement"] is False, "the placeholder budget does not cover the placeholder plan; that is the planning finding"
    assert r["inputs"]["defaulted_assumptions"] == [] and r["limitations"] and res["formulas"] and r["breakeven_grid"]["rows"] and res["kind"] == "simulated"


def test_raising_the_budget_or_cutting_a_cost_recalculates_the_requirement_from_stored_data(world):
    c, envs = world
    p = pid(world); url = f"/v1/tenants/{A}/projects/{p}/scenarios/preview"
    base = c.post(url, json={}, headers=H(envs, "vic")).json()["results"]["startup"]
    cut = c.post(url, json={"capex_buildout_cents": 17_000_000}, headers=H(envs, "vic")).json()["results"]["startup"]
    assert base["total_requirement_cents"] - cut["total_requirement_cents"] == round(5_000_000 * 1.10)       # the cut also removes its 10% contingency
    assert cut["capex_total_cents"] == 37_000_000
    assert c.put(f"/v1/tenants/{A}/projects/{p}/assumptions/capex_buildout_cents", json=dict(label="Build-out", value=17_000_000, unit="cents", basis="founder"), headers=H(envs, "ada")).status_code == 200
    after = c.post(url, json={}, headers=H(envs, "vic")).json()["results"]["startup"]
    assert after["total_requirement_cents"] == cut["total_requirement_cents"], "a stored change and the same what-if give the same number"


def test_invalid_what_ifs_and_non_finite_stored_values_give_a_clean_refusal_never_a_500(world):
    c, envs = world
    p = pid(world); url = f"/v1/tenants/{A}/projects/{p}/scenarios/preview"
    for body in ({"contingency_pct": 150}, {"working_capital_months": -1}, {"price_elasticity": 2}, {"capex_buildout_cents": -5}, {"profit_boost": 1}):
        assert c.post(url, json=body, headers=H(envs, "vic")).status_code == 422, body
    r = c.put(f"/v1/tenants/{A}/projects/{p}/assumptions/weekly_orders", content='{"label":"x","value":NaN,"unit":"orders","basis":"founder"}', headers={**H(envs, "ada"), "Content-Type": "application/json"})
    assert r.status_code == 422, "a non-finite assumption cannot be stored"
    ok = c.post(url, json={}, headers=H(envs, "vic"))
    assert ok.status_code == 200 and math.isfinite(ok.json()["results"]["operating_profit_monthly_cents"])
