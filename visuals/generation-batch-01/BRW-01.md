# BRW-01: Hero Tank Cloister (v2, D-47) — canonical authority for the Tank Cloister and brewing equipment

- **STATUS:** NOT GENERATED — PACKAGE PREPARED; **awaiting founder approval of camera, method and gates** (D-47). Do not generate until approved.
- **PURPOSE:** WE MAKE THE BEER HERE. BRW-01 becomes the canonical visual authority for the Tank Cloister and equipment. It must solve what ARC-02 could not: exactly six fermenters, a true horseshoe, two copper vessels on a raised deck, and real commercial-brewery organisation.
- **Authorities:** geometry = `LOCKED-SCENE-DNA.md` §4 + ARC-01-D (arrangement and mapping, see below). Equipment-photorealism = ARC-01-E attempt 1 **only** (never its camera, layout or symmetry). **ARC-02-A and ARC-02-C are not references for count, arrangement, cones, sleeves, deck, copper or mullions** (D-47).
- **Original v1 prompt** (frontal, centred, daylight, two brewers, steam): superseded, kept as `BRW-01-v1-superseded.md`.

## 1. PROPOSED CAMERA (intentional; replaces the ARC-02 editing setup)
| Item | Value | Why |
|---|---|---|
| Position | Guest side of the interior glass wall: south promenade/mezzanine edge, **about 11 ft above the floor**, about 11 ft south of the production room, **SE of the hall axis** (plan coordinates x=28, y=-11 in a 44x48 ft room; see `BRW-01-plan-camera.png`) | Reads as the real guest vantage (promenade/mezzanine, Locked DNA §5), and is the interior continuation of the ARC-01-D hero bearing (looking NNW) |
| Direction | NNW, about 20 degrees west of the hall's north axis | Oblique, not frontal: the horseshoe fans out and tanks overlap naturally |
| Lens | **21-24 mm equivalent**, full frame, level, verticals straight (shift-lens look) | A 44-ft-wide hall with 19-ft tanks cannot be framed longer from inside |
| Frame | 16:9, 2000x1125 or larger | Matches the blockout |
| Glass | **None in frame.** Treat the interior glass as invisible: the picture is taken as if through clear, non-reflective glass; at most a thin dark-bronze edge at the extreme foreground left | Avoids the reflection and glazing failures that sank ARC-02 |
| Time/light | Evening state: warm shielded 2200-2400K lighting dominant, narrow-beam tank-base uplights, faint indigo from the north clerestory. **Founder option:** daylight clerestory version instead (see section 6) | Evening is the state ARC-02 still needs; BRW-01 becomes its equipment reference |
| People | **None** in the hero render (equipment is the subject; add brewers only in a later variant) | Removes extra-count and anatomy risk |

## 2. COMPOSITION AND MAPPING (from the layout blockout; matches ARC-01-D)
- **Left group, three tanks, receding:** tank 1 (nearest left, leg west), 2, 3 (the smallest in frame, at the north base west of the deck).
- **Centre, raised brew deck** (~24 ft wide, 4 ft high) with **two copper-clad vessels**, copper hood, stack to the roof, stairs, 42-in guardrails; catwalk crossing behind and the west/east catwalk at +11 ft.
- **Right group, three tanks, receding:** tank 6 **large, nearest** at the right edge, tank 5 behind it, tank 4 (north base east of the deck) furthest, partially hidden by 5 and 6. This is the same "3 | deck | 1+2 behind" arrangement seen from outside in ARC-01-D.
- Numbering per Locked DNA: west leg south-north 1, 2; north base 3, 4; east leg north-south 5, 6. **No numerals in the image.**
- Exactly six fermenters, two copper vessels. Every tank identical.

