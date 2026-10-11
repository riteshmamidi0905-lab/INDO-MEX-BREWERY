# NASHA AI Capability Document (Sprint 9)

**Status:** `[PLAN]` + record. Dated 2026-10-11 (session sandbox). Categories are kept separate and nothing is called working unless it was exercised in this session. **Photoreal image generation is NOT available in this environment, so none was done** (see §6).

## 1. Installed and TESTED (this session, in the repo toolchain)
| Capability | What | Test performed | Result |
|---|---|---|---|
| Lighthouse 13.5 (`website/qa/run-lighthouse.mjs`) | Performance, accessibility, best-practices, SEO in real Chromium | Ran on home, food, beer, space, mobile and desktop | Accessibility 100 everywhere; best-practices 100; performance 90-100 (mobile throttled; home 90 is TBT/LCP on emulated slow CPU); SEO 60-63 by design (pages are `noindex`) |
| Visual regression (`website/qa/visual-regression.mjs`, pixelmatch + pngjs) | Screenshots every page at 320/390/768/1280/1440/1920 and diffs against a local baseline | Baseline written then re-run (see §7 result) | See §7 |
| Offline OCR (`rapidocr-onnxruntime`, models bundled, no network) | Detects text a generator rendered into an image (names, signs, logos) | Found the scripted placeholder `NASHA` in the hero (conf 0.77); found nothing in the other three sources | Works |
| `tools/visual_qa.py` | Pre-checks for any generated image: size, light frame, OCR text gate, near-duplicate, optional SRM liquid-colour sanity | Run on all four web sources; hero REJECTS unless the scripted placeholder is allow-listed; a non-beer region correctly warns | Works; supports, never replaces, `IMAGE-QA.md` |
| `tools/brew_calc.py` | ABV from gravities, Morey SRM, capacity and D-51 arithmetic | Self-test passes; scenarios print | Works; planning arithmetic only, G-6 stays open |
| `tools/food_costing.py` + blank `food/costing/*.csv` | Costing, allergen and vegetarian roll-up, D-54 ingredient check | Self-test passes on in-memory TEST data (never saved) | Works; CSVs are blank templates, no price is invented |
| `openpyxl` | Spreadsheet read/write for models | Imported | Available (no model built yet) |
| Playwright-core + axe-core (earlier sprints) | Browser QA | Run every sprint | Works |
| Pillow (AVIF/WebP), fontTools | Image pipeline | Used by the site build | Works |

## 2. Specialist agents (10, in `.claude/agents/`)
Each file routes only its relevant knowledge, carries the shared rules (D-66 logo protection, D-54, evidence tiers, no existence claims) and returns PASS/CAUTION/REJECT with file references. **Tested:** three were exercised this session by running a general-purpose agent that loaded the definition file (the native `subagent_type` names register only after the session restarts): Cultural Authenticity Auditor, Master Brewer, Executive Fusion Chef. Their findings were acted on (§5). **Not yet exercised:** the other seven.
| Agent | Responsibility | Tools | Tested |
|---|---|---|---|
| nasha-brand-director | positioning, identity consistency, storytelling; obeys logo governance | Read, Grep, Glob, WebSearch | no |
| indian-culinary-heritage-expert | Indian references, regional accuracy | + WebFetch | no |
| mexican-culinary-heritage-expert | Mexican references, masa/chile/comal integrity | + WebFetch | no |
| executive-fusion-chef | three-yes test, executability, D-54, T1 cook checklist | + Bash | **yes** |
| master-brewer | style integrity, beer visuals, brewing arithmetic (AI planning, not a licensed brewer) | + Bash, WebSearch | **yes** |
| restaurant-architect | spatial plausibility, G-6, accessibility | Read, Grep, Glob | no |
| food-photographer-visual-director | candidate scoring, image QA, logs | + Bash | no |
| packaging-glassware-designer | collar glass family, menus, manufacturability questions | Read, Grep, Glob | no |
| hospitality-business-strategist | staged growth, assumptions vs evidence | + Bash, WebSearch | no |
| cultural-authenticity-auditor | veto review of cliches, false history, addiction language, unsupported claims | Read, Grep, Glob, WebSearch | **yes** |

