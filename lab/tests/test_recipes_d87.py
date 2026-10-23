"""D-87 quality gates that need no warehouse: prices, beer targets, D-54, recipe->ingredient relationships, reproducible costs, frozen v1 record, workflow and approval authority.
All costs are PLANNING ASSUMPTIONS; nothing here says a dish was cooked or a price was quoted."""
import json
import re

import pytest

from nasha_lab.recipes import beer_costing, bom, costing, model, optimize, pricing, suppliers

from nasha_lab.recipes.store import HUMAN_APPROVERS, RecipeStore, WorkflowError
from nasha_lab.warehouse.procurement import ProcurementError, ProcurementStore

ROOT = model.ROOT
RECIPES, MASTER, CFG = model.load_recipes(), model.load_master(), pricing.load_config()
DISHES = {k: v for k, v in RECIPES.items() if v["kind"] == "dish"}
FOUNDER_APPETIZERS = ["Chicken 65 Totopos", "Mango Habanero Gobi", "Tandoori Paneer Quesadilla Bites", "Masala Street Corn", "Goan Peri-Peri Wings", "Crispy Aloo Chaat Nachos"]
FOUNDER_MAINS = ["Butter Chicken Quesadilla", "Chicken Tikka Tacos", "Kerala Coconut Fish Tacos", "Tandoori Lamb Tacos", "Paneer Makhani Pizza", "Goan Chicken Vindaloo Pizza", "Nawaabi Enchiladas", "Hyderabadi Birria-Style Chicken Tacos"]


def test_menu_prices_are_the_approved_concept_prices():
    assert CFG["prices_usd"] == {"beer_glass": 9.00, "beer_pitcher": 31.00, "appetizer": 13.50, "main": 18.50}
    assert CFG["config_id"] == pricing.V3 and "NOT AN OPERATING MENU" in CFG["status"]
    for r in DISHES.values():
        assert pricing.dish_price_cents(CFG, r["id"]) == {"appetizer": 1350, "main": 1850}[r["menu_category"]]
    for b in CFG["beers"]:
        assert (b["glass_usd"], b["pitcher_usd"]) == (9.0, 31.0)


def test_beer_target_abvs_match_the_beer_specifications_and_stay_provisional():
    specs = {b["id"]: b for b in json.loads((ROOT / "beer/specs/beer_specs.json").read_text())["beers"]}
    got = {b["id"]: b for b in CFG["beers"]}
    assert got["badshah"]["target_abv_pct"] == specs["badshah"]["target_abv_pct"] == 4.7
    assert got["amba-haze"]["target_abv_pct"] == specs["amba-haze"]["target_abv_pct"] == 6.0
    assert all("NOT BREWED OR TESTED" in b["status"] and "PROVISIONAL" in b["status"] for b in CFG["beers"])


def test_serving_volumes_are_exact_provisional_conversions_from_fluid_ounces():
    v = CFG["serving_volumes"]
    assert v["oz_to_ml"] == 29.5735295625                                          # exact definition of a US fluid ounce
    assert (v["glass"]["fl_oz"], v["pitcher"]["fl_oz"]) == (16, 60)
    assert beer_costing.serving_ml(CFG, "glass") == pytest.approx(473.176473, abs=1e-6)
    assert beer_costing.serving_ml(CFG, "pitcher") == pytest.approx(1774.41177375, abs=1e-6)
    assert abs(beer_costing.serving_ml(CFG, "glass") - 473.176) < 1e-3              # matches the founder's figure
    assert abs(beer_costing.serving_ml(CFG, "pitcher") - 1774.414) < 3e-3          # founder's rounded figure differs by 0.002 mL
    assert beer_costing.pitcher_vs_glass(CFG)["glasses_per_pitcher"] == pytest.approx(3.75)
    for k in ("glass", "pitcher"):
        assert "PROVISIONAL" in v[k]["status"] and "physical validation" in v[k]["status"]


