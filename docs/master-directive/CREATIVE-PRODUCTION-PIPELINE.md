# Repeatable production pipelines

## 1. Imagery (merchandise, packaging, food)
Research -> Creative brief (`brand/goods/`, `beer/concepts/`, `food/candidates/`) -> Visual generation (`visuals/tools/concept_art.py` today; an external generator only with your approval, using `visuals/external/PROVENANCE-TEMPLATE.json`) -> Review (cultural, rights, similarity; items needing qualified reviewers are listed in each brief) -> Refinement -> Asset validation (`python3 visuals/tools/validate_assets.py`: provenance present, hashes match, LOCAL-ONLY status, size, no forbidden markers) -> Website integration (only validated assets, originals kept separate from optimized derivatives; noindex until publication is approved).
Run it: `CHROMIUM_PATH=<chrome> python3 visuals/tools/concept_art.py && python3 visuals/tools/validate_assets.py`.

## 2. Cinematic content (brand film, reveals, background video)
Storyboard -> Visual assets -> Animation -> Narration -> Editing -> QA -> Local preview. NOT BUILT: needs a video generator or an animation tool and a licensed synthetic voice (see CREATIVE-AND-VOICE-TOOLING.md). The storyboard is written (`docs/master-directive/BRAND-FILM-STORYBOARD.md`); animation can be done with CSS/SVG on the website, which needs no external tool.

## 3. Engineering education
Voice explanation -> transcription -> technical evaluation -> follow-up questions -> independent coding challenge. Implemented as `lab/learning/explain.py` (coverage and follow-ups) plus the diagnostic and modules in `lab/learning/`.

## Quality gate for every asset
Provenance record; creative decisions recorded; rights considered (no third-party artwork, no logo, AI assistance declared, assignment documented before any commercial use); no claim that an image is a photograph of a real product; synthetic/concept label visible; cultural review flagged where the brief says so.
