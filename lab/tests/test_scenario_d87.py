"""D-87 scenario over a real (small) synthetic warehouse: history preserved, depletion exact, restated revenue tied to the approved price config, variance detection scored
against injected anomalies, procurement proposals, Ops AI evaluation, website/database price consistency, optional WEIR approval flow. SYNTHETIC data only."""
import asyncio
import inspect
import json
import re
import shutil
import sqlite3
import subprocess
import sys

import pytest

from nasha_lab import enterprise_sim as es
from nasha_lab.recipes import beer_costing, bom, model, pricing, suppliers
from nasha_lab.warehouse import ops_ai_eval, pipeline, repro, scenario
from nasha_lab.warehouse.ops_ai import OpsAI, Principal
from nasha_lab.warehouse.procurement import ProcurementStore, ProcurementUpstream, load_recos, weir_policy_with_procurement

CFG = es.SimConfig(name="scn-test", months=10, fast_casual=3, beer_gardens=1, target_orders=30_000, loyalty_profiles=2_500, employees=60, open_at_start=3)
SC = pricing.load_config()


def hist(path):
    con = sqlite3.connect(path)
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'dim_%' OR name LIKE 'fact_%' OR name LIKE 'mart_%') ORDER BY 1")]
    out = {t: tuple(con.execute(f"SELECT count(*), sum(rowid) FROM {t}").fetchone()) for t in names}
    con.close()
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("scn")
    es.generate(CFG, d / "src")
    pipeline.run(d / "src", d / "w.db")
    before_hash = repro.table_hashes(d / "w.db")
    shutil.copy(d / "w.db", d / "w2.db")
    counts = scenario.build(d / "w.db")
    scenario.build(d / "w2.db")
    return d, before_hash, counts


def q(path, sql, p=()):
    c = sqlite3.connect(path); r = c.execute(sql, p).fetchall(); c.close(); return r


def test_historical_tables_are_preserved_byte_for_byte(built):
    d, before, counts = built
    after = {k: v for k, v in repro.table_hashes(d / "w.db").items() if not k.startswith("scn_")}
    assert after == before and counts["scn_menu_item"] == 15


def test_scenario_is_deterministic(built):
    d, *_ = built
    a, b = repro.table_hashes(d / "w.db"), repro.table_hashes(d / "w2.db")
    assert a == b and any(k.startswith("scn_") for k in a)


def test_scenario_references_the_approved_price_config_and_documents_the_prior_one(built):
    d, *_ = built
    assert q(d / "w.db", "SELECT pricing_config, prior_pricing_config FROM scn_scenario_run") == [("price-v3-2026-10-23", "price-v1-placeholder (historical simulation); lineage v2-2026-10-22")]
    p = dict(q(d / "w.db", "SELECT price_key, price_cents FROM scn_pricing WHERE config_id='price-v3-2026-10-23' AND price_cents IS NOT NULL"))
    assert p == {"appetizer": 1350, "main": 1850, "beer_glass": 900, "beer_pitcher": 3100}
    sv = {s: (oz, ml) for s, oz, ml, _ in q(d / "w.db", "SELECT size, fl_oz, volume_ml, status FROM scn_serving")}
    assert sv["glass"][0] == 16 and sv["pitcher"][0] == 60 and sv["glass"][1] == pytest.approx(16 * 29.5735295625) and sv["pitcher"][1] == pytest.approx(60 * 29.5735295625)
    assert all("PROVISIONAL" in r[0] for r in q(d / "w.db", "SELECT status FROM scn_serving"))
    assert {r[0] for r in q(d / "w.db", "SELECT DISTINCT price_basis FROM scn_sim_item_map")} == {"v2_approved", "v1_placeholder_carried"}


