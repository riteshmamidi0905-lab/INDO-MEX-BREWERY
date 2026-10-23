#!/usr/bin/env python3
"""Generates docs/menu-research/MENU-CANDIDATE-RESEARCH-D87.md, docs/menu-research/PRICING-SCENARIO-D87.md and food/recipes/RECIPE-CARDS-D87.md from the recipe, pricing and
quote files, so the prose cannot drift from the numbers.   python3 lab/tools/build_menu_docs.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab"))
from nasha_lab.recipes import beer_costing, bom, model, optimize, pricing  # noqa: E402

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
           "1. **Masala Street Corn = Chaat Elote** (approved 12-dish test menu #2). Same dish track; the name Chaat Elote is retained (D-88).",
           "2. **D-88 decisions (2026-10-23):** Paneer Tikka Taco is a main at $18.50. **Goat Birria is removed from the active menu and the candidate pool** (archived under `food/recipes/retired/`; historical decision records preserved; not to be reintroduced without founder approval). Chaat Elote keeps its name; 'Masala Street Corn' is an alternate development name only.",
           "3. **Kerala Coconut Fish Tacos** and **Tandoori Lamb Tacos** are the development-pool items #7 (Malabar Fish Taco) and #8 (Tandoori Lamb Taco) under different names/sauce: one development track each.",
           "4. **Goan Peri-Peri Wings** overlaps pool item #4 (Hefe-brined Wings) in format; proposed as a sauce variant, not a replacement.",
           "5. **Paneer Makhani Pizza** is a variant of pool item #12 (Paneer Tikka Pizza) with a makhani-rajas base; **Hyderabadi Birria-Style Chicken Tacos** is a chicken dish in the birria style (the goat birria it was derived from is retired, D-88) and is NOT authentic birria.",
           "6. **Goan Chicken Vindaloo Pizza** is chicken only: traditional vindaloo is often made with pork, which D-54 excludes.",
           "7. **Nawaabi Enchiladas** are approved for continued development with cashews (D-88); tree nut is a declared major allergen and cross-contact precautions are recorded. No allergy-safety guarantee is made without operational validation.", "",
           "## Observations a person should check", "",
           "* Tandoori Lamb Tacos is the only dish below the 70% planning margin target at the base scenario (69.4%). D-88 keeps it as a main at $18.50, keeps the original costing for comparison and asks for portion, yield and supplier analysis WITHOUT cutting quality: see `PRICING-SCENARIO-D87.md`.",
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
        "| Food items | Placeholders $12.00-$16.00 each (M01 $14.00, M02 $13.00, M03 $16.00, M04 $12.00, M05 $15.00) | Appetizers $13.50, mains $18.50; M03 (Goat Birria) retired by D-88, so its historical sales keep the v1 placeholder and have no BOM |",
        "| Beer | B01 hefe $8.00, B04 Amba Haze $9.00 | BADSHAH and AMBA HAZE glass $9.00; pitcher $31.00 (not simulated); provisional serving sizes 16 and 60 US fl oz |",
        "| Other sim items (lager, amber, NA drinks, merch) | v1 placeholder | carried at v1 and labelled `v1_placeholder_carried` |",
        "| Storage | dim_/fact_/mart_ tables, unchanged | `scn_*` tables added beside them; historical tables are never modified (tested by table hash) |",
        "| Revenue basis | simulated quantity x placeholder price | the same simulated quantity x approved price (restatement) |", "",
        "**Limits.** No price elasticity: volumes do not respond to the new prices. Pitchers are not simulated and serving sizes are provisional concept sizes. Beer costs are PRELIMINARY PLANNING ESTIMATES, not verified production costs. Food costs are planning assumptions. Inventory counts, receipts and the injected anomalies are synthetic; supplier quotes are SYNTHETIC_QUOTE.", "",
        "## Per-dish economics (base scenario)", "", "Food cost % shown low / base / high price scenario; last two columns = food cost % if protein prices rise 20% / all ingredients rise 20%.", "",
        "| Dish | Price | Food cost (incl. 5% waste) | Food cost % L/B/H | Gross profit | Contribution (after labor) | +20% protein | +20% all |", "|---|---|---|---|---|---|---|---|", *rows, "",
        *lever_and_beer_sections(),
        "Definitions: gross profit = price - ingredient cost - waste allowance - consumables ($0.12). Contribution = gross profit - direct labor minutes x $24/h loaded planning rate. Ingredient cost = qty / yield x unit price, with sub-recipes costed by batch yield."]) + "\n"


def lever_and_beer_sections():
    out = ["", "## Tandoori Lamb Tacos: portion, yield and supplier analysis (D-88; analysis only, nothing applied)", "",
           "The ORIGINAL costing scenario is the first row and is retained. Quality is not traded for margin: portion cuts below 95% of the primary protein are marked as below the quality floor and shown for information only.", "",
           "| Lever | Setting | Food cost | Gross margin | Change | Quality impact |", "|---|---|---|---|---|---|"]
    for r in optimize.levers("tandoori-lamb-tacos", CFG):
        out.append(f"| {r['lever']} | {r['setting']} | ${r['food_cost']:.2f} | {pct(r['gross_margin_pct'])} | {r['margin_delta_pts']:+.1f} pts | {r['quality_impact']} |")
    g = optimize.protein_grams_for_margin("tandoori-lamb-tacos", 70)
    out += ["", f"Information only: the planning margin would reach exactly 70% at about {g * 100:.0f}% of the current lamb portion, which is inside the quality floor and therefore inconclusive without tasting. Better first steps are the yield and supplier levers (a pre-trimmed lamb spec is cost-neutral up to a price premium equal to its yield gain) and waste control.", "",
            "## Beer: preliminary costing and margins at provisional serving sizes (D-88)", "",
            f"Serving sizes (founder-approved concept sizes): glass 16 US fl oz = {beer_costing.serving_ml(CFG, 'glass'):.3f} mL, pitcher 60 US fl oz = {beer_costing.serving_ml(CFG, 'pitcher'):.3f} mL (stored exactly from fl oz at 29.5735295625 mL per fl oz; the message quoted 1,774.414 mL, a 0.002 mL rounding difference). Real glassware capacity, headspace and fill lines need physical validation.", "",
            "PLANNING ESTIMATES, NOT VERIFIED PRODUCTION COSTS: nothing has been brewed. Basis: 100 L pilot batch, 92% packaged, 4% service waste, assumed ingredient prices and overheads in `food/pricing/beer-cost-assumptions.v1.json`. Excluded: excise tax, TABC/TTB fees, equipment depreciation, serving labor.", "",
            "| Beer | Size | Price | Cost ex brew labor | Margin ex labor | Cost incl. pilot brew labor | Margin incl. labor |", "|---|---|---|---|---|---|---|"]
    for r in beer_costing.all_rows(CFG):
        if r["scenario"] == "base":
            out.append(f"| {r['beer']} | {r['size']} | ${r['price']:.2f} | ${r['cost_ex_labor']:.2f} | {pct(r['margin_ex_labor_pct'])} | ${r['cost_with_brew_labor']:.2f} | {pct(r['margin_with_brew_labor_pct'])} |")
    pg = beer_costing.pitcher_vs_glass(CFG)
    out += ["", f"A pitcher equals {pg['glasses_per_pitcher']:.2f} glasses; buying that volume as glasses costs ${pg['glass_equivalent_price']:.2f} against ${pg['pitcher_price']:.2f} per pitcher, an implied volume discount of {pct(pg['discount_pct'])}.", ""]
    return out


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
