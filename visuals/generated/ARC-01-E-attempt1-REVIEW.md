# ARC-01-E, attempt 1 (externally edited hall crop): Review

## What was supplied
- `visuals/generated/ARC-01-E-external-crop-attempt1.webp`: **2000x965** (aspect 2.073, matching the 2.071 crop frame), an externally generated replacement for the Tank Hall crop. Tool/model not stated by the founder (logged as "external, not stated").
- It is **not** a full-frame ARC-01-E. I tested it with the compositing helper: `visuals/generated/ARC-01-E-attempt1-composite-DIAGNOSTIC.png` (a diagnostic only, not a candidate; outside-hall RMSE 0 by construction).

## Verdict: REJECTED AS A DROP-IN FOR ARC-01-D (preservation gate fails)
The image is excellent in itself, but it is **a different view of the hall**, not a refinement of the one in ARC-01-D.

### Preservation gate
| Check | Result |
|---|---|
| Exactly six fermenters | **PASS.** Six: two large tanks at far left and far right, a second tank behind each, and one tank either side of the brew deck. Reads as a horseshoe |
| Same positions, scale and perspective as ARC-01-D | **FAIL.** ARC-01-D is an oblique three-quarter view with a large nearest tank at centre-right and the east-leg tanks behind a mullion. The attempt is a **near-frontal, almost symmetric view**: tanks are re-arranged and re-scaled in the picture, and the camera has changed. Placed behind the exterior glass it contradicts the oblique building |
| Mullions unchanged | **FAIL in the composite.** The generator drew its own mullions (four wide panes) in different places; the frame lock re-pastes D's original mullions, giving **doubled vertical frames** in the diagnostic |
| Two copper vessels, hood and stack | PASS; no extra copper vessels |
| Graphite matte cones | PASS (clearly matte graphite) |
| Marigold sleeves | PASS-ish: six narrow sleeves, deep orange; slightly lighter/brighter than #E8870E |
| Exterior unchanged | Not applicable to a crop; unchanged in the composite by construction |
| New clichés/text/logos | None seen |

### Realism (compared with D)
Materially better: welded stainless pipework, tri-clamp ferrules, butterfly valves, tubular legs with foot plates, round manways with bolted rings, a deck with stairs and 42-in-style railings, grey pumps on skids, a neatly coiled hose, stainless trench drains, seamless warm-grey floor, plausible contact shadows and glass reflections of oaks. Photorealism of the hall alone: about 9/10. Minor concerns: floor is **glossier than the "matte-satin" brief** (hotel-lobby reflections), strong star-flare highlights on a few lights, and the interior is very clean and symmetric.

## Rubric
Not scored as ARC-01-E: it is not a full frame and fails the preservation gate. As a hypothetical composite the hall would raise Photorealism from 7 to about 8-9, but the perspective mismatch and doubled mullions would cost Architectural continuity and Tank Cloister points, so the net is **below 90 and a drift failure under the acceptance rule**.

## Where this leaves the stopping rule (D-40)
- ARC-01-E (this attempt) is **rejected as drift**. Under D-40 the fallback is **ARC-01-D as the canonical day reference by a documented founder waiver at 89/100**. I have **not** declared that waiver; it needs the founder's explicit decision.
- **No ARC-01-F.** Whether a second attempt at E (same prompt, with the perspective locked) is permitted is the founder's call.

## Useful by-product
This frontal view is a strong candidate **reference for BRW-01** (hero Tank Cloister interior), including the floor, drains, deck and pipework language. It is preserved here for that purpose only; BRW-01 stays blocked and is not logged as generated.

## If the founder allows a second E attempt (not an F)
- Feed the **2x crop of D with the mask** and add: "keep the oblique three-quarter camera and the current positions and sizes of all tanks; the large nearest tank at centre-right stays; do not make the view frontal or symmetric; keep mullions in the same places."
- Drop the frame lock if the editor keeps the mullions itself, or lock only after checking alignment.
- Ask for a **matte-satin** floor with soft reflections and no star flares.
