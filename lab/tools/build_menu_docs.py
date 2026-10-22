#!/usr/bin/env python3
"""Generates docs/menu-research/MENU-CANDIDATE-RESEARCH-D87.md, docs/menu-research/PRICING-SCENARIO-D87.md and food/recipes/RECIPE-CARDS-D87.md from the recipe, pricing and
quote files, so the prose cannot drift from the numbers.   python3 lab/tools/build_menu_docs.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab"))
from nasha_lab.recipes import bom, model, pricing  # noqa: E402

R, M, CFG = model.load_recipes(), model.load_master(), pricing.load_config()
D = {k: v for k, v in R.items() if v["kind"] == "dish"}
FOUNDER = [("appetizer", "Chicken 65 Totopos", "chicken-65-totopos"), ("appetizer", "Mango Habanero Gobi", "mango-habanero-gobi"), ("appetizer", "Tandoori Paneer Quesadilla Bites", "tandoori-paneer-quesadilla-bites"),
           ("appetizer", "Masala Street Corn", "chaat-elote"), ("appetizer", "Goan Peri-Peri Wings", "goan-peri-peri-wings"), ("appetizer", "Crispy Aloo Chaat Nachos", "crispy-aloo-chaat-nachos"),
           ("main", "Butter Chicken Quesadilla", "butter-chicken-quesadilla"), ("main", "Chicken Tikka Tacos", "chicken-tikka-tacos"), ("main", "Kerala Coconut Fish Tacos", "kerala-coconut-fish-tacos"),
           ("main", "Tandoori Lamb Tacos", "tandoori-lamb-tacos"), ("main", "Paneer Makhani Pizza", "paneer-makhani-pizza"), ("main", "Goan Chicken Vindaloo Pizza", "goan-chicken-vindaloo-pizza"),
           ("main", "Nawaabi Enchiladas", "nawaabi-enchiladas"), ("main", "Hyderabadi Birria-Style Chicken Tacos", "hyderabadi-chicken-birria-tacos")]
SRC = ("Sources are WEB-SEARCH SNIPPETS only (search results, US index). Primary documents (FDA Food Code, USDA tables, culinary references) could not be fetched in this environment, "
       "so no passage is quoted and every practice statement below is an orientation to be verified, not a citation.")


def pct(x):
    return f"{x * 100:.1f}%"


def research():
    rows = []
    for cat, name, rid in FOUNDER:
        r, e = D[rid], pricing.economics(rid, CFG)
        rows.append(f"| {name} | {cat} | {r['menu_status'].replace('_', ' ')} | ${e['food_cost']:.2f} | {pct(e['food_cost_pct'])} | {pct(e['gross_margin_pct'])} | {', '.join(r['allergens_declared']) or 'none'} | {r['classification_note']} |")
    out = ["# Menu candidate research (D-87)", "",
           "**Status: candidates only; candidates are not additions to the approved menu and replace nothing.** No dish has been cooked, tasted or costed from purchase records. No beef or pork (D-54). No halal claim.", "",
           f"**Prices (approved CONCEPT prices, price-v2-2026-10-22):** house beer glass $9.00, pitcher $31.00, appetizers $13.50, mains $18.50. Glass and pitcher volumes are pending founder decisions and are not assumed.", "",
           f"**Research basis.** {SRC} Each recipe JSON separates `research.practice` (documented regional preparation) from `research.nasha_combination` (the NASHA proposal).", "",
           "## Comparison with the Core 5, the approved 12-dish test menu and the 16-item development pool", "",
           "| Candidate | Category | Status | Base food cost / portion* | Food cost % | Gross margin % | Allergens (derived) | Relationship / proposed change |", "|---|---|---|---|---|---|---|---|", *rows, "",
           "\\* ingredient cost + 5% waste allowance, at PLANNING-ASSUMPTION base prices (not supplier quotes); gross margin also deducts a $0.12 consumables allowance. Target gross margin 70% is a planning target, not an approved threshold.", "",
           "## Proposed changes (documented, not applied)", "",
           "1. **Masala Street Corn = Chaat Elote** (approved 12-dish test menu #2). Same dish track; a rename to 'Masala Street Corn' is a founder decision and is not applied.",
           "2. **Paneer Tikka Taco and Goat Birria** are Core 5 items that are in neither of the founder's candidate lists. They are priced as mains PROVISIONALLY (taco trio / braise plate); the founder should classify them.",
           "3. **Kerala Coconut Fish Tacos** and **Tandoori Lamb Tacos** are the development-pool items #7 (Malabar Fish Taco) and #8 (Tandoori Lamb Taco) under different names/sauce: one development track each.",
           "4. **Goan Peri-Peri Wings** overlaps pool item #4 (Hefe-brined Wings) in format; proposed as a sauce variant, not a replacement.",
           "5. **Paneer Makhani Pizza** is a variant of pool item #12 (Paneer Tikka Pizza) with a makhani-rajas base; **Hyderabadi Birria-Style Chicken Tacos** is a lower-cost chicken variant of the goat birria technique and is NOT authentic birria.",
           "6. **Goan Chicken Vindaloo Pizza** is chicken only: traditional vindaloo is often made with pork, which D-54 excludes.",
           "7. **Nawaabi Enchiladas** introduce a tree-nut (cashew) allergen into the menu; a founder decision whether to accept that trade-off.", "",
           "## Observations a person should check", "",
           f"* Tandoori Lamb Tacos is the only dish below the 70% planning margin target at the base scenario; lamb price risk dominates (see inflation table in the pricing scenario document).",
           "* All other dishes are well above 70% at planning prices; that is a statement about assumptions, and real supplier prices, yields and waste will change it.",
           "* Mains share a single $18.50 price across very different costs; contribution margins differ by up to about $7 per portion (labor planning rate $24/h, 5% waste, $0.12 consumables).", "",
           "## Food-safety and technique orientation (verify with a food-safety professional)", "",
           "Poultry to 74 °C (165 °F); fish to 63 °C (145 °F); whole-muscle lamb to 63 °C with a rest; two-stage cooling of braises and sauces (57→21 °C within 2 h, then to ≤ 5 °C within 4 h more); hot-hold ≥ 57 °C. These are widely published Food Code-style figures recalled from search snippets; local code and a qualified reviewer decide. No part of this document is a certified food-safety programme.", "",
           "## What this document does not claim", "", "No dish was cooked, tasted or validated. No ingredient price is a supplier quote. No allergen statement is a label. The menu is not final and nothing is on sale."]
    return "\n".join(out) + "\n"


def pricing_doc():
    rows = []
    for e in pricing.menu_economics(CFG):
        lo, hi = pricing.economics(e["id"], CFG, "low"), pricing.economics(e["id"], CFG, "high")
        t = pricing.inflation_table(e["id"], CFG, shocks=(0.2,))[0]
        rows.append(f"| {e['name']} | ${e['price']:.2f} | ${e['food_cost']:.2f} | {pct(lo['food_cost_pct'])} / {pct(e['food_cost_pct'])} / {pct(hi['food_cost_pct'])} | ${e['gross_profit']:.2f} | ${e['contribution_margin']:.2f} | {pct(t['protein_only'])} | {pct(t['all'])} |")
    return "\n".join(["# Pricing scenario v2 and how it differs from the placeholder-price simulation (D-87)", "",
        "**Concept prices, not an operating menu.** Simulated revenue computed here is SYNTHETIC and is not NASHA revenue. No restaurant exists.", "",
        "| | Historical simulation (price-v1-placeholder) | Scenario `scn-price-v2-recipes-v1` (price-v2-2026-10-22) |", "|---|---|---|",
        "| Food items | Placeholders $12.00-$16.00 each (M01 $14.00, M02 $13.00, M03 $16.00, M04 $12.00, M05 $15.00) | Appetizers $13.50, mains $18.50 |",
        "| Beer | B01 hefe $8.00, B04 Amba Haze $9.00 | BADSHAH and AMBA HAZE glass $9.00; pitcher $31.00 (not simulated) |",
        "| Other sim items (lager, amber, NA drinks, merch) | v1 placeholder | carried at v1 and labelled `v1_placeholder_carried` |",
        "| Storage | dim_/fact_/mart_ tables, unchanged | `scn_*` tables added beside them; historical tables are never modified (tested by table hash) |",
        "| Revenue basis | simulated quantity x placeholder price | the same simulated quantity x approved price (restatement) |", "",
        "**Limits.** No price elasticity: volumes do not respond to the new prices. Pitchers and serving sizes are not simulated (volumes pending). Beer unit cost and margin are NOT COMPUTABLE until volumes and a costed batch exist. Food costs are planning assumptions. Inventory counts, receipts and the injected anomalies are synthetic; supplier quotes are SYNTHETIC_QUOTE.", "",
        "## Per-dish economics (base scenario)", "", "Food cost % shown low / base / high price scenario; last two columns = food cost % if protein prices rise 20% / all ingredients rise 20%.", "",
        "| Dish | Price | Food cost (incl. 5% waste) | Food cost % L/B/H | Gross profit | Contribution (after labor) | +20% protein | +20% all |", "|---|---|---|---|---|---|---|---|", *rows, "",
        "Definitions: gross profit = price - ingredient cost - waste allowance - consumables ($0.12). Contribution = gross profit - direct labor minutes x $24/h loaded planning rate. Ingredient cost = qty / yield x unit price, with sub-recipes costed by batch yield."]) + "\n"


def cards():
    out = ["# Recipe cards (D-87) — PRELIMINARY, NOT COOKED OR TASTED", "", "Generated from `food/recipes/v1/*.json`. Quantities are grams unless stated and are preliminary estimates; costs are planning assumptions; nothing has been cooked or tasted.", ""]
    for r in D.values():
        e = pricing.economics(r["id"], CFG)
        out += [f"## {r['name']}  (v{r['version']}, {r['menu_category']}, {r['menu_status'].replace('_', ' ')})", "", f"*Status:* {r['status']} · *Development:* {r['development_status']}", "",
                f"*Portion:* {r['portion']['description']}. *Method:* {r['cooking_method']}.", "", "| Ingredient / sub-recipe | Qty | Prep |", "|---|---|---|"]
        for c in r["components"]:
            for l in c["lines"]:
                nm = l.get("subrecipe") or M[l["ingredient"]]["name"]
                out.append(f"| {c['name']}: {nm} | {l['qty']} {l['unit']} | {l.get('prep', '')} |")
        out += ["", "**Steps:** " + " ".join(f"{i + 1}. {s}" for i, s in enumerate(r["method"]["steps"])), "", "**Equipment:** " + ", ".join(r["equipment"]), "",
                f"**Prep/service labor estimate:** {r['workflow']['labor_minutes_per_portion']['prep']} + {r['workflow']['labor_minutes_per_portion']['service']} min per portion.", "",
                f"**Cost (planning):** ingredient ${e['ingredient_cost']:.2f}, with waste ${e['food_cost']:.2f}, food cost {pct(e['food_cost_pct'])} of ${e['price']:.2f}; gross margin {pct(e['gross_margin_pct'])} (target {r['target_gross_margin_pct']}%).", "",
                "**Food safety:** " + " ".join(r["food_safety"]), "", f"**Allergens (derived, not a label):** {', '.join(r['allergens_declared']) or 'none declared'}. {r['allergen_notes']}", "",
                "**Beer pairing hypotheses (not sensory tested):** " + " ".join(f"{p['beer']}: {p['hypothesis']}" for p in r["pairing"]), "",
                f"**Photography brief:** {r['photography']['hero']} Must show: {'; '.join(r['photography']['must_show'])}. Must not show: {'; '.join(r['photography']['must_not_show'])}. Label: {r['photography']['label']}", ""]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    (ROOT / "docs/menu-research").mkdir(exist_ok=True)
    (ROOT / "docs/menu-research/MENU-CANDIDATE-RESEARCH-D87.md").write_text(research())
    (ROOT / "docs/menu-research/PRICING-SCENARIO-D87.md").write_text(pricing_doc())
    (ROOT / "food/recipes/RECIPE-CARDS-D87.md").write_text(cards())
    print("written")
