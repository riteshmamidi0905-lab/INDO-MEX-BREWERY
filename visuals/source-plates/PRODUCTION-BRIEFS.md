# Production source images — briefs for seven individual generations (founder decision 2026-10-22)

The 2026-10-22 contact sheet and its crops are **reference / fit-test only** (low resolution; compositions approved as direction). Production needs **seven separate, high-resolution images**.

## Rules for every image
- **≥ 2048 px on the long side** (higher if the tool supports it). Deliver the generator's **native output**. Never upscale a smaller image and call it an original generation; the intake step is not bypassed (1600 px minimum, readable-text scan, advisory upscale detector, optional `--generated-size WxH` check).
- Photorealistic materials, professional commercial photography, natural shadows and reflections, premium warm lighting, consistent NASHA art direction.
- **No text, numerals, logos, labels or packaging claims anywhere. No invented product specifications.** Regenerate if the model draws any.
- Record for each: tool, plan (or "unverified"), date, exact prompt, native pixel size. Contact-sheet provenance already recorded: ChatGPT image generation, 2026-10-22, requested as unbranded photorealistic NASHA concept imagery; prompt text and plan unverified.
- Every image is a **conceptual AI-generated asset, not a photograph of any existing NASHA product or location**; the Gobi is labelled a **conceptual food visualization, not a tested menu item**.

| # | plate_id | Brief (what must be in frame) | Must stay clear / absent |
|---|---|---|---|
| 1 | `badshah_can` | Straight-on, upright slim aluminium can, realistic **neutral satin metallic** finish with condensation, premium warm lighting, full body visible incl. shoulders and base. | A **large uninterrupted label area** (no printing, embossing, dents, ring-pull marks beyond the real tab). |
| 2 | `amba_can` | **Same physical can dimensions, proportions, pose, camera and lighting as #1** (family consistency), tropical atmosphere (fruit, foliage) in the background. | No branding or decorative label artwork baked into the can; same clear label area. |
| 3 | `badshah_glass` | Weizen (tall vase) glass, hazy pale-gold wheat beer, thick white foam, realistic condensation, scene may include wheat. | **Clear, clean glass surface** with an uninterrupted mid-body zone suitable for vector etching; no etching. |
| 4 | `amba_glass` | Tulip/IPA glass, opaque hazy orange-gold beer, small foam head. | Same: clear surface, no etching, no text. |
| 5 | `hoodie` | Premium **heavyweight forest-green** hoodie, front view, improved lighting, **realistic construction** (seams, ribbed cuffs and hem, hood lining, stitching, drawcords). | **Chest and back free of graphics**, no labels or tag text. (A separate back view is welcome as an extra, but not one of the seven.) |
| 6 | `gobi` | **Editorial** food photography of Mango Habanero Gobi: crisp cauliflower texture, glossy sauce, believable plating, herbs. | No text, logos, menus. Caption: *conceptual food visualization, not a tested menu item*. |
| 7 | `brewhouse_exterior` | Court Brewhouse exterior/courtyard: **central glass-walled brewhouse with visible brewing equipment**, Indian–Mexican courtyard influences (arches, screened/jali-like details, tile, terracotta, planting), realistic structural proportions, warm evening lighting. | **One large, unobstructed, dark rectangular signboard facing the camera**, blank. **No lettering anywhere on the building.** |

## Prompt starters (adapt; always append "no text, no logos, no labels, no packaging claims")
1. "Professional commercial photograph, straight-on, of a single slim aluminium beer can with a neutral satin metallic finish and fine condensation droplets, warm golden evening light, shallow depth of field, soft natural shadow and reflection on a stone surface, large plain unprinted body."
2. "Same can, same camera and lighting as the previous image, tropical atmosphere with mango and palm foliage softly blurred behind, plain unprinted body."
3. "A tall weizen beer glass of hazy pale-gold wheat beer with a thick foam head and condensation, plain clear glass with no etching, warm courtyard light, shallow depth of field."
4. "A tulip IPA glass of opaque hazy orange-gold beer with a small foam head, plain clear glass with no etching, warm light, tropical fruit softly blurred."
5. "Premium heavyweight forest-green hoodie, front view, realistic ribbed cuffs and hem, visible seams and stitching, hood lining and drawcords, soft warm light, plain front with no graphics or labels."
6. "Editorial food photograph of crisp golden fried cauliflower florets in a glossy orange mango-habanero glaze, herbs, on a dark ceramic plate, warm side light, shallow depth of field."
7. "Warm evening photograph of a brewery-restaurant courtyard blending Indian and Mexican architectural influences: arches, screened details, patterned tile, terracotta, planting; a central glass-walled brewhouse with visible stainless brewing vessels; one large dark rectangular signboard above the entrance, completely blank, facing the camera; no lettering anywhere."

## After you generate each one
`python3 visuals/tools/plate_pipeline.py intake <file> --plate-id <id> --prompt-file <prompt.txt> --generated-on YYYY-MM-DD --generated-size WxH` → you review (`review <id> --decision accepted --by Ritesh`) → I set region/quad, `overlay`, `composite` (and `--variant g1` only on eligible full-resolution cans, glassware and signage; original wordmark stays primary; G1 never below 32 px cap height).
