AGENT ANALYSIS - NOT PROFESSIONAL REVIEW - NOT EVIDENCE

# Core 5 commercial logic (system view, pre-sales)

**Status:** planning hypotheses only. Nothing has been cooked, tasted, costed, priced or sold. `ops/menu-engineering/core5-fields.csv` is blank (no units, price, cost, mix, waste, score), so **no Star/Plowhorse/Puzzle/Dog classification, no price, no margin, no food-cost % is given or implied.** `food/costing/recipes.csv` quantities are all "QUANTITY NOT SET"; `ingredients.csv` prices are blank. A chef, food-safety professional, accountant and (for any alcohol link) a Texas alcohol attorney own the real decisions. D-54 holds (no beef/pork; goat reads as goat; no halal claim). D-74 frozen. D-76/D-77 are agent-proposed, unconfirmed. Mustard oil excluded (V-72).

Labels: **OBS** = read in a repo file; **INF** = agent inference; **UNK** = unknown.
Abbreviations: C65 = Chicken 65 Totopos, PT = Paneer Tikka Taco, GB = Goat Birria, GT = Gobi Taco, BC = Butter Chicken Quesadilla. Matrix = `food/CORE5-FOOD-MATRIX.csv`; Cap = `ops/kitchen/capacity-assumptions.json` (invented ranges, not data); Ops = `docs/OPERATIONAL-REQUIREMENTS-CORE5.md`.

## 1. The five dishes as a system (qualitative H/M/L; all INF unless marked)

| Dimension | Reading | Basis (matrix column / file) |
|---|---|---|
| Ingredient overlap | **M**. OBS from recipes.csv: onion in all 5; corn tortilla in 4 (BC uses flour, open); lime 4; cilantro 3; yogurt 3; ginger-garlic 3. Proteins and dried chiles do not cross (chicken only C65+BC). | `core_ingredients`; `food/costing/recipes.csv` |
| Prep overlap | **M-L**. Shared: onion/lime/cilantro cut, tortilla warm. Distinct: marinade (C65, PT), long braise (GB), blanch+roast (GT), sauce reduction (BC). Five different prep tracks. | `cooking_method`, `proposed_construction` |
| Sauce overlap | **L**. Crema (C65), salsa verde (PT), adobo/consomme (GB), tamarind-guajillo glaze + slaw (GT), makhani (BC). Only guajillo (GB, GT) and yogurt marinades (C65, PT) cross. | `core_ingredients`, `acid` |
| Equipment overlap | **M**. Comal appears in 4 dishes (PT, GB, GT, BC) and is the heavy one for BC and GB; fryer only C65 (GT only if batter arm wins); char only PT (+BC chicken); oven GT and GB. | `equipment`; Ops s1 |
| Cook-time distribution | **Wide / bimodal**. GB hours ahead (long lead) then fast order-fire; C65, PT, GT, BC are minutes to order. Per-plate comal slot-minutes (assumed base): BC 18, GB 6, PT 1.4, GT 1.4, C65 0. | `cooking_method`; Cap (ASSUMPTION) |
| Vegetarian coverage | **M**. 2 of 5 (PT, GT) clearly; both contain milk; paneer rennet and tortilla lard to verify; strict status unconfirmed. C65, GB, BC contain meat. Fryer cross-contact if GT goes batter-fried. | `d54_risk`, `allergens_proposed`; ingredients.csv `vegetarian` |
| Protein coverage | **M**. Paneer, cauliflower, chicken (x2), goat. No fish, no lamb in Core 5. Chicken is 2 of 5 (concentration risk, not a flaw). | `core_ingredients` |
| Spice-level coverage | **M**. attr_heat: C65 3, PT 2, GB 2, GT 2, BC 1 (0-5 scale, agent-assigned, not tasted). Mild-to-medium only; no high-heat option. | `attr_heat`, `heat` |
| Texture diversity | **H**. Crisp-fried (C65), char/soft (PT), tender-fibrous + liquid (GB), roasted-crunch + slaw (GT), crisp-shell/melted (BC). | `texture_target` |
| Visual diversity | **H**. Red-orange board, two tacos with char, tacos + consomme cup, dark-tipped florets, cut wedge cross-section. Two are two-taco plates (PT, GT) and look alike at a glance (INF). | `service_vessel` |
| Takeout suitability | **M-L overall**. BC best (but steams if covered), GB tacos fair if consomme packed separately; C65 worst (10-min crispness gate), PT/GT soften. All UNTESTED. | `holding_risk` |
| Hold-time risk | **M-H**. C65 HIGH; GB HIGH (bulk braise cooling/reheat/hold, a food-safety professional sets this); PT and GT MEDIUM-HIGH; BC MEDIUM. | `holding_risk` |
| Labor intensity | **M-H**. Cap (assumed): cooks are the bottleneck in about half of equal-mix samples; GB and BC highest cooks slot-minutes (base 1.6 each); GB has the heaviest back-of-house prep. | Ops s2; Cap |
| Waste exposure | **M-H, mostly UNK**. GB highest (trim/yield unknown, `execution_risk` HIGH, long lead, batch-sized); fresh cauliflower, cilantro, poblano, paneer perishable; fried C65 chips are a waste/oil item. No waste_pct measured. | `execution_risk`; core5-fields (blank) |
| Customer accessibility | **M**. Most accessible INF: BC (familiar cheese/quesadilla, mildest, heat 1), GT/PT (taco form). Least: GB (goat, very high richness) and C65 (heat 3, fried). Zero customer data. | `attr_*`; `richness` |
| Signature potential | **H for C65 and GB, M for PT, BC, L-M for GT**. C65 = the "chip becomes the plate" idea; GB = goat identity; PT and BC are recognisable crossovers; GT has least differentiating claim (matrix: "no traditional Mexican precedent claimed", confidence low-medium). | `nasha_transformation`, `confidence` |