## 3. EQUIPMENT VISIBILITY (must be legible, not decorative)
Polished stainless shell; **matte graphite insulated cone** (clearly darker than the shell); four legs with foot plates; round side manway with clamp; sample valve; thermowell; dished top with top manway, relief/spunding fitting and CIP arm; butterfly valves at the cone outlets; **tri-clamp** fittings; restrained sanitary piping on the inner side of the horseshoe; pumps and a valve train at the deck foot; coiled sanitary hoses on hooks; stainless hot-liquor tank on the deck; **stainless trench drains** along the legs and in front of the deck (floor slopes to them); light **warm-grey seamless satin floor**; **exactly one narrow (~6 in) deep-marigold (~#E8870E) removable powder-coated sleeve** per fermenter (not paint, not yellow, not glowing). Copper only on the two vessels and the hood. No brass.

## 4. INPUTS (`visuals/generated/BRW-01-inputs/` unless noted)
| # | File | Role |
|---|---|---|
| 1 | `BRW-01-layout-blockout.png` (2000x1125) | **Structure/layout guide** (depth/blockout). Six cylinders, graphite cones, sleeves, deck, two copper cylinders, hood and stack, from the proposed camera. Geometry only: copy count, positions, scale and camera, not its flat look. Not a photograph |
| 2 | `visuals/generated/ARC-01-E-inputs/ARC-01-D-hall-crop-2x.png` | Arrangement reference (daylight exterior view of the same hall) |
| 3 | `visuals/generated/ARC-01-E-external-crop-attempt1.webp` | **Equipment-realism reference only** |
| - | `BRW-01-layout-blockout-annotated.png`, `BRW-01-plan-camera.png` | For humans only. **Do not upload the annotated version to the generator** (numerals leak into the image) |

## 5. GENERATION METHOD (proposed)
1. Use a model that accepts a **structure/layout reference** (image-guided generation, depth/line-guided, or "use this image as a layout") plus style references. Upload #1 as the layout/structure guide at high strength; #3 for equipment detail; #2 for arrangement only. Text prompt below.
2. If the tool only supports one image: upload #1 and use the text; add #3 in a second pass for detail only if needed.
3. Generate **4 variants in one run**. Select by count. If a variant has the right count, a **targeted** fix may be allowed only after founder approval.
4. **Iteration cap (proposed):** two runs (8 variants). If none passes the count/arrangement gates, stop and report; no endless regeneration (the ARC-02 lesson).
5. Never retouch or script-grade. Log tool, model, references accepted, strength, seed, variant, date.

## MASTER PROMPT (self-contained; paste whole)
```
Photorealistic professional architectural interior photograph, full-frame camera, 21-24mm equivalent shift-lens look, level camera, perfectly straight verticals, real materials, natural imperfections, no CGI look. 16:9. The camera is on the guest side of a clear glass wall at the south end of a double-height brewing hall (about 38 ft clear), about 11 ft above the floor, looking north-north-west across the open end of a horseshoe of fermenters into the brewers' working floor. No glass, frame or reflection is visible in the picture.
Follow the supplied layout image exactly for camera, count and positions: EXACTLY SIX identical polished stainless-steel conical fermenters, each about 5 ft in diameter and about 19 ft tall including legs, in a HORSESHOE open toward the camera. Three on the left receding in depth (the nearest on the left, then two further away, the third beside the brew deck); in the centre a RAISED STEEL BREW DECK (about 4 ft high, 24 ft wide) with stairs and 42-inch guardrails carrying EXACTLY TWO copper-clad brewing vessels with domed tops (about 7 ft diameter) beneath one copper steam hood and a stack rising to the roof, with a stainless hot-liquor tank, pumps, a valve train and coiled sanitary hoses; on the right one LARGE fermenter nearest the camera, a second behind it, and a third furthest, the two behind partly hidden by the nearest one. A grated steel catwalk with 42-inch guardrails and kick plates at about 11 ft above the floor runs along both legs and behind the deck, with stairs.
Every fermenter: polished cylindrical stainless shell with a round side manway with clamp, sample valve, tri-clamp connections, dished top with top manway, CIP arm and relief fitting; a matte GRAPHITE insulated cone clearly darker than the shell; four short legs on foot plates; butterfly valve at the cone outlet; and exactly ONE narrow (about 6 inches) deep marigold-orange removable powder-coated sleeve of about #E8870E around the middle of the shell: deep orange, not yellow, not glowing. Restrained, tidy sanitary piping on the inner side of the horseshoe. Light warm-grey seamless satin production floor with stainless trench drains along the legs and in front of the deck that catch tiny highlights, floor sloping to the drains. The equipment looks like real commercial brewery equipment, as in the equipment reference image, not like props.
LIGHT: evening. Warm shielded 2300K architectural lighting and narrow-beam uplights at the base of each tank; the Tank Cloister is the brightest large feature but nothing is clipped; stainless shows warm elongated highlights with darker falloff; copper has restrained warm reflections; the back wall and ceiling fall off darker; faint indigo light only from the high north clerestory; realistic contact shadows; no haze, no bloom, no star flares, no god rays, no steam. No people. No logos, no text, no numerals.
```

## NEGATIVE
```
five tanks, seven tanks, eight tanks, extra fermenters, straight row of tanks, circular arrangement, frontal symmetric view, changed camera, silver cones, orange or yellow cones, thick sleeves, yellow sleeves, glowing sleeves, painted bands, extra copper vessels, brass, glass reflections, window frames, daytime sky, orange wash, glossy showroom floor, wet mirror floor, star flares, bloom, HDR, haze, fog, steam, neon, string lights, pendant lights, logos, text, numerals, people, patterned or decorated tanks, sci-fi or fantasy machinery, glowing pipes, cartoon, CGI look
```

## 6. FOUNDER DECISIONS NEEDED BEFORE GENERATING
(a) Camera as proposed? (b) Evening lighting, or the daylight version? (c) No people in the hero render? (d) Iteration cap of two runs? (e) A different tool that accepts a layout/structure reference, since the tool used for ARC-02 ignored the mask.

## ACCEPTANCE (see `visuals/generated/BRW-01-REVIEW-SHEET.md`; do not lower)
Six fermenters counted twice; two copper vessels; horseshoe/oblique arrangement matches the blockout and D mapping; graphite cones; six narrow ~#E8870E sleeves; deck, hood, stack, stair, guardrails, catwalk; sanitary piping, tri-clamps, butterfly valves, pumps, hoses; legs/foot plates; trench drains visible; warm-grey satin floor; evening lighting without orange wash; brewer-credible equipment; rubric >= 90, no hard fail, founder approval.
