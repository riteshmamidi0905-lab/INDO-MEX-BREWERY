# ARC-02-C: true night Tank Hall render, masked into ARC-02-A (ONE controlled generative attempt)

- **STATUS:** NOT GENERATED — PACKAGE READY (founder decision D-45). **One attempt only.** If it fails, STOP and report; no ARC-02-D without a new founder decision.
- **PURPOSE:** ARC-02-A's night exterior is the best we have but its hall interior is wrong (eight fermenters, no copper brewhouse). ARC-02-B (scripted day-to-night grade of ARC-01-D) is **rejected, kept for provenance only**. ARC-02-C replaces *only the interior behind the Tank Hall glazing* with the canonical six-tank brewhouse, genuinely lit as a night scene. This is not grading.
- **SOURCE HIERARCHY:** ARC-02-A = entire night exterior/exposure/sky/landscape/people/entrance/atmosphere (outside the mask it stays pixel-identical). ARC-01-D = Tank Hall camera, mullions, exactly-six geometry, tank scale/positions, central brewhouse. ARC-01-E attempt 1 = **realism reference only** for sanitary equipment detail; never its frontal camera, symmetry, mullions or tank arrangement.
- **Mullions:** ARC-02-A's own mullions are locked and re-pasted by the composite step. ARC-01-D's mullions were registered onto them (same positions to within ~1-2 px, per the ARC-02-B registration), so the layout reference is aligned to the edit crop.

## INPUTS (all in `visuals/generated/ARC-02-C-inputs/`, 2000x1160 unless noted; crop box x40-1040, y250-830 of ARC-02-A, 2x)
| # | File | Role |
|---|---|---|
| 1 | `1-ARC-02-A-hall-context-crop-2x.png` | **Image to edit.** Night photo; canopy, limestone plinth, glazing, entrance for perspective |
| 2 | `2-hall-interior-edit-mask-2x.png` | **Edit mask.** White = may change (inside the glazing). Black = untouched |
| 3 | `3-mullion-frame-lock-mask-2x.png` | White = the original mullions to keep; re-pasted at composite time |
| 4 | `4-ARC-01-D-layout-ref-registered-2x.png` | **Arrangement reference, pixel-registered to #1.** DAYLIGHT: copy tank count, positions, deck, copper vessels, scale. **Never copy its sky, foliage, day exposure or reflections** |
| 5 | `5-ARC-01-E-attempt1-equipment-realism-ref-ONLY.png` (2000x965) | Equipment-detail realism reference only (piping, valves, tri-clamps, legs, pumps, deck, drains). Do not inherit its camera, symmetry, mullions or arrangement |

## EXTERNAL-GENERATION INSTRUCTIONS
1. Use an image editor/model that supports **masked inpainting with additional reference images** (e.g. a reference-aware image-edit model, or Photoshop Generative Fill/inpaint with #4 and #5 dropped in as references). If it takes only one reference, use #4 as the reference and paste the equipment-detail wording of the prompt.
2. Load #1 as the image, #2 as the mask (white = edit). Add #4 (and #5 if supported) as references. Paste the PROMPT and NEGATIVE below. Do **not** let the tool outpaint, resize, crop, or regenerate outside the mask. Request the output at the **same 2000x1160** size (any other size: tell me; I resize).
3. Generate a **single** image (a small batch of variants from the same call is fine to choose between by count, but do not iterate on prompts). Save the best as PNG and place it in the repo as `visuals/generated/ARC-02-C-edited-crop.png`, or upload it to the chat.
4. Do not retouch it. I run `python3 visuals/tools/arc02c_tools.py composite visuals/generated/ARC-02-C-edited-crop.png` (re-pastes ARC-02-A's mullions, feathers only the glass edge, reports outside-hall drift) and then review against `ARC-02-C-REVIEW-SHEET.md`.

## EDIT PROMPT
```
Edit ONLY the white-masked area of image 1: the interior behind the glass of the Tank Hall in a blue-hour night photograph. Everything outside the mask, and the dark-bronze window mullions, must stay exactly as they are. Image 4 (daylight, registered to image 1) shows the exact arrangement, camera and scale to reproduce; treat it as a layout drawing only: do NOT copy its daylight, sky, foliage or reflections. Image 5 shows the level of sanitary-brewery equipment detail wanted; do not copy its camera, symmetry or arrangement.

Replace the incorrect eight-tank interior with the canonical brewhouse, photographed natively at night, seen from the same oblique angle as image 1:
- EXACTLY SIX stainless fermenters, no more and no fewer, in image 4's arrangement: three readable fermenters on the left of the hall (two adjacent large ones at the far left, one slightly smaller one just west of the deck); in the centre a RAISED STEEL BREW DECK; on the right ONE large nearest fermenter with TWO more fermenters behind it to the right, partly hidden by a mullion and by each other. Oblique, not frontal, not a straight row, not symmetric.
- EXACTLY TWO copper-clad brewing vessels with domed tops on the central deck, under one copper hood with a stack rising to the ceiling. No other copper. Realistic steel deck, stair, 42-inch guardrails and catwalk; sanitary stainless piping, tri-clamps, butterfly valves, pumps, restrained sanitary hoses; tank legs with foot plates (four legs each); a seamless warm-grey matte production floor with stainless trench drains where the perspective shows the floor.
- Every fermenter: polished stainless cylindrical shell with a side manway, a matte GRAPHITE insulated cone clearly darker than the shell (never silver, never orange), and ONE narrow (about six inches, roughly one tenth of the tank diameter) deep marigold-orange removable powder-coated sleeve of about #E8870E around the middle of the shell: deep orange, not yellow, not glowing.
TRUE NIGHT LIGHTING, matching the exterior of image 1: the sky and exterior are blue-hour; inside, shielded 2200-2400K warm light and subtle narrow-beam uplights at the tank bases. The Tank Cloister is the brightest large feature of the picture but not overexposed: stainless carries warm elongated highlights with darker falloff; copper vessels have restrained warm reflections; the back of the hall falls off darker; realistic contact shadows; floor satin not glossy; drains catch tiny highlights. Because the interior is brighter than the outside, the glass is clearer than in daytime: only faint blue-hour tree reflections remain. No daytime sky or foliage visible inside the hall. Natural photographic grain and dynamic range, no HDR, bloom or haze.
```
## NEGATIVE
```
seven tanks, eight tanks, five tanks, extra fermenters, straight tank row, symmetric or frontal arrangement, changed camera, moved or duplicated mullions, missing or extra copper vessels, silver cones, orange or yellow cones, thick sleeves, yellow sleeves, glowing sleeves, brass architecture, orange wash, glossy showroom floor, excessive reflections, mirror glass, daytime reflections, sunset reflected in the hall, daytime sky or foliage inside the glass, star flares, star spikes, bloom, HDR, haze, fog, neon, string lights, logos, text, people inside production, architecture changes
```

## Acceptance (do not lower)
All 13 gates in `visuals/generated/ARC-02-C-REVIEW-SHEET.md`: six fermenters (counted twice), two copper vessels, oblique D arrangement, graphite cones, six narrow marigold sleeves, night-exposure match, no day sky/foliage in glass, no composite boundaries, mullions aligned, outside-hall drift effectively zero, hall brightest large feature without clipping, ARC-02 rubric >= 90, no hard fail. Founder approval is never automatic.

## Known limits (stated up front)
- A generator may not hold an exact count of six or the exact tank positions; that is the risk this attempt tests. Do not accept a "close" count.
- ARC-01-D's hall pixels show no trench drains; drains are requested "where perspective permits" and will be judged only if actually visible.
