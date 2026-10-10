# ARC-01-C Review

## Image metadata
- **File:** `visuals/generated/ARC-01-C.webp`, **2000x1128**, sRGB, 368 KB. Supplied by the founder.
- **Tool/date/prompt/reference:** OpenAI image generation (per founder), 2026-10-10, `generation-batch-01/ARC-01-C.md`, edit of ARC-01-B. Seed not exposed.
- **Status:** CANDIDATE — REFINEMENT REQUIRED (near-pass). **Founder approval: NO.**

## Method
Full-frame inspection; crops with 1.6x to 2.5x enlargement of the Tank Hall glass, the brew deck and the west tank group; side-by-side comparison with ARC-01-B; RMSE comparison of four regions (court/arcade 0.24, foreground 0.23, sky 0.07, hall glass 0.25 on a 0-1 scale). **Reading of the RMSE:** outside the glass is nearly as different as inside, so the generator **re-rendered the whole image** rather than editing a masked region. Visually the design is faithfully preserved; the differences are in fine detail (people, foliage, canopy edge, gravel texture), not in architecture.

## Tank count (the critical check)
- **Visible fermenters: 6.** Left of the brew deck: tank 1 and tank 2 (two adjacent tanks, far left, west leg), tank 3 (centre-left, nearer the deck, smaller in perspective). Right of the deck: one large nearest tank (base-east) and two more tanks behind it, partly hidden by a mullion (east leg). That is 2+1 on the west and 1+2 on the east, i.e. the canonical 1-2 / 3 | deck | 4 / 5-6 pattern.
- **Ambiguous fermenter-like objects: 1.** A small copper-gold cylindrical vessel beside the staircase between tanks 2 and 3. It reads as a small ancillary/hot-liquor vessel, not a conical fermenter, but a strict reviewer could count it.
- **Total interpretable fermenters: 6 (7 at most).** No reflections or columns read as extra tanks.

## Horseshoe: PASS
The equipment forms a room: fermenters stand either side of a central raised brew deck with two copper vessels, hood and stack at the back, steel railings and stairs in between; tanks recede at different depths and sizes. It reads as a U opening to the south glass, not a row. (Not every tank is equally visible; the east leg is partly hidden behind a mullion, which is acceptable.)

## Charcoal cones: PARTIAL
Cones are visibly **darker than the shells** (dull grey with warm reflections) but they still read as metallic/brushed grey, not matte charcoal insulation. Do not rationalize: this is only a partial pass.

## Marigold bands: PARTIAL-PASS
All six tanks carry exactly one band, consistent in position and colour (orange, restrained). The nearest tank's band is wider (about 8-10 in equivalent) and a little yellower than the others; the target is a uniform ~6 in deep marigold.

## Copper brew deck: PASS
Two copper-clad domed vessels sit side by side on a raised, railed platform at the back centre, under a copper-toned hood with a stack rising to the ceiling; stainless piping and a stair are visible. They read as brewing equipment, not decoration.

## Catwalk, piping, realism
Railings with kick-plate-like lower rails, stairs, tank-top platform rails, round side manways and piping are all present and plausible. A brewer could plausibly work here. Not visible: trench floor drains, hose management. All code, clearances and equipment accuracy are `[PRO]`. Small ancillary vessel and some pipes are soft/blurred at crop size (AI softness).

## Glass and reflections: PASS
The hall reads as genuinely glazed: tree reflections overlay the left panes, interior uplights and equipment remain visible, the east glass shows sky and foliage. Not mirror-like, not painted.

## Architecture preservation (vs ARC-01-B): PASS with minor drift
Preserved: hall massing, canopy, entrance recess and soffit, arcade and concrete columns, perforated screens, court and rill, restaurant block, roof, two stacks, planting, two walkers, vehicles, oak branch, camera, sun direction. Minor drift: re-rendered people and foliage, slightly different canopy edge and glass reflections, mullions still black (not dark bronze), the east flank still shows solid dark cladding in its upper part. No redesign.

## Screens: PASS
Flat blackened-steel panels with a regular grid of simple round holes; no sunbursts, mandalas, rosettes or medallions. As in ARC-01-B, hole sizes look nearly uniform and no concentric arcs read across panels (accepted).

## Entrance: PASS
Clear recess with cedar soffit and warm downlights, limestone wall change, paver path, planters and grasses framing the doors; the blank monument panel sits slightly in front of the first column (minor).

## Photorealism: 7/10
Strong light, plausible materials and shadows, no fake text, no warped vehicles or furniture. Penalties: AI softness inside the hall and in the far court crowd, uniform warm grade, slightly stylized oak foliage, near-repeated figures in the far court.

## Cultural restraint: 5/5
Contemporary Central Texas; no ornament, no hacienda, palace or theme cues.

## 100-point scorecard
| Criterion | Max | Score | Note |
|---|---|---|---|
| Architectural continuity | 20 | 18 | Strong; black mullions, partly opaque east flank |
| Tank Cloister | 20 | 17 | Six tanks, horseshoe, copper deck, bands; cones only partial, one wide band, one ambiguous vessel |
| Originality | 15 | 12 | Glowing glass hall with a visible copper brewhouse is distinctive |
| Austin / climate plausibility | 10 | 9 | |
| Material discipline | 10 | 9 | Copper only on vessels; black not bronze framing |
| Hospitality appeal | 10 | 9 | |
| Photorealism | 10 | 7 | |
| Cultural restraint | 5 | 5 | |
| **TOTAL** | **100** | **86** | Below the 90 gate |

## Hard-fail check: **NO**
Correct tank count (6); Tank Hall present and dominant; horseshoe present; no medallions; no terracotta/brass dominance; no hacienda/palace; no fake branding; reads as photography; plausibly functional brewery.

## Subjective tests (do not override the score)
- **Would people deliberately drive across Austin to visit?** YES, qualified. The glowing glass hall with a copper brewhouse and orange-banded tanks is a strong reason to pull in, and the shaded court promises a good stay. We cannot know real demand, and the image is a concept.
- **Most memorable thing:** the Tank Hall: tall glass box with the copper brewhouse and banded tanks inside. That is the ideal answer.

## Recommendation
**Not yet canonical (86 < 90).** The remaining defects are small and isolated, so do **not** regenerate the architecture. Run **ARC-01-D**, a targeted edit (cones, band widths, mullion colour, remove the ambiguous vessel, restore sharpness). Because the image generator re-renders globally, if the cone colour or band width fails again, **do it in post-production** (recolour cones to matte charcoal, narrow the band) rather than iterating. Alternatively the founder may accept ARC-01-C as the canonical day reference with the documented deviations; that is the founder's decision, not an automatic pass.
