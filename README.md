# INDO MEX BREWERY

Permanent source of truth for the project. Founder: Ritesh Mamidi. Target market: Austin, Texas.
**Brand name: NASHA** (founder-selected, 2026-10-11; `SELECTED_BY_FOUNDER — LEGAL CLEARANCE PENDING`, D-62). This is not trademark clearance. "INDO MEX BREWERY" remains the repository and working name in earlier history; see `brand/NASHA-BRAND-STRATEGY.md` and `phase-one/09-brand-identity.md` (history).

## Rules for this repo
1. Nothing is deleted. Rejected ideas move to `docs/decisions/REJECTED.md` with the reason.
2. Every factual claim carries an evidence tag (below) and, if verified, a source ID from `research/SOURCES.md`.
3. Specifications for beer and food are **development targets** until pilot brewing and kitchen testing validate them.
4. Images are **concept visuals**. They never depict an operating business, real customers or real testimonials.
5. No website code until the founder approves the Phase One universe.

## Evidence tags
| Tag | Meaning |
|---|---|
| `[VERIFIED S-xx]` | Confirmed against a source listed in `research/SOURCES.md` |
| `[UNCITED]` | Widely documented background knowledge, not yet tied to a citation. Needs a source before external use |
| `[CONCEPT]` | Creative proposal, not a claim of fact |
| `[TEST]` | Requires pilot brewing, kitchen trials or sensory testing |
| `[PRO]` | Requires attorney, architect, engineer, accountant, licensed brewer or TABC confirmation |

## Layout
```
README.md
docs/decisions/        DECISIONS.md, REJECTED.md, OPEN-QUESTIONS.md
research/              SOURCES.md, RESEARCH-BACKLOG.md
phase-one/             the Founding Vision, split into numbered chapters
visuals/prompts/       production prompts (Phase One style bible + first-twelve are SUPERSEDED — RETAINED FOR HISTORY); authority is visuals/VISUAL-DNA.md
visuals/generated/     generated concept images (none yet)
brand/ beer/ food/ architecture/ business/ website/   future working folders
```

## Start here
**Current plan and status: `PROJECT-ROADMAP.md`** (Phase 2 active since D-49).

Phase 1.5 (current): `docs/decisions/DECISIONS.md` → `brand/BRAND-WORLDS.md` → `visuals/VISUAL-DNA.md` → `visuals/ASSET-MANIFEST.md`.
Phase One baseline (kept; Phase 1.5 governs conflicts): `phase-one/00-FOUNDING-VISION-PHASE-ONE.md`.

### Phase 1.5 map
| Area | Files |
|---|---|
| Research | `research/INDIAN-CULINARY-BENCHMARKS.md`, `MEXICAN-CULINARY-BENCHMARKS.md`, `INDIAN-BEER-LANDSCAPE.md`, `MEXICAN-BEER-LANDSCAPE.md`, `WHEAT-BEER-BENCHMARKS.md`, `AUSTIN-COMPETITIVE-LANDSCAPE.md`, `PAIRING-MATRIX-V2.md`, `SOURCES.md`, `RESEARCH-BACKLOG.md`, `RESEARCH-QUALITY-AUDIT.md` |
| Beer | `beer/HEFEWEIZEN-BENCHMARK.md`, `PORTFOLIO-V2.md`, `GLASSWARE-V2.md` |
| Food | `food/OPENING-MENU-V2.md`, `SAUCE-SYSTEM.md` |
| Brand | `brand/NAMING-UNIVERSE-V2.md`, `PARENT-BRAND-CANDIDATES.md`, `BRAND-WORLDS.md` |
| Architecture | `architecture/COURT-BREWHOUSE-V2.md`, `OPERATIONAL-FLOW.md`, `CULTURAL-DESIGN-RESEARCH.md` |
| Business | `business/LICENSING-AND-FEASIBILITY-NOTES.md` |
| Visuals | `visuals/VISUAL-DNA.md`, `ASSET-MANIFEST.md`, `prompts/V2-*.md`, `tools/build_prompts.py` |
| Decisions | `docs/decisions/DECISIONS.md`, `REJECTED.md`, `OPEN-QUESTIONS.md`, `CORRECTIONS.md` |

## Destination expansion (current, for study)
`architecture/FAMILY-DESTINATION-EXPANSION.md`, `FAMILY-ZONING-OPTIONS.md`, `EXPANDED-GUEST-JOURNEY.md`; `interior/` (history story systems); `research/HISTORICAL-CLAIMS-AUDIT.md`; `business/FAMILY-EXPERIENCE-OPERATIONS.md`; prompts `visuals/prompts/{FAM,GAME,RTL,HIS,MAS,JNY}-*.md` (blocked) and `visuals/EXPANSION-MANIFEST.md`.

## Visual Lock (current)
`visuals/VISUAL-DNA.md` (canonical rules) → `visuals/LOCKED-SCENE-DNA.md` (geometry) → `visuals/generation-batch-01/` (5 prompts to generate first; do not generate the other 52 until reviewed).

