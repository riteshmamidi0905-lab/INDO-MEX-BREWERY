# NASHA Generation Log (Sprint 8 onward)

**Status:** `[PLAN]` + record. Every generation run is logged here and in `visuals/generated/LOG.md`. **Logo rule (D-66):** never ask a generator for NASHA text, a logo, icon, monogram or symbol, and never upload an approved master. Generate **blank signage**; add temporary typography afterwards by script only.

## Sprint 8 capability check (2026-10-11)
The session has **no image-generation capability**: no image tool in the tool list (a tool search for image generation returned nothing), no image-model API keys or SDKs in the environment, no GPU, and outbound access is limited by proxy policy. **No image was generated and none was fabricated.** The prompt package is preserved and was tightened for Batch A (below). **Blocker for the founder:** run the batches in an external generator whose commercial-use terms the founder has checked, then ingest per `PROMPT-PACK.md`.

## Sprint 9 capability re-check (2026-10-11)
Re-audited. Image APIs and model hosts (Hugging Face, OpenAI, Stability, fal, Replicate) are unreachable from the sandbox; no GPU; no image tool; registry search shows only connectors the founder must authorise (Hugging Face, Adobe). **Still no image generated.** Added `tools/visual_qa.py` so the first candidates can be pre-checked. See `docs/ai/NASHA-AI-CAPABILITIES.md`.

## Batches (controlled, in order; do not generate all 33 blindly)
| Batch | Contents | Gate before starting | Status |
|---|---|---|---|
| A: the place | A1 EXT-BLUEHOUR, A2 INT-HERO, A3 BAR, A4 FIRE-KITCHEN, A5 PATIO-EVENING, A6 ENTRANCE | Founder approves tool and terms | NOT RUN (no generator) |
| B: food | B1 C65, B2 Paneer Taco, B3 Gobi Taco, B4 Butter Chicken Quesadilla, B5 Goat Birria, B6 Chaat Elote, B7 Cardamom Churros (**no lamb**) | Batch A visually stable; reference library read per dish; **goat must read as goat, no beef or pork** | NOT RUN |
| C: beer and glass | C1 Hefeweizen, C2 Mexican-Style Lager, C3 Vienna Amber, C4 GLS-01 (clean, filled, table, pairing views), C5 GLS-02 family | Reference library §4; **no working-name beers** | NOT RUN |
| D: pairings | D1 Paneer Tikka Taco × Hefeweizen, D2 Chicken 65 Totopos × Mexican-Style Lager, D3 Goat Birria × Vienna Amber, D4 optional | Acceptable food and beer assets exist; label "Proposed pairing, not sensory tested" | NOT RUN |
| E: the rest | dining, signage (blank), people, Austin atmosphere, pop-up, menu mock-ups, merch (blocked until a logo exists) | After A-D | NOT RUN |

## Run record (one row per run; append only)
| Date | Manifest ID | Tool | Model (if exposed) | Prompt ref | Seed | Source inputs | Candidates | Winner and score | Modifications | Rights / commercial status | Archive of rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-11 | NV-PLAN-EXT-BLUEHOUR (A1) | Figma generate_image (paid credits; founder approved cap of 12 calls) | gemini-3.1-flash-image | see prompts below | not exposed | none | c1 only | none selected: **candidate, not accepted** (thumbnail QA only) | none | Figma/model terms UNVERIFIED; PROVISIONAL-LOCAL-ONLY | thumbnail in `visuals/archive/candidates/`; full-res URL expires 2026-10-18 |
| 2026-10-11 | NV-PLAN-INT-HERO (A2) | same | same | below | n/a | none | c1 only | candidate, not accepted | none | same | same |
| 2026-10-11 | NV-PLAN-FIRE-KITCHEN (A4) | same | same | below | n/a | none | c1 only | candidate, not accepted | none | same | same |
| 2026-10-11 | NV-PLAN-PATIO-EVENING (A5) | same | same | below | n/a | none | c1 only | candidate, not accepted | none | same | same |
| 2026-10-11 | NV-PLAN-FOOD-C65 (B1) hero + truth | same | same | below | n/a | none | c1 only (one candidate per view) | candidate, not accepted | none | same | same |

