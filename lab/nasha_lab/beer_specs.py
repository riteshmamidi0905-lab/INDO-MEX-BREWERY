"""NASHA beer specifications (D-85) as ONE structured source of truth, computed with nasha_lab.brewing. Everything is a TARGET or an expected value from a
published formula: nothing has been brewed, measured or tasted. `write()` regenerates beer/specs/beer_specs.json; tests keep labels, website and docs consistent with it.
"""
import json
from pathlib import Path

from . import brewing as B

ROOT = Path(__file__).resolve().parents[2]
PILOT_BATCH_L = 100            # ASSUMPTION: pilot scale is undecided (G-6); 100 L into the fermenter is used only to make quantities concrete
EFFICIENCY = 0.72              # ASSUMPTION: unmeasured pilot-system brewhouse efficiency
STATUS = "Concept formulation, not brewed or tested"
DISCLAIMER = "Target values, not measured production results; not laboratory-verified alcohol content."


def badshah():
    og, fg = 1.048, 1.012
    pct = {"wheat malt": 55, "pilsner malt": 45}
    total, kg = B.grist_for_og(og, pct, PILOT_BATCH_L, EFFICIENCY)
    return {
        "id": "badshah", "name": "BADSHAH", "style": "Hefeweizen (Bavarian-style wheat beer; BJCP 10A Weissbier reference)", "status": STATUS,
        "target_abv_pct": 4.7, "og": og, "fg": fg, "expected_abv_formula_pct": round(B.abv_simple(og, fg), 2), "apparent_attenuation": round(B.apparent_attenuation(og, fg), 3),
        "plato_og": round(B.plato(og), 1), "ibu_objective": 11, "ibu_window": [10, 13], "srm_window": [3, 5], "co2_volumes_target": 3.4, "co2_volumes_window": [3.0, 3.8],
        "grist_percent": pct, "pilot_batch_l": PILOT_BATCH_L, "assumed_efficiency": EFFICIENCY, "grist_total_kg": round(total, 1), "grist_kg": kg,
        "bittering_hops": {"type": "noble-type hop (e.g. Hallertau, Tettnang or Spalt class)", "assumed_alpha_pct": 4.0, "boil_min": 60, "grams_for_objective": round(_grams_for(11, 4.0, 100, 60, 1.044), 0)},
        "contains": ["wheat (gluten)", "barley malt (gluten)"], "no_gluten_free_claim": True,
        "provisional_placeholders": ["package volume", "regulatory/label statements (TTB, TABC)", "certifications", "barcode", "price", "measured ABV"],
    }


def amba_haze():
    fg = 1.015
    pct = {"pilsner malt": 70, "flaked oats": 15, "wheat malt": 12, "dextrin malt": 3}
    puree_kg, brix = 10.0, 15.0
    fruit_pts = B.fruit_gravity_points(puree_kg, brix, PILOT_BATCH_L)
    base_og = B.base_og_for_target_abv(6.0, fg, fruit_pts)
    total, kg = B.grist_for_og(base_og, pct, PILOT_BATCH_L, EFFICIENCY)
    og_total = base_og + fruit_pts / 1000.0
    return {
        "id": "amba-haze", "name": "AMBA HAZE", "style": "Mango-forward juicy (hazy) IPA; BJCP 21B7 Hazy IPA reference", "status": STATUS, "working_name": True,
        "target_abv_pct": 6.0, "base_wort_og": round(base_og, 4), "fruit_gravity_points": round(fruit_pts, 2), "og_with_fruit": round(og_total, 4), "fg": fg,
        "expected_abv_formula_pct": round(B.abv_simple(og_total, fg), 2), "ibu_objective": 35, "ibu_window": [25, 45], "srm_window": [3, 6], "co2_volumes_target": 2.4, "co2_volumes_window": [2.2, 2.6],
        "grist_percent": pct, "pilot_batch_l": PILOT_BATCH_L, "assumed_efficiency": EFFICIENCY, "grist_total_kg": round(total, 1), "grist_kg": kg,
        "mango_puree": {"kg_per_100_l": puree_kg, "assumed_brix": brix, "spec": "aseptic or pasteurised single-strength puree, no added sugar; record preservatives (sulfites are declarable)"},
        "contains": ["barley malt (gluten)", "wheat (gluten)", "oats (gluten-containing in a brewing context)"], "no_gluten_free_claim": True,
        "provisional_placeholders": ["package volume", "regulatory/label statements (TTB, TABC)", "certifications", "barcode", "price", "measured ABV"],
    }


def _grams_for(ibu, aa, batch_l, boil_min, og_boil):
    one = B.tinseth_ibu(1.0, aa, batch_l, boil_min, og_boil)
    return ibu / one


def specs():
    return {"decision": "D-85", "date": "2026-10-22", "disclaimer": DISCLAIMER, "beers": [badshah(), amba_haze()]}


def write(path=None):
    p = Path(path) if path else ROOT / "beer/specs/beer_specs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(specs(), indent=1))
    return p


if __name__ == "__main__":
    print(write())
