#!/usr/bin/env python3
"""Generate the internal beer specification and the two pilot-batch formulation briefs from nasha_lab.beer_specs (one source of truth, so documents,
labels and the website cannot drift). Tags: [EST] = established brewing science/practice; [NASHA-UNTESTED] = a NASHA hypothesis that has never been brewed.

    python3 lab/tools/build_beer_docs.py          # writes beer/specs/BEER-SPECIFICATIONS-V1.md and beer/pilot-briefs/06-*.md, 07-*.md
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab"))
from nasha_lab import beer_specs as S  # noqa: E402
from nasha_lab import brewing as B  # noqa: E402

BANNER = ("> **PRELIMINARY — CONCEPT FORMULATION, NOT BREWED OR TESTED (D-85, D-86).** ABV figures are founder-approved **targets**, not measured results and not laboratory-verified alcohol content. "
          "Expected values below come from published approximations, not from beer. A licensed brewer owns every real decision (G-6 open); regulators own every label statement.")


def spec_doc(sp):
    bd, am = sp["beers"]
    return f"""# NASHA beer specifications v1 (internal) — D-85, 2026-10-22

{BANNER}

## Summary table
| | **BADSHAH** | **AMBA HAZE** (working name) |
|---|---|---|
| Style | {bd['style']} | {am['style']} |
| Status | {bd['status']} | {am['status']} |
| **Target ABV (founder, provisional)** | **{bd['target_abv_pct']}%** | **{am['target_abv_pct']}%** |
| Expected ABV from the formula (not a measurement) | {bd['expected_abv_formula_pct']}% | {am['expected_abv_formula_pct']}% |
| OG (target) | {bd['og']:.3f} (≈ {bd['plato_og']} °P) | {am['og_with_fruit']:.4f} including fruit sugar (base wort {am['base_wort_og']:.4f}) |
| FG (target) | {bd['fg']:.3f} | {am['fg']:.3f} |
| Bitterness objective | {bd['ibu_objective']} IBU (window {bd['ibu_window'][0]}-{bd['ibu_window'][1]}) | {am['ibu_objective']} IBU (window {am['ibu_window'][0]}-{am['ibu_window'][1]}); low perceived bitterness |
| Colour | SRM {bd['srm_window'][0]}-{bd['srm_window'][1]} | SRM {am['srm_window'][0]}-{am['srm_window'][1]} |
| Carbonation | {bd['co2_volumes_target']} vol CO₂ (window {bd['co2_volumes_window'][0]}-{bd['co2_volumes_window'][1]}) | {am['co2_volumes_target']} vol CO₂ (window {am['co2_volumes_window'][0]}-{am['co2_volumes_window'][1]}) |
| Allergen/ingredient notes | contains wheat and barley (gluten); no gluten-free claim | contains barley, wheat, oats (gluten); mango; check puree for sulfites; no gluten-free claim |

## How the figures relate to earlier records
`beer/pilot-briefs/01-hefeweizen.md` recorded an R&D window of 4.8-5.3% ABV, and `beer/concepts/BADSHAH-PAAPI-CONCEPT-SPEC.md` a mango-IPA hypothesis of about 6.0-7.5%. Those are historical (older wording); D-85 sets the provisional targets above. 4.7% is inside the BJCP Weissbier range (4.3-5.6%) quoted in `beer/HEFEWEIZEN-BENCHMARK.md` but below the earlier R&D window, so the first pilot must confirm the yeast and attenuation can land there.

## What is provisional (placeholders until reviewed)
Package volume · measured ABV · label statements and any ABV tolerance language (TTB/TABC review, [PRO]) · certifications (none claimed) · barcode · price · ingredient statements as packaged · allergen statements as packaged.

