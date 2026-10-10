# Hefeweizen Sensory Benchmark Specification (v1)

**Audience:** a professional head brewer. **Status:** direction, not a recipe. Every number is a **development target `[TEST]`**; anything outside BJCP is labeled with confidence. No proprietary recipes were consulted or reverse-engineered. No novelty ingredients (no mango, saffron, chile, tamarind) in this beer, ever.

## 1. Intent in one paragraph
A traditional South German-style Hefeweizen that a Bavarian would respect: brilliant hazy gold, tall dense white foam, **clove and banana in balance with soft bread/wheat**, high carbonation, dry-ish bright finish, low bitterness, drinkable in volume, outstanding with chile heat and fat. If we cannot brew this consistently, nothing else launches.

## 2. Style envelope
| Parameter | Target | Basis |
|---|---|---|
| Style | BJCP 10A Weissbier (Hefeweizen) | `[V S-06]` |
| OG / FG | **BJCP 10A: 1.044-1.053** / 1.008-1.014 (aim mid-range). *Corrected (Phase 2): 1.057 is the 10B Dunkelweizen upper bound* | `[V S-06, S-107]` |
| ABV | 4.8-5.4% (envelope 4.3-5.6%) | `[V S-06]`; narrowed by us |
| IBU | **8-15** (BJCP 10A; our window 10-13). *Corrected (Phase 2): 10-18 is 10B* | `[V S-06, S-107]` |
| SRM | **2-6** (BJCP 10A); our window 3-5. *Resolved (Phase 2): the 14-23 text was the 10B Dunkles range; re-confirm against the official PDF* | `[V S-107]` |
| Wheat | ≥50% malted wheat (BA rule); typical commercial practice higher `[U]` | `[V S-07]` |
| Carbonation | ~3.0-3.8 vol CO₂ (high) `[TEST]` | 3.0 vol cited `[S-44]`; upper range from practice `[U]` |
| Appearance | Hazy, pale-to-deep gold, long-lasting white head | `[V S-06]` |

## 3. Sensory targets (scale 0-5; target ± tolerance)
| Attribute | Target | Fault boundary |
|---|---|---|
| Banana (isoamyl acetate) | 2.5 ± 0.5 | >4: candy/bubblegum fault `[V S-06]` |
| Clove (4-VG) | 2.5 ± 0.5 | >4: medicinal; 0-1: boring |
| Banana : clove ratio | 1 : 1 (accept 0.8-1.3) | |
| Bread/wheat/dough | 2 | |
| Vanilla/smoke (phenolic extras) | ≤1 | |
| Citrus/ester hint | 1 | |
| Hop aroma | ≤0.5 | |
| Bitterness | 1 | |
| Sulfur/diacetyl/DMS/acetaldehyde | 0 | any detectable = batch review |
| Body | Medium-light, creamy, fluffy | |
| Finish | Dry, bright, slightly tangy | |
| Foam | Dense, white, ≥3-4 min visible lacing | |

## 4. Process considerations for the brewer (confidence flagged)
1. **Grain bill:** high-wheat; pilsner malt + wheat malt, optionally small Munich/Vienna for color/bread; discuss whether to use a decoction or step mash. `[Unresolved: confirm with Warner / Weihenstephan literature]`
2. **Ferulic acid rest** (~43-45 °C / 110-113 °F, ~15 min) to feed clove precursors. `[Medium: S-44a]`
3. **Yeast:** a POF+ weizen strain with documented banana/clove expression from a major supplier; choice must be validated in pilot, because strain matters more than any single setting. `[Medium-low]`
4. **Fermentation temperature and pitch rate** shape the banana/clove balance; sources disagree (62-66 °F / 17-19 °C cited; ~0.5 M cells/ml/°P cited once). **Run a designed trial** (3 temps × 2 pitch rates) and measure by sensory + GC if available. `[TEST]`
5. **Open vs closed fermentation:** unresolved; test if equipment allows; closed conicals are standard in the US. `[Unresolved]`
6. **Carbonation and packaging:** high-CO₂ requires kegs/bright tanks rated and serving lines balanced (keg pressure and line length); bottle-conditioning is a possible Reserve path (Erdinger is bottle-conditioned `[V S-43c]`).
7. **Yeast in suspension** for hefe: decide target turbidity (NTU) and sediment strategy. `[TEST]`
8. **Freshness:** serve within weeks; no extended hold; date every keg. Wheat beer ages poorly. `[U]`
9. **Water:** soft-to-moderate; Austin water profile to be tested and adjusted; flag for brewer. `[PRO]`

## 5. Serving specification
- **Temperature:** 4-7 °C (39-45 °F). `[U; TEST]`
- **Glass:** tall weizen vase (see hero glass), rinsed cold, never frozen; volume 0.5 L pour with room for 3-4 cm head.
- **Pour:** tilt 45°, pour 80-85% slowly, rest, swirl last portion to lift yeast, finish upright. Ritual: **Two-Pour** (see rituals).
- **No fruit garnish by default.** (The lemon/orange wedge is an American habit; offer on request only.)

## 6. Food pairing logic `[C]`
Carbonation scrubs fat; banana/clove echo warm spice (clove ↔ cardamom/clove in garam masala; banana ↔ fried-plantain, coconut); low bitterness leaves chile heat unamplified. Best: Chicken 65 totopos, wings, birria, paneer tikka tacos, dal-based dishes, fish tacos. Worst: very bitter or very sweet dishes.

## 7. Evaluation protocol (to hand to a sensory panel)
1. Buy 3 fresh reference weissbiers from major German producers (e.g., Weihenstephaner, Schneider, Ayinger) and one Texas-brewed hefe (e.g., Live Oak). Taste blind with water/cracker between samples.
2. Score each attribute above 0-5. Record pour height, head retention (stopwatch), turbidity, pH, FG, ABV.
3. Pilot batch acceptance: all faults 0; banana and clove each within ±0.5 of target; foam ≥3 min; independent panel (≥5 trained tasters) average ≥ the reference average.
4. Log everything in `beer/pilot-log/` (create when brewing begins).

## 8. Open items
Official BJCP SRM check; Warner/Weihenstephan technical references; yeast supplier data sheets; Austin water report; licensed brewer review `[PRO]`.
