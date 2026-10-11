# NASHA Visual Direction v3 (Sprint 7)

**Status:** `[DESIGN]` direction for how NASHA looks, from the founder's Sprint 7 brief. Name status: `SELECTED_BY_FOUNDER — LEGAL CLEARANCE PENDING` (D-62). **Logo status: none designed; all NASHA lettering in images and on the site is a temporary typographic placeholder, `CONCEPT — NOT OFFICIAL`** (`brand/NASHA-LOGO-GOVERNANCE.md`). Everything depicted is a concept; NASHA does not exist.

## 1. The idea: 100% NASHA
Not half an Indian restaurant plus half a Mexican one. India and Mexico show up as **materials, geometry, fire and hospitality** inside one calm, warm, social place. The brand should be recognisable before the name is read, but **no mark is created or fixed by this document**.

## 2. Reconciling with the locked Visual DNA (conflict recorded, D-65)
`VISUAL-DNA.md` v2 (Oct 2026) forbids brass fixtures, terracotta walls and mosaic-pattern tile ("avoid the generic terracotta + brass + geometric tile look"), and treats India/Mexico links as unverified design rationale. The founder's Sprint 7 brief **asks to explore** terracotta, brass, jali-inspired light and shadow, tile and woven rhythm. Resolution adopted:
- **Keep locked:** the canonical day exterior (`NV-SPACE-EXT-DAY`), limestone and glass hall, timber arcade, **perforated dark screens (already jali-like)**, marigold as the one saturated accent, warm 2200-2400K light, black stoneware tableware, the collar glass.
- **Allowed to explore (as restrained accents, not walls of pattern):** terracotta and clay as small-scale material (planters, a tandoor face, tableware accents), brass as small hardware or a tap tower detail, handmade tile in **few colours** at the bar front, jali-like **light and shadow** cast through the screens, textile rhythm in napkins and aprons. Brass and terracotta are **never a wall, a ceiling or a theme**.
- **Stays out:** Taj Mahal, elephants, Bollywood caricature, mandalas, religious imagery as decoration, sombreros, moustaches, cartoon cactus, Day of the Dead imagery, generic cantina or fiesta décor.
This supersedes the material prohibition **for expansion imagery only**. Earlier images were made under the older rule and stay valid as concept art.

## 3. The Crossing as visual moments (design, not history)
Terracotta against volcanic stone; screen-shadow on a courtyard floor; brass beside clay; tandoor fire beside comal fire; textile geometry beside tile geometry; spice tones beside agave-landscape tones; communal tables for both hospitality traditions. **No image or caption claims shared history**; the site marks each Crossing theme Supported / Analogy / Unresolved.

## 4. Austin
Indoor-outdoor flow, a generous shaded patio, native grasses and live oaks, warm evening light, ceiling fans where plausible, casual sophistication, limestone and cedar, selective industrial craft, bikes and neighbourhood life. **No fake address, no site implied, no Austin landmarks** that would claim a location.

## 5. NASHA photography language
Warm practical light; shallow depth only where it helps; rich texture; steam only where physically plausible; condensation on cold glass; hands sharing; beer pouring; fire; movement; night. Avoid perfect centred product renders, orange-teal grading, heavy haze, empty perfect spaces, repeated faces, fake text. People: natural, diverse, candid, unnamed, never identifiable real individuals; families where the setting suits.

## 6. Concept labelling (elegant, honest)
Every picture carries a small tag in its corner: **Concept visualization** (photographic-style, AI-made) or **Concept illustration** (drawn), with a fuller screen-reader sentence, a site-wide explanation (footer, `about.html#images`), and the Space page note "Concept visualization. Final architecture is subject to professional design and site conditions." No stamps over the picture. Food and beer drawings are also tagged "Proposed presentation" / "Not brewed yet". Pairings are "Proposed pairing, not sensory-tested".

## 7. Motion rules
Motion must communicate **heat** (flame flicker), **pour/fermentation** (rising bubbles), **gathering** (reveal as sections arrive) or **transition** (Two-Pour steps, beer colour change). All of it is disabled or static under `prefers-reduced-motion`, and the page is fully understandable without it. No parallax beyond a slow hero reveal.

## 8. Mobile and performance
Every raster has a **desktop composition and a separate mobile (4:5) composition** with a focal point (`NASHA-VISUAL-MANIFEST.csv`: `src_crop`, `mobile_ar`, `mobile_focus_x`), alt text, dimensions, `loading="lazy"` except the preloaded hero, AVIF + WebP + JPEG fallback, and widths 480-1920. Budgets are enforced by `tools/validate_site.py` and measured by `website/qa/run-qa.mjs`.

## 9. Visual QA gate (before any image is integrated)
Brand consistency; cultural sensitivity; food plausibility; beer plausibility (`NASHA-FOOD-BEER-REFERENCE-LIBRARY.md` §1, §5); architectural plausibility (no impossible fantasy; **equipment size and count never fixed**, G-6); rights status; mobile and desktop crop; alt text; file size; concept label. **Austin test:** would this make an Austin guest curious enough to visit if it existed?

## 10. What no image may do
Imply a built place, a site, an opening date, real guests, real food, a brewed beer, ABV or awards, a final logo, or social proof.

## 11. Reality-first food and beer pipeline (Sprint 8)
References (India, Mexico, beer-style) → NASHA concept → photoreal concept visualization → kitchen or brewery prototype → revision → final product → real professional photography. Full rules, the two-source fusion table, hero and truth views, the glass family and the three-yes test are in `NASHA-FOOD-BEER-REFERENCE-LIBRARY.md` §7-§12. Names never appear inside generated images.

**Marigold note (cultural audit, Sprint 9):** marigold is used as a **colour only**, never as ritual-flower imagery and never as a claim of shared tradition (cempasuchil/genda carry ritual meaning in both cultures).
