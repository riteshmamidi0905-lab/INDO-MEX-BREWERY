# ARC-02-C Review Sheet (complete after external generation)

**Status:** ARC-02-C NOT GENERATED — PACKAGE READY (D-45). Score nothing until an image exists. **One attempt only; if it fails, stop and report. No ARC-02-D automatically.**
**Sources:** ARC-02-A (night exterior authority), ARC-01-D (hall geometry authority), ARC-01-E attempt 1 (equipment realism reference only). **Prompt:** `generation-batch-01/ARC-02-C.md`. ARC-02-B is rejected (provenance only).

## 0. Provenance to record
Tool/model; mask-edit vs other; references supplied (#1-#5) and which the tool accepted; variant chosen; seed if exposed; date; any retouching (none allowed). Composite by `visuals/tools/arc02c_tools.py` (re-pastes ARC-02-A mullions). Founder approval stays NO until stated.

## 1. Acceptance gate (any FAIL = ARC-02-C fails)
| # | Gate | Method | Result |
|---|---|---|---|
| 1 | Exactly six fermenters, counted twice | Manual count at 2x, twice, on the composite | |
| 2 | Exactly two copper brewing vessels (plus hood/stack, no other copper) | Visual | |
| 3 | Canonical oblique ARC-01-D arrangement readable (3 left, central deck, one large nearest right + 2 behind) | Overlay on `4-ARC-01-D-layout-ref-registered-2x.png` | |
| 4 | Graphite cones (dark, matte, not silver/orange) | Zoom + sample | |
| 5 | Six narrow deep-marigold sleeves (~#E8870E, ~6 in, not yellow, not glowing) | Zoom + sample | |
| 6 | Hall lighting genuinely matches ARC-02-A night exposure (2200-2400K, no orange wash, no day-photo look) | Side-by-side with A | |
| 7 | No daytime sky or foliage behind the glass | Visual | |
| 8 | No obvious composite boundaries (glass edge, mullion seams, exposure steps) | Zoom on all hall edges | |
| 9 | Original mullions aligned and unduplicated | Overlay on A | |
| 10 | Outside-hall drift effectively zero | `arc02c_tools.py composite` prints changed px outside mask (must be 0) | |
| 11 | Tank Hall is the brightest large feature without clipping | Luminance check + eye | |
| 12 | Rubric >= 90 | Section 3 | |
| 13 | No hard fail | Section 3 | |

## 2. Night-specific and equipment quality
Stainless: warm elongated highlights, darker falloff. Copper: restrained warm reflections. Uplight narrow-beam at tank bases. Rear of hall darker. Contact shadows. Floor warm-grey satin (not glossy). Trench drains: judge only if visible. Deck: stair, 42-inch guardrails, catwalk. Piping: tri-clamps, butterfly valves, pumps, restrained hoses. Legs/foot plates (four per tank). Manways. No star flares, bloom, HDR, haze, neon, string lights, logos, text, people in production.

## 3. Rubric (ARC-02 night adaptation) and hard fails
| Criterion | Max | Score |
|---|---|---|
| Architectural continuity with ARC-01-D / ARC-02-A | 20 | |
| Tank Cloister [brightest feature, six tanks, copper deck] | 20 | |
| Originality | 15 | |
| Austin / climate plausibility [evening atmosphere] | 10 | |
| Material discipline | 10 | |
| Hospitality appeal | 10 | |
| Photorealism | 10 | |
| Cultural restraint | 5 | |
| **Total** | 100 | |
**Hard fails:** wrong fermenter count; wrong copper-vessel count; arrangement not the oblique D layout; silver/orange cones; thick or yellow sleeves; day sky/foliage in glass or a day-lit hall; visible composite boundary; moved/duplicated mullions; any change outside the hall; Tank Hall not the brightest; star flares/bloom/HDR/haze/neon/string lights; obviously CGI; frontal or symmetric hall.

## 4. Decision
PROVISIONAL WINNER — AWAITING FOUNDER APPROVAL only if all 13 gates pass. Otherwise **ARC-02-C FAILED — STOP AND REPORT**; ARC-02-D requires a new founder decision. Do not score toward 90.
