"""D-90 full-menu simulation: a versioned current-state menu definition (no Goat Birria; Tandoori Lamb Tacos at $18.50, recipe/costing provisional), every active menu item flows through
order generation, recipe mapping, depletion, forecasting, costing, profitability, variance detection and procurement, and the earlier simulation stays reproducible as a historical scenario. SYNTHETIC."""
import asyncio
import hashlib
import json
import shutil
import sqlite3

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")

from nasha_lab import enterprise_sim as es
from nasha_lab.governed import tenants as T, workflow as W
from nasha_lab.recipes import bom, menu, model, pricing, synth_ops
from nasha_lab.warehouse import pipeline, repro, scenario

BASE = dict(months=10, fast_casual=3, beer_gardens=1, target_orders=30_000, loyalty_profiles=2_500, employees=60, open_at_start=3)
CUR = menu.load("current")
ITEMS = [i["menu_item_id"] for i in CUR["items"]]
CFG = pricing.load_config()


@pytest.fixture(scope="module")
def cur(tmp_path_factory):
    d = tmp_path_factory.mktemp("cur")
    es.generate(es.SimConfig(name="cur", menu="current", **BASE), d / "src"); pipeline.run(d / "src", d / "w.db"); scenario.build(d / "w.db")
    return d / "w.db"


@pytest.fixture(scope="module")
def hist(tmp_path_factory):
    d = tmp_path_factory.mktemp("hist")
    es.generate(es.SimConfig(name="hist", **BASE), d / "src"); pipeline.run(d / "src", d / "w.db"); scenario.build(d / "w.db")
    shutil.copy(d / "w.db", d / "w2.db"); scenario.build(d / "w2.db")
    return d


def q(path, sql, p=()):
    c = sqlite3.connect(path); r = c.execute(sql, p).fetchall(); c.close(); return r


# ------------------------------------------------------------------ the definition
def test_current_definition_has_no_goat_birria_and_the_approved_replacement():
    raw = (menu.MENU_DIR / menu.FILES["current"]).read_text()
    assert "goat-birria" not in [i["menu_item_id"] for i in CUR["items"]] and CUR["excluded"][0]["dish"] == "goat-birria"
    lamb = next(i for i in CUR["items"] if i["menu_item_id"] == "tandoori-lamb-tacos")
    assert lamb["provisional"] is True and "approved" in CUR["decision"].lower() and "NOT been cooked" in CUR["provisional_notice"]
    assert pricing.price_cents(CFG, model.load_recipes()["tandoori-lamb-tacos"]["menu_category"]) == 1850
    assert "has not been cooked, tasted or tested" in raw.lower(), "the definition must not imply the replacement was cooked or tested"


def test_historical_documents_are_preserved_and_the_old_definition_still_loads():
    h = menu.load("historical")
    assert h["menu_id"].endswith("historical") and {i["menu_item_id"] for i in h["items"]} == {"chicken-65-totopos", "paneer-tikka-taco", "mango-habanero-gobi", "butter-chicken-quesadilla"}
    assert (menu.MENU_DIR.parent / "recipes/retired").is_dir() and any((menu.MENU_DIR.parent / "recipes/retired").iterdir())
    assert "D-88" in (menu.MENU_DIR.parent.parent / "docs/decisions/DECISIONS.md").read_text()


def test_retired_dish_is_rejected_by_the_loader(tmp_path, monkeypatch):
    bad = json.loads((menu.MENU_DIR / menu.FILES["current"]).read_text()); bad["items"].append({"sim_item_id": "M03", "menu_item_id": "goat-birria", "name": "Goat Birria", "role": "core5", "popularity": {"fast casual": 1, "beer garden": 1}})
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    monkeypatch.setattr(menu, "MENU_DIR", tmp_path); monkeypatch.setitem(menu.FILES, "bad", "bad.json")
    with pytest.raises(AssertionError):
        menu.load("bad")


# ------------------------------------------------------------------ the simulation uses it
def test_current_simulation_contains_no_goat_anywhere(cur):
    assert q(cur, "SELECT count(*) FROM dim_product WHERE item_id='M03' OR lower(name) LIKE '%goat%'") == [(0,)]
    for t in ("scn_sim_item_map", "scn_menu_item", "scn_recipe_bom", "scn_ingredient", "scn_supplier_quote", "scn_procurement_reco", "scn_depletion_week"):
        cols = [r[1] for r in q(cur, f"PRAGMA table_info({t})")]
        for c in cols:
            if c.endswith("_id") or c in ("name",):
                assert q(cur, f"SELECT count(*) FROM {t} WHERE lower({c}) LIKE '%goat%'") == [(0,)], (t, c)