## Rules for every surface (labels, website, menu, decks)
1. A figure appears only as **"target ABV 4.7% (provisional)"** or **"target ABV 6.0% (provisional)"** — never as a bare "4.7% ABV" / "6.0% ABV" that could read as a laboratory-verified or labelled alcohol content.
2. No tasting, brewing or sensory result is claimed. No award, certification or "organic/natural/gluten-free/halal" claim.
3. The Courtyard identity, the G1 restrictions (cans, glassware, signage only; never below 32 px cap height), the brand-v3 palette and the vector masters are unchanged.

## Formulation briefs
`beer/pilot-briefs/06-badshah-formulation-brief.md` · `beer/pilot-briefs/07-amba-haze-formulation-brief.md` · calculations: `lab/nasha_lab/brewing.py`, `lab/nasha_lab/beer_specs.py`, data `beer/specs/beer_specs.json`.
"""


def badshah_doc(b):
    g = b["grist_kg"]
    hops = b["bittering_hops"]
    return f"""# Pilot-batch formulation brief: BADSHAH hefeweizen (target ABV {b['target_abv_pct']}%)

{BANNER}

Tags: **[EST]** established brewing science or practice · **[NASHA-UNTESTED]** a NASHA hypothesis never brewed · **[ASSUMPTION]** a placeholder until measured.
Pilot scale is undecided (G-6); {b['pilot_batch_l']} L into the fermenter is used only to make quantities concrete.

## 1. Style objectives
Hazy gold Bavarian-style Hefeweizen: banana and clove in balance with soft bread/wheat, tall dense white foam, high carbonation, dry-ish bright finish, low bitterness, drinkable in volume, strong with chile heat and fat (existing sensory targets, `beer/pilot-briefs/01-hefeweizen.md`). No fruit, spice or novelty additions. Target ABV {b['target_abv_pct']}% (D-85).

## 2. Numerical targets
| Item | Target | Basis |
|---|---|---|
| OG | {b['og']:.3f} (≈ {b['plato_og']} °P) | **[NASHA-UNTESTED]** inside the BJCP 10A range 1.044-1.053 **[EST]** |
| FG | {b['fg']:.3f} | **[NASHA-UNTESTED]** BJCP 1.008-1.014 **[EST]** |
| Apparent attenuation | {b['apparent_attenuation']:.0%} | derived; typical for the style is about 75-80% **[EST]** |
| **ABV (target)** | **{b['target_abv_pct']}%** | founder target (D-85). Formula (OG-FG)×131.25 gives {b['expected_abv_formula_pct']}% **[EST approximation; measure the beer]** |
| Bitterness | {b['ibu_objective']} IBU (window {b['ibu_window'][0]}-{b['ibu_window'][1]}) | **[NASHA-UNTESTED]** BJCP 8-15 **[EST]** |
| Colour | SRM {b['srm_window'][0]}-{b['srm_window'][1]} | BJCP 2-6 **[EST]** |
| Carbonation | {b['co2_volumes_target']} vol CO₂ ({b['co2_volumes_window'][0]}-{b['co2_volumes_window'][1]}) | high carbonation is characteristic **[EST]**; the brewer sets the final value |

## 3. Grain bill concept
| Malt | % of grist | Pilot-batch mass ({b['pilot_batch_l']} L, assumed {b['assumed_efficiency']:.0%} efficiency) |
|---|---|---|
| Wheat malt | {b['grist_percent']['wheat malt']}% | {g['wheat malt']} kg |
| Pilsner malt | {b['grist_percent']['pilsner malt']}% | {g['pilsner malt']} kg |
| **Total** | 100% | **{b['grist_total_kg']} kg** (computed so that OG = {b['og']:.3f}) |

- **[EST]** Hefeweizen grists are at least 50% malted wheat; wheat has no husk, so the mash can stick: rice hulls (about 2-4% of grist weight, zero extract) are a common process aid. **[NASHA-UNTESTED]** start with 3% and let the brewer decide.
- **[ASSUMPTION]** {b['assumed_efficiency']:.0%} brewhouse efficiency is a placeholder; the first pilot measures it and the masses are recalculated.
- No specialty malts: they are not needed for the style, and keeping the bill simple makes yeast character the experiment.