## Existing-asset decision (hero)
`NV-HERO-01` (the founder's night exterior) shows eight tanks uncropped, which would imply a tank count (G-6). A purpose-built replacement could not be generated. The published crop shows only **one partial tank**, a truer image than the uncropped source and far better than leaving the problem. It is **kept temporarily**, documented in the manifest `qa_result`, and to be replaced when A1 exists. The image is not replaced by anything worse.

## Sprint 9 generation record (6 of the 12 approved Figma calls used; 6 unused)
**What worked:** the founder connected Figma; `generate_image` (paid Figma AI credits, per-call cost not shown to the agent) produced 6 images at 1376x768 (hero/interior/kitchen/patio), 1200x896 (dish hero) and 1024x1024 (dish truth view). Each call returned a hosted URL valid 7 days and a 256 px inline preview.
**Hard limitation:** the sandbox proxy blocks `www.figma.com`, so **no full-resolution file could be downloaded**. QA was done on the 256 px previews only, which cannot check text/logos, faces, duplicated pieces or fine food texture. **Nothing is accepted or integrated.** The previews are archived in `visuals/archive/candidates/` (outside the site build).
**Founder action (by 2026-10-18):** download the six PNGs from these URLs into `visuals/archive/candidates/` (names suggested: A1-...-c1.png, A2-, A4-, A5-, B1-hero-, B1-truth-), then the next session runs `tools/visual_qa.py` on each, scores them against `IMAGE-QA.md`, and integrates winners. URLs: A1 `https://www.figma.com/api/mcp/asset/7b936b6a-bf5f-4d9d-825c-271a985453bb.png); A2 /3da5c76c-de6c-4f3a-936c-903f1c64f64b.png); A4 /bb4aedbc-a236-46e8-a60e-af7ac8600fa4.png); A5 /e6d383dc-5c4d-4a2b-ab75-bb0612983ab7.png); B1 hero /a44f828b-ec6a-47fe-b7fd-a5bf282264e6.png); B1 truth /d5c2cde2-c80a-4b66-95ca-97be95e69980.png` (all under `https://www.figma.com/api/mcp/asset/`). If a URL has expired, the prompts below can be re-run.
**Not generated (deliberately):** A3 bar (the A2 interior shows the tiled bar) and A6 entrance; the remaining dishes, beers, glassware and pairings; a candidate set was not produced because candidates cannot be QA'd at full resolution. 6 calls are held in reserve.
**Prompts used (no NASHA text, blank signage, no tank count):**
- A1: contemporary Austin limestone and glass brewery restaurant at blue hour, glowing amber interior, covered cedar arcade with dark perforated steel screens, gravel patio with long communal tables and relaxed diverse diners (backs/profiles), string lights, live oak, native grasses, bicycles, only a partial glimpse of steel tanks through one glass section, blank dark monument sign, no text/logos/address/cars, 2300K light, 24mm.
- A2: interior at evening, long dark pecan bar with square matte tile front in bone and marigold, matte black tap handles, steel shelves of tall glasses, terrazzo floor, limestone, perforated screens, long communal tables with black stoneware, guests not looking at camera, partial tanks through a glass wall, open kitchen with a clay tandoor glowing and steel hood, no text, 28mm.
- A4: open kitchen, cook lifting a skewer from a clay tandoor, second cook at an iron comal pressing tortillas, steel hood, black stoneware at the pass, safe practice, steam only above the comal, 35mm shallow depth.
- A5: covered Austin patio on a warm evening, cedar beams, ceiling fans, perforated screens, communal tables, string lights, live oak, grasses, mixed diners, children at one table, bicycles, limestone wall, no text.
- B1 hero: Chicken 65 integrated with thick irregular fried masa totopos on matte black stoneware at 45 degrees; bite-size boneless chicken with uneven red-orange coating distributed through an open chip layer; curry leaves, sliced green chile, lime wedge, small raita-crema pool, side window light, blurred pale beer behind; no text.
- B1 truth: same plate top-down, nothing else on the table.

## Sprint 10 generation record (cap 12 total approved in Sprint 9; 10 used, 2 held)
Verified at sprint start: 6 calls used in Sprint 9, 6 remained. Sprint 10 used 4 more; **2 remain; no spending beyond the 12-call cap without a new explicit cap.** Hugging Face invoke is still disabled (`gradio=none`). Full-resolution originals were not provided and cannot be downloaded in the sandbox; QA is preview-only (see `CANDIDATE-REVIEW.md`).
| Call | Purpose | Candidate | Preview result | Decision | URL (expires 2026-10-18) |
|---|---|---|---|---|---|
| 7 | A3 bar | A3-c1 | plausible | PENDING FULL-RES | https://www.figma.com/api/mcp/asset/5ac9e101-d7fd-4e52-9dc6-294233ca5dad.png |
| 8 | A6 entrance (blank sign) | A6-c1 | plausible, strong continuity | PENDING FULL-RES | https://www.figma.com/api/mcp/asset/d9545d4b-1e14-4ea1-bc49-af98d134c8a9.png |
| 9 | A4 regenerate after tandoor research (V-49) | A4-c2 | reads as a tandoor | PENDING FULL-RES; c1 superseded (pizza-oven look), URL c1: https://www.figma.com/api/mcp/asset/bb4aedbc-a236-46e8-a60e-af7ac8600fa4.png | https://www.figma.com/api/mcp/asset/a9f35477-e73b-4fe5-a21d-b06403f0c9e6.png |
| 10 | C6 gate-beer family (Hefeweizen, Mexican-Style Lager, Vienna Amber) | C6-c1 | beer styles plausible; collar ring not visible | PENDING FULL-RES | https://www.figma.com/api/mcp/asset/e25ee2ee-c47e-48fd-87d2-6218202e9120.png |
**Prompts (no NASHA text, blank signage, no tank count):** A3: pecan bar along its length, bone and marigold tile front, twelve plain unlabeled tap handles, steel shelves of collar-ringed glasses, bartender pouring wheat beer, guests talking to each other, blurred hint of tanks, no text. A6: limestone entrance at dusk with cedar canopy, glowing glass door, blank dark monument sign, perforated screen, bike rack, two guests from behind, patio lights. A4 c2: commercial tandoor (clay-lined cylindrical chamber, steel/tiled outer body, narrow top opening) with a cook lowering a vertical skewer, separate carbon-steel comal station, steel hood, no flame outside equipment. C6: three beers in related tall glasses with a raised ring (collar): hazy pale straw-gold Hefeweizen with thick moussy white head; clear pale gold Mexican-style lager; clear copper-amber Vienna lager with off-white head; plain glasses, no text.
**Held (2 calls):** for retries after full-res QA. Paneer Tikka Taco, Gobi Taco, Butter Chicken Quesadilla, Goat Birria, Pilsner/Witbier/Dunkelweizen, glass-family studies (Collar Weizen, Collar Lager, Collar Pilsner), pairings and the Two-Pour were **not generated**: no cap remains to do them well and candidates cannot yet be QA'd.
