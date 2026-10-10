# ARC-01-D Review

> **FINAL STATUS (D-42, 2026-10-10): APPROVED — CANONICAL DAY EXTERIOR — FOUNDER WAIVER 89/100. Founder approval: YES.** Review below is the historical record (written when the status was CANDIDATE). ARC-01 iteration is finished.

## Provenance (read this first)
- **File:** `visuals/generated/ARC-01-D.png`, **2000x1128**, lossless PNG.
- **How it was made:** **not** by an image generator. No image-generation capability exists in this environment, so I performed the five requested refinements as a **documented post-production edit of the ARC-01-C pixels** with a script (`visuals/tools/postedit_arc01d.py`, OpenCV/Pillow). Tool for the log: *Claude Code post-production script on ARC-01-C (not a generative model)*. If you prefer a true generator edit, the prompt in `generation-batch-01/ARC-01-D.md` is still valid.
- **Status:** CANDIDATE — REFINEMENT REQUIRED (89/100, no hard fail; 1 point under the gate). **Founder approval: NO.**

## What was done, and what the pixels show
| # | Requested refinement | Method | Result (checked on 3x crops, before/after) |
|---|---|---|---|
| 1 | Cones to matte charcoal | Soft colour-model recolour of cone pixels (dull brown-grey cluster) to neutral graphite (~RAL 7016-like, luminance-preserving) inside cone zones; gold legs, pipes and background excluded | **PASS.** All six cones now read matte graphite, clearly darker than the polished shells, not black voids. Two earlier attempts (hard polygon fill, flood-fill) left artefacts and were discarded. Slight cool cast on the two far east cones |
| 2 | Six uniform narrow deep-marigold bands | Per-column detection of each band, narrowed to ~10% of the tank's visible diameter (≈6 in on a 5-ft tank), gap filled by inpainting, recoloured to #E8870E with preserved shading | **PASS.** Nearest tank's band reduced from ~14 px to ~8 px; all bands now proportionate and consistently deep orange. No new orange added |
| 3 | Remove the ambiguous small vessel | Strip cloned from clean neighbouring background and feather-blended | **PASS.** The small copper-gold cylinder beside the west stair is gone; stair and pipework remain. Both large copper vessels, hood and stack untouched |
| 4 | Dark-bronze mullions | Dark neutral frame pixels shifted from ~(31,24,19) to ~(45,30,21) | **PASS (subtle, as asked).** Frames read very dark warm bronze, not black, not shiny |
| 5 | Equipment realism | Mild feathered unsharp mask inside the glass | **PARTIAL.** Slightly crisper valves and rails; the source resolution and AI softness limit what sharpening can do |
Preservation: only the hall glass was changed. Outside the hall box the maximum pixel difference from ARC-01-C is 8/765 (feather bleed), i.e. effectively identical. Camera, crop, massing, entrance, canopy, screens, court, people, vehicles, sky and light are untouched.

## Verification of constraints
- **Fermenters:** still exactly six in the same positions (nothing added, removed or moved). Two copper vessels on the deck unchanged.
- **No** new terracotta, brass, ornament, logo, text, neon or string lights.

## Scorecard
| Criterion | Max | Score | Note |
|---|---|---|---|
| Architectural continuity | 20 | 19 | Identical to ARC-01-C; bronze mullions fixed; east flank still partly solid cladding |
| Tank Cloister | 20 | 18 | Six tanks, horseshoe, copper deck, graphite cones, uniform bands; floor drains/hoses not added; equipment still soft |
| Originality | 15 | 12 | Unchanged |
| Austin / climate plausibility | 10 | 9 | Unchanged |
| Material discipline | 10 | 10 | Copper only on vessels; frames now bronze |
| Hospitality appeal | 10 | 9 | Unchanged |
| Photorealism | 10 | 7 | Still AI-smooth in the hall interior and far court; a post-edit cannot add real resolution |
| Cultural restraint | 5 | 5 | |
| **TOTAL** | **100** | **89** | **1 point below the 90 gate** |

## Hard-fail check: NO
Correct count; Tank Hall dominant; horseshoe present; screens plain; no ornament; no fake branding; reads as photography; plausibly functional.

## Honest recommendation
ARC-01-D is the best exterior so far and every specific defect from the ARC-01-C review is fixed except resolution. The remaining deficit is **photorealism**, not design: it comes from the generator's resolution and style, and no further targeted edit will cure it. **Do not keep iterating on ARC-01.** Options for the founder:
1. **Accept ARC-01-D as the canonical day-exterior reference** with a documented waiver of the 1-point gap (design is locked; use it as the reference for ARC-02/BRW-01 prompts), then rely on professional rendering/photography later for final quality; or
2. Request one last clean generator pass using ARC-01-D as the input if the founder wants the extra point.
I have **not** promoted it: status stays CANDIDATE — REFINEMENT REQUIRED until you decide.

## Subjective tests
- **Destination test: YES.** The glowing glass hall with a visible copper brewhouse and banded graphite-coned tanks is a strong reason to pull in, and the shaded court promises a good stay.
- **Most memorable thing:** the Tank Hall.
