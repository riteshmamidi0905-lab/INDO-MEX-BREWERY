# ARC-02-B: Tank Hall correction of ARC-02-A (masked edit)

- **STATUS:** NOT GENERATED
- **PURPOSE:** ARC-02-A is faithful outside the glass but invented the hall interior (8 tanks, no copper vessels, silver cones, thick sleeves). Restore the canonical interior from ARC-01-D under the existing night lighting. **Edit only the glass of the Tank Hall; change nothing else.**
- **INPUTS:** (1) `visuals/generated/ARC-02-B-inputs/ARC-02-A-hall-crop-2x.png` with `hall-edit-mask-2x.png` (white = may change) and `hall-frame-lock-mask-2x.png`; (2) **arrangement reference:** `visuals/generated/ARC-01-E-inputs/ARC-01-D-hall-crop-2x.png` (the canonical interior in daylight; copy its tank count, positions, deck, copper vessels, but relight for night).
- **FINISH:** `python3 visuals/tools/arc02_tools.py composite visuals/generated/ARC-02-A.webp <edited_crop.png>` then `python3 visuals/tools/structure_check.py visuals/generated/ARC-01-D.png visuals/generated/ARC-02-B.png`.
- **Fallback if the editor cannot count to six:** build the hall interior from ARC-01-D's pixels with a night colour grade (scripted), rather than regenerating again. No iteration cap is set; ask the founder before any waiver.

## EDIT PROMPT
```
Edit only the equipment visible behind the glass of the Tank Hall (white mask area) in the first image, using the second image as the exact arrangement reference. The first image is a blue-hour night photograph; keep its warm shielded interior light, its glass reflections and its mullions exactly. Rebuild the interior so that it matches the second image's layout, relit for night:
- EXACTLY SIX stainless fermenters, no more: three on the left of the glass (two large adjacent tanks at far left, one smaller one west of the raised deck), and on the right the one large nearest tank with two more tanks behind it partly hidden by a mullion. Remove the two extra small tanks that currently stand at the centre-left.
- In the centre, restore the RAISED BREW DECK with TWO copper-clad brewing vessels with domed tops, a copper hood and a stack rising to the ceiling, steel railings and a stair, exactly as in the second image; copper only on those two vessels and their hood.
- On every fermenter: polished stainless shell; a matte GRAPHITE insulated cone clearly darker than the shell (not silver); four legs; a round side manway; and ONE narrow (about six inches, about one tenth of the tank diameter) deep marigold-orange (about #E8870E) removable powder-coated sleeve around the middle of the shell, no thicker or yellower than in the second image.
- Seamless warm-grey production floor with stainless trench drains, restrained piping, tri-clamp fittings and valves, plausible pumps, as in the second image.
- Night lighting: warm shielded uplights at the tank bases and linear ceiling lights make the tanks and copper vessels the brightest large objects in the picture; the equipment glows softly through clear glass; faint plausible reflections only; no star flares, no haze.
Do not change anything outside the glass: architecture, entrance, arcade, screens, court, rill, people, vehicles, sky, planting, light. No logos, no readable text.
```
## NEGATIVE
```
seven tanks, eight tanks, extra tanks, missing copper vessels, no deck, silver or shiny cones, thick or yellow sleeves, painted bands, extra copper, brass, a frontal or symmetric view, changed mullions, changes outside the hall glass, star flares, lens flares, haze, glowing screens, string lights, neon, text, logos
```
## Acceptance
Exactly six tanks; two copper vessels with hood; graphite cones; narrow sleeves; Tank Hall the brightest large feature; exterior unchanged (`structure_check` recall >= 0.80 by eye and metric); ARC-01 rubric (night) >= 90 with no hard fail; founder approval.
