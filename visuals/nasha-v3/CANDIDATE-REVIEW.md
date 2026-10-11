# NASHA Candidate Review (Sprint 10)

## Sprint 18 update (2026-10-11): native-size visual QA of recompressed copies; exact originals NOT preserved
**Status: VISUALLY QA'D - ORIGINAL FILES NOT PRESERVED.** The sandbox cannot reach figma.com (proxy 403, name does not resolve; WebFetch fails too). The founder opened the Figma links in a browser and sent the images through chat. Nine arrived at native size (1376x768, 1200x896 for A6, 1024x1024 for B1 truth) but as lossy WebP re-encodes, so none is byte-identical to Figma's PNG, no SHA-256 of an original exists, and **0/10 exact originals are preserved in the repository**. The copies were reviewed in the session only and not committed. A4 c1 was not re-viewed (superseded by c2; founder-stated status: ambiguous pizza/fire-oven look, internal reference only). Figma generation calls remain 10/12 used, 2 held. Links reportedly expire 2026-10-18; the founder chose not to spend more time on recovery.
| Code | Provisional outcome (from the lossy copy; final classification not possible without the exact file) | Key limitation |
|---|---|---|
| A1 exterior | ACCEPTED WITH LIMITATIONS | two full tanks and a partial third imply a tank count (G-6); concept of a building that does not exist |
| A2 interior | ACCEPTED WITH LIMITATIONS for bar/tile/mood; REWORK for kitchen and tanks | copper pizza-style oven (not a tandoor); two tanks visible; repeated clasped-hands pose |
| A3 bar | ACCEPTED WITH LIMITATIONS (mood, materials); REWORK for tap system | nine handles float over an arch with no shanks; tanks visible; glass is not Glass V2 |
| A4 c1 | SUPERSEDED / INTERNAL REFERENCE ONLY | pizza-oven look (not re-viewed) |
| A4 c2 | ACCEPTED WITH LIMITATIONS (preferred kitchen concept) | tandoor plus comal reads right; hood, flue and suppression are NOT engineering or code validation |
| A5 patio | ACCEPTED WITH LIMITATIONS (internal only) | children at a table with beer: responsible-alcohol and public-use concern; soft hands |
| A6 entrance | ACCEPTED FOR INTERNAL CONCEPT USE (strongest) | blank sign, no tanks; concept only |
| B1 hero | ACCEPTED WITH LIMITATIONS as chicken/garnish reference; chips REWORK | thin generic chips (GENERIC_NACHOS risk); Composed-like layout; not evidence |
| B1 truth | ACCEPTED WITH LIMITATIONS | better Integrated-style layout; chips still thin and flatbread-like; not evidence |
| C6 beer family | ACCEPTED WITH LIMITATIONS (colour/style reference only) | not Glass V2; low shelf-like collar bulge; near-brimful fills; not brewed |
No image is called final photography, evidence or legally cleared (PROVISIONAL-LOCAL-ONLY). Design warning (not evidence): AI generators repeatedly render the Mexican component as generic tortilla chips rather than a thick, irregular, blistered nixtamal totopo; the next useful Chicken 65 image must come from a real cook.

**Status:** `[ANALYSIS]`. **Full-resolution QA has NOT been done for any candidate.** The only files available in the sandbox are 256 px previews, and the sandbox proxy blocks `www.figma.com`, so the 7-day originals cannot be fetched here (`curl` returns 403 on CONNECT). Decisions below are therefore **PENDING FULL RESOLUTION** unless a candidate is already superseded. Previews can show composition and gross plausibility only; they cannot clear people, text/logo, food-texture or equipment gates. **Nothing is accepted.** All rights are PROVISIONAL-LOCAL-ONLY (`docs/ai/FIGMA-AI-TERMS-REVIEW.md`).

**To resume:** download each PNG from the URL in `GENERATION-LOG.md` into `visuals/archive/candidates/` named `<CODE>-<name>-c<N>.png`, run `python3 tools/review_candidates.py`, then complete the human gates in `IMAGE-QA.md` and record ACCEPT / ACCEPT WITH EDIT / REGENERATE / REJECT here.

| Code | Candidate | Preview observations | Suspected defects to check at full-res | Decision | Rights |
|---|---|---|---|---|---|
| A1 | exterior blue hour, c1 | covered patio, string lights, timber arcade, glass storefront, bicycles, diners; no visible tanks; no readable text at 256 px | text/sign, faces, bicycle geometry, whether the building matches the canonical limestone/glass/screens, sign blankness | PENDING FULL-RES | PROVISIONAL |
| A2 | main interior, c1 | bone/marigold tile bar front, terrazzo, partial tanks through glass, open kitchen with oven glow, long table | **several guests face the camera** (reject/regenerate if confirmed); kitchen oven reads closer to a pizza oven than a tandoor; tank implication | PENDING FULL-RES (likely REGENERATE if confirmed) | PROVISIONAL |
| A3 | bar, c1 | pecan bar, tile front, tap tower with plain handles, tall glasses on shelves, bartender pouring, guests talking to each other, tanks as blurred hint | tap tower geometry, glass shapes, any readable beer labels or text, hands | PENDING FULL-RES | PROVISIONAL |
| A4 | fire kitchen, c1 | glowing oven with skewers, cook, comal | oven reads like a pizza oven | **SUPERSEDED by c2 (REGENERATE done)** | PROVISIONAL |
| A4 | fire kitchen, c2 | cylindrical steel-bodied tandoor, cook lowering a vertical skewer, comal station, hood | flame/embers safety, hands and skewer, equipment realism, text | PENDING FULL-RES | PROVISIONAL |
| A5 | evening patio, c1 | fans, string lights, communal tables, live oak, bicycles, mixed diners | a few diners look at the camera, faces, children, hands | PENDING FULL-RES | PROVISIONAL |
| A6 | entrance, c1 | limestone, cedar canopy, glowing glass door, blank monument sign, screen, bicycles, two guests from behind, patio lights | sign must be truly blank, door geometry, text | PENDING FULL-RES | PROVISIONAL |
| B1 | Chicken 65 Totopos hero, c1 | chicken among thick irregular chips, curry leaves, sliced green chile, lime, raita, beer behind | identical/duplicated chicken pieces, chip thickness and masa texture, coating realism, lime, glass geometry | PENDING FULL-RES | PROVISIONAL |
| B1 | Chicken 65 Totopos truth, c1 | top-down plate, chicken distributed through open chip layer, raita pool, lime | repeated pieces, plate geometry, curry leaf realism | PENDING FULL-RES | PROVISIONAL |
| C6 | gate beers family, c1 | three distinct beers (hazy gold with thick white head, clear gold, clear copper) | **no raised collar ring visible: glass family concept unproven**; liquid physics, foam, background people | PENDING FULL-RES (glass concept likely needs regeneration) | PROVISIONAL |

**Three-yes for Chicken 65 Totopos (preview level only, UNVERIFIED):** INDIA plausible, MEXICO plausible, ONE DISH plausible. Not qualifying for integration until full-res and the kitchen test.