def test_restated_revenue_uses_approved_prices_and_leaves_v1_revenue_unchanged(built):
    d, *_ = built
    for item, price in (("M01", 1350), ("M04", 1350), ("M02", 1850), ("M05", 1850), ("B01", 900), ("B04", 900)):
        units, gross, v1_gross = q(d / "w.db", "SELECT sum(units), sum(restated_gross_cents), sum(v1_gross_cents) FROM scn_item_month WHERE item_id=?", (item,))[0]
        assert gross == units * price
        hist_gross = q(d / "w.db", "SELECT sum(gross_cents) FROM mart_product_month WHERE item_id=?", (item,))[0][0]
        assert v1_gross == hist_gross                                            # the historical figure is still what the mart says
    assert q(d / "w.db", "SELECT restated_gross_cents = v1_gross_cents FROM scn_item_month WHERE item_id='B02' LIMIT 1") == [(1,)]   # lager keeps v1 placeholder
    assert q(d / "w.db", "SELECT DISTINCT price_basis FROM scn_item_month WHERE item_id='M03'") == [("v1_placeholder_carried",)]       # retired Goat Birria: history carried, not restated
    assert q(d / "w.db", "SELECT count(*) FROM scn_recipe_bom WHERE recipe_id='goat-birria'") == [(0,)]


def test_inventory_depletion_matches_an_independent_recomputation(built):
    d, *_ = built
    recipes, master = model.load_recipes(), model.load_master()
    mapping = SC["menu_item_mapping_to_sim"]
    con = sqlite3.connect(d / "w.db")
    rows = con.execute("SELECT l.location_id, c.week, p.item_id, sum(f.qty) FROM fact_order_line f JOIN dim_product p USING(product_key) JOIN dim_location l USING(location_key) JOIN scn_calendar c USING(date_key) WHERE p.item_id IN ('M01','M02','M04','M05') GROUP BY 1,2,3").fetchall()
    want = {}
    for loc, wk, item, u in rows:
        for ing, qty in bom.explode(mapping[item], recipes, master).items():
            want[(loc, wk, ing)] = want.get((loc, wk, ing), 0.0) + u * qty
    got = {(a, b, c): t for a, b, c, t in con.execute("SELECT location_id, week, ingredient_id, theoretical_qty FROM scn_depletion_week")}
    con.close()
    assert got.keys() == want.keys() and all(abs(got[k] - want[k]) < 1e-6 for k in want)


def test_variance_detector_finds_injected_anomalies_without_reading_them(built):
    d, *_ = built
    assert "scn_injected_anomaly" not in inspect.getsource(scenario.detect_variance)
    con = sqlite3.connect(d / "w.db")
    s = scenario.score_detection(con)
    con.close()
    assert s["injected_cells"] == 11 and s["recall"] == 1.0 and s["precision"] >= 0.9, s


def test_demand_forecast_is_nonnegative_with_backtest_and_recommendations_are_proposals(built):
    d, *_ = built
    assert q(d / "w.db", "SELECT count(*) FROM scn_demand_forecast WHERE forecast_qty < 0") == [(0,)]
    assert q(d / "w.db", "SELECT count(*) FROM scn_forecast_backtest WHERE wape IS NOT NULL") [0][0] > 0
    recos = load_recos(d / "w.db")
    assert recos and {r["status"] for r in recos} == {"PROPOSED"} and {r["price_class"] for r in recos} == {"SYNTHETIC_QUOTE"}
    quotes = suppliers.load()["quotes"]
    pack = {(x["quote_id"]): x["pack_qty"] for x in quotes}
    for r in recos[:40]:
        assert r["order_qty"] % pack[r["quote_id"]] == pytest.approx(0, abs=1e-9)           # whole packs only
        best = suppliers.compare(quotes, r["ingredient_id"], r["order_qty"] and (r["need_qty"] * 1.1 - r["on_hand_qty"]), on="2026-10-22")[0]
        assert best["quote_id"] == r["quote_id"]                                            # cheapest valid synthetic quote


def test_ops_ai_scenario_evaluation_passes_every_case(built, tmp_path):
    rep = ops_ai_eval.run_eval(built[0] / "w.db", tmp_path / "a.db")
    assert rep["summary"]["passed"] == rep["summary"]["cases"] >= 50 and rep["summary"]["failure_kinds"] == {"wrong_answer": 0, "false_allow": 0, "false_deny": 0, "wrong_refusal": 0}


