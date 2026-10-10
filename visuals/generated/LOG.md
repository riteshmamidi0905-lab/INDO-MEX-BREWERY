# Generation Log

No images generated yet. For each output record every column. Concept visual, not an operating business (record in caption/metadata, not in the image).

| Asset ID | Tool | Model | Date | Prompt (file@version) | Reference image | Seed | Version | Status | Founder approval | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| ARC-01-A | OpenAI image generation (per founder) | not recorded by founder | 2026-10-10 | generation-batch-01/ARC-01.md (v1) | none | not exposed | v1 | **CANDIDATE — REFINEMENT REQUIRED** | **NO** | File `ARC-01-A.webp` (2000x1130) supplied by founder; review in `ARC-01-A-REVIEW.md`; score 73/100; hard fail (screens) |
| ARC-01-B | External generator (per founder; tool/model not recorded) | not recorded | 2026-10-10 | generation-batch-01/ARC-01-B.md | ARC-01-A (optional) | not exposed | v1 | **CANDIDATE — REFINEMENT REQUIRED** | **NO** | File `ARC-01-B.webp` (2000x1125); review in `ARC-01-B-REVIEW.md`; 78/100; hard fail: tank count (~8) |
| ARC-01-C | OpenAI image generation (per founder) | not recorded | 2026-10-10 | generation-batch-01/ARC-01-C.md | ARC-01-B | not exposed | v1 | **CANDIDATE — REFINEMENT REQUIRED (near-pass)** | **NO** | `ARC-01-C.webp` 2000x1128; review `ARC-01-C-REVIEW.md`; **86/100; no hard fail**; six tanks verified; cones partial, one wide band, one ambiguous vessel |
| ARC-01-D | **Claude Code post-production script (not a generative model)**; script `visuals/tools/postedit_arc01d.py` | n/a | 2026-10-10 | edit spec = `generation-batch-01/ARC-01-D.md` (executed as a pixel edit, not a prompt) | ARC-01-C | n/a | v1 | **APPROVED — CANONICAL DAY EXTERIOR — FOUNDER WAIVER 89/100 (D-42)** | **YES** | `ARC-01-D.png` 2000x1128; review `ARC-01-D-REVIEW.md`; all five refinements applied; remaining gap = photorealism (source resolution) |
| ARC-01-E | | | | generation-batch-01/ARC-01-E.md (final realism pass; masked hall-glass edit recommended) | ARC-01-D (+ crop and masks in `ARC-01-E-inputs/`) | | | **CLOSED (D-42): no further attempts. Attempt 1 REJECTED FOR ARC-01** | NO | Review sheet `ARC-01-E-REVIEW-SHEET.md`; helper `visuals/tools/arc01e_tools.py`; stopping rule D-40 (no ARC-01-F) |
| ARC-01-E attempt 1 (crop) | External image generator (tool/model not stated by founder) | not stated | 2026-10-10 | generation-batch-01/ARC-01-E.md | ARC-01-D crop + mask | not exposed | attempt-1 | **REJECTED FOR ARC-01 / RETAINED AS BRW-01 REALISM REFERENCE** | NO | `ARC-01-E-external-crop-attempt1.webp` (2000x965); diagnostic `ARC-01-E-attempt1-composite-DIAGNOSTIC.png`; review `ARC-01-E-attempt1-REVIEW.md`; hall realism excellent; candidate BRW-01 reference only |
| ARC-02 | | | | generation-batch-01/ARC-02.md (audited and corrected, D-42) | **ARC-01-D (canonical)** as init/reference | | | **IN PROGRESS: ARC-02-A received (70/100, hard fail); ARC-02-B correction prepared** | NO | Review sheet `ARC-02-REVIEW-SHEET.md`; drift check `visuals/tools/structure_check.py` |
| ARC-02-A | External image generator (tool/model not stated) | not stated | 2026-10-10 | generation-batch-01/ARC-02.md | ARC-01-D (per instructions) | not exposed | A | **CANDIDATE — REFINEMENT REQUIRED (hard fail: 8 tanks, copper vessels missing)** | NO | `ARC-02-A.webp` 2000x1114; `ARC-02-A-REVIEW.md`; 70/100; structure recall 0.69; exterior and night atmosphere strong |
| ARC-02-B | | | | generation-batch-01/ARC-02-B.md (hall-glass-only correction) | ARC-02-A crop + ARC-01-D hall crop | | | NOT GENERATED | NO | Inputs in `ARC-02-B-inputs/`; helper `visuals/tools/arc02_tools.py` |
| BRW-01 | | | | generation-batch-01/BRW-01.md | approved ARC-01, ARC-02 | | | NOT GENERATED | | |
| GLS-01 | | | | generation-batch-01/GLS-01.md | none | | | NOT GENERATED | | |
| GLS-02 | | | | generation-batch-01/GLS-02.md | approved GLS-01 | | | NOT GENERATED | | |

## Attempt record
| Date | Asset | Outcome |
|---|---|---|
| 2026-10-10 | ARC-01 (A-D) | **Not generated.** This cloud session has no image-generation capability (no image tool or API; only ImageMagick, which cannot produce a photoreal render). No candidates exist; none were fabricated. Prompt `generation-batch-01/ARC-01.md` is unchanged and ready for an external generator. |