## Status (2026-10-11, Sprint 5: staged path, MVP, IP; readiness now design 41% / evidence 4% of 95)
Sprint 5 added `validation/MOBILE-MVP-STRATEGY.md` and `TRACTION-METRICS.md` (+ empty event log), `investor/CAPITAL-LADDER-AND-INVESTOR-STRATEGY.md`, `ip/IP-OWNERSHIP-FRAMEWORK.md` with asset registers, `marketing/…FOUNDATION.md`, `docs/decisions/ATTORNEY-QUESTIONS.md`, ledger entries V-23..V-34, and records NASHA as a founder-proposed candidate (D-59). The staged-company path is a hypothesis (D-60). Nothing was tested, brewed, sold or contacted.

## Status (2026-10-11, Sprint 4: digital blueprint, Track A)
Start at `concept/INDO-MEX-BREWERY-MASTER-CONCEPT.md` and `docs/readiness/VALIDATION-SCOREBOARD.md`. Sprint 4 added the master concept, brand architecture, guest experience architecture, spatial vision, visual world and briefs, menu storytelling, beer brand experience, business-model map, financial-model architecture (blank 70-variable register), investor story and data-room map, website IA, readiness scoreboard (**design completeness 41%, evidence-backed readiness 5%**) and the brewery-scale decision analysis. **Track A documents add no evidence.** Two-track rule: D-58.

## Status (2026-10-11, Phase 2 Sprint 3)
Sprint 3 added `research/VERIFICATION-LEDGER.md` (evidence tiers; no T0 facts), `docs/decisions/DECISION-GATES.md` (F-1..F-5, G-6..G-12), `research/market-survey/observations.csv` (19 LOW-confidence rows), `brand/TRADEMARK-SCREENING.md` (preliminary web screen, not clearance), `brand/CULTURAL-INTEGRITY-AND-ADVISORS.md`, `architecture/COMPACT-FUNCTIONAL-PROGRAM.md`, `beer/pilot-briefs/00-BREWER-HANDOFF.md`, `food/t1-test-sheets/` upgrades, `tools/validate_repo.py`. Still nothing brewed, cooked, interviewed, quoted or generated.

## Status (Sprint 2, 2026-10-10)
**Dietary policy D-54: no beef, no pork (not claimed halal).** Sprint 2 added `food/MENU-V1.1-TEST-MENU.md`, `food/t1-test-sheets/`, `beer/pilot-briefs/`, `research/market-survey/`, `research/customer-discovery/`, `docs/decisions/DIETARY-AUDIT-D54.md`, `tools/diet_audit.py`. Nothing has been cooked, brewed, surveyed or generated.

## Status (Phase 2 Sprint 1)
Phase 2 v1 shipped: `beer/OPENING-BEER-PROGRAM-V1.md`, `food/MENU-DEVELOPMENT-MATRIX-V1.md`, `experience/GUEST-JOURNEY-V1.md`, `architecture/MASTER-PLAN-PHASE2.md`, `business/AUSTIN-FEASIBILITY-V1.md`, `brand/BRAND-SYSTEM-V0.md`; GLS-01/02 packages prepared; sources S-76..S-118 added (search-extract level, re-verify before external use, D-53).

## Status (earlier, 2026-10-10)
Phase One written; Phase 1.5 (research deepening + brand world) complete as a draft awaiting founder review. **No images generated yet** (external tool required); 57 prompts are ready; the first five (Visual Lock batch) are finalized in `visuals/generation-batch-01/`.
**ARC-01-D is the APPROVED canonical day exterior (founder waiver 89/100, D-42).** **ARC-02 ON HOLD, tool-limited (D-47): no canonical night image; ARC-02-A is a non-canonical night-atmosphere reference; ARC-02-B/C rejected.** Next: BRW-01 (package prepared, not generated). Website: not started, by instruction.

Sprint 6 selected NASHA (D-62) and added `brand/NASHA-BRAND-STRATEGY.md`, `brand/NASHA-IDENTITY-SYSTEM.md`, a working local website prototype (`website/`: `build.py`, `src/`, `data/`, `dist/`, `qa/`, `DESIGN-SYSTEM.md`), `tools/validate_site.py`, `visuals/NASHA-VISUAL-AUDIT-AND-GENERATION-QUEUE.md`, `ip/NASHA-TRADEMARK-ATTORNEY-PACKAGE.md`, `marketing/NASHA-DOMAIN-AND-HANDLE-INVENTORY.md` and `marketing/NASHA-MARKETING-HOOKS.md`. To rebuild: `python3 website/build.py`. Nothing is deployed, owned, cleared or sold.

Sprint 7 (`NASHA` visual world): `visuals/NASHA-VISUAL-DIRECTION-V3.md`, `visuals/NASHA-FOOD-BEER-REFERENCE-LIBRARY.md`, `visuals/NASHA-VISUAL-MANIFEST.csv` (canonical visual manifest), `visuals/nasha-v3/PROMPT-PACK.md`, `brand/NASHA-LOGO-GOVERNANCE.md` and the empty `brand/logo/` vault, a rebuilt eight-page website (Experience and Space added) with an image pipeline. **No logo exists; no photoreal food or beer image exists; AI-made images are provisional and labelled concept visualizations.**