def test_beer_costs_are_labelled_preliminary_and_internally_consistent():
    rows = beer_costing.all_rows(CFG)
    assert len(rows) == 12 and all("NOT A VERIFIED PRODUCTION COST" in r["status"] for r in rows)
    for b in ("badshah", "amba-haze"):
        g, p = (beer_costing.economics(b, s, "base", CFG) for s in ("glass", "pitcher"))
        assert p["cost_ex_labor"] / g["cost_ex_labor"] == pytest.approx(3.75)             # cost scales with volume
        assert g["margin_ex_labor_pct"] == pytest.approx(1 - g["cost_ex_labor"] / 9.0) and p["margin_ex_labor_pct"] == pytest.approx(1 - p["cost_ex_labor"] / 31.0)
        lo, ba, hi = (beer_costing.economics(b, "glass", s, CFG)["cost_ex_labor"] for s in ("low", "base", "high"))
        assert lo < ba < hi
        assert g["cost_with_brew_labor"] > g["cost_ex_labor"]
    assert "excise" in " ".join(beer_costing.assumptions()["excluded"])


def test_all_founder_candidates_are_accounted_for_and_classified():
    names = {r["name"]: r for r in DISHES.values()}
    for n in FOUNDER_APPETIZERS + FOUNDER_MAINS:
        if n == "Masala Street Corn":
            assert "Chaat Elote" in names and "Masala Street Corn" not in names     # name retained; alternate development name only
            assert names["Chaat Elote"]["menu_category"] == "appetizer" and "alternate development name" in names["Chaat Elote"]["classification_note"]
        elif n == "Butter Chicken Quesadilla":
            assert any(x.startswith("Butter Chicken") for x in names)
        else:
            assert n in names, n
            assert names[n]["menu_category"] == ("appetizer" if n in FOUNDER_APPETIZERS else "main")
    assert len(DISHES) == 15 and len(RECIPES) - len(DISHES) == 12


def test_no_beef_or_pork_anywhere_in_ingredients_or_recipes():
    for ing in MASTER.values():
        assert not model.D54.search(ing["name"]), ing["name"]
    for r in RECIPES.values():
        used = [ln.get("ingredient") for ln in model.iter_lines(r) if "ingredient" in ln]
        assert all(not model.D54.search(MASTER[i]["name"]) for i in used)
        if r["kind"] == "dish":
            assert r["dietary"]["d54_compliant"] is True and r["dietary"]["halal_claim"] is False
    assert model.validate() == []


def test_recipe_to_ingredient_relationships_are_closed_and_boms_match_costs():
    for rid in DISHES:
        flat = bom.explode(rid, RECIPES, MASTER)
        assert flat and all(i in MASTER and not MASTER[i].get("derived_from") for i in flat)
        # independent identity: sum(AP qty x base price) == recipe cost (cost = qty / yield x price, BOM = qty / yield)
        assert sum(q * MASTER[i]["price"]["base"] for i, q in flat.items()) == pytest.approx(costing.recipe_cost(rid, RECIPES, MASTER, "base")["total"], rel=1e-9)


def test_cost_calculations_are_reproducible_and_scenario_ordered():
    a, b = pricing.menu_economics(CFG), pricing.menu_economics(CFG)
    assert a == b
    for rid in DISHES:
        lo, ba, hi = (pricing.economics(rid, CFG, s)["food_cost"] for s in ("low", "base", "high"))
        assert lo < ba < hi


def test_cost_arithmetic_checked_by_hand_for_one_sub_recipe():
    r = RECIPES["raita-crema"]
    by_hand = sum(l["qty"] * costing.TO_PURCHASE[l["unit"]] / (MASTER[l["ingredient"]]["yield_pct"] / 100) * MASTER[l["ingredient"]]["price"]["base"] for l in r["lines"])
    assert costing.recipe_cost("raita-crema", RECIPES, MASTER)["total"] == pytest.approx(by_hand)
    # hung curd is priced from yogurt / 50% yield
    assert costing.unit_price(MASTER["i-hung-curd"], MASTER, "base") == pytest.approx(MASTER["i-yogurt"]["price"]["base"] / 0.5)


def test_economics_identities_and_inflation_sensitivity():
    for rid in DISHES:
        e = pricing.economics(rid, CFG)
        assert e["gross_profit"] == pytest.approx(e["price"] - e["food_cost"] - e["consumables"])
        assert e["contribution_margin"] == pytest.approx(e["gross_profit"] - e["direct_labor"])
        assert e["food_cost"] == pytest.approx(e["ingredient_cost"] * 1.05)
    t = pricing.inflation_table("tandoori-lamb-tacos", CFG)
    assert [x["all"] for x in t] == sorted(x["all"] for x in t) and t[3]["protein_only"] > t[0]["protein_only"]
    assert t[3]["dairy_only"] < t[3]["protein_only"]                         # lamb is protein-dominated


