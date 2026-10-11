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
| *(none yet)* | | | | | | | | | | | `visuals/archive/rejected/` |

## Existing-asset decision (hero)
`NV-HERO-01` (the founder's night exterior) shows eight tanks uncropped, which would imply a tank count (G-6). A purpose-built replacement could not be generated. The published crop shows only **one partial tank**, a truer image than the uncropped source and far better than leaving the problem. It is **kept temporarily**, documented in the manifest `qa_result`, and to be replaced when A1 exists. The image is not replaced by anything worse.
