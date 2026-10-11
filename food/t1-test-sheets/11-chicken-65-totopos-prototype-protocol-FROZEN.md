# CHICKEN 65 TOTOPOS: T1 PHYSICAL PROTOTYPE PROTOCOL (FROZEN BEFORE COOKING)

**Status: PROTOTYPE HYPOTHESIS, NOT FINAL.** Nothing here is a final recipe, a historical claim or a result. **Nothing has been cooked.** The physical test decides what survives; AI visualizations propose, physical testing decides. D-54: **no beef, no pork**, and no hidden derivatives (lard, tallow, suet, gelatin, chicharron); not claimed halal. Dish name stays **Chicken 65 Totopos** (never "nachos").
**Question for Session 1:** which construction (A Integrated, B Ring, C Composed board) gives the strongest Chicken 65 identity + totopo identity + eating quality + 10-minute structural survival? One question only; marinade, coating, chile, acid, crema, garnish, chip thickness and plating are optimised in later sessions.

## 1. Research basis (T1 search summaries; V-38, V-39, V-51, V-52, V-56, V-57, V-58; no regional lineage is claimed)
| | Commonly observed | Source-specific | NASHA R&D choice | Unverified |
|---|---|---|---|---|
| Chicken 65 | boneless thigh; curd + ginger-garlic + red chilli (often coriander, cumin) marinade; rice flour and/or cornflour coating; medium-hot oil, small batches; curry leaf and green chilli fried and tossed through; lemon | double fry; egg white; sugar in marinade | **dry-to-lightly-coated South Indian restaurant-style direction (hypothesis, not a historical claim)** because it must coexist with crisp chips; thigh for moisture and holding | origin stories (contested folklore); any Hyderabad vs Chennai variant |
| Totopos | tortillas dried, cut, fried in small batches at about 170-175 C, salted while hot (some say Mexico does not salt); Oaxacan originals are baked or comal-toasted, pricked, irregular | thickness not specified in sources | a **sturdier chip** to carry chicken is a NASHA structural target, **not** a claim about traditional totopos | whether thick chips hold crisp under chicken |

## 2. Decisions and reasons (chef may change BEFORE cooking, never after)
- **Chicken cut:** boneless **thigh**, cut about 2.5 cm (a NASHA operational choice: moisture, tenderness, fry-and-hold behaviour, repeatability and bite size; not presented as traditional).
- **Chip method for T1: FRIED**, from **real nixtamal corn tortillas** (from a tortilleria or good store; record brand/type, thickness, corn type if known), dried first, cut in sixths. Reason: best corn flavour, crispness and structural strength for the restaurant product; baked and toasted are later controls. **Do not use bagged flavoured supermarket chips**; if you must, label the whole run "ROUGH CONVENIENCE TEST" and it **does not count**.
- **Oil:** neutral vegetable oil, lard-free (statement/label photographed). Fresh oil for the run; record type, set point and each batch.
- **Same components for A, B and C:** one chicken batch per iteration, one chip batch per iteration, same garnish, same acid, same crema, same portion targets. Only the construction changes.
- **Crema:** optional component, same placement in all three (small pool at the plate edge) in Session 1; **placement (side, pool, drizzle, dots) is a Session 2 question**. Lime and onion are the default accompaniments.
- **Garnish (each has a reason):** curry leaf (Chicken 65 identity, fried crisp), green chile (heat and identity), lime (acid, cuts fat), thin onion (traditional-style accompaniment), no other garnish.

## 3. Portion targets (weigh and record the ACTUAL value; write NOT MEASURED if skipped)
Per plate: cooked chicken 120 g, chips 60 g, crema 20 g, curry leaf 1 g, green chile 5 g, onion 10 g, lime 1/6. **Plates: 3 constructions x 2 iterations = 6, plus 1 spare, plus a bare-chip control (60 g) per iteration, plus extra chips on the side for T+5/T+10 crispness scoring.**

