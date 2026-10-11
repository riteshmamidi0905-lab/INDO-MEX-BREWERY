# NASHA Prompt Pack (Sprint 7)

**Status:** `[PLAN]` prompts only. **Nothing here has been generated** (this session has no image generator). Run in an external tool **only after the founder has checked that tool's commercial-use terms**, and never upload any approved master logo to a third-party generator (`brand/NASHA-LOGO-GOVERNANCE.md`). Keep every output `CONCEPT — NOT OFFICIAL` and `PHOTOREALISTIC CONCEPT VISUALIZATION` (never "real NASHA photography"). Log each run in `visuals/generated/LOG.md` (tool, model, date, prompt, seed if exposed) and the manifest.

## Shared base (prepend to every prompt)
> Photorealistic hospitality photography of a future Indo-Mex brewery and kitchen in Austin, Texas. Warm practical light (2200-2400K), natural textures, restrained styling, approachable not luxury. India and Mexico appear through materials, fire, geometry and tableware, not costume or cliche. Matte black stoneware plates with raw rim, stainless katori, pecan tables, limestone and glass. **No text, no logos, no readable signage, no prices, no real people or celebrities. No beef or pork. No orange-teal grade, no heavy haze, no floating ingredients, no impossible architecture.** Natural proportions of food, glass and beer exactly as they would exist in a working kitchen and bar.

## Logo and lettering rule (D-66, absolute)
Never ask the generator to render NASHA text, a logo, icon, monogram, symbol or lockup, and never upload any NASHA artwork. Every sign in a prompt is **blank** ("a blank dark monument sign", "a blank fascia"). The temporary typographic NASHA placeholder, where needed, is added **afterwards by deterministic script** (`website/tools/make_sources.py`). Reject any output with generator-made lettering.

## Batch A continuity bible (use in every Batch A prompt so it is the SAME restaurant)
Limestone walls and pale Texas limestone plinth; black-framed floor-to-ceiling glass; cedar and pecan timber; dark perforated blackened-steel screens with a regular grid of round holes (jali-like light and shadow); long pecan bar with a front of square handmade matte tiles in bone and marigold; blackened steel shelving and rails; speckled terrazzo floor; matte black stoneware; thali trays and stainless katori; indigo-and-bone linen; warm 2200-2400K practical light; collar glassware. Landscape: live oak, native grasses, gravel, limestone. **Brewery rule (G-6): show the brewery only partially, through glass partitions, in perspective or cropped; never a full row of tanks, never a countable set, no capacity, no layout.** No NASHA text, no logos, blank signage. People are synthetic, candid, diverse, mid-activity, not looking at the camera.

## Reality-first rules for food and beer (Sprint 8, mandatory)
- **Never** prompt with only "Indian-Mexican X". Each food prompt below states the INDIA reference, the MEXICO reference and the NASHA transformation; read `NASHA-FOOD-BEER-REFERENCE-LIBRARY.md` §7 first and pass its three-yes test.
- **Two views per dish:** a HERO view (45-degree editorial restaurant photograph) and a TRUTH view (top-down or slightly elevated, exactly what is on the plate). Generate several plating candidates for the hero dish and log the scoring.
- **No text anywhere in the image:** no dish names, beer names, labels, menu or sign lettering. Add names in HTML/CSS.
- Beer: research the style first (reference library §4), use the matching NASHA collar glass (§10), no invented beer, never the working-name beers.
- Reference photographs are research only: never copy, trace, publish or imply affiliation.

## Realism rules
Follow `visuals/NASHA-FOOD-BEER-REFERENCE-LIBRARY.md` §3-§5 for every dish and beer. **Reject** any output that fails the two truth questions. Tank size and count are undecided (G-6): do not depict a number or scale as final.

## Ingest steps
1. Save the chosen file under `visuals/web-source/<NV-ID>.webp` (do not overwrite an existing source).
2. In `visuals/NASHA-VISUAL-MANIFEST.csv` set `source_file`, `kind` to `raster`, `src_crop`, `mobile_ar`, `mobile_focus_x`, `status` to `INTEGRATED-PROVISIONAL`, real `alt_text`, creation method/tool/date/prompt, and honest rights notes.
3. `python3 website/build.py && cd website/qa && node run-qa.mjs && cd ../.. && python3 tools/validate_repo.py`.

## EXT-BLUEHOUR
**Manifest ID:** `NV-PLAN-EXT-BLUEHOUR` · **Priority:** P1 · **Page:** index.html

Exterior of a contemporary Austin Hill-Country-style limestone and glass brewery-restaurant at blue hour, long covered timber arcade with dark perforated screens casting jali-like light patterns, generous patio with long communal tables and a live oak, warm interior glow, glimpses of stainless fermentation tanks behind glass (do not state a number or size), a BLANK dark fascia and a BLANK monument sign (no lettering at all), a few relaxed people, no address, no street signs.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## ENTRANCE
**Manifest ID:** `NV-PLAN-ENTRANCE` · **Priority:** P1 · **Page:** space.html

