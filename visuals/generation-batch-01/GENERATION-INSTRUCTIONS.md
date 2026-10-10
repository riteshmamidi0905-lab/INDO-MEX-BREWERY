# Generation Instructions: Batch 01 (Visual Lock)

Five assets lock the world: **ARC-01, ARC-02, BRW-01, GLS-01, GLS-02.** Do **not** generate any of the other 52 assets until this batch is reviewed and approved. Do not build a website.

> **Update (D-42, current):** ARC-01 is FINISHED. **ARC-01-D is APPROVED — CANONICAL DAY EXTERIOR (founder waiver 89/100).** ARC-02 is unblocked (`ARC-02.md`, use ARC-01-D as the init/reference image). BRW-01, GLS-01, GLS-02, expansion, branding and website remain blocked until instructed.

> **Superseded update (D-40):** ARC-01-D (89/100, scripted edit) is the geometry authority. The only pending ARC-01 step is **ARC-01-E** (`ARC-01-E.md`). If E is rejected, ARC-01-D becomes canonical by founder waiver; there is no ARC-01-F. ARC-02 stays blocked until then.

> **Earlier update (2026-10-10):** ARC-01-A was generated and reviewed (73/100, hard fail on screens). The next image is **ARC-01-B** (`ARC-01-B.md`). ARC-01.md is superseded. ARC-02, BRW-01 and the glasses stay blocked until ARC-01-B is approved.

## Sequence (do not reorder without a strong reason)
1. **ARC-01.** Generate 4 or more variants. Founder reviews. Revise until approved. Save the approved image as the canonical day reference.
2. **ARC-02** using approved ARC-01 as the image reference (same camera, same building).
3. **BRW-01** using approved ARC-01/ARC-02 as references for materials, glass and tank design.
4. **GLS-01.**
5. **GLS-02** using approved GLS-01 as the reference.
6. Founder visual-lock review of all five together. Only then continue with remaining architecture, beer, food, people, packaging, merchandise, website heroes (in that order). Website development comes last.

## How to use the prompts
- Paste the **MASTER PROMPT** whole. They are long on purpose: continuity matters more than brevity. If the tool has a negative-prompt field, paste the **NEGATIVE CONSTRAINTS** there; otherwise append them after the text "Avoid:".
- Use the stated aspect ratio. Request at least 4 variants per run.
- If the tool accepts reference images, attach the references named in each file. Without references, repeat the geometry text verbatim (the prompts already do).
- Keep seeds where the tool allows and log them.
- Never ask the generator to write the sentence "Concept visual: not an operating business" inside the image. Record it in the caption/metadata.
- If a tool garbles small text (tank numerals): remove the numerals; do not accept distorted text.

## Short-form fallback (for tools with a ~300-word limit)
Always keep these core facts in any shortened prompt.
- **Common geometry:** "Contemporary Central Texas brewery; double-height glass-walled brewing hall (left) with limestone plinth, bronze mullions and concrete canopy; entrance recess beside its SE corner with a blank blackened-steel sign; shaded courtyard to the right with 14-ft arcades of board-formed concrete columns, cedar elm beams, charcoal standing-seam roof, laser-cut blackened-steel screens with round perforations forming ring shapes; long low limestone restaurant block across the court with two slim steel stacks; gravel court with a shallow stone rill, pecan communal tables, cedar elms, live oaks, native grass; EXACTLY SIX polished stainless conical fermenters in a HORSESHOE, charcoal insulated cones, one narrow marigold-orange band each, two copper-clad brew vessels on a raised deck at the back."
- **ARC-01:** + "late-afternoon hard sun from camera-left, eye level, 24-28mm, 16:9, straight verticals, no logo, no text."
- **ARC-02:** + "Same scene and camera as the supplied reference photograph (ARC-01-D), relit at blue hour/night: deep indigo sky, tanks the brightest large feature behind real glass, shielded warm 2300K light, dark flat perforated panels (no glow), restaurant and kitchen windows warm, relaxed guests at communal tables, no string lights, neon, flares or starbursts, exactly six tanks, graphite cones, narrow marigold sleeves, two copper vessels, no architecture changes, 16:9."
- **BRW-01:** + "interior from behind bronze-framed glass, camera 4 ft high, 28-35mm, six tanks horseshoe, two copper vessels on deck, catwalk, trench drains, two brewers working, 16:9."
- **GLS-01:** "Empty 0.5 L Weizen glass, 24-25 cm tall, thick base, fine rim, one raised clear ring a quarter of the way up the base, on pale limestone, raking studio light, 100mm macro, 4:5, no print, no logo."
- **GLS-02:** "Four empty glasses with the same ring: tall Hefeweizen, conical Lager, stemmed Reserve goblet with one step, small Flight tulip, descending heights, limestone studio, 3:2."

## Handling drift
- Wrong number of tanks → regenerate or inpaint; never accept five or seven.
- Tanks decorated or patterned → regenerate.
- Terracotta/brass/tile creeping in → add to negatives and regenerate.
- Mullion rhythm, canopy, arcade depth are secondary; tank count/arrangement, glass ring position and hero camera are primary.
- If one image is excellent but off in a detail, fix in post (inpainting) rather than rerolling forever, and log it.

## Logging (required)
For every output, add a row to `visuals/generated/LOG.md`: asset ID, tool, model, date, prompt (file + version), reference image, seed, version, status, founder approval, notes. Store the approved files in `visuals/generated/` using `ARC-01_v03_approved.png` style names.

## Review gate
The founder reviews the five together using each file's REVIEW CHECKLIST and ACCEPTANCE CRITERIA. Outcome per asset: APPROVED / REVISE / REJECT. Only approved images become references.
