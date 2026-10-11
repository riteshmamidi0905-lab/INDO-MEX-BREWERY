# Operational requirements for the Core 5 (for a restaurant architect and an equipment/kitchen consultant)

**Status: PLANNING INPUT. Not an architect-approved plan, not a HACCP plan, not a code review.** Nothing here has been cooked, timed or reviewed by a person. Capacity numbers are assumptions (`ops/kitchen/capacity-assumptions.json`, rebuilt by `python3 tools/kitchen_capacity.py`), labelled CAPACITY PLANNING EXERCISES. Food-safety figures are T4 (general knowledge of US FDA Food Code values, not read from the Code) used as planning defaults and are UNVERIFIED for Austin/Texas; the health authority decides.

## 1. What the five dishes ask of a kitchen
| Station | Chicken 65 Totopos | Paneer Tikka Taco | Gobi Taco | Butter Chicken Quesadilla | Goat Birria |
|---|---|---|---|---|---|
| Deep fryer | Chicken and chips (main load) | none | only if the batter-fried arm wins | none | none |
| Comal / plancha | tortilla-free | tortilla warm, paneer finish (arm B) | tortillas, glaze set | **heaviest: griddling every quesadilla** | dip and griddle tacos, warm tortillas |
| Char (charbroiler, tandoor or substitute) | none | paneer char (arm A; tandoor only if real) | none (oven roast) | chicken char | none |
| Oven / combi | none | none | roast cauliflower | none | sealed-pot braise (hours) |
| Cold storage | marinated chicken, crema | hung curd, paneer | cauliflower, slaw | sauce, filling, cheese | braised goat, consomme, **cooling capacity** |
| Hot hold | chips (short window), consomme | none (order-fire) | none | sauce | consomme |

Unknowns to put to the professionals: whether a tandoor or a charbroiler is wanted (and hood, clearances, fire-suppression, gas/solid-fuel constraints: regulatory matrix says NOT FOUND, not resolved); comal/plancha size and heat-recovery; fryer oil volume and a dedicated vegetarian oil path (cross-contact with chicken in one fryer is a real design question: allergen matrix lists contains vs may cross-contact); walk-in space for braise cooling; ventilation for charred chile smoke.

## 2. Capacity planning exercise: where the pressure is
Method: slot-minutes per plate with low/base/high ranges, seeded random draws from the invented ranges (1-3 fryer baskets, 8-16 comal positions, 2-4 cooks, 1-2 pass positions). Orders arrive at once (10, 20, 30). Clear time is a lower bound (no queueing delay, no walking).
- **Equal mix:** cooks (labour) is the bottleneck in about half of sampled ranges (clear time roughly 5 / 9 / 14 min at 10/20/30 orders, base case); comal and pass each roughly a quarter. The fryer is never the limit in these assumed ranges. Shares are the fraction of INVENTED ranges in which a station comes out highest, not a probability of anything real.
- **Comal-heavy mix (goat + quesadilla popular):** the comal is the bottleneck in about 80% of samples; roughly 7 / 14 / 21 min at 10/20/30 base case. The quesadilla alone (assumed 18 slot-minutes per plate) drives this. **Measure first:** minutes one quesadilla occupies a comal position at service temperature, and how many positions are usable at once.
- **Fry-heavy mix (Chicken 65 popular):** cooks again about 54%, fryer about 18%, pass about 28%.
- Reading: this assumption set points to labour and comal rather than the fryer; no kitchen data exists. Real ticket times would change that; until then it is a hypothesis, not a forecast.

## 3. What to measure first (cheap, in a home kitchen or pop-up)
1. Quesadilla comal minutes per plate (Session 4 times record this).
2. Paneer char time per batch and holding (Session 2).
3. Goat braise yield, cooling time from 135 F to 70 F and to 41 F (FDA general planning figures, unverified for Austin) in shallow pans vs ice bath (Session 5).
4. Chicken 65 fry-to-plate time and chip crispness decay (Session 1).
Then rerun the capacity exercise with measured values and delete the assumptions they replace.

## 4. Goat production flow (planning sketch for professional review)
Receive (tag, temperature, supplier documentation to verify) -> trim/portion -> adobo (toast whole spices, fry the paste) -> sealed pot braise in oven -> **cool in shallow pans / ice bath** (planning figures: 135 to 70 F within 2 h, then to 41 F within 4 more h) -> refrigerated storage with date label -> reheat to 165 F within 2 h -> hot hold at 135 F or higher (consomme) -> order-fire dip and comal. Review points for a food-safety professional: cooling method and capacity, reheat limits, whether the Austin authority requires a variance for any step, labelling and shelf life. No claim of HACCP approval.

## 5. Glass-system options (service, not kitchen)
Five shapes (current V2), three (tall Hefeweizen, tall Pilsner/Mexican lager, short Vienna/Witbier) or two (tall and short). Operations preference: fewer shapes (rack, polish, breakage, inventory); brand/style preference: five. Unresolved; manufacturer and bar manager input needed. Collar ring is OFF by default (adds manufacturing and cleaning risk, grip benefit unproven).

## 6. Questions for the architect
- Where does the comal sit relative to the pass (it is the likely bottleneck)?
- Can the brewery's cold side and the kitchen's cooling needs share planning (walk-in, drains, glycol)?
- Dry-goods and masa/nixtamal storage; dish-wash for plate and glass volume; tandoor or substitute placement, hood and fire-code route (unknown).
- Patio and take-away path for Chicken 65 (chip crispness window is short, test it).
