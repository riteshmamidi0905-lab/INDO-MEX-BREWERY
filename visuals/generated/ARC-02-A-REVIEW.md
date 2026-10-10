# ARC-02-A Review

## Metadata
- **File:** `visuals/generated/ARC-02-A.webp`, **2000x1114** (ARC-01-D is 2000x1128, so the frame is about 1.2% shorter), supplied by the founder; external generator (tool/model not stated); prompt `generation-batch-01/ARC-02.md` with ARC-01-D as reference. One image, not four variants.
- **Status:** CANDIDATE — REFINEMENT REQUIRED. **Hard fail: YES (Tank Cloister).** Founder approval: NO.
- **Method:** full frame, side-by-side with ARC-01-D, crops at 1.5x and 2.5x of the Tank Hall and the arcade, `structure_check.py`.

## Preservation vs ARC-01-D
| Check | Result |
|---|---|
| Camera, crop, massing | **Strong match.** Same oblique view, hall left, entrance centre-left, arcade right, oak branch upper left, pickup bottom-left, SUV bottom-right, two walkers, restaurant block, two stacks, rill, tables. Slightly shorter frame |
| `structure_check` (D vs ARC-02-A) | **edge recall 0.69, precision 0.72.** Calibration: D vs B 0.73, D vs A 0.59, D vs E-composite 0.95. Inside the "inspect" band; by eye the exterior is faithful, and the loss is mostly the changed hall interior and night edges |
| Entrance recess, soffit, plinth, canopy | Preserved |
| Concrete-and-cedar arcade, standing-seam roof | Preserved |
| Screens | PASS: flat dark perforated panels, no sunburst/medallion; warm points show through the holes, a little more luminous on the right-hand panel (acceptable, watch it) |
| Mullions | Dark bronze preserved |

## Tank Cloister: HARD FAIL
Counting at 2.5x: **eight** stainless fermenters with sleeves (three large at the left, two small at the centre-left, one large nearest at centre-right, two behind it at the right). **The two copper-clad brewing vessels, the copper hood and the stack are missing**; the raised brew deck is not readable. Cones read brushed stainless, **not graphite**. Sleeves are wider and yellower than the narrow deep-marigold spec. The hall interior was re-invented rather than relit from ARC-01-D.

## Night quality
| Item | Result |
|---|---|
| Sky | PASS: deep indigo, faint warm afterglow at the left horizon, thin cloud |
| Tank Hall brightest large feature | PARTIAL: it glows warmly but the court and arcade are about as bright; the tanks are not clearly the brightest |
| Lighting | PASS: warm shielded, entrance soffit downlights, arcade washers, restaurant windows warm, no string lights, neon, colour or festival lighting, no flares |
| Reflections | PASS: plausible faint reflections in the glass and a subtle rill reflection |
| Oaks | Softly uplit; upper-left branch is warm and slightly stylized |
| People | PASS: about 25 mixed, candid, relaxed, not crowded; same two walkers |
| Photorealism | Good light and depth, still AI-smooth; soft interior |

## Rubric
| Criterion | Max | Score |
|---|---|---|
| Architectural continuity | 20 | 16 |
| Tank Cloister | 20 | 5 |
| Originality | 15 | 12 |
| Austin / evening plausibility | 10 | 9 |
| Material discipline | 10 | 7 |
| Hospitality appeal | 10 | 9 |
| Photorealism | 10 | 7 |
| Cultural restraint | 5 | 5 |
| **Total** | **100** | **70** |
**Hard fail: YES: wrong fermenter count (8), copper vessels missing.** Not eligible as a provisional winner.

## Recommendation
Keep everything outside the hall glass; it is the best night exterior atmosphere so far. Fix only the hall interior: a **masked, hall-glass-only correction (ARC-02-B)** that restores ARC-01-D's arrangement under night lighting (six tanks; copper deck, hood and stack; graphite cones; narrow sleeves). Inputs are prepared in `visuals/generated/ARC-02-B-inputs/`; prompt in `generation-batch-01/ARC-02-B.md`. If the generator cannot count to six, build the hall interior from ARC-01-D's own pixels with a night grade (scripted fallback) instead of regenerating again.
