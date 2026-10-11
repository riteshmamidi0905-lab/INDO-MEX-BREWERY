# Pilot Brief: Hefeweizen (SONA): the gate beer

**Status:** brewer-facing brief. **Nothing has been brewed.** This is a *specification of intent and a test plan*, not a recipe. **No** grist, hop weights, spice doses, brewhouse efficiency, water chemistry, pitch rates, fermentation schedules or production yields appear here, and none may be inferred from it: they are the **licensed head brewer's professional responsibility** and come only from real brewing work. Reference ranges: BJCP 2021 via search extracts (`S-107, S-108`; open the PDF before use). Targets are `[TEST]`. Parent documents: `beer/OPENING-BEER-PROGRAM-V1.md`, `beer/HEFEWEIZEN-BENCHMARK.md`. Pairings: `food/MENU-V1.1-TEST-MENU.md`.

## 1. Intended sensory identity
A traditional South German-style Hefeweizen a Bavarian would respect: hazy gold, tall dense white foam, **banana and clove in balance** with soft bread/wheat, high carbonation, dry-ish bright finish, low bitterness, drinkable in volume, outstanding with chile heat and fat. No fruit, spice or novelty ingredient, ever. (Older wording "if this beer fails, nothing launches" is superseded: see 00-BREWER-HANDOFF.md section 0b and BREWER-REVIEW-FORM.md; thresholds are founder/R&D proposals a brewer should set.)

## 2. Style reference and target ranges
| Item | BJCP reference | Our R&D window `[TEST]` |
|---|---|---|
| OG / FG | 1.044-1.053 / 1.008-1.014 | 1.048-1.052 / 1.010-1.013 |
| ABV | 4.3-5.6% | 4.8-5.3% |
| IBU | 8-15 | 10-13 |
| SRM | 2-6 | 3-5 |
| Carbonation | high | ~3.0-3.8 vol CO₂ (to be set by the brewer) |
| Sensory (0-5) | banana, clove | banana 2.5±0.5, clove 2.5±0.5 (ratio ~1:1), bread/wheat 2, bitterness 1, hop aroma ≤0.5 |

## 3. Unacceptable faults (any detectable at panel = batch review)
- Banana above ~4 (candy/bubblegum) or clove above ~4 (medicinal); either at 0-1 (boring)
- Banana:clove ratio outside ~0.8-1.3
- Diacetyl, DMS, acetaldehyde, sulfur or any infection
- Excess vanilla/smoke phenolics (>1)
- Thin or fast-collapsing foam (< ~3 min visible); flat carbonation
- Over-clear beer if haze is intended, or heavy sediment taste

## 4. Service
| Item | Value |
|---|---|
| Serving temperature | 4-7 °C (39-45 °F) `[U; TEST]`; start tests at 5 °C |
| Glass | Collar Weizen (0.5 L beer, ~0.68 L brim, 3-4 cm head), rinsed cold, never frozen |
| Pour / ritual | **Two-Pour:** pour ~80-85% at an angle, rest, swirl the yeast, finish upright. No fruit garnish by default. |
| Food pairings (test set) | Chicken 65 Totopos, Hefe-Brined Wings, Paneer Tikka Taco, Butter Chicken Rajas Quesadilla, Malabar Fish Taco |

## 5. QC measurements to record on every pilot batch
| Measurement | Method (head brewer to specify) | Record |
|---|---|---|
| Original and final gravity; ABV | Hydrometer/densitometer | |
| Wort pH and finished-beer pH | Calibrated meter | |
| IBU | Lab or calculation, stated | |
| Colour (SRM/EBC) | Spectrophotometer or comparator | |
| Turbidity / appearance | Visual and NTU meter if available; decide the target haze at P1 | |
| Carbonation (volumes CO₂) | Measured, not assumed | |
| Diacetyl/VDK check | Forced test before cold crash | |
| Packaged dissolved oxygen | Meter (kegs) | |
| Foam: head height and retention (stopwatch) | Standard pour, same glass | |
| Microbiological check | Head brewer / lab | |
| Days in tank by stage (log, do not assume) | Brewer's log | |

## 6. Sensory panel structure
- **Panel:** at least 5 trained tasters (brewer, chef, two guests with beer training, one outsider), blind, randomised order, water and plain cracker between samples.
- **Samples:** pilot beer plus 3 classic German weissbiers plus 1 Texas hefeweizen commercial reference beers (below) plus one duplicate for consistency.
- **Scoring:** 0-5 per attribute (banana, clove, bread/wheat, vanilla/smoke, citrus/ester, bitterness, body, finish, foam, haze), plus overall quality and "would order a second" yes/no.
- **Records:** `beer/pilot-log/` (create when brewing begins): batch ID, date, observations, scores, decisions.

## 7. Reference beers (choose and record at P2; availability and exact specs to be confirmed)
- Weihenstephaner Hefeweissbier, Schneider Weisse (Tap 7), Ayinger Bräu-Weisse (German references named in the benchmark; confirm availability)
- Live Oak Hefeweizen (Texas reference; 5.3% ABV, 10 IBU per the brewery, `S-116`)

## 8. Pilot questions to answer
1. Which POF+ weizen yeast gives the banana/clove balance the panel scores best (candidates by datasheet: Wyeast 3068, White Labs WLP380, Fermentis W-68; highly flocculent strains are a poor fit for a hazy hefe)?
2. How do fermentation temperature and pitch rate move banana vs clove in *our* equipment (design the trial with the head brewer; sources disagree)?
3. Does a ferulic-acid rest change clove at our scale (an independent homebrew test reportedly found no difference: verify)?
4. Open vs closed fermentation, if equipment allows.
5. How does Austin tap water need to be treated for this beer (lab-test the water first)?
6. Can we hold carbonation, foam and haze consistent keg to keg?
7. How fast does quality fall after packaging (freshness window)?

## 9. Pass / fail gate
**PASS** only if: all faults 0; banana and clove each within ±0.5 of target and ratio ~1:1; foam ≥ ~3 minutes; independent panel average ≥ the reference average; three consecutive batches consistent. **FAIL** otherwise: revise and repeat; see the CONTINUE / REVISE / DE-PRIORITIZE / REMOVE outcomes in 00-BREWER-HANDOFF.md section 0b.

## 10. What remains the head brewer's professional responsibility
Recipe design (grist, hops, adjuncts), mash and water strategy, yeast selection and pitching, fermentation and conditioning schedules, lager time, carbonation and packaging, sanitation and safety, QC methods and limits, scale-up, TTB/regulatory formula questions, and the decision to proceed or stop. This brief gives the intent and the gates only.
