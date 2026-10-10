# ARC-02 Review Sheet (to complete after external generation)

**Status:** ARC-02 NOT GENERATED — PROMPT AUDITED, READY (unblocked by D-42). No ARC-02 image exists; do not score anything until one does.
**Reference:** `visuals/generated/ARC-01-D.png` (canonical, founder waiver 89/100). **Prompt:** `generation-batch-01/ARC-02.md`. **Method:** ARC-01-D as the init/reference image, moderate relight strength; generate 4 variants and compare before choosing.

## 0. Provenance to record
Tool/model; init image and strength; seed if exposed; variant letter; whether masked/global; date. Founder approval stays NO until stated.

## 1. Preservation gate (any FAIL = reject that variant)
| Check | Method | Result |
|---|---|---|
| Same camera/crop/lens family (oblique 35-40 degree view, hall left third, entrance centre-left, arcade right, oak branch upper left, pickup bottom-left, SUV bottom-right) | Flicker/overlay against ARC-01-D | |
| Structure preserved | `python3 visuals/tools/structure_check.py visuals/generated/ARC-01-D.png <ARC-02>`; **calibration:** D vs D 1.00; D vs C 1.00; D vs E-attempt-1 composite 0.95 (hall only changed); D vs B 0.73 (same design, visibly different camera/massing); D vs A 0.59. **Guide:** recall >= 0.80 pass; 0.65-0.80 inspect by eye; < 0.65 reject. Night lighting lowers scores a little, so the eye decides | |
| Exactly six fermenters, same arrangement; graphite cones; six narrow deep-marigold sleeves | Count twice at 2x | |
| Exactly two copper-clad vessels with hood and stack; no extra copper | Visual | |
| Dark-bronze mullions; plain perforated screens (flat, dark, no glow, no medallion) | Visual | |
| Entrance recess, restaurant block with two stacks, concrete-and-cedar arcade, court, rill, tables, oaks, landscaping unchanged | Visual | |
| No Game Hall, Adventure Court, Outlet, history exhibits, new buildings | Visual | |
| No string lights, neon, coloured lighting, festival lighting, flares, starbursts | Visual | |
| No logo, readable text, terracotta/brass dominance, palms/agave | Visual | |

## 2. Night-specific quality
| Item | Pass? |
|---|---|
| Deep indigo sky with faint west afterglow (not black, not sunset-orange) | |
| Tank Hall is the brightest large feature; tanks softly uplit; sleeves restrained deep orange | |
| Glass reads as glass: mostly transparent, faint plausible reflections of sky/oaks | |
| Warm 2200-2400K shielded light only; arcade washers and soffit downlights; entrance soffit lit | |
| Screens dark and industrial; only tiny pinpoints of light through holes | |
| Rill reflection gentle; oaks softly uplit; restaurant and kitchen windows warm; no open flames | |
| People: ~20-30, mixed, candid, relaxed, not crowded; two walkers at the entrance as in D | |
| Photographic realism: long-exposure feel, natural grain, natural dynamic range, no HDR/haze/CGI sheen | |

## 3. Rubric (same eight categories as ARC-01; night adaptations in brackets)
| Criterion | Max | Score |
|---|---|---|
| Architectural continuity with ARC-01-D | 20 | |
| Tank Cloister [brightest feature, six tanks, copper deck] | 20 | |
| Originality | 15 | |
| Austin / climate plausibility [evening atmosphere] | 10 | |
| Material discipline | 10 | |
| Hospitality appeal [alive, calm, "I need to go there tonight"] | 10 | |
| Photorealism | 10 | |
| Cultural restraint | 5 | |
| **Total** | 100 | |
**Hard fails:** geometry drift or different camera; wrong fermenter count; Tank Hall not the brightest/hidden; glowing or medallion screens; string/festival/neon/colour lighting or starburst flares; fake branding; expansion elements; terracotta/brass dominance; obviously CGI; nightclub/festival scene.

## 4. Decision
PROVISIONAL WINNER — AWAITING FOUNDER APPROVAL only if every gate passes, total >= 90, and no hard fail. Otherwise CANDIDATE — REFINEMENT REQUIRED. Founder approval is never automatic. (No iteration cap has been set for ARC-02; avoid the ARC-01 pattern of endless regeneration: prefer targeted fixes and ask the founder before waiving.)
