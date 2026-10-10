# INDO MEX BREWERY

Permanent source of truth for the project. Founder: Ritesh Mamidi. Target market: Austin, Texas.
Working name only. See `phase-one/09-brand-identity.md` for the naming evaluation.

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

## Status (2026-10-10)
Phase One written; Phase 1.5 (research deepening + brand world) complete as a draft awaiting founder review. **No images generated yet** (external tool required); 57 prompts are ready; the first five (Visual Lock batch) are finalized in `visuals/generation-batch-01/`.
**ARC-01-D is the APPROVED canonical day exterior (founder waiver 89/100, D-42).** ARC-02-A (best night exterior) and ARC-02-B rejected; **ARC-02-C package ready (D-45), awaiting one external generation.** Website: not started, by instruction.