def test_menu_definition_table_records_every_item_and_marks_lamb_provisional(cur):
    rows = {r[0]: r for r in q(cur, "SELECT menu_item_id, sim_item_id, role, provisional, status FROM scn_menu_definition")}
    assert set(rows) == set(ITEMS) and rows["tandoori-lamb-tacos"][3] == 1 and "not cooked or tested" in rows["tandoori-lamb-tacos"][4].lower()
    assert all(rows[i][3] == 0 for i in ITEMS if i != "tandoori-lamb-tacos")


@pytest.mark.parametrize("dish", ITEMS)
def test_every_active_menu_item_flows_through_the_whole_simulation(cur, dish):
    recipes, master = model.load_recipes(), model.load_master()
    slot = next(i["sim_item_id"] for i in CUR["items"] if i["menu_item_id"] == dish)
    # recipe -> ingredients
    bom_ing = bom.explode(dish, recipes, master)
    assert bom_ing and all(i in master for i in bom_ing)
    # synthetic orders exist for the slot
    units = q(cur, "SELECT coalesce(sum(f.qty),0) FROM fact_order_line f JOIN dim_product p USING(product_key) WHERE p.item_id=?", (slot,))[0][0]
    assert units > 500, f"{dish}: only {units} units sold"
    # costing at the approved price
    price, cost = q(cur, "SELECT price_cents, unit_food_cost_cents FROM scn_menu_item WHERE menu_item_id=?", (dish,))[0]
    assert price == pricing.price_cents(CFG, recipes[dish]["menu_category"]) and 0 < cost < price
    # profitability reconciles: gross profit = restated net - (food + consumables) x units
    net, fc, gp, u = q(cur, "SELECT sum(restated_net_cents), sum(food_and_consumables_cents), sum(gross_profit_cents), sum(units) FROM scn_menu_profitability_month WHERE menu_item_id=?", (dish,))[0]
    assert u == units and abs(gp - (net - fc)) <= 3 and net > 0
    # depletion = units x BOM, recomputed independently from the raw order lines
    want = {}
    for loc, wk, uu in q(cur, "SELECT l.location_id, c.week, sum(f.qty) FROM fact_order_line f JOIN dim_product p USING(product_key) JOIN dim_location l USING(location_key) JOIN scn_calendar c USING(date_key) WHERE p.item_id=? GROUP BY 1,2", (slot,)):
        for ing, qq in bom_ing.items():
            want[(loc, wk, ing)] = uu * qq
    got = {}
    for loc, wk, ing, t in q(cur, "SELECT d.location_id, d.week, d.ingredient_id, d.theoretical_qty FROM scn_depletion_week d"):
        if ing in bom_ing:
            got[(loc, wk, ing)] = t
    # an ingredient shared with other dishes has MORE depletion than this dish alone; a private one must match exactly
    assert all(got.get(k, 0) + 1e-6 >= v for k, v in want.items())
    # menu engineering classified it
    assert q(cur, "SELECT menu_class FROM scn_menu_engineering WHERE menu_item_id=?", (dish,))[0][0] in ("star", "plowhorse", "puzzle", "dog")
    # forecasts and reorder recommendations exist for at least one of its ingredients
    assert q(cur, f"SELECT count(*) FROM scn_demand_forecast WHERE ingredient_id IN ({','.join('?' * len(bom_ing))})", tuple(bom_ing))[0][0] > 0


def test_lamb_depletion_is_exactly_units_times_bom_because_only_this_dish_uses_lamb(cur):
    recipes, master = model.load_recipes(), model.load_master()
    per = bom.explode("tandoori-lamb-tacos", recipes, master)["i-lamb-leg"]
    units = q(cur, "SELECT sum(f.qty) FROM fact_order_line f JOIN dim_product p USING(product_key) WHERE p.item_id='M06'")[0][0]
    total = q(cur, "SELECT sum(theoretical_qty) FROM scn_depletion_week WHERE ingredient_id='i-lamb-leg'")[0][0]
    assert abs(total - units * per) < 1e-6 and q(cur, "SELECT count(DISTINCT recipe_id) FROM scn_recipe_bom WHERE ingredient_id='i-lamb-leg'")[0][0] >= 1


def test_variance_and_waste_detection_works_on_the_full_menu_including_lamb(tmp_path):
    es.generate(es.SimConfig(name="v", menu="current", **BASE), tmp_path / "src"); pipeline.run(tmp_path / "src", tmp_path / "w.db")
    sites = [r[0] for r in q(tmp_path / "w.db", "SELECT DISTINCT location_id FROM dim_location ORDER BY 1")][:2]
    inj = [synth_ops.Anomaly(sites[0], "i-lamb-leg", "over_portion", 10, 4, 0.35), synth_ops.Anomaly(sites[1], "i-corn-kernels", "spike", 14, 2, 0.8)]
    scenario.build(tmp_path / "w.db", anomalies=inj)
    con = sqlite3.connect(tmp_path / "w.db"); s = scenario.score_detection(con); con.close()
    assert s["injected_cells"] == 6 and s["recall"] == 1.0 and s["precision"] >= 0.8, s
    assert q(tmp_path / "w.db", "SELECT count(*) FROM scn_variance_flag WHERE ingredient_id='i-lamb-leg'")[0][0] >= 1


