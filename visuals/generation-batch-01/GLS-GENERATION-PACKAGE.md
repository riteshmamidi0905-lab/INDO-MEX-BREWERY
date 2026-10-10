# GLS-01 / GLS-02: final generation package

**Status:** **NOT GENERATED.** No image-generation tool exists in this environment (D-10), so nothing was rendered; no GLS image is claimed. Everything needed for a single run by the founder is ready.

## The glass family (canonical, `LOCKED-SCENE-DNA.md` §8; D-50)
| Glass | Height | Beer | Form | Collar |
|---|---|---|---|---|
| **Collar Weizen** | ~24-25 cm | ~0.5 L + 3-4 cm head | Tall wheat-beer vase, fine rim, thick clear base | Raised clear-glass ring ~5 mm proud, ~12 mm tall, rounded, one-quarter up (~6 cm) |
| **Collar Lager** | ~20 cm | ~0.4 L | Tall conical | Same ring, one-quarter up |
| **Reserve / Stepwell Goblet** | ~17 cm | ~0.20-0.25 L | Short stem, one subtle step in the bowl | Ring at the bowl-stem junction |
| **Collar Tulip (flight)** | ~10 cm | ~120 ml (4 oz) | Small tulip | Same ring, one-quarter up |
The collar is a **physical raised clear-glass ring**, integral to the glass and never wider than the rim. It is **not** paint, a logo or an ethnic motif. All glass is clear and colourless: no print, etching, colour, metal, facets or handles.

## Inputs (`visuals/generated/GLS-inputs/`)
| File | Use |
|---|---|
| `GLS-01-profile-guide-clean.png` | **Upload this one** for GLS-01: to-scale proportion reference (no text, so nothing leaks into the render) |
| `GLS-02-family-profile-guide-clean.png` | Upload this one for GLS-02 |
| `GLS-01-profile-guide.png`, `GLS-02-family-profile-guide.png` | Annotated versions for people; **do not upload** |
Drawings come from `visuals/tools/gls_profile_guide.py` (parametric outlines from the Locked DNA dimensions; not renders, not engineering).

## Run plan
1. **GLS-01:** paste the MASTER PROMPT and NEGATIVE from `GLS-01.md`; attach the clean guide as the proportion reference; ask for **4 variants**; save the best as PNG. Review with `visuals/generated/GLS-01-REVIEW-SHEET.md`.
2. **GLS-02:** paste `GLS-02.md`; attach the clean family guide and the best passing GLS-01 image; 4 variants; review with `GLS-02-REVIEW-SHEET.md`.
3. One targeted refinement per glass is allowed; then stop and report (no endless regeneration).
4. Do not retouch; log tool, references accepted, variant, seed, date in `visuals/generated/LOG.md`.
5. Not a manufacturing drawing: custom glass needs a glass engineer and dishwasher/thermal testing (`beer/GLASSWARE-V2.md`).
