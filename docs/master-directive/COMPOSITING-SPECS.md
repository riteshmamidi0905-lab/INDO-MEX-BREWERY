# Photorealistic compositing specifications (v1, 2026-10-22)

Status: SPEC ONLY. No photorealistic plate exists yet (no free generator reachable from Claude Code; see `PHOTOREAL-BLOCKER.md`). The compositing tool is built and tested on a procedural plate (`visuals/tools/composite_label.py`, `brand/tools/can_mockups.py`).

## Rules that apply to every plate
1. **Blank**: no text, numerals, logos, ABV, barcodes or marks anywhere on the product or in the scene's signage. Reject and regenerate any plate that has them; never repair model-drawn text.
2. **Provenance first**: record tool, plan (free/paid), date, prompt, the account owner, and the tool's terms-of-use link in `visuals/brand-v3/PROVENANCE.json` before the plate is used. Source plates are "AI-generated concept imagery", never "product photography".
3. **Branding comes only from verified vector masters** (`brand/logo/CONTROLLED-MASTERS/…`, `visuals/brand-v3/labels/*.svg`). Placeholders (ABV, volume, ingredients, certifications, regulatory text, barcode) stay as placeholders.
4. Source (full-resolution plates, PSD/PNG) and optimised web assets live in separate folders; web assets never overwrite sources.
5. QA at full size and at website display sizes (1600, 800, 400 px wide); checklist below.

## Plate specifications
| Plate | Blank-plate requirement | Composite method | Zones to mask |
|---|---|---|---|
| BADSHAH can + wheat-beer glass | 500 ml-style slim can, plain satin aluminium or flat dark-green matte body, 3/4 or straight-on, soft side light; weizen glass (tall vase shape) with pale hazy-gold beer, white foam, **no etching/label**; neutral surface | Can: `cylinder_warp` + plate-luminance shading (label zone = full body between shoulders). Glass: place crest as a 1-colour print (white 85% opacity, multiply by glass refraction mask), size ≤ 18% of glass height | can label zone; glass print zone (mid-body, 45–60% of height) |
| AMBA HAZE can + IPA glass | Same can body (family consistency); tulip/teku-style glass with opaque, orange-gold hazy beer, small foam head, no etching | Same as above | same |
| Court Brewhouse exterior + courtyard | Evening exterior: arched openings, glass-walled brewhouse visible, courtyard seating with fire pit, planted; **sign panel left empty** (flat dark board); no people faces required; no readable text anywhere | Perspective-warp the wordmark/crest onto the empty sign panel (4-point homography), add emissive glow as a soft screen layer, never as a model-drawn logo | sign board; optional second small sign |
| THE COURTYARD hoodie | Forest-green hoodie flat-lay or on a neutral form, **blank chest/front**, visible fabric texture and folds | Place symbol + monogram with multiply + 6–10% displacement from the fabric luminance; keep colour in the printed-ink gamut (antique gold ≈ #B8923A) | chest zone, left-chest zone |
| Mango Habanero Gobi | Plated fried cauliflower with mango-habanero glaze, herbs; plausible fryer crust and glaze gloss; no text; plate/surface blank. Disclose: **concept dish, never cooked or tasted by us; image is illustrative** | No logo compositing needed except an optional menu card (flat) | none |

## Prompts for blank plates (to run in a free tier you already hold; check its terms and record them)
- *BADSHAH/AMBA can*: "Studio product photo of a single blank, unlabelled 500 ml slim aluminium beer can, matte [dark green | satin silver], soft warm side light, shallow depth of field, plain warm-grey surface, no text, no logos, no printing of any kind."
- *Glasses*: "A tall weizen beer glass filled with hazy pale-gold wheat beer and a thick white foam head, plain glass, no etching, no text, warm window light, blurred courtyard background." / "A tulip IPA glass with hazy orange-gold beer and a small foam head, plain, no text."
- *Brewhouse*: "Dusk photograph of a contemporary brewery-restaurant courtyard: arched steel-framed windows, a glass-walled brewhouse with tanks glowing, planted courtyard with a fire pit and warm string lights, a large **blank dark sign board** above the entrance, no text anywhere."
- *Hoodie*: "Forest-green heavyweight hoodie, front view, plain with no print, soft studio light, visible knit texture, neutral background."
- *Gobi*: "Crispy fried cauliflower florets tossed in a glossy orange mango-habanero glaze, fresh herbs, on a dark ceramic plate, side light, no text."

## QA checklist (reject on any "no")
- No text/numerals/logo-like marks left in the plate. · Label edges follow the can's curvature; seams not visible in front view. · Shading/specular from the plate preserved on the ink. · Colour of ink inside brand palette ±8 ΔE after shading. · Foam/glass/liquid plausible for the style (hefeweizen = hazy pale gold, tall vase glass; hazy IPA = opaque orange-gold, tulip). · Hoodie print follows folds. · Disclosure caption "AI-generated concept imagery — not a product photograph" on every use. · Recorded provenance and rights status.