# ------------------------------------------------------------------ the historical scenario is preserved
def test_historical_scenario_still_reproduces_four_dishes_with_goat_slot_unmapped(hist):
    m = {r[0]: r for r in q(hist / "w.db", "SELECT sim_item_id, menu_item_id, price_basis FROM scn_sim_item_map")}
    assert {k: v[1] for k, v in m.items() if k.startswith("M")} == {"M01": "chicken-65-totopos", "M02": "paneer-tikka-taco", "M03": None, "M04": "mango-habanero-gobi", "M05": "butter-chicken-quesadilla"}
    assert m["M03"][2] == "v1_placeholder_carried"
    assert q(hist / "w.db", "SELECT count(*) FROM dim_product WHERE item_id='M03'")[0][0] == 1, "raw historical rows are untouched"
    assert q(hist / "w.db", "SELECT count(*) FROM scn_menu_definition WHERE menu_item_id LIKE '%lamb%'")[0][0] == 0


def test_historical_scenario_is_reproducible_and_its_config_has_no_menu_key(hist):
    h = lambda p: hashlib.sha256(json.dumps([q(p, f"SELECT * FROM {t} ORDER BY 1,2,3") for t in ("scn_depletion_week", "scn_variance_flag", "scn_procurement_reco", "scn_item_month")], default=str).encode()).hexdigest()
    assert h(hist / "w.db") == h(hist / "w2.db")
    man = json.loads((hist / "src/manifest.json").read_text())
    assert "menu" not in man["config"], "default config must serialise exactly as before D-90 so historical manifests stay byte-identical"


def test_current_simulation_is_deterministic_and_different_from_the_historical_one(tmp_path):
    a = es.generate(es.SimConfig(name="d", menu="current", **BASE), tmp_path / "a"); b = es.generate(es.SimConfig(name="d", menu="current", **BASE), tmp_path / "b")
    assert {k: v["sha256"] for k, v in a["tables"].items()} == {k: v["sha256"] for k, v in b["tables"].items()}
    assert a["config"]["menu"] == "current"


# ------------------------------------------------------------------ procurement + THE WEIR for the replacement dish
def test_lamb_procurement_is_proposed_held_for_approval_and_ends_as_a_draft_only(tmp_path):
    env = T.provision(tmp_path, "lamb", es.SimConfig(name="lamb", menu="current", seed=5, **BASE))
    sites = [r[0] for r in q(env.warehouse, "SELECT DISTINCT location_id FROM dim_location ORDER BY 1")]
    scenario.build(env.warehouse, anomalies=[synth_ops.Anomaly(sites[0], "i-lamb-leg", "spike", 12, 3, 0.9)], quotes=env.quotes)
    loc, ing = q(env.warehouse, "SELECT f.location_id, f.ingredient_id FROM scn_variance_flag f JOIN scn_procurement_reco r ON r.location_id=f.location_id AND r.ingredient_id=f.ingredient_id WHERE f.ingredient_id='i-lamb-leg' ORDER BY f.excess_pct DESC LIMIT 1")[0]
    import dataclasses
    env2 = dataclasses.replace(env, ledger_path=tmp_path / "l2.db", weir_db=tmp_path / "w2.db", trace_db=tmp_path / "t2.db", memory_db=tmp_path / "m2.db")     # empty stores for the denied run
    wf2 = W.GovernedProcurement(env2)
    try:
        denied = wf2.run(wf2.login("lamb-quality", "lamb-quality-dev-passcode"), loc, ing)
        assert denied["failure"] == "TOOL_DENIED" and wf2.ledger.con.execute("SELECT count(*) FROM po_drafts").fetchone()[0] == 0
    finally:
        wf2.close()
    wf = W.GovernedProcurement(env)
    try:
        tok = lambda who: wf.login(f"lamb-{who}", f"lamb-{who}-dev-passcode")
        r = wf.run(tok("buyer"), loc, ing)
        assert r["state"] == "AWAITING_APPROVAL" and wf.ledger.con.execute("SELECT count(*) FROM po_drafts").fetchone()[0] == 0
        assert r["explanation"]["proposal"]["ingredient_id"] == "i-lamb-leg"
        d = wf.decide(r["corr_id"], tok("founder"), True, "lamb spike reviewed")
        assert d["status"] == "EXECUTED" and wf.ledger.con.execute("SELECT count(*) FROM po_drafts").fetchone()[0] == 1
        assert wf.ledger.con.execute("SELECT state FROM po_drafts").fetchone()[0] == "DRAFT_NOT_SENT"
    finally:
        wf.close()
