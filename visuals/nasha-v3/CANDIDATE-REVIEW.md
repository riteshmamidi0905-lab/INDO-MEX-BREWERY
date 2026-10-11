# NASHA Candidate Review (Sprint 10)

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
