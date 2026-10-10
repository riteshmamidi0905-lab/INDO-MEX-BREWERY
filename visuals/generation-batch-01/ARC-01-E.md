# ARC-01-E: Final realism pass (image-to-image refinement of ARC-01-D)

- **ID:** ARC-01-E  |  **STATUS:** NOT GENERATED — FINAL REALISM PASS PREPARED
- **Authority:** ARC-01-D (`visuals/generated/ARC-01-D.png`, 2000x1128, 89/100, scripted post-production edit of ARC-01-C) is the composition and geometry authority. Visual DNA v2.1 and Locked Scene DNA v1.2 govern everything else (D-39).
- **PURPOSE:** solve the one remaining deficit, the AI-soft Tank Hall interior, **without changing the design**. Add micro-realism only.
- **STOPPING RULE (D-40):** if ARC-01-E drifts, miscounts or adds problems it is **rejected** and ARC-01-D becomes the canonical day reference through a documented founder waiver at 89/100. **There is no ARC-01-F** unless the founder explicitly overrides.
- **ASPECT:** 16:9, identical framing (2000x1128).

## RECOMMENDED METHOD (protects everything outside the glass)
Earlier edits re-rendered the whole image, so do **not** send the full frame to a global image-to-image model. Instead:
1. Run `python3 visuals/tools/arc01e_tools.py prepare` (already run; outputs are in `visuals/generated/ARC-01-E-inputs/`): `ARC-01-D-hall-crop-2x.png` (the Tank Hall crop at 2x, 1740x840), `hall-edit-mask-2x.png` (white = interior behind the glass, may change), `hall-frame-lock-mask-2x.png` (mullions, must not change).
2. Give the crop plus the edit mask to the image editor, with the EDIT PROMPT below (inpainting at 2x gives the model room for fine detail).
3. Composite the result back: `python3 visuals/tools/arc01e_tools.py composite <edited_crop.png>`. It feathers the edit, re-pastes the original mullions, and leaves every pixel outside the hall glass identical to ARC-01-D.
4. Check drift: `python3 visuals/tools/arc01e_tools.py compare visuals/generated/ARC-01-E.png`.
If the tool cannot mask, send the whole of ARC-01-D with the same prompt, then still run `compare`; a global re-render with outside-hall RMSE > 10 fails the preservation test.
Log in `visuals/generated/LOG.md` the tool and model that produced the **edited crop** (the composite script is not a generator).

## EDIT PROMPT (paste whole)
```
This is a surgical realism edit of an existing architectural photograph of a Central Texas craft brewery. The image is the glazed Tank Hall seen from outside at late afternoon. Edit ONLY the brewery equipment and floor visible behind the glass (white area of the mask). Keep every object at exactly the same position, scale, count and colour as in the input; add only fine real-world detail and photographic realism. Do not redesign anything.

KEEP EXACTLY AS IS: EXACTLY SIX stainless-steel fermenters in the existing horseshoe (two on the west side, one west of the raised brew deck, one east of it, two behind it on the east side, as in the input); each fermenter's polished stainless cylindrical shell, matte graphite insulated cone, four legs, side manway and its single narrow (about six inches, about one tenth of the tank diameter) deep marigold-orange (about #E8870E) removable powder-coated sleeve around the middle of the shell; the two large copper-clad brewing vessels with domed tops on the raised brew deck with their copper hood and stack, exactly where they are; the dark-bronze window mullions; the concrete canopy, limestone, entrance, arcade and everything outside the glass; the camera, perspective, sun direction and warm shielded interior lighting. No extra, missing, resized, moved or reordered tanks. No additional copper vessels: copper only on those two vessels and their hood.

ADD ONLY THIS MICRO-REALISM, as it would appear in a sharp commissioned architectural photograph of a newly opened premium working brewhouse:
1. Sanitary stainless pipework: smooth 2B/brushed stainless tube with neat orbital-weld seams, consistent routing, clean elbows and tees, supported by simple stainless pipe clamps on the structure.
2. Tri-clamp connections: crisp ferrules with visible gaskets and wing-nut clamps at every pipe joint and tank outlet.
3. Butterfly valves with short stainless lever handles at the cone outlets and on the main headers.
4. Tank legs and foot plates: four tubular stainless legs per tank with bracing and adjustable foot plates bolted to the floor, with small contact shadows.
5. Hoses: a few restrained sanitary hoses (clear or white braided) neatly coiled on stainless wall hooks or hanging from the raised deck, never draped across walkways.
6. Stainless trench drains: slim grated trench channels about six inches wide running along the base of the west and east tank groups and in front of the brew deck, with a faint film of moisture beside the drain grates.
7. Production floor: a seamless sealed warm-grey brewery floor (matte-satin urethane-cement look) with subtle tonal variation and soft contact shadows under tank legs and equipment; it is NOT the guest terrazzo and has no tile pattern.
8. Brew deck: realistic stairs with non-slip treads, steel guardrails at 42 inches with a mid-rail and kick plate, grated deck surface, and clean connections to the two copper vessels.
9. Pumps and utilities: one or two stainless sanitary pumps with grey motors on a skid, glycol and CIP lines with neat insulation sleeves, small control boxes in grey; physically plausible connections only.
10. Stainless reflections: believable, soft, warm interior reflections and slight tonal variation between polished and brushed surfaces; fingerprint-free; tiny working marks and micro-scuffs only where physically natural.
11. Glass: natural, physically plausible reflections of the oak trees and sky on the outer glass at moderate strength with slight refraction at the mullion edges; the equipment stays clearly visible through it.
12. Depth: subtle atmospheric separation behind the glass, back wall slightly darker than the foreground equipment, believable depth of field consistent with the rest of the photograph.
13. Shadows: physically plausible contact shadows and soft occlusion shadows between tanks, deck, floor and pipes, consistent with the warm shielded uplights.
14. Sharpness: crisp equipment edges and fine detail equal to the sharpness of the limestone and concrete outside, without oversharpening, halos or artificial HDR.
The brewery must look clean, new and working: not dirty, not distressed, not abandoned, not grimy. Natural dynamic range, correct verticals, no CGI sheen, no artificial haze, no synthetic symmetry. No readable numbers, labels, text or logos anywhere.
```

## NEGATIVE PROMPT
```
seventh tank, extra fermenters, missing fermenter, moved tanks, resized tanks, reordered tanks, a row of tanks, silver or shiny cones, thick or yellow tank bands, painted tank bands, extra copper vessels, copper pipes everywhere, decorative copper, brass, terracotta, ink-blue or coloured decorative tile, colourful cultural tile, jaali, mandalas, rosettes, sunbursts, radial screen motifs, religious imagery, cultural symbols, agave feature planting, palms, string lights, neon, hacienda styling, Indian palace styling, Mexican theme-park styling, logos, readable signage, numbers or labels, new people, new vehicles, new buildings, changes to architecture, changes to the arcade or screens, changes to the entrance, changes to the sky or light, bright bronze or golden mullions, black mullions, guest terrazzo on the production floor, dirt, rust, grime, graffiti, cartoon, CGI render look, plastic surfaces, oversharpening, HDR halos, cinematic haze, fog, lens flare, mirror-like glass, missing glass
```

## ACCEPTANCE RULE (summary; full sheet in `visuals/generated/ARC-01-E-REVIEW-SHEET.md`)
E wins only if all are true: exactly six fermenters; no architectural geometry drift; Tank Cloister intact; exterior essentially unchanged; equipment materially more realistic than D; no new clichés; ARC-01 rubric >= 90/100; no hard fail. Otherwise reject E; D becomes canonical by founder waiver at 89/100. No ARC-01-F.
