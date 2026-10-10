# BRW-01: Hero Tank Cloister (v2, D-47) — canonical authority for the Tank Cloister and brewing equipment

- **STATUS:** NOT GENERATED — **PACKAGE APPROVED FOR GENERATION (D-48)**; Run 1 (four variants) pending, to be made by the founder with ChatGPT image generation.
- **PURPOSE:** WE MAKE THE BEER HERE. BRW-01 becomes the canonical visual authority for the Tank Cloister and equipment. It must solve what ARC-02 could not: exactly six fermenters, a true horseshoe, two copper vessels on a raised deck, and real commercial-brewery organisation.
- **Authorities:** geometry = `LOCKED-SCENE-DNA.md` §4 + ARC-01-D (arrangement and mapping, see below). Equipment-photorealism = ARC-01-E attempt 1 **only** (never its camera, layout or symmetry). **ARC-02-A and ARC-02-C are not references for count, arrangement, cones, sleeves, deck, copper or mullions** (D-47).
- **Original v1 prompt** (frontal, centred, daylight, two brewers, steam): superseded, kept as `BRW-01-v1-superseded.md`.

## 1. APPROVED CAMERA (D-48)
| Item | Value |
|---|---|
| Position | Guest side of the interior glass wall: south promenade/mezzanine edge, **camera height about 10.5-11 ft**, about 12 ft south of the production room, southeast of the hall axis (plan x=30, y=-12 in the 44x48 ft room; `BRW-01-plan-camera.png`) |
| Bearing | **NNW** (about 13 degrees west of the hall's north axis), continuing ARC-01-D's visual logic |
| Lens | **24 mm full-frame equivalent**; 22-26 mm allowed only if necessary to fit the composition. **Do not default to 21 mm** (distortion enlarges the nearest fermenter and collapses the far side of the horseshoe). Verticals corrected. Priority: readable six-tank geometry, not field of view |
| Frame | 16:9 |
| Glass | None visible; no frame, reflection or window edge |
| Light | Evening/blue hour. Interior practical light about 2300K; **subtle cool ambient blue-hour fill** so stainless stays neutral and reads as stainless; restrained, architectural tank-base uplights (not theatrical beams). Do not turn the room orange |
| People | **None** |

## 2. COMPOSITION AND SPATIAL ORGANISATION
Primary fact: **EXACTLY SIX FERMENTERS TOTAL, forming ONE horseshoe/U around the central raised brew deck.** The following only describes where those same six stand; it never adds tanks:
- the **west leg recedes northward** (two fermenters, the nearer on the left of frame);
- the **north pair flank the brew deck** (one west of the deck, one east of it);
- the **east leg returns southward toward the camera** (two fermenters), the **nearest of them is spatially Tank 6** and appears large at the right edge, with the other east-leg fermenter and the east north-pair fermenter partly hidden behind it.
Raised brew deck at the centre with **two copper-clad vessels**, hood, stack, stairs, 42-in guardrails; catwalk at +11 ft. **No numeral appears in the image.** Tank 3 is not "an extra tank beside the deck": it is the west member of the north pair.

## 3. EQUIPMENT VISIBILITY (must be legible, not decorative)
Polished stainless shell; **matte graphite insulated cone** (clearly darker than the shell); four legs with foot plates; round side manway with clamp; sample valve; thermowell; dished top with top manway, relief/spunding fitting and CIP arm; butterfly valves at the cone outlets; **tri-clamp** fittings; restrained sanitary piping on the inner side of the horseshoe; pumps and a valve train at the deck foot; coiled sanitary hoses on hooks; stainless hot-liquor tank on the deck; **stainless trench drains** along the legs and in front of the deck (floor slopes to them); light **warm-grey seamless satin floor**; **exactly one narrow (~6 in) deep-marigold (~#E8870E) removable powder-coated sleeve** per fermenter (not paint, not yellow, not glowing). Exactly two copper-clad brewing vessels; the copper may continue into their associated hood/duct where the locked design requires, but no additional copper tanks. No brass.

## 4. INPUTS (`visuals/generated/BRW-01-inputs/`), in priority order
| # | File | Role |
|---|---|---|
| 1 | `BRW-01-layout-blockout.png` (2000x1125, unannotated) | **Composition / spatial-count reference.** Six cylinders, graphite cones, sleeves, deck, two copper cylinders, hood, stack, at the approved camera. Not a photograph; copy count, positions, scale and camera, not its flat look |
| 2 | `2-ARC-01-D-hall-arrangement-ref.png` (1740x840) | **Canonical architectural/arrangement reference** (the hall from outside, daylight). Arrangement only |
| 3 | `3-ARC-01-E-attempt1-equipment-realism-ref-ONLY.png` (2000x965) | **Equipment-detail/photorealism reference ONLY.** Do not inherit its frontal symmetry, camera or layout |
| - | `BRW-01-layout-blockout-annotated.png`, `BRW-01-plan-camera.png` | Humans only. **Do NOT upload the annotated blockout** (numerals leak) |
Not references: ARC-02-A/B/C (never for Tank Hall geometry).

## 5. GENERATION METHOD AND RUN POLICY (D-48)
- Tool: **ChatGPT image generation** with the actual unannotated blockout plus the two canonical references. **The blockout is not mathematically enforced** (no ControlNet-level lock); the acceptance gates, not the method, decide usability.
- **Run 1 = four variants.** STOP and formally review all four before authorising Run 2. Maximum two runs / eight variants in total.
- If any Run-1 variant scores >= 90, has no hard fail and passes every mandatory gate, **do not generate Run 2** to look for something prettier. If all four fail, report exactly why before Run 2.
- **Hard count gate first:** count fermenters manually twice at enlarged scale before aesthetics. 5 = reject; 6 = continue; 7+ = reject. Count copper vessels independently (exactly two).
- No retouching, no scripted grading. Log tool, references accepted, variant, date, run number.

## MASTER PROMPT (self-contained; paste whole)
```
Photorealistic professional architectural interior photograph, full-frame camera, 24mm equivalent lens, level camera with corrected, perfectly straight verticals, real materials, natural imperfections, no CGI look. 16:9.

THE ONE RULE: EXACTLY SIX FERMENTERS TOTAL, forming ONE horseshoe (U) around a central raised brew deck. Six, not five, not seven, not eight. Everything below only describes where those same six stand; it never adds a tank.

Use the first reference image (a plain 3D layout block-out) for camera position, composition, count and spatial positions; use the second reference (the building from outside) for the hall and the arrangement; use the third reference only for the level of real sanitary-brewery equipment detail, not for its camera or layout. The result must be a photograph of real equipment, not a copy of the flat block-out.

Camera: on the guest side of a clear glass wall at the south end of a double-height brewing hall (about 38 ft clear), about 10.5 to 11 ft above the floor, southeast of the hall axis, looking north-north-west across the open end of the horseshoe into the brewers' working floor. Oblique, not frontal, not symmetric. No glass, window frame or reflection is visible.

Spatial organisation of the six fermenters: the west leg recedes northward (two fermenters, on the left of the frame); the two fermenters of the north pair flank the central brew deck (one west of it, one east of it); the east leg returns southward toward the camera (two fermenters), its nearest fermenter standing large at the right edge of the frame with the other east-leg fermenter and the east north-pair fermenter partly hidden behind it. No numerals appear anywhere.

Centre: a raised steel brew deck (about 4 ft high, 24 ft wide) with stairs and 42-inch guardrails carrying EXACTLY TWO copper-clad brewing vessels with domed tops (about 7 ft diameter) beneath one copper steam hood and stack rising to the roof, with a stainless hot-liquor tank, pumps, a valve train and restrained coiled sanitary hoses. A grated steel catwalk with 42-inch guardrails and kick plates at about 11 ft above the floor runs along both legs and behind the deck, with stairs. No brass.

Every fermenter is identical, about 5 ft in diameter and 19 ft tall including legs: a polished stainless cylindrical shell with a round side manway with clamp, sample valve, tri-clamp connections, dished top with top manway, CIP arm and relief fitting; a matte GRAPHITE insulated cone clearly darker than the shell; four short legs on foot plates; a butterfly valve at the cone outlet; and exactly ONE narrow (about 6 inches) deep marigold-orange removable powder-coated sleeve of about #E8870E around the middle of the shell (deep orange, not yellow, not glowing). Restrained, tidy sanitary piping on the inner side of the horseshoe. A light warm-grey seamless satin production floor with stainless trench drains along the legs and in front of the deck that catch tiny highlights, floor sloping to the drains. It looks like real commercial brewery equipment, not props.

Light: blue-hour evening. Interior practical lighting about 2300K, shielded and low, plus subtle cool blue-hour ambient fill from the high north clerestory, so the stainless stays neutral and reads as stainless; the room must not turn orange. Narrow, restrained, architectural uplights at the base of each tank, not theatrical beams. The tank cloister is the brightest large feature but nothing is clipped; stainless shows warm elongated highlights with darker falloff; copper has restrained warm reflections; the back wall and ceiling fall off darker; realistic contact shadows. No people. No logos, text or numerals. No haze, bloom, star flares, god rays or steam.
```

## NEGATIVE
```
five tanks, seven tanks, eight tanks, extra fermenters, straight row of tanks, circular arrangement, frontal symmetric view, changed camera, silver cones, orange or yellow cones, thick sleeves, yellow sleeves, glowing sleeves, painted bands, extra copper vessels, brass, glass reflections, window frames, daytime sky, orange wash, amber monochrome room, glossy showroom floor, wet mirror floor, star flares, bloom, HDR, haze, fog, steam, neon, string lights, pendant lights, logos, text, numerals, people, patterned or decorated tanks, sci-fi or fantasy machinery, glowing pipes, cartoon, CGI look
```

## 6. Founder decisions (all resolved, D-48)
Camera approved with refinement (24 mm, 10.5-11 ft); evening/blue hour with cool ambient fill; no people; two-run cap; ChatGPT image generation with the unannotated blockout.

## ACCEPTANCE (see `visuals/generated/BRW-01-REVIEW-SHEET.md`; do not lower)
Six fermenters counted twice; two copper vessels; horseshoe/oblique arrangement matches the blockout and D mapping; graphite cones; six narrow ~#E8870E sleeves; deck, hood, stack, stair, guardrails, catwalk; sanitary piping, tri-clamps, butterfly valves, pumps, hoses; legs/foot plates; trench drains visible; warm-grey satin floor; evening lighting without orange wash; brewer-credible equipment; rubric >= 90, no hard fail, founder approval.