def test_scenario_tools_are_audited_and_default_deny(built, tmp_path):
    ai = OpsAI(built[0] / "w.db", tmp_path / "a.db")
    ids = [r[0] for r in q(built[0] / "w.db", "SELECT location_id FROM dim_location ORDER BY 1")]
    r = ai.call(Principal("f", "finance"), "menu_economics", {})
    assert r["ok"] and r["provenance"]["synthetic"] and {x["price_cents"] for x in r["rows"]} == {1350, 1850}
    assert ai.call(Principal("sm", "site_manager", ids[0]), "supplier_comparison", {"ingredient_id": "i-paneer"})["code"] == "role_denied"
    assert ai.call(Principal("sm", "site_manager", ids[0]), "variance_flags", {"location_id": ids[1]})["code"] == "site_scope"
    assert ai.call(Principal("x", "intern"), "price_config", {})["code"] == "role_denied"
    n = ai.audit.execute("SELECT count(*) FROM ops_ai_audit").fetchone()[0]
    assert n == 4 and ai.audit.execute("SELECT count(*) FROM ops_ai_audit WHERE tool IN ('menu_economics','supplier_comparison','variance_flags','price_config')").fetchone()[0] == 4
    ai.close()


def test_no_beef_or_pork_in_any_scenario_table(built):
    con = sqlite3.connect(built[0] / "w.db")
    names = [r[0] for r in con.execute("SELECT name FROM scn_ingredient")] + [r[0] for r in con.execute("SELECT ingredient_id FROM scn_recipe_bom")]
    con.close()
    assert not [n for n in names if model.D54.search(n)]


def test_website_and_database_prices_agree(built):
    subprocess.run([sys.executable, str(model.ROOT / "website/preview_courtyard.py")], check=True, capture_output=True)
    html = (model.ROOT / "website/preview-courtyard/menu.html").read_text()
    page = {m[0]: int(m[1]) for m in re.findall(r'data-recipe="([a-z0-9-]+)" data-category="[a-z]+"><div class="slot img">.*?data-price-cents="(\d+)"', html, re.S)}
    db = dict(q(built[0] / "w.db", "SELECT menu_item_id, price_cents FROM scn_menu_item"))
    assert page == db and len(page) == 15 and "goat" not in html.lower()
    beer_prices = {int(x) for x in re.findall(r'data-beer="[a-z-]+">.*?data-price-cents="(\d+)".*?data-price-cents="(\d+)"', html, re.S)[0]}
    assert beer_prices == {900, 3100} and "Target ABV 4.7%" in html and "Target ABV 6.0%" in html and "provisional concept sizes" in html.lower() and "16 US fl oz" in html and "60 US fl oz" in html
    assert "$9.00" in html and "$31.00" in html and "$13.50" in html and "$18.50" in html
    assert "noindex" in html and "nothing is open" in html.lower() and not model.D54.search(re.sub(r"\b(not|no|never)\s+(a\s+)?(beef|pork)\b", "", re.sub(r"<[^>]+>", " ", html), flags=re.I))


def test_dashboard_page_is_built_and_labelled_synthetic(built, tmp_path):
    from nasha_lab.warehouse import dashboards
    dashboards.build_all(built[0] / "w.db", tmp_path)
    h = (tmp_path / "menu-economics.html").read_text()
    assert "SYNTHETIC" in h and "$13.50" in h and "$18.50" in h and "concept prices" in h.lower() and "not NASHA revenue" in h