**System observations (INF):** (a) The set is diverse in texture and look but thin on shared prep, so complexity scales roughly with item count. (b) Comal is the common constraint (Ops s2); labour second. (c) The set has no cold/fresh or sweet component beyond slaw and garnish (see the options below; no new dish proposed). (d) Spice range is narrow.

## 2. Role hypotheses (HYPOTHESES, not validated)

| Role | Hypothesis | Reasons (INF) | What would overturn it |
|---|---|---|---|
| **HERO PRODUCT** | Chicken 65 Totopos | Strongest single identity claim ("chip becomes the plate"); shareable; fryer is not the limiting station in the assumed ranges; Session 1 protocol is the only frozen, ready-to-cook item (D-74); pairs with Mexican Lager/Pilsner per matrix. | Fails the 10-minute crispness gate (all three constructions); fry-to-table time makes it unsuitable off-site; guests rate it below other items; advisor says the name or form misrepresents the dish. GB is the alternate hero if goat sells out repeatedly. |
| **ACCESSIBLE PRODUCT** | Butter Chicken & Roasted Poblano Quesadilla | Mildest (heat 1), familiar cheese format, lowest hold risk (MEDIUM), supports families. | Comal minutes per plate prove too high (assumed 18, the heaviest) so it throttles service; leak/sog cannot be controlled; guests find it generic; Taco forms (PT) prove more approachable. |
| **VEGETARIAN HERO** | Paneer Tikka Taco | Char and salsa/acid architecture gives it a stronger "dish" identity than GT; paneer is robust; GT's design is still unresolved (fry vs roast conflict; confidence low-medium). | Tandoor/charbroiler path is not feasible (unresolved) and the comal substitute is flat; paneer dries within the hold window; GT beats it in Session 2/3 tasting; vegetarian guests prefer GT's crunch; rennet issue prevents a vegetarian claim. |
| **OPERATIONAL RISK PRODUCT** | Goat Birria (first), Butter Chicken Quesadilla (second, comal) | GB: long lead, sourcing, unknown yield, cooling/reheat/hold process, HIGH on both holding and execution. BC: highest assumed comal load, drives the comal-heavy bottleneck (~80% of samples). | Real braise yield and cooling data are benign and a commissary can do it; comal measured much faster than 18 slot-min; C65 fryer/oil handling turns out harder than assumed. |
| **CULINARY CREDIBILITY PRODUCT** | Goat Birria | Closest to a named traditional dish (Jalisco birria de chivo) so a Mexican advisor/chef can judge fidelity; D-54 forces goat, which strengthens the claim. Credibility lives or dies on the plain-adobo control vs the Indian layer. | Blind test (vs lamb taco, plain adobo) shows no difference or the Indian layer harms it; advisor review rejects the framing; goat cut/age not obtainable. Alternative: PT (tradition-rooted in Punjabi restaurants) if GB is not feasible. |

Disagreement-free note: these roles do not conflict with D-54, D-66, D-74.

## 3. Menu architecture options for a capital-efficient MVP (if Core 5 testing succeeds)

Not costed: no dollar or percent figures. "Average ticket" is directional only.

| Option | SKU complexity | Prep complexity | Guest choice | Throughput | Waste | Inventory | Identity | Avg-ticket potential | Beer pairing | Veg access |
|---|---|---|---|---|---|---|---|---|---|---|
| **3-item MVP** (e.g. C65, PT, BC) | Low | Low-M (marinades + one sauce; no braise) | Low-M; one veg, one share, one gateway | Highest of the options (no GB; comal still BC-bound) | Low | Small; ~13 distinct ingredients (INF) | M; no goat, so the differentiator is missing | Lowest | Lager/Pilsner (C65), Vienna (BC), Witbier (PT) | Low (one dish) |
| **5-item Core 5** | M-H | H (five parallel prep tracks, long-lead goat) | M-H | Comal and labour bound (Cap/Ops) | M-H (GB, perishables) | Largest produce/dairy spread; two tortilla types | **H**; full identity | Moderate | Strongest: all five beers have a first-flight dish (matrix `pairing_first_flight`) | M (2 dishes) |
| **Core 5 + 2 sides** | H | H plus (adds two prep tracks) | H | Sides can ease wait or add fryer/comal load | M-H | Wider | M-H, dilutes if sides are generic | Higher | Neutral-to-helpful | Depends on side; **UNK** |
| **Core 5 + dessert** | H | H plus (a sweet track; fryer or cold) | H | Small extra; end-of-meal slot | M (low-volume item) | Slightly wider | M-H | Higher via add-on | Dessert-beer pairing UNTESTED | Likely yes (INF) |
| **Core 5 + rotating special** | H, variable | H, unpredictable | H | Variable | M-H; also uses leftover prep | Variable | M-H; can carry beer-collab story | Directional uplift, unknown | Can be written around a beer | Variable |