Sprint 8: no image generator was available, so no new images were made (see `visuals/nasha-v3/GENERATION-LOG.md`); the prompt pack and QA gate are ready for external generation; added an asset-stage mechanism, a Building NASHA journey, an interactive beer explorer, edge-trimmed sources, and extended QA and validators.

Sprint 9: built the AI environment (10 specialist agents in `.claude/agents/`, `tools/visual_qa.py`, `brew_calc.py`, `food_costing.py`, Lighthouse and visual-regression QA; record in `docs/ai/NASHA-AI-CAPABILITIES.md`). With the founder-connected Figma tool, 6 image candidates were generated under a capped paid approval; none is accepted or integrated because full-resolution files cannot be downloaded in the sandbox (see `visuals/nasha-v3/GENERATION-LOG.md`).

Sprint 10: the essence line is now "food and beer designed together to draw you in" (D-71). Four more Figma candidates were generated (A3 bar, A6 entrance, A4 tandoor regeneration, gate-beer family), 10 of 12 approved calls used; none is accepted because full-resolution files cannot be downloaded in the sandbox (`visuals/nasha-v3/CANDIDATE-REVIEW.md`, `tools/review_candidates.py` is the resume path). Added Figma terms review (T1), Chicken 65 construction comparison sheet, photography protocol and a concept-vs-real template. Nothing physical was tested.

Sprint 11: candidate originals still unrecovered (founder runs `tools/founder_download_candidates.sh` before 2026-10-18); built the real-cook evidence machinery (`food/t1-test-sheets/10-t1-session-run-of-show.md`, `food/t1-results/`, `tools/t1_record.py`), culinary design memory, glass checklist, beer progression and a regression log. No physical test, no new generation.

Sprint 12: no cook data and no candidate files were supplied, so nothing physical happened. Delivered the cook kit and then stopped documenting: `food/t1-test-sheets/11-chicken-65-totopos-prototype-protocol-FROZEN.md` (frozen decision rule, shopping list, quantities, day card, score sheet, photography sequence), `tools/t1_randomize.py`, the 1-5 recorder with failure gates, and `12-paneer-tikka-taco-session-2-prep.md`. Next input must be physical: the cook results and photos (and the candidate PNGs before 2026-10-18).

Sprint 13: still no physical input. Quantities were audited (1.3 kg trimmed chicken, 24 tortillas; see `food/t1-test-sheets/13-session-1-quantity-audit-shopping-cook-card.md`). Chicken 65 Totopos: NOT PERFORMED.

Sprint 14 (tooling, not evidence): the canonical tool inventory is `docs/tools/NASHA-CAPABILITY-MATRIX.md` (INSTALLED / TESTED / OPERATIONAL are earned separately). New tested tools: `tools/photo_ingest.py`, `recipe_scale.py`, `experiment_stats.py`, `menu_engineering.py`, `glass_model.py` + `render_stl.py` (Blender/OpenSCAD), `nasha_search.py`, `fin_model.py`, `security_check.sh`; 11 new specialist agents (4 tested, `docs/ai/AGENT-TEST-LOG.md`); blank `ops/templates/`. Evidence stays 4/95 and design 43/95. **Founder action still open: download the 10 Figma originals before 2026-10-18 (`tools/founder_download_candidates.sh`).**


Sprint 15 (external intelligence; no score change): connected and used Yelp (49 real Austin listings, `ops/data/`) and Consensus (5 peer-reviewed abstracts, `research/LITERATURE-LEDGER.csv`). Added research ledger rows V-59..V-70, `docs/regulatory/REGULATORY-MATRIX.csv`, `docs/ai/PROVIDER-TERMS-MATRIX.csv`, `research/heritage/HERITAGE-CLAIMS.csv`, `research/EXTERNAL-INTELLIGENCE-S15.md`, glass collar studies (`visuals/glass-studies/`, concept geometry, manufacturability unverified), BeerJSON validation, 4 project skills and tool upgrades. All other external data hosts remain blocked from this sandbox (the allow-list to request is in the research file). Chicken 65 Totopos: NOT PERFORMED. Evidence 4/95 and design 43/95 unchanged.

Sprint 16 (Core 5 x Core 5, no score change): D-75 selected the focused development portfolio (5 foods, 5 house beers; everything else stays in the R&D backlog). Canonical files: `food/CORE5-FOOD-MATRIX.csv`, `beer/CORE5-BEER-MATRIX.csv`, `food/CORE5-PAIRING-MATRIX.csv` (25 PAIRING HYPOTHESES, NOT SENSORY TESTED), `research/CORE5-PRODUCT-SYSTEM.md`, five concept glasses with validated capacities (`visuals/glass-studies/core5/`, MANUFACTURABILITY UNVERIFIED), pilot briefs for all five beers, allergen/costing/menu-engineering structures (all prices blank), `docs/ai/ASSET-PROVENANCE-REPORT.md`, cultural wording corrections on the site. Nothing is cooked or brewed; Chicken 65 Totopos: NOT PERFORMED. Founder items open: Figma originals by 2026-10-18; physical Session 1.
