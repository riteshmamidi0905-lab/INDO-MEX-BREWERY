#!/usr/bin/env python3
"""Authoring script for the D-87 candidate recipes (PRELIMINARY, NOT COOKED OR TASTED). Writes food/recipes/v1/*.v1.json, extends the ingredient master and
back-fills menu metadata on the earlier dishes. Idempotent: re-running rewrites the same files.   python3 lab/tools/build_candidate_recipes.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "food/recipes/v1"
MASTER = ROOT / "food/recipes/ingredients/ingredient-master.json"
LABEL = "Conceptual food visualization — AI-generated concept art, not a photograph and not a tested menu item."
STATUS = "PRELIMINARY ESTIMATE — NOT COOKED OR TASTED"
EST = "All quantities, yields, times and costs are preliminary estimates until a person cooks and measures them. Nothing here has been cooked or tasted."

NEW_INGREDIENTS = [   # id, name, category, unit, yield, allergens, veg, (low, base, high), note
    ("i-lamb-leg", "Lamb leg, boneless, trimmed", "protein", "kg", 75, [], False, (13, 15.5, 19), "trim loss ~25% (fat, sinew); supplier statement required"),
    ("i-white-fish", "Firm white fish fillet, skinless (species TBD: mahi/redfish/cod)", "protein", "kg", 100, ["fish"], False, (9.5, 12, 15), "species and sourcing are open decisions (menu matrix item 7)"),
    ("i-chicken-wing", "Chicken wing, bone-in, split (as purchased weight)", "protein", "kg", 100, [], False, (3.6, 4.6, 6.2), "cost on purchased weight; cooked yield about 60% by weight (bone and fry loss)"),
    ("i-coconut-milk", "Coconut milk, unsweetened", "pantry", "l", 100, [], True, (3.0, 3.8, 4.8), "coconut is not on the current US FDA major-allergen list; check supplier labelling"),
    ("i-potato", "Potato, waxy", "produce", "kg", 85, [], True, (1.0, 1.4, 1.9), "peel loss ~15%"),
    ("i-wheat-flour", "Wheat flour, bread/high-protein", "grain", "kg", 100, ["wheat"], True, (0.8, 1.0, 1.4), ""),
    ("i-yeast-dry", "Dry yeast", "pantry", "kg", 100, [], True, (7, 9, 12), ""),
    ("i-mozzarella", "Low-moisture mozzarella", "dairy", "kg", 100, ["milk"], True, (6.5, 8.5, 11), "check rennet type for the vegetarian claim"),
    ("i-cashew", "Cashew, raw pieces", "pantry", "kg", 100, ["tree_nut"], True, (11, 14, 18), "tree-nut allergen: Nawaabi sauce only"),
    ("i-chile-arbol", "Chile de árbol, dried", "spice", "kg", 80, [], True, (18, 22, 28), ""),
    ("i-tamarind-paste", "Tamarind paste", "pantry", "kg", 100, [], True, (5, 7, 9), ""),
    ("i-mustard-seed", "Black mustard seed", "spice", "kg", 100, [], True, (5, 7, 9), ""),
    ("i-black-pepper", "Black pepper, ground", "spice", "kg", 100, [], True, (14, 18, 24), ""),
    ("i-cardamom", "Green cardamom, ground", "spice", "kg", 100, [], True, (55, 80, 110), ""),
    ("i-saffron", "Saffron threads", "spice", "kg", 100, [], True, (2500, 3500, 5000), "used in fractions of a gram"),
    ("i-cabbage", "Green cabbage", "produce", "kg", 85, [], True, (1.0, 1.5, 2.2), "core/outer-leaf loss ~15%"),
]
SUPPLIER_CAT = {"protein": "S01", "produce": "S03", "dairy": "S04", "grain": "S05", "pantry": "S05", "spice": "S05", "oil": "S05", "aromatic": "S03", "herb": "S03"}


def L(i, q, u="g", prep=None):
    d = {"ingredient": i, "qty": q, "unit": u}
    if prep:
        d["prep"] = prep
    return d


def S(s, q, prep=None):
    d = {"subrecipe": s, "qty": q, "unit": "g"}
    if prep:
        d["prep"] = prep
    return d


def sub(rid, name, batch, lines, method, sauce_spec, safety, allergens, evidence, shelf="3 days at ≤ 5 °C (ASSUMPTION: set by a food-safety professional)"):
    return {"id": rid, "version": "1.0", "kind": "subrecipe", "name": name, "status": STATUS, "batch_yield_g": batch, "shelf_life_note": shelf, "lines": lines, "method": method,
            "sauce_spec": sauce_spec, "food_safety": safety, "allergens_declared": allergens, "test_variables": [], "evidence": evidence, "estimates_label": EST}


SUBS = [
    sub("peri-peri-sauce", "Goan-leaning peri-peri sauce (chile, garlic, lemon, vinegar)", 520,
        [L("i-chile-arbol", 30, "g", "soaked 15 min in hot water, drained"), L("i-garlic", 40), L("i-lemon-juice", 60, "ml"), L("i-cider-vinegar", 40, "ml"), L("i-oil-neutral", 80, "ml"),
         L("i-tomato-passata", 150), L("i-salt", 8), L("i-oregano-mx", 2), L("i-jaggery", 15), L("i-water", 0.1, "l")],
        ["Soak the chiles, drain, blend with garlic, passata, lemon, vinegar and water until smooth.", "Cook in the oil 8-10 min, stirring, until the raw-garlic edge is gone and the sauce coats a spoon; season.", "Cool in a shallow pan (two-stage cooling) and chill."],
        {"texture": "pourable, clings", "acid": "medium-high", "heat": "2-3", "use": "toss for wings"}, ["Two-stage cooling: 57→21 °C within 2 h, then to ≤ 5 °C within a further 4 h.", "Date-mark and discard per policy."],
        [], ["Practice: peri-peri (piri-piri) is a chile-garlic-citrus/vinegar sauce associated with Portuguese-influenced cooking including Goa (web-search snippet level only; primary sources not retrieved). NASHA composition is new."]),
    sub("vindaloo-sauce", "Chicken vindaloo-style sauce (vinegar-chile-spice, no pork)", 640,
        [L("i-onion-red", 200), L("i-ginger", 30), L("i-garlic", 40), L("i-red-chilli-powder", 25), L("i-guajillo", 20, "g", "toasted, soaked, drained"), L("i-cumin-ground", 6), L("i-turmeric", 2),
         L("i-black-pepper", 3), L("i-clove", 1), L("i-cinnamon", 2), L("i-cider-vinegar", 120, "ml"), L("i-jaggery", 12), L("i-oil-neutral", 60, "ml"), L("i-tomato-passata", 100),
         L("i-salt", 10), L("i-water", 0.15, "l")],
        ["Blend onion, ginger, garlic, toasted chiles, spices and vinegar to a paste.", "Cook the paste in oil 15 min, add passata, jaggery, salt and water; simmer 15 min to a thick sauce.", "Cool in shallow pans; chill. Chicken is added and braised separately in the dish recipe."],
        {"texture": "thick, jammy", "acid": "high (vinegar)", "heat": "3", "use": "braise base for pizza topping"}, ["Two-stage cooling within 2 h + 4 h.", "Date-mark and discard per policy."],
        [], ["Practice: vindaloo derives from Portuguese carne de vinha d'alhos; the Goan version is a vinegar-and-chile marinade/braise traditionally with pork (web-search snippet level). NASHA uses CHICKEN ONLY (D-54: no pork)."]),
    sub("nawaabi-enchilada-sauce", "Nawaabi enchilada sauce (cashew-cream, tomato, mild chile, saffron)", 900,
        [L("i-cashew", 90, "g", "soaked 30 min in hot water"), L("i-cream", 0.2, "l"), L("i-onion-white", 150), L("i-ginger-garlic-paste", 30), L("i-tomato-passata", 250), L("i-ancho", 25, "g", "toasted, soaked"),
         L("i-butter", 30), L("i-cardamom", 1), L("i-kasuri-methi", 2), L("i-saffron", 0.1, "g", "bloomed in a spoon of warm water"), L("i-salt", 8), L("i-water", 0.12, "l")],
        ["Sweat the onion in butter; add ginger-garlic paste and cardamom; add passata and ancho and simmer 15 min.", "Blend with the soaked cashews, cream and water until silky; pass through a sieve.", "Return to heat, add saffron and kasuri methi, adjust salt; cool and chill."],
        {"texture": "silky, nappe", "acid": "low-medium", "heat": "1", "richness": "high", "use": "enchilada sauce"}, ["Two-stage cooling within 2 h + 4 h.", "TREE NUT: cashew. Dedicated utensils and allergen label."],
        ["milk", "tree_nut"], ["Practice: Mughlai/'nawaabi' gravies use a cashew-cream base (web-search snippet level). Enchilada sauce structure is Mexican. The combination is a NASHA proposal."]),
    sub("kerala-coconut-sauce", "Kerala-leaning coconut crema (coconut, curry leaf, tamarind, lime)", 520,
        [L("i-coconut-milk", 0.4, "l"), L("i-green-chile", 20), L("i-ginger", 20), L("i-curry-leaf", 5, "g", "fried 15 s in the oil"), L("i-turmeric", 2), L("i-mustard-seed", 3, "g", "popped in the oil"),
         L("i-tamarind-paste", 20), L("i-lime-juice", 25, "ml"), L("i-oil-neutral", 20, "ml"), L("i-salt", 6)],
        ["Pop mustard seed and fry curry leaf in the oil; add ginger and chile, then turmeric.", "Add coconut milk and tamarind; simmer gently 10 min (do not boil hard); cool.", "Blend smooth, add lime and salt; chill."],
        {"texture": "pourable crema", "acid": "medium", "heat": "1-2", "use": "fish taco sauce"}, ["Two-stage cooling within 2 h + 4 h.", "Check coconut-milk labelling; no allergen-free claim."],
        [], ["Practice: Kerala fish dishes combine coconut milk, tamarind/kokum, turmeric, chile and curry leaf (web-search snippet level). Taco format is a NASHA composition."]),
    sub("kachumber-slaw", "Kachumber-style cabbage slaw", 220,
        [L("i-cabbage", 150, "g", "finely shredded"), L("i-onion-red", 40), L("i-cilantro", 10), L("i-lime-juice", 20, "ml"), L("i-chaat-masala", 2), L("i-salt", 3)],
        ["Shred the cabbage, toss with salt and rest 10 min, squeeze lightly.", "Add onion, cilantro, lime and chaat masala; make small batches (hold ≤ 4 h for crunch)."],
        {"texture": "crunchy", "acid": "high", "heat": "0", "use": "fish taco acid and crunch"}, ["Wash produce; hold at ≤ 5 °C."], [], ["Menu matrix item 7 specifies a cabbage-lime acid."], shelf="same day (ASSUMPTION)"),
    sub("pizza-dough", "Pizza dough (direct, cold-ferment)", 1020,
        [L("i-wheat-flour", 600), L("i-water", 0.38, "l"), L("i-yeast-dry", 4), L("i-salt", 12), L("i-oil-neutral", 30, "ml")],
        ["Mix to a smooth dough, bulk 1 h, divide into 230 g balls, cold-ferment 24 h at ≤ 5 °C, temper 1 h before stretching."],
        {"texture": "elastic", "use": "pizza base, 230 g per pizza"}, ["Keep balls refrigerated; discard after 72 h (ASSUMPTION)."], ["wheat"], ["Standard bakery practice; hydration about 63% is an ASSUMPTION to be tested in the NASHA oven."], shelf="72 h at ≤ 5 °C (ASSUMPTION)"),
]

PAIR = {   # per-dish beer hypotheses (NOT sensory tested)
    "bad": "BADSHAH hefeweizen (target ABV 4.7%)", "amba": "AMBA HAZE (target ABV 6.0%)"}


def pairing(bad, bad_risk, amba, amba_risk):
    tag = "PAIRING HYPOTHESIS - NOT SENSORY TESTED; the beer does not exist yet"
    return [{"beer": PAIR["bad"], "hypothesis": bad, "risk": bad_risk, "status": tag}, {"beer": PAIR["amba"], "hypothesis": amba, "risk": amba_risk, "status": tag}]


def photo(hero, show, not_show, realism):
    return {"hero": hero, "must_show": show, "must_not_show": not_show + ["any text, logo or menu card"], "realism_notes": realism, "label": LABEL}


def dish(id_, name, cat, role, method, portion, comps, steps, params, plating, equip, safety, stations, prep, svc, fry, pair, ph, allergens, notes, veg, evidence, research, cls_note, status_note="candidate"):
    return {"id": id_, "name": name, "menu_role": role, "menu_category": cat, "menu_status": status_note, "classification_note": cls_note, "cooking_method": method,
            "portion": portion, "components": comps, "sauces": [l["subrecipe"] for c in comps for l in c["lines"] if "subrecipe" in l], "method": {"steps": steps, "critical_parameters": params},
            "plating": plating, "equipment": equip, "food_safety": safety,
            "workflow": {"stations": stations, "labor_minutes_per_portion": {"prep": prep, "service": svc}, "fryer_load": fry, "capacity_note": "estimate; measure at T1"},
            "pairing": pair, "photography": ph, "allergens_declared": allergens, "allergen_notes": notes, "evidence": evidence, "research": research,
            "version": "1.0", "kind": "dish", "status": STATUS, "development_status": "DRAFT v1.0 — desk estimate; kitchen test not started; no costed purchase records",
            "target_gross_margin_pct": 70, "estimates_label": EST, "dietary": {"vegetarian": veg, "d54_compliant": True, "halal_claim": False, "notes": "no beef or pork ingredient; supplier statements required"}, "photography_label": LABEL}


def cp(txt):  # standard poultry safety lines
    return [f"{txt} to 74 °C (165 °F), probed in the thickest piece.", "Raw-protein board/utensils separated; hand-wash; marinate at ≤ 4 °C, discard marinade.", "Hot-hold ≥ 57 °C (135 °F) or discard within 2 hours (policy to be set by a food-safety professional)."]


R_PRACTICE = "RESEARCHED PRACTICE = documented regional preparation; NASHA COMBINATION = proposal not found in a traditional source. Sources are web-search snippets; primary documents were not retrieved (WebFetch unavailable)."

DISHES = [
    dish("tandoori-paneer-quesadilla-bites", "Tandoori Paneer Quesadilla Bites", "appetizer", "Shareable small plate", "Marinate, griddle paneer; press quesadilla on a hot comal; cut in 8 triangles",
         {"description": "1 shareable plate (8 triangles)", "targets": {"paneer": "110 g", "flour tortillas": "2 x 25 cm halves", "oaxaca": "50 g", "dips": "hari 30 g + raita-crema 25 g"}, "construction": "folded half-moon quesadilla pressed, cut in 8"},
         [{"name": "Tandoori paneer", "lines": [L("i-paneer", 110, "g", "cut 1.5 cm cubes"), L("i-hung-curd", 25), L("i-red-chilli-powder", 2), L("i-ginger-garlic-paste", 5), L("i-garam-masala", 1), L("i-kasuri-methi", 0.5), L("i-salt", 1.2), L("i-lemon-juice", 4, "ml"), L("i-oil-neutral", 8, "ml")]},
          {"name": "Quesadilla", "lines": [L("i-flour-tortilla-25", 2, "each"), L("i-cheese-oaxaca", 50), L("i-oil-neutral", 5, "ml", "comal allocation")]},
          {"name": "Dips and garnish", "lines": [S("hari-salsa-verde", 30), S("raita-crema", 25), S("pickled-red-onion", 10), L("i-cilantro", 1)]}],
         ["Marinate paneer 2-4 h at ≤ 4 °C (acid ≤ 30 min per paneer texture note).", "Sear paneer on a very hot comal until charred spots form.", "Fill tortilla with oaxaca and paneer, press 2-3 min per side until crisp and melted.", "Rest 30 s, cut in 8, plate with dips."],
         {"comal_C": "about 220 (chef decision)", "press_time": "2-3 min/side"}, "Black stoneware plate, triangles fanned, dips in two small bowls, pickled onion heap.",
         ["Comal/flat-top", "Press or weighted pan", "Cold storage ≤ 4 °C"], ["Pasteurized dairy only (supplier statement).", "Hold assembled-unfried quesadillas ≤ 4 °C; discard marinade."], ["cold prep", "comal"], 3.0, 2.5, "none",
         pairing("Carbonation and soft body cut cheese richness; clove/banana esters may echo tandoori spice.", "Banana ester vs charred paneer.", "Mango-citrus hop aroma lifts the charred spice.", "Bitterness stacks with chile heat."),
         photo("Overhead, black stoneware, warm side light.", ["pressed golden triangles with visible paneer and melted cheese", "green and cream dips", "pink pickled onion"], ["pizza-style topping", "melted cheese sauce pool"], "Crisp tortilla edges with char spots; cheese pulls only if hot."),
         ["milk", "wheat"], "Milk (paneer, cheese, yogurt, crema); wheat (tortilla). Comal shared with other items; no allergen-free claim.", True,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#6 Paneer Tikka Taco, #10, #11 flavour logic)", "food/SAUCE-SYSTEM.md (hari, raita-crema)"],
         {"practice": "Paneer tikka (marinated, tandoor-char) is an established North Indian preparation; quesadilla is a Mexican format.", "nasha_combination": "Paneer tikka inside a pressed quesadilla cut into bites is a NASHA proposal.", "note": R_PRACTICE},
         "Appetizer per the founder candidate list; shares paneer, hari and raita with the approved Paneer Tikka Taco (cross-utilization)."),
    dish("goan-peri-peri-wings", "Goan Peri-Peri Wings", "appetizer", "Shareable small plate", "Dry-brine wings, fry in two stages to 74 °C, toss in peri-peri sauce",
         {"description": "1 shareable plate (about 6 split wing pieces)", "targets": {"wings (as purchased)": "300 g", "peri-peri sauce": "45 g", "raita-crema": "30 g"}, "construction": "wings tossed in sauce, crema on the side"},
         [{"name": "Wings", "lines": [L("i-chicken-wing", 300), L("i-salt", 2), L("i-turmeric", 0.3), L("i-red-chilli-powder", 1.5), L("i-cornflour", 8), L("i-oil-neutral", 22, "ml", "fry allocation")]},
          {"name": "Sauce and garnish", "lines": [S("peri-peri-sauce", 45), S("raita-crema", 30), S("pickled-red-onion", 10), L("i-lime", 0.17, "each"), L("i-cilantro", 1)]}],
         ["Dry-brine wings 2-12 h at ≤ 4 °C; pat dry; dust with cornflour just before frying.", "Fry at about 175 °C 9-11 min until deep golden; probe to 74 °C.", "Toss in warm peri-peri sauce; plate with crema, onion and lime."],
         {"fry_temp_C": "about 175 (chef decision)", "core_C": "74 minimum"}, "Black stoneware plate, wings piled, crema pool at the edge, lime wedge.",
         ["Fryer", "Probe thermometer", "Toss bowls"], cp("Cook wings"), ["cold prep", "fryer", "plating"], 3.0, 3.0, "H",
         pairing("Carbonation cleans fry fat; soft wheat body tempers chile.", "Thin body against heavy sauce.", "Fruity hop aroma against garlic-lemon heat.", "IBU amplifies chile heat."),
         photo("Three-quarter angle, warm side light.", ["glossy red-orange sauced wings", "lime and cilantro", "white crema pool"], ["blue-cheese dip", "celery sticks (not in recipe)"], "Sauce should coat, not pool."),
         ["milk"], "Milk (crema). Fryer shared; no allergen-free claim.", False,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#4 Hefe-brined Wings: related; this candidate has a different sauce and no beer brine)"],
         {"practice": "Peri-peri/piri-piri chicken is an established Portuguese-influenced preparation (Goa shares the heritage).", "nasha_combination": "Peri-peri wings with raita-crema and pickled onion are a NASHA proposal.", "note": R_PRACTICE},
         "Overlaps approved pool item #4 (Hefe-brined Wings) in format; differs in sauce. Not a replacement; proposed as a sauce variant."),
    dish("crispy-aloo-chaat-nachos", "Crispy Aloo Chaat Nachos", "appetizer", "Vegetarian shareable", "Boil then fry potato cubes; fry totopos; assemble with chutneys, hari, raita-crema and sev",
         {"description": "1 shareable plate", "targets": {"potato cubes": "160 g raw", "totopos": "about 60 g (55 g raw tortilla)", "sev": "6 g"}, "construction": "chips on a board with crisp potato, sauces drizzled at the last moment"},
         [{"name": "Crisp aloo", "lines": [L("i-potato", 160), L("i-oil-neutral", 25, "ml", "fry allocation"), L("i-chaat-masala", 2.5), L("i-red-chilli-powder", 0.5), L("i-salt", 1)]},
          {"name": "Totopos", "lines": [L("i-corn-tortilla", 55), L("i-salt", 0.8), L("i-oil-neutral", 15, "ml", "fry allocation")]},
          {"name": "Chutney and garnish", "lines": [L("i-tamarind-paste", 8), L("i-jaggery", 5), S("hari-salsa-verde", 25), S("raita-crema", 25), S("pickled-red-onion", 10), L("i-sev", 6), L("i-cilantro", 2), L("i-lime", 0.17, "each")]}],
         ["Boil potato cubes until just tender, drain and air-dry; chill.", "Fry cubes at 175 °C until crisp; toss with chaat masala and salt.", "Fry totopos last; assemble with chutneys, hari, raita-crema, onion, sev; plate in 60 s."],
         {"fry_temp_C": "about 175", "plate_time_s": "60"}, "Chips and crisp potato on a board; sauces drizzled in lines, not a cheese blanket.",
         ["Fryer", "Steam/boil pot", "Cold storage"], ["Cool boiled potato quickly (two-stage) if held; fry from chilled.", "Fryer oil management; shared fryer = no allergen-free claim."], ["cold prep", "fryer", "plating"], 3.5, 2.5, "H",
         pairing("Carbonation and wheat softness relieve fried starch.", "Banana vs tamarind.", "Tropical hop aroma echoes tamarind-mango sweetness.", "Sweetness stacking with chutney."),
         photo("Overhead, black board.", ["crisp golden potato cubes among thick chips", "green, white and brown sauce lines", "fine sev"], ["melted cheese sauce, jalapeño rings, sour-cream blobs (GENERIC_NACHOS is a D-74 failure gate)"], "Chips must look thick and sturdy."),
         ["milk"], "Milk (crema). Fryer shared; check sev (besan) and tamarind labels. No allergen-free claim.", True,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#1 totopo logic; #2 Chaat Elote layering)", "food/SAUCE-SYSTEM.md"],
         {"practice": "Aloo tikki/aloo chaat with tamarind, mint and yogurt are established North Indian street foods.", "nasha_combination": "Serving aloo chaat on fried totopos (a chaat-nacho hybrid) is a NASHA proposal.", "note": R_PRACTICE},
         "New vegetarian appetizer; must NOT read as generic nachos (D-74)."),
    dish("chicken-tikka-tacos", "Chicken Tikka Tacos", "main", "Taco trio", "Yogurt-spice marinade, high-heat grill/broil to 74 °C, 3 corn tortillas",
         {"description": "3 tacos", "targets": {"chicken (raw)": "180 g (60 g per taco)", "corn tortillas": "3 x ~26 g", "raita-crema": "36 g", "hari": "24 g"}, "construction": "chopped grilled chicken, onion, hari and raita-crema"},
         [{"name": "Chicken tikka", "lines": [L("i-chicken-thigh", 180), L("i-hung-curd", 40), L("i-ginger-garlic-paste", 8), L("i-red-chilli-powder", 3), L("i-garam-masala", 1.5), L("i-turmeric", 0.5), L("i-kasuri-methi", 0.5), L("i-salt", 2.5), L("i-lemon-juice", 6, "ml"), L("i-oil-neutral", 12, "ml")]},
          {"name": "Tortillas and garnish", "lines": [L("i-corn-tortilla", 78), S("pickled-red-onion", 20), S("hari-salsa-verde", 24), S("raita-crema", 36), L("i-cilantro", 2), L("i-lime", 0.33, "each")]}],
         ["Marinate 4-12 h at ≤ 4 °C.", "Grill/broil on high heat until charred at the edges; probe 74 °C; rest 2 min; chop.", "Warm tortillas on the comal; assemble."],
         {"core_C": "74 minimum", "marinade_time": "4-12 h at ≤ 4 °C"}, "Three tacos on a board, lime, extra hari on the side.",
         ["Charbroiler/tandoor substitute", "Comal", "Probe thermometer"], cp("Cook chicken"), ["cold prep", "grill", "comal"], 4.0, 3.5, "L",
         pairing("Soft wheat body and carbonation cut char and marinade.", "Banana vs char.", "Citrusy hops lift yogurt tang.", "Bitterness vs char."),
         photo("Three-quarter angle, board.", ["charred chicken pieces with red-orange marinade", "pickled onion, hari, crema"], ["generic taco-truck toppings (cheese, sour cream swirl)"], "Show char, not uniform colour."),
         ["milk"], "Milk (hung curd, crema). Tortilla label check. No allergen-free claim.", False,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#6, #8 marinade logic)"],
         {"practice": "Chicken tikka is an established tandoori preparation (yogurt-spice marinade, high heat).", "nasha_combination": "Chicken tikka as corn-tortilla tacos with hari and raita-crema is a NASHA proposal.", "note": R_PRACTICE},
         "Main per founder list; shares marinade/sauces with Paneer Tikka Taco."),
    dish("kerala-coconut-fish-tacos", "Kerala Coconut Fish Tacos", "main", "Taco trio", "Marinate, pan-sear/shallow-fry fish to 63 °C, tacos with coconut crema and slaw",
         {"description": "3 tacos", "targets": {"fish (raw)": "170 g", "corn tortillas": "3 x ~26 g", "coconut sauce": "45 g", "slaw": "45 g"}, "construction": "crisp-edged fish pieces on tortilla, coconut crema, slaw"},
         [{"name": "Fish", "lines": [L("i-white-fish", 170), L("i-turmeric", 0.5), L("i-red-chilli-powder", 2), L("i-salt", 2), L("i-lime-juice", 8, "ml"), L("i-ginger-garlic-paste", 5), L("i-rice-flour", 14), L("i-oil-neutral", 30, "ml", "pan-fry allocation"), L("i-curry-leaf", 1, "g", "fried 15 s")]},
          {"name": "Tortillas, sauce and garnish", "lines": [L("i-corn-tortilla", 78), S("kerala-coconut-sauce", 45), S("kachumber-slaw", 45), S("pickled-red-onion", 12), L("i-cilantro", 2), L("i-lime", 0.33, "each")]}],
         ["Marinate fish 20-30 min at ≤ 4 °C (acid limits time).", "Dust in rice flour; pan-sear/shallow-fry until crisp edges; probe 63 °C (145 °F).", "Warm tortillas; assemble with sauce, slaw, onion; fry curry leaf to garnish."],
         {"core_C": "63 minimum (fish)", "marinade_time": "20-30 min"}, "Three tacos, white sauce, green slaw, fried curry leaf.",
         ["Flat-top/pan", "Probe thermometer", "Cold storage"], ["Fish to 63 °C (145 °F); fish species and sourcing TBD (parasite destruction/supplier documentation per official guidance).", "FISH allergen: dedicated utensils and label; shared fryer/pan = cross-contact."], ["cold prep", "flat-top", "plating"], 4.0, 4.0, "L",
         pairing("Wheat softness and carbonation suit light fish and coconut.", "Esters vs coconut.", "Tropical hops echo coconut-mango.", "Hop bitterness vs delicate fish."),
         photo("Three-quarter angle, light side window.", ["golden fish pieces", "white coconut sauce", "pink and green slaw", "fried curry leaf"], ["fish fingers/tartar look", "beer-batter puffiness"], "Light crisp crust only."),
         ["fish"], "Fish. Fryer/pan cross-contact; coconut labelling check. No allergen-free claim.", False,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#7 Malabar Fish Taco: same concept, coconut sauce instead of Malabar pepper sauce)"],
         {"practice": "Kerala fish curries combine coconut milk, turmeric, tamarind/kokum, chile and curry leaf. Fish tacos are a Baja/Mexican format.", "nasha_combination": "Kerala-style coconut crema on fish tacos is a NASHA proposal.", "note": R_PRACTICE},
         "Equals approved pool item #7 (Malabar Fish Taco) in concept; naming differs (Kerala vs Malabar). Treat as the same development track."),
    dish("tandoori-lamb-tacos", "Tandoori Lamb Tacos", "main", "Taco trio", "Long marinade, grill lamb to 63 °C (+ rest), 3 tacos",
         {"description": "3 tacos", "targets": {"lamb (raw trimmed)": "190 g", "corn tortillas": "3 x ~26 g", "raita-crema": "36 g", "hari": "24 g"}, "construction": "sliced grilled lamb, onion, hari, raita-crema"},
         [{"name": "Lamb", "lines": [L("i-lamb-leg", 190), L("i-hung-curd", 45), L("i-ginger-garlic-paste", 10), L("i-red-chilli-powder", 3), L("i-garam-masala", 2), L("i-turmeric", 0.5), L("i-cumin-ground", 1), L("i-salt", 3), L("i-lemon-juice", 8, "ml"), L("i-oil-neutral", 15, "ml")]},
          {"name": "Tortillas and garnish", "lines": [L("i-corn-tortilla", 78), S("pickled-red-onion", 20), S("hari-salsa-verde", 24), S("raita-crema", 36), L("i-cilantro", 2), L("i-lime", 0.33, "each")]}],
         ["Marinate 8-24 h at ≤ 4 °C.", "Grill on high heat to 63 °C (145 °F) minimum, rest 3 min, slice across the grain.", "Warm tortillas; assemble."],
         {"core_C": "63 minimum + rest", "marinade_time": "8-24 h at ≤ 4 °C"}, "Three tacos, sliced lamb fan, bright herb sauces.",
         ["Charbroiler/tandoor substitute", "Comal", "Probe thermometer"], ["Whole-muscle lamb to 63 °C with a 3-minute rest (official guidance; confirm local code); cut/diced or tenderized pieces to 71 °C.", "Raw-protein separation; discard marinade."], ["cold prep", "grill", "comal"], 4.5, 3.5, "L",
         pairing("Wheat body and carbonation tame fat and char.", "Esters vs lamb gaminess.", "Fruit and hop aroma against rich lamb.", "Bitterness vs char."),
         photo("Three-quarter angle, board.", ["pink-centred sliced lamb with char", "pickled onion, hari, crema"], ["beef-style carne asada look", "pulled/shredded texture"], "Show char and sliced pink; no steak-house garnish."),
         ["milk"], "Milk. Tortilla label check. No allergen-free claim.", False,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#8 Tandoori Lamb Taco, D-54)"],
         {"practice": "Lamb tikka/seekh in tandoor-style marinades is established; taco is a Mexican format.", "nasha_combination": "Documented as 'our own composition' in menu matrix #8.", "note": R_PRACTICE},
         "Equals approved pool item #8 (Tandoori Lamb Taco). Lamb costing carries high price risk."),
    dish("paneer-makhani-pizza", "Paneer Makhani Pizza", "main", "Pizza (12 inch, one person)", "Stretch dough, makhani-rajas base, bake hot; paneer finished with char",
         {"description": "1 pizza, about 30 cm", "targets": {"dough": "230 g", "makhani-rajas": "60 g", "paneer": "90 g", "mozzarella": "90 g", "oaxaca": "30 g"}, "construction": "makhani base, cheese, seared paneer cubes, rajas, onion"},
         [{"name": "Base", "lines": [S("pizza-dough", 230), S("makhani-rajas-sauce", 60), L("i-mozzarella", 90), L("i-cheese-oaxaca", 30)]},
          {"name": "Toppings", "lines": [L("i-paneer", 90), L("i-hung-curd", 15), L("i-kasuri-methi", 0.5), L("i-red-chilli-powder", 1), L("i-salt", 1), S("roasted-poblano-rajas", 40), S("pickled-red-onion", 12), L("i-cilantro", 2), L("i-oil-neutral", 5, "ml")]}],
         ["Marinate paneer cubes 2 h; sear.", "Stretch dough, sauce, cheese, rajas; bake in hot oven until blistered.", "Add paneer, onion, cilantro, kasuri methi at the end."],
         {"oven_C": "TBD by oven (menu matrix: deck/wood-fired)", "bake_time": "TBD at T1"}, "Whole pizza on a board, sliced in 6.",
         ["High-heat oven", "Peel", "Cold storage"], ["Pasteurized dairy only.", "Oven/hood and fuel decisions are professional review items."], ["dough", "oven"], 3.5, 3.0, "none",
         pairing("Wheat body suits tomato-cream.", "Esters vs sweet tomato.", "Hop aroma cuts cream.", "Bitterness vs tomato acidity."),
         photo("Overhead, wooden peel.", ["blistered crust edge", "orange makhani base, cubes of paneer, green poblano strips"], ["pepperoni-style toppings", "cheese pull cliché"], "Leopard-spot char only if oven allows."),
         ["milk", "wheat"], "Milk, wheat. No allergen-free claim.", True,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#12 Paneer Tikka Pizza, Makhani-Rajas or Hari base)"],
         {"practice": "Paneer tikka and makhani gravy are established North Indian preparations; 'paneer pizza' is a common fusion item.", "nasha_combination": "Makhani-rajas base on a pizza is a NASHA proposal.", "note": R_PRACTICE},
         "Variant of approved pool item #12 (Paneer Tikka Pizza), with makhani base. Oven is a gating professional item."),
    dish("goan-chicken-vindaloo-pizza", "Goan Chicken Vindaloo Pizza", "main", "Pizza (12 inch, one person)", "Braise chicken in vindaloo sauce, drain, top and bake",
         {"description": "1 pizza, about 30 cm", "targets": {"dough": "230 g", "chicken (raw)": "130 g", "vindaloo sauce": "60 g", "mozzarella": "85 g"}, "construction": "braised vindaloo chicken, dry-ish, on mozzarella"},
         [{"name": "Base", "lines": [S("pizza-dough", 230), L("i-mozzarella", 85)]},
          {"name": "Vindaloo chicken", "lines": [L("i-chicken-thigh", 130), S("vindaloo-sauce", 60), L("i-water", 0.02, "l")]},
          {"name": "Finish", "lines": [L("i-onion-red", 25), L("i-green-chile", 4), L("i-cilantro", 2), S("raita-crema", 20), L("i-lime", 0.17, "each")]}],
         ["Braise chicken in vindaloo sauce to 74 °C, shred or chop, reduce until nearly dry.", "Cool two-stage if batch-cooked; chill.", "Top the stretched dough, bake hot; finish with onion, chile, cilantro and raita-crema."],
         {"core_C": "74 minimum", "topping": "must be dry (menu matrix: 'dry shred only')"}, "Whole pizza on a board, crema in lines.",
         ["High-heat oven", "Braise pot/tilting kettle", "Probe thermometer"], ["Poultry to 74 °C; cool braise per two-stage rule; reheat to 74 °C if re-heated for hot holding.", "NO PORK: traditional vindaloo is often pork; NASHA recipe is chicken only (D-54)."], ["braise", "dough", "oven"], 4.0, 3.0, "none",
         pairing("Carbonation cleans vinegar-chile richness.", "Esters vs vinegar tang.", "Fruity hops soften vinegar heat.", "Bitterness stacks with chile."),
         photo("Overhead, wooden peel.", ["deep red braised chicken pieces", "white raita-crema lines", "red onion and green chile"], ["pork look", "pineapple or other non-recipe toppings"], "Topping should look dry-roasted, not saucy."),
         ["milk", "wheat"], "Milk, wheat. No allergen-free claim.", False,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#13 Birria Pizza conditional: 'dry shred only' logic)"],
         {"practice": "Goan vindaloo is a vinegar-chile marinade/braise, traditionally pork in many versions.", "nasha_combination": "Chicken vindaloo as a pizza topping is a NASHA proposal.", "note": R_PRACTICE},
         "New main; pork-free by design (D-54)."),
    dish("nawaabi-enchiladas", "Nawaabi Enchiladas", "main", "Baked enchilada plate", "Poach/sear tikka-spiced chicken, roll in tortillas, bake in nawaabi sauce",
         {"description": "3 rolled enchiladas", "targets": {"chicken (raw)": "150 g", "corn tortillas": "3 x ~26 g", "nawaabi sauce": "150 g", "oaxaca": "60 g"}, "construction": "rolled filled tortillas under sauce and cheese, baked"},
         [{"name": "Filling", "lines": [L("i-chicken-thigh", 150), L("i-ginger-garlic-paste", 6), L("i-garam-masala", 1), L("i-red-chilli-powder", 1.5), L("i-salt", 2), L("i-oil-neutral", 10, "ml"), L("i-cheese-oaxaca", 60)]},
          {"name": "Tortillas and sauce", "lines": [L("i-corn-tortilla", 78), L("i-oil-neutral", 20, "ml", "tortilla dip allocation"), S("nawaabi-enchilada-sauce", 150)]},
          {"name": "Garnish", "lines": [S("raita-crema", 20), S("pickled-red-onion", 12), L("i-cotija", 8), L("i-cilantro", 2)]}],
         ["Season and cook chicken to 74 °C; shred.", "Soften tortillas in warm oil, fill with chicken and oaxaca, roll.", "Sauce, bake until bubbling at 74 °C core; garnish."],
         {"core_C": "74 minimum (assembled)", "bake": "TBD at T1"}, "Baking dish plated on a board, crema and onion on top.",
         ["Oven", "Comal", "Probe thermometer"], cp("Cook filling") + ["TREE NUT: cashew sauce; allergen label required."], ["prep", "comal", "oven"], 4.0, 4.0, "L",
         pairing("Soft body and carbonation relieve rich cream sauce.", "Esters vs saffron.", "Hop aroma cuts cashew cream.", "Bitterness vs sweet sauce."),
         photo("Three-quarter angle, ceramic baking dish.", ["sauce-covered rolled tortillas", "browned oaxaca", "crema and pickled onion"], ["tomato-red Tex-Mex enchilada look", "melted yellow cheddar"], "Sauce should be pale orange-gold, not red."),
         ["milk", "tree_nut"], "Milk, TREE NUT (cashew). No allergen-free claim.", False,
         ["food/SAUCE-SYSTEM.md (makhani-rajas rich-sauce logic)"],
         {"practice": "Mughlai gravies are cashew-and-cream based; enchiladas are rolled filled tortillas in chile sauce.", "nasha_combination": "Nawaabi cashew-cream sauce on enchiladas is a NASHA proposal.", "note": R_PRACTICE},
         "New main; tree-nut allergen is a deliberate trade-off to be decided."),
    dish("hyderabadi-chicken-birria-tacos", "Hyderabadi Birria-Style Chicken Tacos", "main", "Taco trio with dipping broth", "Marinate, braise chicken in guajillo-ancho-Hyderabadi marinade to 74 °C, crisp tacos on comal",
         {"description": "3 tacos + 90 g broth", "targets": {"chicken (raw)": "200 g", "corn tortillas": "3 x ~26 g", "oaxaca": "45 g"}, "construction": "shredded braised chicken, cheese, dipped tortillas crisped on comal, broth cup"},
         [{"name": "Braised chicken", "lines": [L("i-chicken-thigh", 200), L("i-hung-curd", 40), L("i-ginger-garlic-paste", 10), L("i-guajillo", 8), L("i-ancho", 6), L("i-green-chile", 6), L("i-mint", 4), L("i-cilantro", 4), L("i-onion-red", 30), L("i-garam-masala", 2), L("i-red-chilli-powder", 2), L("i-turmeric", 0.5), L("i-cumin-ground", 1), L("i-cinnamon", 0.5), L("i-clove", 0.3), L("i-bay", 0.2), L("i-salt", 3), L("i-lemon-juice", 8, "ml"), L("i-oil-neutral", 15, "ml"), L("i-water", 0.08, "l")]},
          {"name": "Tacos", "lines": [L("i-corn-tortilla", 78), L("i-cheese-oaxaca", 45), L("i-oil-neutral", 12, "ml", "comal allocation"), L("i-onion-white", 25), L("i-cilantro", 3), L("i-lime", 0.33, "each"), S("pickled-red-onion", 15)]}],
         ["Marinate 6-12 h at ≤ 4 °C.", "Braise covered at about 150 °C oven or gentle simmer until tender; core 74 °C minimum; skim fat; shred.", "Dip tortillas in the braise fat, fill with chicken and cheese, crisp on a hot comal; serve with the strained broth."],
         {"core_C": "74 minimum", "broth": "strained, reheated to 74 °C before service"}, "Three tacos with a small cup of broth, onion, cilantro, lime.",
         ["Braise pot/oven", "Comal", "Probe thermometer", "Broth cups"], ["Poultry to 74 °C; braise/broth cooled by two-stage rule and reheated to 74 °C for service.", "Hot-hold broth ≥ 57 °C; discard rules per policy."], ["braise", "comal"], 5.0, 3.5, "none",
         pairing("Carbonation and wheat body soften deep chile; clove echo.", "Banana vs cinnamon-clove.", "Citrus hop aroma against braise richness.", "Bitterness vs deep chile."),
         photo("Three-quarter angle, board with broth cup.", ["red-brown crisped tacos", "visible shredded chicken and melted cheese", "broth cup with fat sheen"], ["beef-style birria look (goat birria is approved separately)"], "Chicken must look like chicken, not beef."),
         ["milk"], "Milk. Tortilla label check. No allergen-free claim.", False,
         ["food/MENU-DEVELOPMENT-MATRIX-V1.md (#9 Dum Goat Birria, #13)"],
         {"practice": "Birria is a Jalisco braised-meat dish with guajillo-ancho adobo, typically beef/goat; Hyderabadi cooking uses yogurt-spice marinades and dum braises.", "nasha_combination": "Chicken in a Hyderabadi-guajillo marinade as 'birria-style' tacos is a NASHA proposal and not authentic birria.", "note": R_PRACTICE},
         "Overlaps approved Goat Birria in technique; chicken variant, lower cost. Not a replacement."),
]

BACKFILL = {   # earlier dishes: menu metadata
    "chicken-65-totopos": ("appetizer", "approved_core5", "Core 5 anchor appetizer; matches founder candidate 'Chicken 65 Totopos'."),
    "mango-habanero-gobi": ("appetizer", "approved_core5", "Core 5 appetizer; matches founder candidate 'Mango Habanero Gobi' (D-84: not a taco)."),
    "butter-chicken-quesadilla": ("main", "approved_core5", "Core 5 main; matches founder candidate 'Butter Chicken Quesadilla'."),
    "paneer-tikka-taco": ("main", "approved_core5", "Core 5 item; not in the founder's appetizer/main candidate lists: provisionally priced as a main (taco trio) pending founder classification."),
    "goat-birria": ("main", "approved_core5", "Core 5 item; not in the founder's appetizer/main candidate lists: provisionally priced as a main pending founder classification."),
    "chaat-elote": ("appetizer", "approved_menu_v1_1", "Approved 12-dish test menu item #2. Overlaps founder candidate 'Masala Street Corn': treated as the same dish track (rename not applied)."),
}


def main():
    m = json.loads(MASTER.read_text())
    have = {i["id"] for i in m["ingredients"]}
    for (iid, name, cat, unit, y, al, veg, pr, note) in NEW_INGREDIENTS:
        if iid in have:
            continue
        m["ingredients"].append({"id": iid, "name": name, "category": cat, "unit": unit, "yield_pct": y, "allergens": al, "vegetarian": veg, "d54": "no beef/pork derivative expected; supplier statement required",
                                 "notes": note, "price": {"low": pr[0], "base": pr[1], "high": pr[2]}})
    MASTER.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
    for r in SUBS + DISHES:
        (V1 / f"{r['id']}.v1.json").write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
    for rid, (cat, st, note) in BACKFILL.items():
        p = V1 / f"{rid}.v1.json"
        r = json.loads(p.read_text())
        r.update({"menu_category": cat, "menu_status": st, "classification_note": note, "target_gross_margin_pct": 70,
                  "development_status": "DRAFT v1.0 — desk estimate; kitchen test not started; no costed purchase records"})
        r.setdefault("research", {"practice": "see evidence list", "nasha_combination": "see cultural/food research files", "note": "Earlier research baseline; not re-sourced in D-87."})
        p.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
    print("ok", len(SUBS), "sub-recipes", len(DISHES), "dishes", len(m["ingredients"]), "ingredients")


if __name__ == "__main__":
    main()
