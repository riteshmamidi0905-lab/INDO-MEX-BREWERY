# SESSION 2 CARD: Paneer Tikka Taco

**Status:** FROZEN PROTOCOL, NOT PERFORMED. NOTHING HAS BEEN COOKED. Generated from `food/sessions/sessions.json` (gates hash `564204de7f11`). Open this card, shop, cook, record. You do not need the rest of the repository.

**Primary question:** Can recognizable paneer tikka and a credible Mexican taco become one coherent NASHA dish without either side disappearing, and which AVAILABLE heat source preserves the tikka identity well enough for early testing?

**Hypothesis (analysis, not evidence):** ANALYSIS, not evidence: very high direct heat for a short time gives char without drying the paneer; the marinade must be thick (hung curd) to cling; the tortilla and fresh salsa carry the Mexican identity; the dish is a taco if it is small, folded and eaten by hand, not a wrap.

## What you are comparing
- **A:** Charbroiler / high-heat grill
- **B:** Comal or plancha (flat, dry-seared)
- **C:** Tandoor (ONLY if a real appropriate tandoor is available; otherwise skip, do not simulate)
- Control: unmarinated paneer charred on the A heat source (shows what the marinade adds)

**Test variable:** heat source (A vs B, C if available). A substitute is NOT the same as a tandoor; record the limitation.

**Keep identical (controlled):**
- same paneer block and cut
- same marinade batch and time
- same corn tortilla batch, warmed the same way
- same salsa, onion, cilantro, lime
- same plate; 2 small tacos per plate

## Shopping (separate: required, screening substitutes, never-acceptable, verify)
**REQUIRED**
- [ ] paneer block 1.0 kg (one brand, one lot)
- [ ] plain yogurt 500 g to hang (or Greek-style strained yogurt 350 g)
- [ ] fresh nixtamal corn tortillas 24, 12-15 cm, label shows no lard
- [ ] tomatillos 300 g, serrano 3, cilantro 1 bunch, white onion 2, limes 4, lemon 1
- [ ] ginger-garlic paste 30 g, Kashmiri-type chilli powder 8 g, turmeric 3 g, kasuri methi 4 g, chaat masala 6 g, fine salt 30 g (marinade, control and salsa)
- [ ] neutral cooking oil 100 ml

**SUBSTITUTE ALLOWED FOR SCREENING**
- [ ] jarred salsa verde (record label)
- [ ] Greek yogurt instead of hanging curd (record fat %)
- [ ] frozen paneer (record; texture differs)

**SUBSTITUTE NOT ACCEPTABLE**
- [ ] mustard oil (excluded, V-72)
- [ ] tortillas with lard or unreadable label (D-54)
- [ ] flour tortillas (that is a different dish)
- [ ] pre-seasoned 'tikka masala' paste in place of the marinade (not the test)

**SOURCE TO VERIFY**
- [ ] paneer label: milk and acid only (no animal rennet; D-54)
- [ ] tortilla ingredient list
- [ ] whether the paneer is cow or buffalo milk (record)

**Quantity audit:** 2 constructions (A, B) x 2 iterations = 4 marinated plates + 1 spare = 5 x 120 g = 600 g marinated; 2 control plates (A heat source only, NOT compared with arms A/B) = 240 g plain. Total 7 plates; buy 1.0 kg. Tortillas 2 per plate x 7 = 14 + 6 trial = 24 (fresh nixtamal tortillas are often sold in 10-12 cm packs: record the diameter you get). ASSUMPTIONS: weigh real yields.

**Labels:** Read every jar, can, paste and packet label for animal ingredients (D-54) before cooking.

