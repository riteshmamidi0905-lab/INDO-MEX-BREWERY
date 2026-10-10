# Generation Log

No images generated yet. For each output record every column. Concept visual, not an operating business (record in caption/metadata, not in the image).

| Asset ID | Tool | Model | Date | Prompt (file@version) | Reference image | Seed | Version | Status | Founder approval | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| ARC-01-A | OpenAI image generation (per founder) | not recorded by founder | 2026-10-10 | generation-batch-01/ARC-01.md (v1) | none | not exposed | v1 | **CANDIDATE — REFINEMENT REQUIRED** | **NO** | File `ARC-01-A.webp` (2000x1130) supplied by founder; review in `ARC-01-A-REVIEW.md`; score 73/100; hard fail (screens) |
| ARC-01-B | External generator (per founder; tool/model not recorded) | not recorded | 2026-10-10 | generation-batch-01/ARC-01-B.md | ARC-01-A (optional) | not exposed | v1 | **CANDIDATE — REFINEMENT REQUIRED** | **NO** | File `ARC-01-B.webp` (2000x1125); review in `ARC-01-B-REVIEW.md`; 78/100; hard fail: tank count (~8) |
| ARC-01-C | OpenAI image generation (per founder) | not recorded | 2026-10-10 | generation-batch-01/ARC-01-C.md | ARC-01-B | not exposed | v1 | **CANDIDATE — REFINEMENT REQUIRED (near-pass)** | **NO** | `ARC-01-C.webp` 2000x1128; review `ARC-01-C-REVIEW.md`; **86/100; no hard fail**; six tanks verified; cones partial, one wide band, one ambiguous vessel |
| ARC-01-D | **Claude Code post-production script (not a generative model)**; script `visuals/tools/postedit_arc01d.py` | n/a | 2026-10-10 | edit spec = `generation-batch-01/ARC-01-D.md` (executed as a pixel edit, not a prompt) | ARC-01-C | n/a | v1 | **CANDIDATE — REFINEMENT REQUIRED (89/100, no hard fail)** | **NO** | `ARC-01-D.png` 2000x1128; review `ARC-01-D-REVIEW.md`; all five refinements applied; remaining gap = photorealism (source resolution) |
| ARC-01-E | | | | generation-batch-01/ARC-01-E.md (final realism pass; masked hall-glass edit recommended) | ARC-01-D (+ crop and masks in `ARC-01-E-inputs/`) | | | **NOT GENERATED as a full frame — FINAL REALISM PASS PREPARED; attempt 1 (crop) REJECTED as drift, see row below** | NO | Review sheet `ARC-01-E-REVIEW-SHEET.md`; helper `visuals/tools/arc01e_tools.py`; stopping rule D-40 (no ARC-01-F) |
| ARC-01-E attempt 1 (crop) | External image generator (tool/model not stated by founder) | not stated | 2026-10-10 | generation-batch-01/ARC-01-E.md | ARC-01-D crop + mask | not exposed | attempt-1 | **REJECTED as drop-in: perspective/position drift (frontal view vs oblique), doubled mullions in composite** | NO | `ARC-01-E-external-crop-attempt1.webp` (2000x965); diagnostic `ARC-01-E-attempt1-composite-DIAGNOSTIC.png`; review `ARC-01-E-attempt1-REVIEW.md`; hall realism excellent; candidate BRW-01 reference only |
| ARC-02 | | | | generation-batch-01/ARC-02.md | approved ARC-01 | | | NOT GENERATED | | |
| BRW-01 | | | | generation-batch-01/BRW-01.md | approved ARC-01, ARC-02 | | | NOT GENERATED | | |
| GLS-01 | | | | generation-batch-01/GLS-01.md | none | | | NOT GENERATED | | |
| GLS-02 | | | | generation-batch-01/GLS-02.md | approved GLS-01 | | | NOT GENERATED | | |

## Attempt record
| Date | Asset | Outcome |
|---|---|---|
| 2026-10-10 | ARC-01 (A-D) | **Not generated.** This cloud session has no image-generation capability (no image tool or API; only ImageMagick, which cannot produce a photoreal render). No candidates exist; none were fabricated. Prompt `generation-batch-01/ARC-01.md` is unchanged and ready for an external generator. |