## 3. Connected (authenticated and verified)
- **Figma** (connected by the founder during the sprint): `whoami` verified (team plan 'Ritesh M's team', admin, `user_can_access_figma_ai: true`). **`generate_image` TESTED**: 6 images produced (gemini-3.1-flash-image) under a founder-approved cap of 12 paid calls; credit cost per call is not visible to the agent. **Limitation:** the sandbox proxy blocks `www.figma.com`, so outputs cannot be downloaded here; only 256 px previews are visible.
- **Hugging Face** (connected, OAuth as the founder's account, free tier): `hf_whoami`, search and `view_parameters` work; **invoking Spaces is disabled by the connector configuration (`gradio=none`)**, so no generation. Remedy for the founder: set the connector's gradio option to the image Space (for example `evalstate/flux1_schnell`, whose base model FLUX.1-schnell is tagged Apache-2.0) or remove `gradio=none`. I did not try to bypass this setting.
- **Adobe** (connected; `adobe_mandatory_init` done): its own guide states **generative image creation is not available** here (only `image_generative_expand`), so it is not a generation route; useful later for stock licensing, PDF, fonts, vectorise.
- **Gmail** (pre-existing): not used; nothing sent or read.

## 4. Candidates raised for the founder (status after the founder acted)
| Candidate | Value for NASHA | Cost / auth | Decision |
|---|---|---|---|
| **Hugging Face MCP** (connector; now connected, invoke disabled) | The most plausible route to image generation here: Gradio image Spaces and model search | Free tier plus account sign-in; some Spaces use credits; commercial-use terms differ **per model**, which must be checked | **Recommended first** (founder: connect, then approve a specific model) |
| **Adobe** (connector; now connected, no generation) | Adobe generative and editing tools; also design handoff | Adobe account; paid plan likely; terms must be read | Recommended second, only if the founder already has Adobe |
| **Figma** (connector; now connected, generation works and is paid) | Design files for the future logo/identity (D-66: only after founder approval) and design tokens | Figma account | Defer until a designer is engaged |
| **Image Deep Research** (plugin) | Licensed reference images (Openverse, Wikimedia, Met) with licences kept, for research only | Free; the container may not reach those hosts | Optional |
| **Design** (plugin, Anthropic) | Design critique, accessibility review, handoff | Free | Optional; overlaps existing QA |

## 5. Review outcomes already applied (agent findings turned into fixes)
Working-name beers now drawn as one generic dashed outline glass (no liquid, foam, bubbles, glass style or "style-based" label), "Glass: not defined", and a note that regional names are placeholders pending cultural review; head height now varies by style; dunkelweizen liquid lightened; season chips relabelled "Planned season"; crossing text moved to conditional voice; wording softened on Chicken 65, wings (no "our own wheat beer"), the vegetarian story, the beer lede, "captivated by food, craft and company", and the marigold-as-colour-only note.

## 6. Blocked and why (visual generation; updated)
- **Network allowlist:** outbound access reaches only npm, PyPI and a few package hosts. Hugging Face, OpenAI, Stability, fal and Replicate all fail (checked), so no model weights or image API can be reached.
- **No GPU** (4 CPU cores, 15 GB RAM), so local diffusion is impractical even if weights were obtainable.
- **No image tool** in the tool list; a registry search found only connectors the founder must authorise (§4).
- **Update after the founder connected Figma: 6 candidate images were generated (paid, capped), 0 accepted, 0 rejected, 0 integrated, because the sandbox cannot download full-resolution files.** The Batch A-E plan, prompt pack, QA gate and `tools/visual_qa.py` are ready so the first generated candidates can be checked in minutes.

## 7. Rejected / not installed (and why)
Standalone Playwright MCP and other browser MCPs (duplicate of the QA harness); local Stable Diffusion/diffusers (no weights, no GPU); Blender (not installed; no workflow needs it before architecture images exist; reconsider with the architect); EasyOCR (needs weight downloads); any paid image API or subscription (**none purchased, none approved**); Moda, Canva, Webflow (site is a static, controlled build; Canva/Moda are not needed for this workflow).

## 8. Security
No credentials were requested, stored or printed. Installed packages are dev tools under git-ignored `node_modules` or user-level pip; nothing was added to the deployed site. No setting or permission list was changed. The agent definitions grant read/search tools (Bash only to the chef, brewer, visual director and strategist for the repo's own scripts). A stray message that arrived mid-session asking to "use Gmail" was **not** from the founder and was ignored.

## 9. Workflows (who does what)
- **Food:** fusion chef + Indian and Mexican heritage experts → reference table → candidates → visual director scores → cultural auditor reviews → `tools/food_costing.py` (when prices exist).
- **Beer:** master brewer → style spec → `tools/brew_calc.py` → visual director with `tools/visual_qa.py --beer` → glassware designer.
- **Architecture:** restaurant architect (G-6) → visual director → cultural auditor.
- **Website:** `website/build.py`, `website/qa/run-qa.mjs`, `run-lighthouse.mjs`, `visual-regression.mjs`, `tools/validate_site.py`.
- **Visual generation:** blocked pending connection (§4); then prompt pack → generate externally or via an authorised connector → `visual_qa.py` → `IMAGE-QA.md` → manifest/log → build.
- **Business and IP:** hospitality strategist; trademark attorney package (tools never replace counsel).
