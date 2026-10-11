# NASHA Image QA Gate (Sprint 8)

**Status:** `[PLAN]` the gate every generated or composited image must pass **before** it is integrated. Any single hard failure means **REJECT**. Never accept an image because generation succeeded; keep the best output, not the first. Rejected candidates are archived under `visuals/archive/rejected/` (outside the website build; never copied to `dist/`).

## Gates (record PASS / CAUTION / HARD FAIL for each in the manifest `qa_result` column)
| Gate | Question | Hard fail examples |
|---|---|---|
| Brand | Does it look like NASHA (limestone, glass, timber, perforated screens, pecan, blackened steel, restrained marigold, 2200-2400K light)? | A different-looking restaurant; theme-park styling |
| Cultural | Does it avoid stereotypes (see `NASHA-VISUAL-DIRECTION-V3.md` §2)? | Sombreros, Taj Mahal, mandala wallpaper, cantina kitsch |
| Food | Could a competent NASHA kitchen plausibly serve this (reference library §3, §5)? | Impossible geometry, plastic food, **beef or pork (D-54)**, goat birria that reads as beef, cauliflower like chicken |
| Beer | Could a qualified brewer pour this style (reference library §4)? | Whipped-cream foam, wrong colour for the style, lime by default, floating bubbles, invented beer |
| Architecture | Could it plausibly be built, without fixing equipment scale (**G-6**)? | Impossible structure; a visible tank count or capacity; the old eight-tank view |
| Austin | Could it belong in Austin without a theme park, a fake skyline, address or landmark? | Skyline, identifiable property, street sign |
| Evidence | Does it imply NASHA already exists, or show real guests, tested food, brewed beer? | Crowds presented as customers; "finished dish" captions |
| Logo | Did the generator invent any branding, lettering, icon or monogram? | **Any generator-made lettering or mark.** Prompts never ask for NASHA text; signs are blank, and temporary typography is added afterwards by script |
| Rights | Is generator, model, date, prompt, seed, inputs and modifications recorded; is use status honest? | Missing log entry; marking commercial use cleared without checking terms |
| Accessibility | Is there meaningful alt text; no baked-in text? | Readable fake text |
| Mobile | Does the 4:5 composition keep the subject (food, glass, hands, fire, entrance, bar, table)? | Subject lost in the crop |
| Performance | Does it fit the budget (hero AVIF about 130 KB desktop, 60 KB mobile; others lazy)? | Oversized files |

## Scoring (for P1 assets, generate several candidates if capability allows)
Score each candidate 0-5 on: realism, continuity with the batch, composition, mobile survival, honesty. A candidate with any hard fail scores 0. Record the winner, the runners-up and the reason in `GENERATION-LOG.md`.

## Continuity checklist for Batch A (the place)
Same limestone, glass and screens; pecan bar with bone and marigold hand-made tile front; blackened steel; terrazzo floor; matte black stoneware; warm 2200-2400K practical light; collar glassware; partial brewery views through glass **with no fixed tank count**; Austin landscape (live oak, grasses); relaxed synthetic people not looking at the camera.

## Sprint 8 addition: reality-first tests (mandatory, from the founder's reference standard)
1. **Three-yes fusion test** for every dish (reference library §7): Indian component recognisable; Mexican component recognisable; one intentional dish. Any NO rejects.
2. **Caption-removed tests** (reference library §12) for food, beer and glass.
3. **Two views** per dish (hero and truth) and **several candidates** for the hero dish, scored and logged.
4. **No generated text**: no dish names, beer names, menu text, signs or packaging lettering in any image; names live in HTML/CSS.
5. **Labels:** food "Proposed presentation, not cooked or tested"; beer "Not brewed yet, style-based concept visualization"; glass "Concept glassware, manufacturing unverified".
6. **Blocked:** Chaat Elote (Indian chaat reference open), Tandoori Lamb Taco (lamb cut), the working-name beers (no defined style).