Eye-level approach to a glass entrance door at dusk, limestone wall, plain dark monument sign (no text), warm interior light, tanks softly visible, native grasses, two relaxed guests approaching from behind.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## INT-HERO
**Manifest ID:** `NV-PLAN-INT-HERO` · **Priority:** P1 · **Page:** experience.html; space.html

24mm interior view along a long pecan bar toward a glass wall showing stainless fermentation tanks, open kitchen with a visible tandoor mouth and a comal glow to the right, communal tables, terrazzo floor, warm 2300K practical lights, small brass tap-tower detail, plausible architecture, diverse relaxed guests.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## BAR
**Manifest ID:** `NV-PLAN-BAR` · **Priority:** P1 · **Page:** experience.html; space.html

Bar with a tap wall (matte black handles with single marigold ring), back bar of open steel shelving with collar glassware, bar front in square handmade tile in two colours (bone and marigold), dark pecan top, stools, sightline to a glass brewery.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FIRE-KITCHEN
**Manifest ID:** `NV-PLAN-FIRE-KITCHEN` · **Priority:** P1 · **Page:** experience.html; crossing.html

Cook at a clay tandoor mouth lifting a skewer, a second cook at a flat comal pressing tortillas, canvas aprons, flame glow, safe practices (hood, no loose clothing near flame), warm light, stainless and black stoneware, steam only where physically plausible.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## PATIO-EVENING
**Manifest ID:** `NV-PLAN-PATIO-EVENING` · **Priority:** P1 · **Page:** experience.html; space.html

Evening covered patio, shade structure, ceiling fans, string lights, greenery, long communal tables with plates and beer glasses, mixed friends and families, live oak, relaxed Austin atmosphere.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## DINING-HALL
**Manifest ID:** `NV-PLAN-DINING-HALL` · **Priority:** P2 · **Page:** space.html

Dining hall with long communal tables, jali-like screen shadow on limestone, plates and glasses, warm low light.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-C65
**Manifest ID:** `NV-PLAN-FOOD-C65` · **Priority:** P1 · **Page:** food.html

INDIA: authentic Chicken 65, bite-size boneless chicken with a crisp fried red-orange coating, curry leaves and sliced green chile. MEXICO: real totopos, thick sturdy irregular fried corn-masa pieces (not thin supermarket chips). NASHA: an INTEGRATED plate in which the chicken pieces sit among a loose open layer of totopos so chips stay crisp, raita-crema as a restrained drizzle or small pool, lime wedge, matte black stoneware. Two views: hero at 45 degrees with side window light, and a top-down truth view. Candidates: integrated, layered-open, side-by-side; score all.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-PANEER-TACO
**Manifest ID:** `NV-PLAN-FOOD-PANEER-TACO` · **Priority:** P1 · **Page:** food.html

Two small folded corn-tortilla tacos with charred paneer tikka cubes (cream with brown char), thin red onion, cilantro, small green salsa and lime on matte black stoneware; tortilla about 13 cm; modest filling.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-GOBI-TACO
**Manifest ID:** `NV-PLAN-FOOD-GOBI-TACO` · **Priority:** P1 · **Page:** food.html

Two corn tortilla tacos with crisp spiced cauliflower florets (floret structure, golden-brown tips, tamarind-chile glaze), pale lime slaw; must not look like fried chicken.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-BCQ
**Manifest ID:** `NV-PLAN-FOOD-BCQ` · **Priority:** P1 · **Page:** food.html

Griddled flour tortilla quesadilla cut into wedges showing melted cheese and roasted poblano strips, golden-brown blistered tortilla, a small bowl of orange-red butter-chicken dip, griddle marks.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-GOAT-BIRRIA
**Manifest ID:** `NV-PLAN-FOOD-GOAT-BIRRIA` · **Priority:** P1 · **Page:** food.html

Three small griddled red-tinged tacos with shredded GOAT meat (not beef; leaner and darker than beef), consomme in a cup with an orange fat sheen, chopped onion, cilantro, lime. No beef, no pork.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-ELOTE
**Manifest ID:** `NV-PLAN-FOOD-ELOTE` · **Priority:** P1 · **Page:** food.html

Charred corn in a cup or on the cob with restrained crema-raita drizzle, crumbled cotija-style cheese, chaat masala dusting, a few crisp bits; not chaotic.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-CHURROS
**Manifest ID:** `NV-PLAN-FOOD-CHURROS` · **Priority:** P2 · **Page:** food.html

Four to six ridged, star-shaped, sugar-dusted golden churros with a visible soft interior, small bowl of dark jaggery-chocolate sauce.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FOOD-LAMB
**Manifest ID:** `NV-PLAN-FOOD-LAMB` · **Priority:** P3 · **Page:** food.html

