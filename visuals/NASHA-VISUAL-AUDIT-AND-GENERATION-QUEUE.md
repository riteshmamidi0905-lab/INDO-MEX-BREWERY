# NASHA: Visual Audit and Generation Queue

**Status:** `[ANALYSIS]` of existing visual assets, their fitness for the NASHA website, and a prioritised queue. **Nothing was generated this sprint.** Image rights are unresolved (`ip/IP-OWNERSHIP-FRAMEWORK.md`), so no raster image is published on the website.

## 1. What exists (see `visuals/ASSET-MANIFEST.md`, `visuals/generated/LOG.md`)
Earlier sprints produced AI-assisted renders and guides for the hall, brewhouse, tanks and glasswork. Their provenance and tool terms are logged but **commercial-use rights and consistency are unresolved**, and the night-hall render problem is unsolved. They are **concept art for the founder**, not publishable brand assets, and are labelled so.

## 2. Fitness for the website
| Use | Existing asset suitable? | Decision |
|---|---|---|
| Hero | No: rights unresolved, night hall unsolved | Original vector illustration written for the site (`website/build.py`, hero SVG). Rights-clean, tiny (about 3 KB), accessible, reduced-motion safe. |
| Place / zones | Partly | Vector zone diagram on the home page. |
| Beer glasses | Partly | Two simple vector glass icons. |
| Food | **None.** No food photography exists because no dish has been cooked. | Text-only dish cards. **No stock or AI food images**, which would misrepresent. |
| People, brewers, guests | None | None shown. Never fabricate guests or testimonials. |
| Logo | None designed | Typographic wordmark in Instrument Serif, tracked capitals. Explicitly a placeholder. |

## 3. Gaps, in order of importance
1. A **real logo/wordmark** by a designer, under a written assignment (after name clearance).
2. **Real food photography** of dishes after kitchen tests (T1 cooking), shot by a photographer under a written assignment.
3. **Hall and tank imagery** that survives scrutiny: an architect/illustrator commission or properly licensed renders, not an unrepeatable AI run.
4. Real portraits/process photography once a brewer and kitchen exist.
5. A hand-drawn spot-illustration set for the Crossing (spice, grain, fire), if budget allows.

## 4. Generation queue (do not run until the founder approves the tool terms)
| Priority | Asset | Purpose | Gate |
|---|---|---|---|
| P1 | Hall at dusk, one consistent view | Replace vector hero only if rights are clear | Verify tool commercial terms; keep prompts, seeds, dates in the log; label as AI-assisted |
| P2 | Four glass/beer studio renders | Beer page | Same, plus must match the actual glassware once chosen |
| P3 | Texture/pattern for Crossing (non-literal, stereotype-free) | Section dividers | Cultural advisor review |
| Never | Photoreal "food" of dishes not yet cooked; fake people; fake press | | Misrepresentation |

## 5. Rules adopted for the site
Every file on the site is registered in `ip/website-asset-rights-register.csv`, regenerated from `website/dist/` by the build and enforced by `tools/validate_site.py`. AI-assisted authorship is declared in the register rather than hidden.
