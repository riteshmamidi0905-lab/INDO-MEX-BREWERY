# Source-plate import folder (concept imagery only)

You generate **clean, unbranded** plates with ChatGPT's image-generation tool; Claude composites the verified NASHA vector artwork onto them. Nothing here is published, and nothing is a photograph of an existing NASHA product or location.

## How to deliver a plate
1. Drop the image into `visuals/source-plates/incoming/<plate_id>/` (or tell me the path), plus a `.txt` with the exact prompt, the date, and which ChatGPT plan/model you used (record "not independently verified" if unsure).
2. I run `python3 visuals/tools/plate_pipeline.py intake <file> --plate-id <id> --prompt-file <prompt.txt> --generated-on YYYY-MM-DD`. Automatic checks: format, ≥ 1600 px long side, and an OCR scan that must find **no readable text**.
3. **You review and accept** (`review <id> --decision accepted --by Ritesh`). Compositing refuses any plate that is not human-accepted.
4. I set the region/quad in `visuals/compositing-configs/<id>.json`, check it with `overlay`, then `composite`. Outputs land in `visuals/composites/<id>/` with full-size PNG, 1600/800/400 px WebP and a provenance sidecar. `qa` re-verifies hashes.

## Plate ids and what each plate must look like
| plate_id | Subject | Must be | Must NOT contain |
|---|---|---|---|
| `badshah_can` | slim aluminium can | upright, straight-on, satin/matte **single colour** body, full body visible, soft side light | any text, numerals, logos, barcodes, ring-pull branding, graphics |
| `badshah_glass` | tall weizen (vase) glass | hazy pale-gold wheat beer, thick white foam, empty mid-body (print zone ≥ 150 px wide in final image) | etching, text, brand marks |
| `amba_can` | **same can body as BADSHAH** | same pose/lighting for family consistency | as above |
| `amba_glass` | tulip IPA glass | opaque orange-gold hazy beer, small foam head, plain mid-body | etching, text, brand marks |
| `brewhouse_exterior` | dusk exterior + courtyard | arched steel-framed windows, glass-walled brewhouse, fire pit, planting; **one large blank dark sign board facing the camera** | any signage text, menus, readable posters |
| `hoodie` | forest-green hoodie, front | plain, visible knit texture/folds, blank chest | any print, label, tag text |
| `gobi` | plated crispy cauliflower in glaze | dark plate, herbs, side light | text, logos, menus; (concept dish — never prepared or tasted by us) |

Prompts for each are in `docs/master-directive/COMPOSITING-SPECS.md`. Add "no text, no logos, no labels, no packaging claims" to every prompt, and regenerate if the model draws any anyway.

## Rules the pipeline enforces
- Every plate and composite is recorded as: **AI-generated conceptual asset, not a photograph of any existing NASHA product or location.** Tool/plan/terms are recorded as unverified unless you verify them.
- Only verified vector masters are used (`visuals/brand-v3/labels`, `visuals/brand-v3/artwork`). Specs on label art stay placeholders: ABV, volume, ingredients, certifications, regulatory text, barcode, tasting notes.
- **Glass-A G1** is allowed only on cans (`--variant g1`), glassware and architectural signage; its cap height must be ≥ 32 px on the final image (≈ ≥ 136 px wide for the text cut, ≥ 154 px for the small cut). Apparel, food and small formats use the original wordmark.
- Never push, merge, deploy or publish from this folder without the founder's approval.

## Reference / fit-test category (2026-10-22 decision)
The seven low-resolution crops and the contact sheet they came from are in `reference-fit-test/` with review status `reference`: compositions approved as creative direction, **not** production assets. They fail the 1600 px intake minimum and must not be upscaled. See `PRODUCTION-BRIEFS.md` for the seven replacement images.

## Layout
`incoming/` (received, unreviewed) · `accepted/` · `rejected/` · `reference-fit-test/` · `PLATE-REGISTER.json` (provenance + review state) · `../compositing-configs/*.json` · `../composites/` (outputs + `COMPOSITE-REGISTER.json`).