## 4. Prototype starting quantities (hypothesis for the chef to adjust; per 1 kg raw boneless thigh)
Marinade: ginger-garlic paste 40 g, red chilli powder 12 g (Kashmiri-type for colour; chef decides heat), turmeric 2 g, coriander powder 6 g, salt 10 g, lemon juice 25 ml, thick yogurt 60 g; rest 1 hour to overnight at 4 C or below. Coating just before frying: rice flour 40 g + cornflour 40 g (record flours used; note any egg white). Finish: curry leaves 15 g and slit green chiles 30 g fried crisp in the oil and tossed through; lemon. Frying: set point about 175 C (chef decision), small batches, rest, **probe every batch to 74 C (165 F) in the thickest piece**. **Raw chicken needed for the full plan: about 1.6 kg** (two iterations of about 0.8 kg, covering plates plus tasting extras).

## 5. Constructions (same components, different geometry; photograph each)
- **A Integrated (founder-preferred direction):** an open layer of chips on a black stoneware plate, the chicken pieces distributed through and among them, curry leaf and chile scattered, crema pool at the edge, lime beside.
- **B Ring:** a ring of upright/leaning chips around the edge, chicken piled in the centre ring, crema in a katori or edge pool, lime beside; keeps a dry chip surface.
- **C Composed board:** chips, chicken (on a small rack or liner) and crema in controlled contact on a board, one composed arrangement; risk: reads as two foods.
- **Control:** 60 g of bare chips on a plate, untouched, scored at the same times.
**Do not name a winner in advance.** It is acceptable for none of A, B, C to win.

## 5b. Frozen decision rule (set BEFORE cooking; founder's recommended starting thresholds, 1-5 scale; not industry standards)
| Gate | Minimum |
|---|---|
| Chicken 65 identity | 4.0 |
| Totopo identity | 4.0 |
| NASHA fusion coherence | 4.0 |
| T+10 crispness | 3.5 |
| Structural integrity | 3.5 |
| Overall desire for another bite | 4.0 |
A construction **passes an iteration** only if every gate is met **and** no failure gate is triggered. It needs **2 passing iterations** to be named a candidate; one good plate is a PROMISING PROTOTYPE, never a VALIDATED SIGNATURE DISH. These thresholds are frozen in `tools/t1_record.py` (`FROZEN`) by this commit; changing them after tasting is not allowed. Outcomes: KEEP / REWORK / HOLD / CUT.
**Automatic failure gates (recorded as codes in `gate_failures`, pipe-separated):** `NOT_65` chicken no longer reads as Chicken 65; `NO_CORN` Mexican corn component disappears; `SOGGY` chips unpleasantly soggy within reasonable table time; `IMPRACTICAL` cannot be eaten practically; `COLLAPSE` construction falls apart; `SAUCE_DOMINATES`; `GENERIC_NACHOS`; `UNRELATED_CHIPS` (tastes like Chicken 65 with unrelated chips); `D54`; `UNSAFE`.

## 6. Panel, blinding and honesty
Record panel size and each taster's role and familiarity with Indian and Mexican food (`panel_n`, `panel_roles`). Include, named, one Indian-identity and one Mexican-identity perspective (n = 1 each, recorded apart from the average) and a general diner. A few people give **directional qualitative evidence, not market validation.** Blinding: run `python3 tools/t1_randomize.py R1-it1` for random 3-digit codes, write only codes on the plates, keep the key sealed until scoring ends; **appearance cannot be blinded**, so flavour and texture are the only blinded signals (record `blinded` honestly).