## 4. Mash and process concept
- **[EST]** A short **ferulic-acid rest (about 43-45 °C, 10-20 min)** raises the ferulic acid that POF+ yeast converts to 4-vinyl guaiacol (clove). **[NASHA-UNTESTED]** include it, then a **saccharification rest around 64-66 °C** aiming at the {b['apparent_attenuation']:.0%} attenuation, then mash-out about 76 °C.
- **[EST]** Modern well-modified malts rarely need a protein rest; wheat's protein supports foam and haze. **[NASHA-UNTESTED]** no protein rest.
- Boil 60-75 min. Water: soft, low-alkalinity; **water chemistry is a brewer/lab decision** (no recipe is given here).

## 5. Hop selection rationale
- **[EST]** Hefeweizen uses hops only for balance; hop aroma should be nearly absent so it does not mask banana and clove.
- **[NASHA-UNTESTED]** a single bittering addition of a **{hops['type']}**, assumed {hops['assumed_alpha_pct']}% alpha acid, 60 min boil: about **{int(hops['grams_for_objective'])} g per {b['pilot_batch_l']} L** gives about {b['ibu_objective']} IBU by the Tinseth formula (**[EST]** formula; the alpha acid is an **[ASSUMPTION]**: use the lot's certificate). No late or dry hops.

## 6. Yeast considerations
- **[EST]** The style is defined by a **POF+ Bavarian wheat yeast**: it makes isoamyl acetate (banana) and 4-vinyl guaiacol (clove). Highly flocculent strains clear the beer and are a poor fit for a hazy hefe.
- **[EST]** Banana ester tends to rise with higher wort gravity, **lower pitch rate**, warmer fermentation and lower wort oxygen; clove tends to rise with ferulic-acid availability and moderate temperature. These are tendencies, not rules.
- **[NASHA-UNTESTED]** compare 2-3 candidate strains (datasheet candidates listed in the existing brief: Wyeast 3068, White Labs WLP380, Fermentis W-68; availability unverified) in split fermentations; score banana:clove ratio. Pitch at roughly half to two-thirds of a standard ale rate; the brewer sets the number.

## 7. Fermentation approach
- **[NASHA-UNTESTED]** pitch around 17-18 °C, allow primary to settle at about 19-21 °C for 4-6 days (log, do not assume), then a diacetyl/VDK check, then cool for conditioning. Open-top or shallow fermenters favour esters but are a brewer/sanitation decision.
- **Conditioning/packaging:** **[EST]** wheat beers are traditionally bottle- or keg-conditioned with yeast in suspension; for cans, yeast and viable-cell control, oxygen pickup and over-carbonation are real risks. **[NASHA-UNTESTED]** keg first (draft program) before any can run; canning needs a package-stability plan reviewed by the brewer.

## 8. Quality-control requirements (record on every pilot batch)
| Measurement | Method | Target / action |
|---|---|---|
| OG, FG (stable on two consecutive days) | densitometer or hydrometer | OG {b['og']:.3f}, FG {b['fg']:.3f}; record actual |
| **ABV (measured)** | densitometer/distillation-based method chosen by the brewer | compare with the {b['target_abv_pct']}% target; the measured value, not the target, governs any label |
| Mash pH, wort pH, finished pH | calibrated meter | record; the brewer sets windows |
| IBU | lab or stated calculation | window {b['ibu_window'][0]}-{b['ibu_window'][1]} |
| Colour, turbidity | SRM/EBC comparator; NTU if available | SRM {b['srm_window'][0]}-{b['srm_window'][1]}; decide the haze target at P1 |
| CO₂ volumes | measured, not assumed | {b['co2_volumes_window'][0]}-{b['co2_volumes_window'][1]} |
| VDK (diacetyl) forced test | before cold crash | no detectable diacetyl |
| Dissolved oxygen at packaging | meter | as low as practicable; limit set by the brewer |
| Foam height and retention | standard pour, stopwatch | collapse slower than about 3 minutes **[NASHA-UNTESTED]** |
| Microbiological check | brewer/lab | no spoilage organisms |
| Sensory panel | ≥ 5 trained tasters, blind, randomised, reference beers | banana 2.5±0.5, clove 2.5±0.5 (ratio about 1:1), bread/wheat 2, bitterness 1, hop aroma ≤ 0.5 (existing targets) |

## 9. Sensory goals (targets, not results)
Banana and clove balanced (ratio about 0.8-1.3), soft bread/wheat, high effervescence, dense persistent foam, no diacetyl/DMS/acetaldehyde/sulfur, no medicinal clove, no bubblegum banana, finish dry-ish and bright.

## 10. Established vs untested
| Established (published practice) | Untested NASHA formulation |
|---|---|
| POF+ yeast makes banana/clove; ferulic rest; wheat ≥ 50%; rice-hull aid; high carbonation; low IBU | the exact 55/45 bill and 3% hulls, the 64-66 °C rest for {b['apparent_attenuation']:.0%} attenuation, ~{int(hops['grams_for_objective'])} g hop charge, strain choice, 19-21 °C schedule, 4.7% as a delivered result |

## 11. Qualified review required before any brewing
Licensed head brewer (recipe, process, packaging, safety) · TTB formula/label status and TABC · allergen labelling (wheat/barley gluten) · water report · cold-chain policy · attorney (names). No logo or lockup in test materials beyond the approved concept art.
"""


def amba_doc(a):
    g = a["grist_kg"]
    m = a["mango_puree"]
    bitter_g = 80
    ibu_boil = B.tinseth_ibu(bitter_g, 12.0, a["pilot_batch_l"], 60, 1.050)
    return f"""# Pilot-batch formulation brief: AMBA HAZE mango-forward juicy IPA (working name; target ABV {a['target_abv_pct']}%)

{BANNER}

Tags: **[EST]** established brewing science or practice · **[NASHA-UNTESTED]** a NASHA hypothesis never brewed · **[ASSUMPTION]** a placeholder until measured. AMBA HAZE is an experimental concept outside the Core 5 (D-75); the no-IPA-at-opening reversible item B-2 is unchanged.
Pilot scale is undecided (G-6); {a['pilot_batch_l']} L into the fermenter is used only to make quantities concrete.

## 1. Style objectives
Juicy, soft and hazy; **mango-forward** from fruit plus hop-derived tropical aroma (mango, passion fruit, stone fruit), low perceived bitterness, round full mouthfeel, stable haze, no harsh astringency, no raw vegetal or onion/garlic hop character. Target ABV {a['target_abv_pct']}% (D-85).

## 2. Numerical targets
| Item | Target | Basis |
|---|---|---|
| Base-wort OG | {a['base_wort_og']:.4f} | computed so that, with fruit sugar, the beer reaches the ABV target **[NASHA-UNTESTED]** |
| Fruit sugar contribution | +{a['fruit_gravity_points']:.1f} gravity points | {m['kg_per_100_l']:g} kg puree per {a['pilot_batch_l']} L at an assumed {m['assumed_brix']:g} °Brix, treated as fully fermentable **[ASSUMPTION]** |
| OG including fruit | {a['og_with_fruit']:.4f} | |
| FG | {a['fg']:.3f} | hazy IPAs typically finish about 1.010-1.018 **[EST]**; the brewer sets the window |
| **ABV (target)** | **{a['target_abv_pct']}%** | founder target (D-85); formula gives {a['expected_abv_formula_pct']}% **[EST approximation; measure the beer]** |
| Bitterness | {a['ibu_objective']} IBU (window {a['ibu_window'][0]}-{a['ibu_window'][1]}) | **[NASHA-UNTESTED]**; late hopping keeps perceived bitterness low **[EST]** |
| Colour | SRM {a['srm_window'][0]}-{a['srm_window'][1]} | |
| Carbonation | {a['co2_volumes_target']} vol CO₂ ({a['co2_volumes_window'][0]}-{a['co2_volumes_window'][1]}) | typical IPA range **[EST]** |

## 3. Grain bill concept
| Malt/adjunct | % of grist | Pilot-batch mass ({a['pilot_batch_l']} L, assumed {a['assumed_efficiency']:.0%} efficiency) |
|---|---|---|
| Pilsner malt | {a['grist_percent']['pilsner malt']}% | {g['pilsner malt']} kg |
| Flaked oats | {a['grist_percent']['flaked oats']}% | {g['flaked oats']} kg |
| Wheat malt | {a['grist_percent']['wheat malt']}% | {g['wheat malt']} kg |
| Dextrin malt | {a['grist_percent']['dextrin malt']}% | {g['dextrin malt']} kg |
| **Total** | 100% | **{a['grist_total_kg']} kg** |

- **[EST]** Oats and wheat add protein and beta-glucan that support haze and a soft, full mouthfeel; flaked oats can make the mash viscous, so **rice hulls (about 3-5%)** are common. These are gluten-containing in a brewing context; no gluten-free claim.
- **[EST]** A low-sulfate, higher-chloride water profile is the usual practice for softness; **[NASHA-UNTESTED]** target a chloride:sulfate ratio above 1.5:1; the brewer and a water report decide.

## 4. Mango addition
- **Specification [NASHA-UNTESTED]:** {m['spec']}. {m['kg_per_100_l']:g} kg per {a['pilot_batch_l']} L is a **starting hypothesis**, not a tuned dose.
- **[EST]** Fruit sugar ferments and raises ABV (included above); fruit lowers pH, adds pectin and brings spoilage/refermentation risk; aroma is lost to CO₂ scrubbing if added too early.
- **[NASHA-UNTESTED]** add near the end of active fermentation, then hold for gravity stability before packaging. Alternatives to test: earlier addition (more fermented-out), a pectinase decision (haze vs clarity).

## 5. Hop selection rationale
- **Aim:** tropical mango/passion-fruit/stone-fruit aromatics with low bitterness.
- **[EST]** Citra-, Mosaic- and Galaxy-type hops are widely used for tropical aroma (high in geraniol, linalool and thiol precursors). Nelson Sauvin- or El Dorado-type hops add white-wine/stone-fruit notes but can turn harsh or catty at high rates.
- **[NASHA-UNTESTED]** a Citra + Mosaic + Galaxy-class blend, availability and prices unverified.
- **Schedule hypothesis [NASHA-UNTESTED]:** about {bitter_g} g of a clean ~12% alpha bittering hop at 60 min (≈ {ibu_boil:.0f} IBU by Tinseth **[EST formula; alpha is an ASSUMPTION]**), a **whirlpool/hop-stand** charge of about 5 g/L at roughly 80 °C for 20 min (adds bitterness that the Tinseth boil formula does not model; expected roughly 8-15 IBU, **measure**), and **dry hops** totalling about 8-12 g/L split across the active-fermentation window. Total bitterness is judged by lab IBU against the {a['ibu_objective']} IBU objective.
- **[EST]** Dry-hopping during active fermentation can transform hop terpenes and release thiols (biotransformation); it also carries oxygen and **hop creep** risk (below).

## 6. Yeast considerations
- **[EST]** Haze-friendly IPA yeasts are ester-forward (stone fruit, citrus), of low-to-medium flocculation, and ferment around 19-22 °C. A cleaner American ale strain lets hops and fruit lead.
- **[NASHA-UNTESTED]** compare a London Ale III-type strain (stone-fruit esters, haze) with a clean American ale strain in split fermentations; choose by mango-forward score and stability. Strain names and availability are unverified.

## 7. Fermentation approach
- **[NASHA-UNTESTED]** pitch around 18 °C, rise to about 20-21 °C, dry-hop on day 2-3, add mango near the end of active fermentation, then hold at a stable gravity before a gentle cold crash. Closed transfers throughout.
- **[EST]** Oxygen control is critical in hazy IPAs: oxygen pickup after fermentation causes rapid oxidation (darkening, loss of juicy aroma, stale/cardboard notes).

## 8. Package-safety requirements (cans)
- **[EST]** **Hop creep**: enzymes from dry hops can re-ferment dextrins, dropping FG and over-pressurising packages. Require a **stable FG for several days after the last dry hop** and a **forced-fermentation test** on a warm sample before any can run.
- **[EST]** Fruit and dry hops raise microbial-stability questions; keg first, can only after the brewer approves a stability plan.
- Allergen/ingredient statements as packaged (barley, wheat, oats; check puree for sulfites) are provisional until reviewed.

## 9. Quality-control requirements (record on every pilot batch)
| Measurement | Method | Target / action |
|---|---|---|
| OG (base wort), post-fruit gravity, FG stable ≥ 3 days | densitometer | base OG {a['base_wort_og']:.4f}; FG {a['fg']:.3f}; record actual |
| **ABV (measured)** | method chosen by the brewer | compare with the {a['target_abv_pct']}% target; the measured value governs any label |
| pH (mash, wort, beer) | calibrated meter | the brewer sets windows (hazy IPA beer pH is typically around 4.2-4.6 **[EST]**; fruit lowers it) |
| IBU | lab or stated calculation | window {a['ibu_window'][0]}-{a['ibu_window'][1]} |
| Colour, turbidity (NTU), haze stability | comparator; cold storage 4 weeks at 4 °C and an accelerated warm hold | stable haze, no gel/chill-haze collapse |
| CO₂ volumes | measured | {a['co2_volumes_window'][0]}-{a['co2_volumes_window'][1]} |
| Dissolved/total package oxygen | meter | as low as practicable; limit set by the brewer |
| Hop-creep forced-fermentation test | warm sample, 3-5 days | no gravity drop |
| Microbiological check (incl. yeast/mould from fruit) | brewer/lab | no spoilage organisms |
| Sensory panel | ≥ 5 trained tasters, blind | see §10 |

## 10. Sensory goals (targets, not results)
Mango/tropical fruit 3, citrus/stone fruit 2.5, resin/pine ≤ 1, perceived bitterness 1.5, soft round mouthfeel 3, stable haze; no diacetyl, no vegetal/onion-garlic, no astringency, no oxidation, no solvent/fusel. **No tasting has been performed.**

## 11. Established vs untested
| Established (published practice) | Untested NASHA formulation |
|---|---|
| Oats/wheat for haze and body; hop-stand and dry-hop aroma; biotransformation; DO control; hop creep; fruit sugar ferments | the exact grist, {m['kg_per_100_l']:g} kg/{a['pilot_batch_l']} L puree, {bitter_g} g bittering + ~5 g/L whirlpool + 8-12 g/L dry hop, strain choice, addition timing, {a['target_abv_pct']}% as a delivered result |

## 12. Qualified review required before any brewing
Licensed head brewer · TTB formula approval for a fruit beer and label review · TABC · allergen labelling · puree supplier specification · microbiological and package-stability plan · attorney (the working name AMBA HAZE is unscreened).
"""


def main():
    sp = S.specs()
    out = {
        ROOT / "beer/specs/BEER-SPECIFICATIONS-V1.md": spec_doc(sp),
        ROOT / "beer/pilot-briefs/06-badshah-formulation-brief.md": badshah_doc(sp["beers"][0]),
        ROOT / "beer/pilot-briefs/07-amba-haze-formulation-brief.md": amba_doc(sp["beers"][1]),
    }
    for p, t in out.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t)
    S.write()
    return out


if __name__ == "__main__":
    for p in main():
        print(p.relative_to(ROOT))