def test_estimates_are_never_labelled_as_quotes_or_results():
    assert all(q["price_class"] == "SYNTHETIC_QUOTE" for q in suppliers.load()["quotes"])
    assert all(i["price"]["low"] <= i["price"]["base"] <= i["price"]["high"] for i in MASTER.values() if "price" in i)
    for r in RECIPES.values():
        assert "NOT COOKED OR TASTED" in r["status"]
    assert suppliers.generate() == suppliers.load()                             # committed quotes are exactly reproducible


def test_historical_placeholder_prices_are_frozen_and_distinct_from_v2():
    frozen = json.loads((pricing.PRICING / "price-v1-placeholder.json").read_text())
    assert "FROZEN" in frozen["status"] and frozen["items"] == pricing.v1_catalog_snapshot()
    assert frozen["items"]["M01"]["price_cents"] == 1400 and frozen["items"]["M01"]["price_cents"] != pricing.dish_price_cents(CFG, "chicken-65-totopos")


def test_allergen_derivation_covers_the_new_dishes():
    d = lambda r: model.derived_allergens(r, RECIPES, MASTER)
    assert "tree_nut" in d("nawaabi-enchiladas") and "fish" in d("kerala-coconut-fish-tacos") and "wheat" in d("paneer-makhani-pizza")
    assert "wheat" not in d("chicken-65-totopos")
    for r in DISHES.values():
        if r["dietary"]["vegetarian"]:
            assert all(MASTER[i]["vegetarian"] in (True, "check") for i in bom.explode(r["id"], RECIPES, MASTER)), r["id"]


def test_recipe_versions_are_immutable_and_only_humans_approve():
    s = RecipeStore()
    r = dict(DISHES["goan-peri-peri-wings"])
    s.create_draft(r, "agent-1", "agent")
    with pytest.raises(WorkflowError):
        s.create_draft(r, "agent-1", "agent")                                  # same version cannot be edited in place
    s.submit(r["id"], r["version"], "agent-1", "agent")
    with pytest.raises(WorkflowError):
        s.approve(r["id"], r["version"], "agent-1", "agent", "ok")
    with pytest.raises(WorkflowError):
        s.approve(r["id"], r["version"], "chef-1", "head_chef", "  ")          # comment required
    s.approve(r["id"], r["version"], "chef-1", "head_chef", "reviewed desk estimate only")
    assert s.status(r["id"], r["version"]) == "approved" and "head_chef" in HUMAN_APPROVERS
    assert s.verify_audit()[0]
    s.con.execute("UPDATE audit SET detail='tampered' WHERE seq=1"); s.con.commit()
    assert not s.verify_audit()[0]


def test_procurement_proposals_need_human_approval_and_never_send():
    s = ProcurementStore()
    reco = {"reco_id": "R-1", "supplier_id": "S01", "ingredient_id": "i-chicken-thigh", "location_id": "L01", "order_qty": 15.0, "unit": "kg", "est_cost_usd": 111.0, "price_class": "SYNTHETIC_QUOTE", "inputs_hash": "abc"}
    s.propose(reco, "ops-ai-agent", "agent")
    for who, role in (("ops-ai-agent", "agent"), ("ops-ai-agent", "founder"), ("x", "analyst")):
        with pytest.raises(ProcurementError):
            s.approve("R-1", who, role, "go")
    assert s.po_drafts() == [] and s.status("R-1") == "PROPOSED"
    po = s.approve("R-1", "founder-1", "founder", "approved for draft")
    assert s.po_drafts()[0][0] == po and s.po_drafts()[0][4] == "DRAFT_NOT_SENT"
    assert s.verify_audit()[0]
    with pytest.raises(ProcurementError):
        s.propose({**reco, "reco_id": "R-2", "price_class": "MADE_UP"}, "agent", "agent")


def test_menu_research_dossier_lists_every_candidate_and_proposed_changes():
    doc = (ROOT / "docs/menu-research/MENU-CANDIDATE-RESEARCH-D87.md").read_text()
    for n in FOUNDER_APPETIZERS + FOUNDER_MAINS:
        assert n in doc, n
    assert "web-search snippet" in doc.lower() and "not additions" in doc.lower() and "No beef or pork" in doc