## 7. Kitchen day card
1. **Before:** write down chip source, flour used, oil, pre-set numbers; photograph every label (D-54); confirm tasters' allergies (dairy in crema; wheat/rice flour; shared fryer oil); clean workspace; thermometer calibrated (ice water).
2. **Prep:** marinate chicken (<= 4 C); dry and cut tortillas; weigh everything.
3. **Iteration 1:** fry chips (one batch, record time and gap to plating); fry chicken in small batches, probe each batch; toss with fried curry leaf and chile; weigh portions. Run the randomizer; **stagger plating 3 minutes apart**; plate A, B, C and the control from the same batches; log room temperature; assembly time per plate.
4. **Per plate (stopwatch):** T+0 (score within 60 seconds), T+5, T+10 left untouched on the table (ambient); score chips from the **extra chips on the side** at each time; probe temperature at each time. **Do not rescue a plate before scoring it.**
5. **Photograph** (section 9) before anyone touches a plate; failures before cleanup.
6. **Iteration 2:** fresh batches, new codes, same procedure.
7. **Same day:** enter rows in `food/t1-results/t1-results.csv` (only real values; `NOT MEASURED` where skipped), fill `09-concept-vs-real-comparison.md`, then `python3 tools/t1_record.py report`. Discard plates held over 2 hours (or 1 hour above 32 C).

## 8. Score sheet (one per taster; 1-5; fill on paper before discussion)
| Code | Time | Chicken 65 identity | Totopo identity | Fusion coherence | Crispness | Structure | Flavour | Aroma | Another bite? | Comment |
|---|---|---|---|---|---|---|---|---|---|---|
| ___ | T+0 | | | | | | | | | |
| ___ | T+5 | | | | | | | | | |
| ___ | T+10 | | | | | | | | | |
(repeat per code; the control row is crispness and corn flavour only)

## 9. Photography sequence (fixed protocol: `food/PHOTOGRAPHY-PROTOCOL-T1.md`)
Fixed position (tripod or a stack of books), grey card, same time of day, sequence log. Per construction: **hero 45 degrees, truth top-down, construction close-up (chicken-chip contact), T+0, T+5, T+10, failure** (before touching). Also: **bare-chip control, Chicken 65 alone, totopos alone**. Allowed edits: exposure, white balance, crop, rotation. **Never** remove defects, add ingredients, change colour materially, replace pieces, hide sogginess or composite. Food only, no faces. Name files `C65-<code>-<shot>-<time>-it<n>.jpg`; record photographer, date, device, edits, rights owner.

## 10. Required vs nice to have
**Required:** kitchen scale (1 g), instant-read probe thermometer, timer/stopwatch, a deep pot or fryer with a frying thermometer, spider/skimmer and a rack over a tray, mixing bowls, knives and boards, black plates (or any plain dark plates), a small bowl for crema, a phone camera, a stack of books or tripod for a fixed camera. **Nice to have:** a second set of hands, a grey card, a dedicated fryer, a ruler for the frame, a heat lamp (not used in Session 1). **Home-kitchen limitation:** a pot is not a restaurant fryer (recovery and temperature control differ); record the vessel and what you could not control.

## 11. Shopping list (supports 2 iterations of A/B/C plus control; do not overbuy)
- **Chicken:** boneless skinless thighs, about 1.6 kg.
- **Marinade/spices:** ginger and garlic (or ready paste, label checked), red chilli powder (Kashmiri-type) about 40 g, turmeric, ground coriander, salt, lemons 4, thick plain yogurt 150 g.
- **Coating:** rice flour 150 g, cornflour 150 g.
- **Totopos:** fresh nixtamal corn tortillas, about 48 (check label for lard; ask for lard-free), 6 per plate-equivalent plus control and extras.
- **Sauce:** thick plain yogurt or Mexican crema about 150 g (for the optional crema; label checked), salt.
- **Garnish:** fresh curry leaves 1 large bunch (about 40 g), green chiles (serrano or Indian green) about 120 g, limes 6, red onion 1.
- **Frying:** neutral vegetable oil (lard-free label) about 3 L.
- **Measurement/photography:** paper towels, parchment/paper liners, labels, marker, ice (for thermometer check), small cups for side chips, food-safe gloves, sealed envelope for the randomizer key, grey card or plain grey paper.