# ---------------------------------------------------------------- THE WEIR approval flow (skips when THE WEIR is not installed)
def test_procurement_proposals_go_through_the_weir_write_gate(built, tmp_path):
    pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
    pytest.importorskip("weir_testbed", reason="INTEGRATION UNAVAILABLE: weir_testbed not installed")
    from mcp_weir.gateway import Gateway
    from mcp_weir.policy import parse_policy
    from mcp_weir.store import Store
    from nasha_lab.warehouse import ops_ai_weir as W
    recos = {r["reco_id"]: r for r in load_recos(built[0] / "w.db", limit=3)}
    rid = next(iter(recos))
    store, weir = ProcurementStore(), Store(str(tmp_path / "weir.db"))
    ops = OpsAI(built[0] / "w.db", tmp_path / "ops.db")
    gw = Gateway(parse_policy(weir_policy_with_procurement(W.policy())), weir, {"warehouse": W.OpsAIUpstream(ops, Principal("e", "exec")), "procurement": ProcurementUpstream(store, recos),
                                                                          "notes": __import__("weir_testbed.servers", fromlist=["x"]).in_process_upstreams(__import__("weir_testbed.world", fromlist=["x"]).World.from_fixture({}))["notes"]})
    run = asyncio.run
    run(gw.start())
    s = gw.open_session("proc-1")
    first = run(gw.call_tool_detailed(s, "procurement__propose_purchase_order", {"reco_id": rid, "note": "weekly reorder proposal"}))
    assert not first.forwarded and first.approval_id and store.con.execute("SELECT count(*) FROM reco").fetchone()[0] == 0      # held: nothing stored while pending
    assert weir.resolve_approval(first.approval_id, True) == "approved"
    again = run(gw.call_tool_detailed(s, "procurement__propose_purchase_order", {"reco_id": rid, "note": "weekly reorder proposal"}))
    assert again.forwarded and store.status(rid) == "PROPOSED" and store.po_drafts() == []                                      # a proposal, never an order
    assert weir.verify_chain()[0]


def test_beer_economics_and_levers_tables_match_the_python_model(built):
    d, *_ = built
    cfg = pricing.load_config()
    for beer, size, scen, cost, margin in q(d / "w.db", "SELECT beer_id, size, scenario, cost_ex_labor_cents, margin_ex_labor_pct FROM scn_beer_economics"):
        e = beer_costing.economics(beer, size, scen, cfg)
        assert cost == pytest.approx(e["cost_ex_labor"] * 100) and margin == pytest.approx(e["margin_ex_labor_pct"])
    assert q(d / "w.db", "SELECT count(DISTINCT menu_item_id) FROM scn_cost_lever") == [(15,)]
    assert q(d / "w.db", "SELECT lever FROM scn_cost_lever WHERE menu_item_id='tandoori-lamb-tacos' ORDER BY rowid LIMIT 1") == [("original",)]
    assert q(d / "w.db", "SELECT count(*) FROM scn_supplier_sensitivity WHERE delta_pct < -1e-9") == [(0,)]


def test_menu_engineering_classes_follow_the_documented_rule(built):
    d, *_ = built
    rows = q(d / "w.db", "SELECT menu_item_id, units, mix_pct, gross_profit_per_unit_cents, menu_class FROM scn_menu_engineering")
    tot_u = sum(r[1] for r in rows)
    gp = dict(q(d / "w.db", "SELECT menu_item_id, sum(gross_profit_cents) FROM scn_menu_profitability_month GROUP BY 1"))
    avg_gp = sum(gp.values()) / tot_u
    for mid, u, mix, gpu, cls in rows:
        pop, mar = u / tot_u >= 0.7 / len(rows), gp[mid] / u >= avg_gp
        assert cls == {(1, 1): "star", (1, 0): "plowhorse", (0, 1): "puzzle", (0, 0): "dog"}[(int(pop), int(mar))]
        assert mix == pytest.approx(u / tot_u, abs=1e-4)


def test_dashboard_has_beer_levers_engineering_and_forecast_sections(built, tmp_path):
    from nasha_lab.warehouse import dashboards
    dashboards.build_all(built[0] / "w.db", tmp_path)
    h = (tmp_path / "menu-economics.html").read_text()
    for needle in ("Menu engineering", "NOT verified production costs".replace("NOT", "not"), "Recipe-cost levers: Tandoori Lamb Tacos", "Supplier-price sensitivity", "Ingredient demand forecast", "16 and 60 US fl oz", "original scenario first"):
        assert needle in h, needle
    assert "Goat" not in h