DO NOT GENERATE until the lamb-cut decision is made.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## BEER-HEFE
**Manifest ID:** `NV-PLAN-BEER-HEFE` · **Priority:** P1 · **Page:** beer.html

Hefeweizen in a tall weizen vase glass: hazy pale straw to gold, thick moussy white head (not whipped cream), fine steady bubbles, condensation, shallow depth on a dark wood bar. No label, no text.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## BEER-LAGER
**Manifest ID:** `NV-PLAN-BEER-LAGER` · **Priority:** P1 · **Page:** beer.html

Mexican-style pale lager: clear pale to deep gold, white medium head, fine bubbles, tall conical glass, condensation. No lime unless specified.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## BEER-VIENNA
**Manifest ID:** `NV-PLAN-BEER-VIENNA` · **Priority:** P1 · **Page:** beer.html

Vienna lager: bright, clear light reddish amber to copper, large off-white persistent head, conical lager glass, warm rim light preserving the true liquid colour.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## GLS-01
**Manifest ID:** `NV-PLAN-GLS-01` · **Priority:** P1 · **Page:** beer.html

Use the profile guides in visuals/generated/GLS-inputs. Four views: clean product, beer-filled, table-service, food-pairing. Raised ring collar one quarter up the base. Conceptual; no manufacturing claim.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## GLS-02
**Manifest ID:** `NV-PLAN-GLS-02` · **Priority:** P2 · **Page:** beer.html

Family line-up of weizen vase, conical lager and short stemmed reserve goblet with the same collar language.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## PAIR-PANEER-HEFE
**Manifest ID:** `NV-PLAN-PAIR-PANEER-HEFE` · **Priority:** P2 · **Page:** food.html; beer.html

Paneer Tikka Taco on matte black stoneware beside a Hefeweizen on a pecan table, warm evening light, Austin patio softly behind.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## PAIR-C65-LAGER
**Manifest ID:** `NV-PLAN-PAIR-C65-LAGER` · **Priority:** P2 · **Page:** food.html; beer.html

Chicken 65 Totopos beside a Mexican-style lager.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## PAIR-BIRRIA-VIENNA
**Manifest ID:** `NV-PLAN-PAIR-BIRRIA-VIENNA` · **Priority:** P2 · **Page:** food.html; beer.html

Goat birria tacos and consomme beside a Vienna amber lager.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## PAIR-ELOTE-LAGER
**Manifest ID:** `NV-PLAN-PAIR-ELOTE-LAGER` · **Priority:** P3 · **Page:** food.html; beer.html

Chaat Elote beside a pale lager (pairing from the canonical list).

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## TWO-POUR
**Manifest ID:** `NV-PLAN-TWO-POUR` · **Priority:** P2 · **Page:** beer.html

Sequence: beer one, the dish, beer two, on one table; show only the arrangement, no claim about taste.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## MENU-MOCK
**Manifest ID:** `NV-PLAN-MENU-MOCK` · **Priority:** P2 · **Page:** food.html

Printed menu mock-up, indigo cover and a spread with categories, vegetarian markers and heat dots; NO prices, no readable fake dish text beyond placeholders.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## FLIGHT-CARD
**Manifest ID:** `NV-PLAN-FLIGHT-CARD` · **Priority:** P2 · **Page:** food.html; beer.html

Four-glass tasting flight on a pecan board with a small card; beers from the canonical list; no prices.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## SIGNAGE
**Manifest ID:** `NV-PLAN-SIGNAGE` · **Priority:** P2 · **Page:** space.html

Fascia and monument sign at night. BLOCKED until a logo is founder-approved; use plain placeholder lettering only.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## MERCH
**Manifest ID:** `NV-PLAN-MERCH` · **Priority:** P3 · **Page:** about.html

Glass, can and apron mock-ups. BLOCKED until a logo is approved and cleared.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## POPUP-REAL
**Manifest ID:** `NV-PLAN-POPUP-REAL` · **Priority:** P2 · **Page:** labs.html; experience.html

One possible early form: a pop-up stand or brewery-residency bar at dusk; not a final vehicle; no event details.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## PEOPLE-TABLE
**Manifest ID:** `NV-PLAN-PEOPLE-TABLE` · **Priority:** P2 · **Page:** index.html; experience.html

Friends sharing food and beer at a long table, candid, diverse, not identifiable real people.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## AUSTIN-ATMOS
**Manifest ID:** `NV-PLAN-AUSTIN-ATMOS` · **Priority:** P2 · **Page:** index.html; space.html

Austin evening atmosphere: live oak, limestone, warm light, bikes; no landmark, no address.

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

## NIGHT-FIRE-FERMENT
**Manifest ID:** `NV-PLAN-NIGHT-FIRE-FERMENT` · **Priority:** P2 · **Page:** index.html; crossing.html

Matched diptych: flame at a tandoor and a fermentation tank with a marigold band (size not stated).

**Alt text to write at integration:** describe what is seen, then "Concept visualization."

