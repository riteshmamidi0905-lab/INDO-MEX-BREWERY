# T1 SESSION PLAN: first R&D cook (Chicken 65 Totopos A/B/C and Paneer Tikka Taco)

**Status:** PLAN. **Nothing has been cooked.** This is a run-of-show so one real session produces clean evidence. It contains no results. Sheets to fill: `07-chicken-65-construction-comparison.md`, `03-paneer-tikka-taco.md`, `01-chicken-65-totopos.md` (ingredients, policy), `09-concept-vs-real-comparison.md`; data rows go in `food/t1-results/t1-results.csv` (real cooks only); photo rules in `food/PHOTOGRAPHY-PROTOCOL-T1.md`. D-54: no beef, no pork. The physical dish has authority over any AI concept image.

## Before the day (decide and write down BEFORE cooking)
- The pre-set decision rule on sheet 07 (minimum crispness at 10 minutes, identity and coherence scores) and the same on sheet 03. Do not change it after tasting.
- Which Chicken 65 lineage the cook follows (chef decision; Tamil Nadu/Chennai-associated, Hyderabadi and Andhra versions differ) and the marinade (chef decision).
- Totopos: nixtamalised-corn tortillas cut and fried, baked or toasted; record which and the source (no undisclosed flour-masa chips). Lard-free statement for tortillas and oil (D-54).
- Panel: at least 5 tasters including, if possible, one person who knows South Indian food and one who knows Mexican food; each scores blind to construction labels (A/B/C written on the underside of the vessel only).
- Equipment: fryer with thermometer, probe thermometer, scale, timer, camera/phone, labels, black stoneware, katori, board for C, paper liners.

## Run of show (times are relative; adjust to the kitchen)
1. **Prep (T-90 to T-0):** marinate and prepare chicken per the chosen method; prepare totopos (one batch, divided across A, B, C); lime, onion, curry leaf, green chile; optional crema as a side. Weigh everything; photograph labels.
2. **Cook batch 1:** fry chicken; fry/toast chips. Plate **A, B, C from the same batches** with the same chicken weight and chip weight per plate. Record weights.
3. **At plating (T+0):** probe temperature; photograph each construction: hero (45 degrees), truth (top-down), construction close-up, with the label hidden. Taste panel scores T+0.
4. **T+5 and T+10:** leave plates untouched on the table (table conditions, not the pass); photograph and probe at each time; score crispness, sauce migration, structure, flavour again.
5. **Failures:** photograph and record honestly (soggy chips, dry chicken, broken chips). Do not rearrange.
6. **Repeat** at least once with a fresh batch to test repeatability (iteration 2).
7. **Paneer Tikka Taco (if capacity):** cook per sheet 03; plate two tacos; score paneer identity, char, marinade, moisture, tortilla compatibility, garnish, acid, heat, structure, Indian, Mexican and NASHA identity; hold at 0/5/10; photograph hero/truth/construction/failure.
8. **Beer (optional):** if any beer is tried with a dish, record which and what it did (not a NASHA beer; no claims).
9. **Same day:** enter rows in `t1-results.csv`, fill the sheets, name photographs per the protocol, and complete `09-concept-vs-real-comparison.md` against the concept images (hero and truth views).

## After the session
Run `python3 tools/t1_record.py report`. A winner is named only if the rule is met over at least two iterations; otherwise say NO WINNER. One cook justifies at most the **PROTOTYPE** stage; set `visual_stage` and `stage_evidence_ref` only with real photographs and the completed comparison file.