def test_paneer_tikka_taco_is_a_main_at_18_50():
    r = DISHES["paneer-tikka-taco"]
    assert r["menu_category"] == "main" and pricing.dish_price_cents(CFG, "paneer-tikka-taco") == 1850


def test_goat_birria_is_retired_from_menu_pool_bom_quotes_and_pricing_but_preserved_as_history():
    assert "goat-birria" not in RECIPES and "goat-birria-braise" not in RECIPES
    retired = model.load_retired()
    assert set(retired) == {"goat-birria", "goat-birria-braise"} and all(r["menu_status"] == "retired" and "founder approval" in r["lifecycle"] for r in retired.values())
    assert "goat-birria" not in bom.SIM_ITEM_TO_RECIPE.values() and "M03" not in CFG["menu_item_mapping_to_sim"]
    assert CFG["retired_items"][0]["recipe_id"] == "goat-birria" and "M03" in CFG["sim_items_without_v2_price"]
    assert all(q["ingredient_id"] != "i-goat-bone-in" for q in suppliers.load()["quotes"])
    used = {ln["ingredient"] for r in RECIPES.values() for ln in model.iter_lines(r) if "ingredient" in ln}
    assert "i-goat-bone-in" not in used and MASTER["i-goat-bone-in"].get("retired")
    assert all(e["id"] != "goat-birria" for e in pricing.menu_economics(CFG))
    decisions = (ROOT / "docs/decisions/DECISIONS.md").read_text()
    assert "Goat Birria" in decisions and "D-88" in decisions and "not to be reintroduced without founder approval" in decisions.lower().replace("do not reintroduce", "not to be reintroduced")


def test_every_dish_with_allergens_has_cross_contact_precautions_and_no_safety_guarantee():
    for r in DISHES.values():
        assert not r["allergens_declared"] or r["cross_contact_precautions"], r["id"]
        assert "No allergen-free or allergy-safe guarantee" in r["allergen_claim"] and "operational validation" in r["allergen_claim"]
    n = DISHES["nawaabi-enchiladas"]
    assert "tree_nut" in n["allergens_declared"] and "MAJOR allergen" in n["allergen_notes"]
    assert any("dedicated blender" in p for p in n["cross_contact_precautions"]) and "i-cashew" in bom.explode("nawaabi-enchiladas", RECIPES, MASTER)
    assert "tree_nut" in model.derived_allergens("nawaabi-enchiladas", RECIPES, MASTER)


def test_tandoori_lamb_levers_keep_the_original_scenario_and_respect_the_quality_floor():
    rows = optimize.levers("tandoori-lamb-tacos", CFG)
    base = pricing.economics("tandoori-lamb-tacos", CFG)
    assert rows[0]["lever"] == "original" and rows[0]["margin_delta_pts"] == 0 and rows[0]["gross_margin_pct"] == pytest.approx(base["gross_margin_pct"]) and round(base["gross_margin_pct"] * 100, 1) == 69.4
    assert {r["lever"] for r in rows} >= {"portion", "yield", "supplier", "waste"}
    below = [r for r in rows if r["lever"] == "portion" and "x0.90" in r["setting"]]
    assert below and "BELOW QUALITY FLOOR" in below[0]["quality_impact"] and "do not apply" in below[0]["quality_impact"]
    assert any(r["lever"] == "yield" and r["margin_delta_pts"] > 0 for r in rows) and any(r["lever"] == "supplier" for r in rows)
    assert DISHES["tandoori-lamb-tacos"] == model.load_recipes()["tandoori-lamb-tacos"]            # levers never edit the recipe
    g = optimize.protein_grams_for_margin("tandoori-lamb-tacos", 70)
    assert 0.9 < g < 1.0 and pricing.economics("tandoori-lamb-tacos", CFG)["meets_target_margin"] is False


def test_supplier_price_shock_never_lowers_cost_and_hits_dependent_dishes():
    rows = optimize.supplier_sensitivity(0.15, CFG)
    assert rows and all(r["delta_pct"] >= -1e-12 for r in rows)
    hit = [r for r in rows if r["delta_pct"] > 0.01]
    assert hit and all(r["share_of_cost"] > 0 for r in hit)
