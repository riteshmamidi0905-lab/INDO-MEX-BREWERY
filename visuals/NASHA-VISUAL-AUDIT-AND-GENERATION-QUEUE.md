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

---
## Sprint 7 audit of every existing project image (KEEP / REWORK / REPLACE / ARCHIVE)
**Status:** `[ANALYSIS]`. Judged on quality, brand fit, rights, accuracy, consistency and usefulness, **not** because an image is AI-assisted. **Rights for all of them are unverified** (founder-supplied from external tools, terms never checked), so any use is `PROVISIONAL-LOCAL-ONLY` until the founder verifies tool terms or replaces them. None is on a public site (the prototype is local and `noindex`).

| File | Source | Verdict | Reason | Website use |
|---|---|---|---|---|
| `ARC-02-A.webp` | Founder, external generator | **KEEP** (hero) | Best night exterior; hall glowing, patio alive, plausible architecture. Review hard fail: 8 tanks vs six locked, and brewery scale is undecided (G-6) | `NV-HERO-01` with a scripted temporary-wordmark overlay on the blank sign, and crops `NV-SPACE-ENTRANCE`, `NV-SPACE-PATIO` |
| `ARC-01-D.png` | Founder (ARC-01-C) + Claude Code scripted post-edit | **KEEP** | Founder-approved canonical day exterior (D-42 waiver) | `NV-SPACE-EXT-DAY` |
| `BRW-01-R1-V1.webp` | Founder, external generator | **REWORK** | Strong brewhouse look; hard fails: orange wash, glossy floor, straight row; and its scale must not be read as final | `NV-BREWERY-HALL`, provisional |
| `ARC-01-E-external-crop-attempt1.webp` | Founder, external generator | **KEEP** (secondary) | Rejected as an ARC-01 drop-in, but an excellent through-glass brewery view | `NV-BREWERY-GLASS` |
| `ARC-02-C-attempt1-fullframe.webp` | Founder, external generator | **ARCHIVE** | Seven tanks, orange wash, sunset sky in night glass | none |
| `ARC-02-B.png` | Claude Code scripted composite | **ARCHIVE** | Founder-rejected (D-45); day-lit hall in night glass | none |
| `ARC-01-A.webp`, `ARC-01-B.webp` | Founder, external generator | **ARCHIVE** | Superseded candidates (hard fails: screens, ~8 tanks) | none |
| `ARC-01-C.webp` | Founder, external generator | **ARCHIVE** | Parent of ARC-01-D; superseded | none |
| `ARC-01-E-attempt1-composite-DIAGNOSTIC.png` | Claude Code diagnostic | **ARCHIVE** | A diagnostic, not a candidate | none |
| `*-inputs/` masks, crops, blockouts (16 files) | Working files | **ARCHIVE** | Inputs for earlier edits | none |
| `GLS-inputs/GLS-01*, GLS-02*` profile guides (4 files) | Claude Code drawn guides | **KEEP** (as generation inputs) | Needed for the collar glass (GLS-01, GLS-02) | none (inputs only) |

**Counts (10 candidate images + 16 working inputs + 4 glass guides):** KEEP **2** images + 4 glass guides (3 KEEP image entries incl. the secondary `ARC-01-E` crop = **3** KEEP images in total); REWORK **1**; REPLACE **0** (replacement images are planned, not yet made); ARCHIVE **6** images (ARC-02-C, ARC-02-B, ARC-01-A, ARC-01-B, ARC-01-C, ARC-01-E diagnostic) + 16 working inputs. 

**Gaps (specific):** a purpose-made blue-hour hero with a proper fascia sign; main interior; bar; fire and open kitchen; patio at night; dining hall; every dish and beer as a **photoreal concept visualization** (none exists); glassware GLS-01 and GLS-02 views; pairing compositions; menu and flight mock-ups; pop-up; people. See `visuals/nasha-v3/PROMPT-PACK.md`. Until they exist, drawn **concept illustrations** stand in, and food and beer drawings follow `NASHA-FOOD-BEER-REFERENCE-LIBRARY.md`.
