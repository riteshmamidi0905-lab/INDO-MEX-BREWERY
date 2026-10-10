# ARC-02-B Review (strict; ARC-02 review sheet rubric)

**Provenance:** ARC-02-B is a **scripted/composited derivative of ARC-02-A + ARC-01-D — NOT a newly generated image.** Tool: `visuals/tools/composite_arc02b.py` (mullion-based affine registration of ARC-01-D's Tank Hall into ARC-02-A's glass, reflection suppression, night grade, uplight, sleeve/copper colour control). Founder approval: **NO**.

## Measurements
| Check | Result |
|---|---|
| Outside-hall drift vs ARC-02-A | **0 changed pixels** of 1,988,993 outside the glass mask (max diff 0). Only feathered ring (~26k px) and glass interior differ. |
| Structure vs ARC-01-D (`structure_check.py`) | recall 0.67 / precision 0.71 (inspect band; whole-frame, includes day→night edge changes; by eye the hall geometry and mullions match) |
| Fermenters (counted twice at 2x) | **6** (3 left of deck, nearest large tank right + 2 behind it); eight-tank defect gone |
| Copper vessels | **2**, with hood and stack |
| Cones | 6, dark graphite, but **blotchy/speckled** from the median neutralisation; not clean |
| Sleeves | 6, sampled ≈ (224,130,13)/(216,126,13) ≈ #E8870E; narrow, but their edges look cut-out/patchy on the darkened shells |
| Trench drains | **Not visible** (ARC-01-D's hall pixels do not show them; not faked) |

## Defects (why it reads artificial)
1. Daylight-lit hall in night glass: left panes still show sunset sky/foliage reflections and bright daytime stainless on the right-hand tank; hall and exterior do not share one exposure.
2. Pushing the grade darker (ev −0.9) darkened the left tanks and brew deck into murk while the right tank stays day-bright; sleeves then float as bright decals.
3. Cone speckle and brown cast; compositing seams visible at left upper panes (hard-edged reflection-mask boundaries).
4. Warm uplight at tank bases is barely perceptible; no convincing night glass transparency.

## Score (strict)
Continuity 15/20, Tank Cloister 14/20, originality 10/15, Austin plausibility 5/10, materials 6/10, hospitality 6/10, photorealism 4/10, cultural restraint 4/5 = **64/100**.
**Hard fail: YES** — hall does not belong to the night exposure (day photo behind night glass); cone/sleeve artefacts.
**Recommendation:** do **not** approve and do not proceed to ARC-02-C automatically. Scripting a day image into night cannot yield a plausible result; a true night render of the Tank Hall (generator, using ARC-01-D hall + ARC-02-A frame) or founder waiver decision is needed.