"Sides", "dessert" and "special" are placeholders; **no new dish is proposed here.** The repo's 12-dish test set (validation/MOBILE-MVP-STRATEGY.md s5) already names candidates (e.g. chaat elote, churros); those are not Core 5 and are untested.

### Which vehicle could run which format (INF; verify permits/legal with the relevant authority and attorney)
Basis: validation/MOBILE-MVP-STRATEGY.md s2-s4 (T1/T3 sources, unverified).

| Vehicle | 3-item | 5-item | +sides | +dessert | +special | Constraint |
|---|---|---|---|---|---|---|
| Private tasting | Yes | **Yes** (pre-ordered small portions; goat batch fits) | Yes | Yes | Yes | Alcohol sale/service structure: Texas alcohol attorney. Best place to test pairing without selling beer. |
| Pop-up (commissary-based) | Yes | **Likely** (commissary kitchen supports braise) | Likely | Likely | Yes | Host, commissary and permit status UNK. |
| Brewery residency | Yes | **Likely, host kitchen limits UNK** | Possible | Possible | Yes | Host constraints (fryer/comal availability, hood); host sells beer, not NASHA. |
| Trailer | Yes | Tight: comal and fryer both needed; goat braise must come from a commissary | Unlikely | Unlikely | Possible | Menu usually 4-8 items; equipment and fire approvals; cannot sell alcohol. |
| Truck | Yes | Tight (as trailer) | Unlikely | Unlikely | Possible | Highest asset commitment; no alcohol; kitchen is cramped. |

### Provisional recommendation (HYPOTHESIS)
**Phase structure: a 5-item Core 5 at a small-portion private tasting and commissary pop-up, then reduce to the dishes that earned a place.** Concretely:
1. Learning vehicle = private tasting / commissary pop-up (matches the "best learning per dollar" ordering in validation/MOBILE-MVP-STRATEGY.md s4).
2. Full 5 dishes in small portions for the first rounds so every dish gets a verdict (hold-time, comal minutes, goat yield, vegetarian preference). Order-fire only; goat as a pre-announced limited batch (sell-out frequency is itself data).
3. Before any trailer or residency, cut to a **3-4 item running menu** chosen from measured ticket time and waste: provisionally C65 (identity), one vegetarian (PT or GT), one gateway (BC), goat only if yield/cooling are proven. Add one rotating special only after the core is stable.
4. No sides or dessert in the first rounds (extra variables).

**This optimises learning and execution, not the eventual opening menu.** The flagship menu, pricing and size are open for the founder, chef, and an accountant. Beer pairing claims stay hypotheses until tasted with real beer.

## 4. Data that would change the recommendation
1. Measured comal minutes per quesadilla and per goat taco (Session 4/5); could move BC out of the first round or confirm it.
2. C65 crispness at T+10 for each construction (Session 1); decides hero vs not and takeout/trailer suitability.
3. Goat: supplier, cut, trim/yield, cooling and reheat times, hold; decides whether GB can run at all off a commissary.
4. Paneer char outcome by heat source and hold (Session 2); tandoor/charbroiler feasibility; Gobi fry vs roast decision.
5. Tasting scores per dish (core5-fields `customer_score_0_5`), repeat orders and sell-outs; the only data that can justify any quadrant classification.
6. Real ingredient prices and recipe quantities (costing files) and an accountant-reviewed cost basis; none exists.
7. Commissary/host kitchen availability, permit and fire path, brewery willingness (validation/MOBILE-MVP-STRATEGY.md s4 unknowns).
8. Vegetarian guests' stated preference, and rennet / lard / stock verification for a vegetarian claim.
9. Professional input: chef (feasibility), food-safety (goat process), Mexican and Indian cultural advisors, alcohol attorney.

## 5. Recorded disagreement / reconciliation
- **validation/MOBILE-MVP-STRATEGY.md s5 vs Core 5 (who: that doc's 12-dish set; what: lists a Tandoori Lamb Taco, Chaat Elote and Churros and assigns Gobi Taco to a fryer, flour tortilla for the quesadilla and "Raita-Crema" dip; why it differs: it predates the Core 5 decision).** Core 5 matrix has Gobi roast-first, no lamb, crema/dip still open. This document follows the Core 5 matrix; the MVP doc's menu should be reconciled by its owner. Not silently merged.
- Matrix itself flags unresolved conflicts (Gobi fry vs roast; BC "raita-crema" vs makhani dip; tortilla type), which affect every comparison above.