## Day plan
1. T-4 h: put yogurt in a cloth/sieve over a bowl in the fridge to hang (weigh result; about 250 g)
2. T-2 h: weigh paneer, cut cubes; marinate 600 g in a covered bowl at 5 C or below; keep 240 g plain, salted
3. T-1 h: make salsa verde, chop onion and cilantro, set plates and photo corner, run `python3 tools/t1_randomize.py <run>`
4. T-10 min: preheat heat sources A and B; warm tortillas on a dry comal only when plating
5. Cook identical small batches per arm; pull at 60 C core (record seconds on heat); plate within 3 min of each other
6. Score immediately (T+0), again at T+5 (moisture/WEEPING) and T+10 (tortilla, structure); photos at each time
7. Within the 10-minute window hold cooked cubes at 60 C or above, then discard

## Equipment
- [ ] heat source A (charbroiler or very hot grill pan/grill) preheated 10 min
- [ ] comal or plancha or heavy cast iron (B) preheated 10 min
- [ ] infrared thermometer for surface temperature (record it for A and B)
- [ ] instant-read probe thermometer
- [ ] 1 g scale
- [ ] timers x2
- [ ] same plates x7
- [ ] second person for plating/codes

## T2 BASELINE MARINADE: R&D HYPOTHESIS, NOT FINAL NASHA RECIPE (proportions are ordinary home-recipe patterns; no source gives restaurant weights)
- **marinate:** 2 h refrigerated (30 min to 4 h is the commonly observed range; never past 8 h)
- **paneer:** block cut into about 2 cm cubes, cold, patted dry; about 6 cubes (about 55 g, WEIGH them) per taco as a TEST START; marinate 600 g, keep 240 g plain (salted 2 g) for the control plates
- **tortilla:** fresh nixtamal corn, 12-15 cm, lard-free, warmed on a dry comal
- **salsa:** salsa verde (tomatillo, serrano, cilantro, lime, salt) 15 g per taco; raw white onion 8 g; cilantro 2 g; lime wedge
- **per 600g paneer:**
  - hung curd (from 500 g yogurt hung 2 h): 150 g
  - ginger-garlic paste: 18 g
  - red chilli powder (Kashmiri type): 4.5 g
  - turmeric: 1.2 g
  - kasuri methi (crushed): 1.8 g
  - chaat masala: 3 g
  - salt: 6 g
  - lemon juice: 9 ml
  - neutral oil: 12 ml
  - mustard oil: NONE (excluded, V-72)
  - besan: NONE in baseline (a later variable)

## Variables and how well each is supported
| Variable | Class | Note |
|---|---|---|
| paneer source | NASHA R&D CHOICE | buy ONE block type for the test and record brand/label; in-house vs bought is a later variable (coagulation temperature changes firmness: L-008, Hussain 2024) |
| cube size about 2 cm | COMMONLY OBSERVED | home blogs differ (1.5-5 cm); uneven pieces cook unevenly |
| hung curd marinade | SOURCE-SUPPORTED (T1 blogs) | undrained curd makes the marinade runny; thick clings |
| marinate 1-4 h, not past 8 h | COMMONLY OBSERVED | texture softens and marinade waters after long salt exposure |
| rubbery paneer = overcooking and moisture loss | COMMONLY OBSERVED | pull when edges are charred and the centre is still soft |
| mustard oil | UNVERIFIED / EXCLUDED | FDA Import Alert 26-04 (V-72); regulatory review |
| besan in marinade | NASHA R&D CHOICE | not in baseline; later single-variable test |
| pineapple | UNCERTAIN / ADVISOR | al pastor echo; excluded from the baseline; never called al pastor |
| tandoor throughput and hood needs | UNVERIFIED | Austin hood/fire rules not found (V-66) |

## Measure (write down; never estimate later)
- [ ] raw paneer weight and cooked weight per plate (g)
- [ ] marinade weight clinging (g, paneer before/after marinating)
- [ ] seconds on heat per batch and surface temperature if measurable
- [ ] char area from top-down photo (visual estimate)
- [ ] minutes per plate (active)
- [ ] paneer core temperature (record; paneer is a held dairy item)

