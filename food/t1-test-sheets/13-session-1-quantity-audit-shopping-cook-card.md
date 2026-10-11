# Session 1 — Quantity audit, shopping list, marinade, totopos, cook card

Status: PREPARATION ONLY. No cook has been performed. Corrects the quantities in sheet 11 §4 and §11; the experimental design and the frozen D-74 rule are unchanged.
Evidence stays 4/95. Design stays 43/95.

## 1. Quantity audit (assumptions marked; measure and record the real yields)
| Item | Value |
|---|---|
| Constructions | 3 (A Integrated, B Ring, C Composed) |
| Iterations | 2 (fresh batch and fresh oil each) |
| Tasting plates | 6 (one per construction per iteration; panel takes small bites at T+0/5/10) |
| Control plates | 2 (bare chips, 30 g, one per iteration) |
| Cooked chicken per plate | 120 g |
| Chips per plate | 60 g |
| Per-iteration cooked chicken | 3 x 120 = 360 g |
| Safety buffer | 60 g (spare/dropped plate) |
| Probe/sacrificial piece | 40 g |
| Cooked need per iteration | 460 g |
| Cooked yield assumption | 0.75 of raw (ASSUMED, matches sheet 11's 1.6 kg -> 1.2 kg; record the real yield) |
| Raw chicken per iteration | 460 / 0.75 = 613 g -> **650 g trimmed** |
| Total raw, trimmed | **1.30 kg** (was 1.6 kg; -19%) |
| Buy | **1.4 kg** boneless skinless thighs (trim loss allowance) |
| Chips per iteration | 3 x 60 + 30 control + 30 buffer = 240 g |
| Finished chip per tortilla | about 20 g (ASSUMED; weigh it) -> 12 tortillas, 6 wedges each |
| Tortillas | **24 cooked** (was 48), buy **30** (6 for oil-temperature and wedge trial) |

## 2. Final shopping list
- Chicken thigh, boneless skinless: 1.4 kg.
- Nixtamal corn tortillas: 30; check the label for corn, water, lime (cal) only; no lard (D-54). Record product, source, diameter, thickness.
- Neutral frying oil: 4 L (record type).
- Ginger-garlic paste 80 g; Kashmiri-type red chilli powder 20 g; turmeric 5 g; coriander powder 12 g; fine salt 30 g (plus chip salt).
- Thick plain yogurt 120 g; lemons 2; limes 3.
- Rice flour 80 g; cornflour 80 g.
- Mexican crema 150 g (same tub for all plates).
- Fresh curry leaves 1 packet (about 20 g); serrano or green chiles 6; 1 small white onion.
- Consumables: paper towels, gloves, labelling tape, zip bags or a covered tub for marinating, trash bags.

## 3. T1 BASELINE MARINADE — R&D HYPOTHESIS, NOT FINAL NASHA RECIPE
Held constant across A, B and C. Quantities are scaled from sheet 11 (per kg) to the trimmed weight. Weigh the actual trimmed chicken and scale from the table if it differs.
| Ingredient | Per 650 g batch | Both batches (1.30 kg) |
|---|---|---|
| Ginger-garlic paste | 26 g | 52 g |
| Red chilli powder | 7.8 g | 15.6 g |
| Turmeric | 1.3 g | 2.6 g |
| Coriander powder | 3.9 g | 7.8 g |
| Salt | 6.5 g | 13 g |
| Lemon juice | 16 ml | 32 ml |
| Thick yogurt | 39 g | 78 g |
| Coating, added just before frying: rice flour | 26 g | 52 g |
| Coating: cornflour | 26 g | 52 g |

Cut thighs to about 2.5 cm pieces. Marinate 1 h to overnight at 4 C or below. Both batches are the same marinade; if marinated in one tub, split by weight afterwards. Garnish for the whole run: curry leaves about 8 g, slit green chile about 40 g (fried briefly, dried first), onion 70 g, lime 1/6 per plate, crema 20 g per plate.

## 4. Totopo procedure (fried, never baked)
1. Stack the tortillas uncovered for 2-4 h (or overnight) so they dry; record the corn type/product label, diameter and thickness.
2. Cut each into 6 wedges; record the wedge count.
3. Heat fresh oil to 175-180 C (350-355 F) measured with a thermometer; record the measured temperature.
4. Fry in small batches, not crowded, until the bubbling slows and the edge is golden; time it (expect about 1-2 min, record the real figure).
5. Lift to a wire rack (not paper), salt immediately, and weigh a finished batch. Chips are fried LAST so they are fresh at plating.
A thick NASHA chip is a design choice, not claimed as a Mexican standard.

## 5. Equipment checklist
Required: instant-read probe thermometer; frying thermometer; 1 g kitchen scale; heavy pot or Dutch oven; spider/skimmer; wire racks and sheet pans; oven or warm place held at about 90 C for the chicken; splatter screen; two timers; identical plain plates (7, plus 2 for control); lid or extinguisher nearby; a second person; paper score sheets and pens; labelling tape; smartphone with fixed stand and a constant light.
Nice to have: calipers or ruler; a neutral backdrop; a second phone for T+10.

## 6. One-page cook sequence
1. Day before or morning: trim and weigh chicken; mix marinade; run `python3 tools/t1_randomize.py <run>` for plate codes (key sealed; a second person plates; this is not double-blind). Dry tortillas.
2. Setup: fill the score sheets, set the photo stand, label plates with codes only.
3. Iteration 1: coat chicken; fry in small batches at about 175 C; probe each batch to 74 C (165 F), discard anything under it as UNSAFE; hold at 90 C; fry curry leaf and chile; fry chips last; plate A/B/C and the control within 3 min of each other with identical component weights.
4. Photograph each plate at T+0, T+5, T+10 (same position); score the six gates at each time before touching or repairing the plate; run the three-yes question per construction.
5. Record failure modes at T+10. Do not re-crisp.
6. Iteration 2: fresh oil and a fresh batch, repeat with new codes.
7. Same evening: fill `food/t1-results/t1-results.csv` (recorder), photo IDs, provenance; send photos and the sheets to the repo.

## 7. Data and photo checklist
- Run ID and date; cook; panel size, roles, and whether any member knew the constructions (blinded = no, partially at best).
- Chicken: raw and trimmed weight, marinate time, oil type, oil temperature, cooked weight, probe reading per batch.
- Totopos: product, source, diameter, thickness, corn type, wedge count, oil, measured oil temperature, fry time, finished weight.
- Per plate: code, construction, iteration, component weights, six gate scores at T+0/5/10, failure modes at T+10, notes.
- Photos per plate (originals, unedited): chicken alone, totopos alone, hero 45 degrees, top-down, construction close-up, T+0, T+5, T+10, any failure, control. For each photo: ID, date, construction, hold time, photographer, device, edits (crop/exposure/white balance/rotation only), rights owner, identifiable people.
- Figma originals: if the founder has downloaded the 10 PNGs with `tools/founder_download_candidates.sh` before 2026-10-18, add them to `visuals/archive/candidates/` and run `python3 tools/review_candidates.py`.
