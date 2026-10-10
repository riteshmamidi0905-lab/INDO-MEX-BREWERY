# ARC-01-E Review Sheet

> **CLOSED (D-42): no further ARC-01-E attempts; ARC-01-D is the canonical day exterior by founder waiver.** Kept for history.

**Status:** ARC-01-E — NOT GENERATED — FINAL REALISM PASS PREPARED. No ARC-01-E image exists. Do not fill in scores until one does.
**Compare against:** `visuals/generated/ARC-01-D.png` (89/100). **Prompt:** `generation-batch-01/ARC-01-E.md`. **Tools:** `visuals/tools/arc01e_tools.py`.

## 0. Provenance to record
Tool/model that produced the edited crop; whether masked (recommended) or global; reference images used (ARC-01-D crop + masks); whether the composite script was used (then outside-hall pixels are identical by construction). Founder approval remains NO until explicitly given.

## 1. Preservation gate (all must PASS; any FAIL = reject E)
| Check | Method | Result |
|---|---|---|
| Exactly six fermenters, same positions (west pair, west-of-deck, east-of-deck, east pair) | Count twice on 2x crops; overlay D and E and compare positions; count anything fermenter-like and list ambiguous objects | |
| Two copper vessels only, same place; no other copper | Visual | |
| Marigold sleeves: six, narrow, uniform, #E8870E-like, same height positions | Visual + eyedropper | |
| Graphite matte cones unchanged | Visual | |
| Dark-bronze mullions unchanged | Frame lock; visual | |
| Exterior unchanged (canopy, entrance, arcade, screens, court, rill, restaurant block, stacks, trees, people, vehicles, sky, light, crop) | `python3 visuals/tools/arc01e_tools.py compare ARC-01-E.png` -> outside-hall RMSE (<=3 pass, 3-10 inspect, >10 reject) and side-by-side flicker comparison | |
| Screens still plain perforated panels (no sunburst, rosette, mandala) | Visual | |
| No new clichés/text/logos/neon/string lights/brass/terracotta/agave/palms | Visual | |

## 2. Realism improvements (must be MATERIAL, judged by eye at 100% and 200%)
| Item | Better than D? (Y/N) | Notes |
|---|---|---|
| Sanitary pipework (welds, routing, clamps) | | |
| Tri-clamp ferrules/gaskets | | |
| Butterfly valves | | |
| Tank legs and foot plates | | |
| Restrained hoses | | |
| Stainless trench drains | | |
| Seamless warm-grey production floor (not terrazzo) | | |
| Brew-deck stairs and railings | | |
| Pumps/utilities plausible | | |
| Stainless reflections believable | | |
| Glass reflection/refraction believable | | |
| Depth behind glazing | | |
| Contact/occlusion shadows | | |
| Sharpness without halos or oversharpening | | |
| Clean-new look (not dirty/distressed) | | |
Optional objective proxy: hall sharpness ratio from `compare` (E/D > 1.2 suggests more detail); never decisive.

## 3. ARC-01 rubric (strict; E must reach >= 90 with no hard fail)
| Criterion | Max | D | E |
|---|---|---|---|
| Architectural continuity | 20 | 19 | |
| Tank Cloister | 20 | 18 | |
| Originality | 15 | 12 | |
| Austin / climate plausibility | 10 | 9 | |
| Material discipline | 10 | 10 | |
| Hospitality appeal | 10 | 9 | |
| Photorealism | 10 | 7 | |
| Cultural restraint | 5 | 5 | |
| **Total** | 100 | **89** | |
**Hard fails:** wrong fermenter count; Tank Hall hidden; horseshoe absent; ornament/medallions; terracotta/brass dominance; hacienda/palace/theme-park look; dominant fake branding; obviously CGI; could not function as a brewery.

## 4. Decision
- **E WINS (PROVISIONAL WINNER — AWAITING FOUNDER APPROVAL)** only if every gate in sections 1-3 passes and total >= 90.
- **E REJECTED** if there is any geometry drift, wrong tank count, architectural change, new visual problem, hard fail, or score < 90 -> **ARC-01-D becomes the canonical day reference through a documented founder waiver at 89/100.** No ARC-01-F unless the founder explicitly overrides (D-40).
- Whichever path: founder approval stays NO until stated by the founder.