## Photograph (same device, place, light, position; originals untouched; crop/exposure/white balance/rotation only; no generative edits)
- [ ] paneer block label
- [ ] raw cubes weighed
- [ ] marinated cubes
- [ ] cooked cubes alone (45 degrees)
- [ ] plated taco hero 45 degrees
- [ ] top-down
- [ ] cross-section (cut one taco)
- [ ] T+5
- [ ] T+10
- [ ] failure photos
- [ ] control

## FROZEN GATES (NASHA R&D THRESHOLDS: NOT INDUSTRY STANDARDS. 1-5 scale. A construction passes an iteration only if EVERY gate is met at its stated time and no failure gate fires; two passing iterations before any winner; NONE WINS is valid.)
Score each gate at its time (1-5, panel mean). Do not re-crisp or repair plates before scoring. Hold times: T+0, T+5, T+10.

| Gate | Minimum | Score at | Note |
|---|---|---|---|
| paneer_tikka_identity | 4.0 | T+0 |  |
| taco_identity | 4.0 | T+0 |  |
| nasha_coherence | 4.0 | T+0 |  |
| moisture | 3.5 | T+5 | paneer neither weeping nor dry (also judge WEEPING here at T+5) |
| char | 3.5 | T+0 | visible char without bitterness |
| tortilla_integrity | 3.5 | T+10 |  |
| structural_integrity | 3.5 | T+10 |  |
| another_bite | 4.0 | T+0 |  |
| service_practicality | 3.5 | T+0 | can be finished to order at a plausible service pace (cook records minutes per plate) |

**Failure gates (any one fails the iteration):**
- `NOT_TIKKA`: reads as grilled cheese or generic cheese taco
- `NOT_TACO`: reads as a wrap or naan roll
- `RUBBERY`: paneer is chewy or rubbery
- `NO_CHAR`: no real char
- `WEEPING`: marinade or whey pools; coating slides off
- `TORTILLA_TEAR`: tortilla tears or goes soggy by T+10
- `SALSA_DOMINATES`: salsa erases the tikka
- `IMPRACTICAL`: cannot be finished to order at service pace
- `D54`: any beef/pork derivative incl. bovine rennet in a cheese or lard in tortillas
- `UNSAFE`: food-safety temperature or handling failure

**Decision rule:** NASHA R&D THRESHOLDS: NOT INDUSTRY STANDARDS. 1-5 scale. A construction passes an iteration only if EVERY gate is met at its stated time and no failure gate fires; two passing iterations before any winner; NONE WINS is valid. NONE WINS is a valid result. Thresholds are never changed after tasting.

## Safety, D-54, allergens
- Marinate at 5 C or below; discard marinated or cooked paneer left out of temperature control 2 h or more.
- Paneer is ready-to-eat dairy: cross-contact and clean hands/boards are the real risk.
- Record core temperature of every batch; UNSAFE = record and do not taste.
- Rule: WEEPING is judged at T+5 together with the moisture gate.
- **Panel:** Minimum 4 tasters, at least 3 of whom did not cook; same tasting order for everyone, plain unsalted tortilla/cracker and room-temperature water between samples; blind codes from `python3 tools/t1_randomize.py <run>` plated by a second person (not double-blind). n<8: raw values only.
- No beef, no pork, no hidden derivatives (lard in tortillas, stocks/bouillon/gelatin, animal rennet from a bovine source, Worcestershire, processing aids). No halal claim.
- EXCLUDED from all baselines (ledger V-72: FDA Import Alert 26-04 treats expressed mustard oil as an unsafe food additive; labelling it 'external use only' does not change that). Use a neutral oil. Flag for regulatory review; never improvise a legal conclusion.
- Allergens: see `food/ALLERGEN-MATRIX.csv`; cross-contact is a process issue; no allergen-free claim.

## After the cook
- python3 tools/session_record.py add ... (see food/sessions/README.md) then python3 tools/session_record.py report
- Scores go in `food/sessions/results.csv` (one row per gate, time, construction, iteration; `real_cook` only; photo IDs and panel size required). Ingest photos with `python3 tools/photo_ingest.py ingest ...`.
- Anything not measured is `NOT MEASURED`. Never fill from memory.
