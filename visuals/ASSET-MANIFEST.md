# Master Asset Manifest

**57 assets planned. All status: NOT GENERATED.** No image-generation capability exists in the authoring session; images will be produced in another system using `visuals/prompts/V2-*.md`. The 12 Foundation Set images (F01-F12) are included and marked.

Authoritative style: `visuals/VISUAL-DNA.md`. Regenerate this file and the prompts with `python3 visuals/tools/build_prompts.py`.

## Generation order
1. ARC-01, ARC-02, BRW-01 (lock the building and the Tank Cloister); approve before anything else.
2. GLS-01, GLS-02 (lock the glass). 3. BER-*, INT-01. 4. Food and kitchen. 5. Court, people, packaging, merch, details. 6. Website heroes last (they reuse the locked look).
## QA gate for each image
Six tanks in a horseshoe; one marigold band; charcoal cones; terrazzo floor; collar on glass; black stoneware on food; no brass/terracotta; anatomy and glass geometry correct; no readable fake text; label as concept visual.

| ID | Category | Subject | Purpose | Aspect | Camera/lens feel | Lighting | Continuity requirements | Prompt file | Status | Foundation |
|---|---|---|---|---|---|---|---|---|---|---|
| ARC-01 | ARCHITECTURE | Exterior, day | Establish the building for all later images | 3:2 | 24mm tilt-shift feel, eye level, vertical lines straight | Hard midday Texas sun, deep crisp shadows, dusty blue sky | HALL | V2-01-architecture.md | NOT GENERATED | F01 |
| ARC-02 | ARCHITECTURE | Exterior, night | Night hero and website exterior | 3:2 | 24mm, tripod long exposure feel | Blue hour into night: indigo sky, warm amber glow from inside, tanks softly uplit, wet pavement reflections | HALL | V2-01-architecture.md | NOT GENERATED | F02 |
| ARC-03 | ARCHITECTURE | Roadside approach, dusk | Roadside visibility and sign context | 16:9 | 35mm from a two-lane Texas road, slightly low | Dusk, last light, car headlights streaking, hall glowing | HALL | V2-01-architecture.md | NOT GENERATED |  |
| ARC-04 | ARCHITECTURE | Entrance threshold | The moment of first sight: 'they make beer here' | 4:5 | 28mm, eye level, vertical composition | Shaded threshold with warm interior glow beyond | HALL, FLOOR | V2-01-architecture.md | NOT GENERATED |  |
| ARC-05 | ARCHITECTURE | Aerial site view | Site massing and flow | 16:9 | Drone-style, 60 m altitude, 24mm | Late-afternoon sun with long shadows | HALL, COURT | V2-01-architecture.md | NOT GENERATED |  |
| BRW-01 | BREWHOUSE | Tank Hall wide | The 'holy shit, they make it all here' image | 3:2 | 24mm, from the entrance looking down the horseshoe | Warm 2300K low light, tanks softly uplit, subtle daylight from north clerestory | HALL, FLOOR | V2-02-brewhouse.md | NOT GENERATED | F03 |
| BRW-02 | BREWHOUSE | Mezzanine looking down | Show guests watching brewing | 4:5 | 28mm, high angle over the glass rail | Warm uplight from the tanks below | HALL | V2-02-brewhouse.md | NOT GENERATED |  |
| BRW-03 | BREWHOUSE | Brew deck | Authenticity of the hot side | 3:2 | 35mm, eye level on the deck | Warm practical lights, steam backlit | HALL | V2-02-brewhouse.md | NOT GENERATED |  |
| BRW-04 | BREWHOUSE | Fermenter detail | Icon detail used across the site and merch | 4:5 | 85mm macro, shallow depth | Soft warm sidelight, condensation highlights | HALL | V2-02-brewhouse.md | NOT GENERATED |  |
| BRW-05 | BREWHOUSE | Brewer sampling | Craft credibility | 3:2 | 85mm, over-the-shoulder | Warm side light, tank blurred behind | HALL, GLASS | V2-02-brewhouse.md | NOT GENERATED |  |
| BRW-06 | BREWHOUSE | Mill room | Operational honesty | 3:2 | 28mm, eye level | Bright utilitarian work light plus warm window | HALL | V2-02-brewhouse.md | NOT GENERATED |  |
| ING-01 | INGREDIENTS | Grain and hops | Ingredient story | 1:1 | Top-down 50mm flat lay | Soft window light from the left | TABLE | V2-03-ingredients.md | NOT GENERATED |  |
| ING-02 | INGREDIENTS | Masa and chiles | Masa and chile story | 1:1 | Top-down 50mm flat lay | Soft window light from the left | TABLE | V2-03-ingredients.md | NOT GENERATED |  |
| ING-03 | INGREDIENTS | Fruit, spice and marigold | The crossing: mango, tamarind, marigold | 1:1 | Top-down 50mm flat lay | Soft window light from the left | TABLE | V2-03-ingredients.md | NOT GENERATED |  |
| BER-01 | BEER | Hefeweizen hero pour | Hero beer image | 4:5 | 100mm macro, f/3.2, slightly low angle | Window backlight with warm bokeh, rim light on the glass | GLASS, BAR | V2-04-beer-glassware.md | NOT GENERATED | F05 |
| BER-02 | BEER | Two-pour ritual | Ritual storytelling | 3:2 | 50mm, over-the-shoulder | Warm table light with window fill | GLASS, TABLE, PEOPLE | V2-04-beer-glassware.md | NOT GENERATED |  |
| BER-03 | BEER | Five-beer lineup | Portfolio overview | 16:9 | 50mm, eye level along the bar | Warm bar light, tanks glowing through glass behind | GLASS, BAR | V2-04-beer-glassware.md | NOT GENERATED |  |
| BER-04 | BEER | Beer flight | Flight system | 3:2 | 50mm, 30-degree angle | Warm window light with soft shadows | GLASS, TABLE | V2-04-beer-glassware.md | NOT GENERATED | F11 |
| BER-05 | BEER | Dark beer in goblet | Reserve series look | 4:5 | 85mm, low angle | Warm candle-like side light | GLASS, TABLE | V2-04-beer-glassware.md | NOT GENERATED |  |
| GLS-01 | GLASSWARE | Hero glass, empty | Hero glass identity | 4:5 | 100mm product macro, straight on | Soft raking light revealing the ring collar, dark gradient background | GLASS | V2-04-beer-glassware.md | NOT GENERATED | F06 |
| GLS-02 | GLASSWARE | Glass family | The system | 3:2 | 70mm product shot | Soft raking light | GLASS | V2-04-beer-glassware.md | NOT GENERATED |  |
| GLS-03 | GLASSWARE | Collar detail | Detail for merch and web | 1:1 | Macro 105mm | Backlit with warm edge light | GLASS | V2-04-beer-glassware.md | NOT GENERATED |  |
| FOD-01 | FOOD | Chicken 65 totopos | Signature | 4:5 | 100mm, 45-degree angle | Side window light with soft shadow, warm | TABLE | V2-05-food-kitchen.md | NOT GENERATED | F07 |
| FOD-02 | FOOD | Dum goat birria | Signature | 4:5 | 100mm, 45-degree angle | Side window light, steam visible | TABLE | V2-05-food-kitchen.md | NOT GENERATED | F08 |
| FOD-03 | FOOD | Butter chicken rajas quesadilla | Signature | 4:5 | 100mm, 35-degree angle | Warm side light | TABLE | V2-05-food-kitchen.md | NOT GENERATED | F09 |
| FOD-04 | FOOD | Gobi taco | Vegetarian signature | 4:5 | 100mm, 45-degree angle | Side window light | TABLE | V2-05-food-kitchen.md | NOT GENERATED | F10 |
| FOD-05 | FOOD | Paneer tikka taco | Vegetarian signature | 4:5 | 100mm, 45-degree angle | Side window light | TABLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| FOD-06 | FOOD | Malabar fish taco | Signature | 4:5 | 100mm, 45-degree angle | Side window light | TABLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| FOD-07 | FOOD | Mole-Salan bowl | Vegetarian signature (salan x mole) | 4:5 | 100mm, overhead | Soft window light | TABLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| FOD-08 | FOOD | Hefe-brined wings | Beer-and-food tie | 3:2 | 85mm, 45-degree angle | Warm side light | TABLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| FOD-09 | FOOD | Shared table spread | Beer and food together | 16:9 | 35mm, high angle, overhead 45-degree | Warm evening light | TABLE, GLASS, PEOPLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| KIT-01 | KITCHEN | Open kitchen and fire | Fire and authenticity | 3:2 | 35mm, eye level | Warm flame glow, tandoor mouth and comal visible | TABLE, PEOPLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| KIT-02 | KITCHEN | Masa station | Handmade tortillas | 4:5 | 85mm, over the shoulder | Soft warm light | PEOPLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| KIT-03 | KITCHEN | Pizza oven | Pizza program | 3:2 | 50mm, eye level | Warm oven glow | TABLE, PEOPLE | V2-05-food-kitchen.md | NOT GENERATED |  |
| INT-01 | INTERIOR | Main bar | Hero interior | 3:2 | 28mm, eye level along the bar | Warm low light, tanks glowing through the glass behind | BAR, FLOOR, GLASS, HALL | V2-06-interior-courtyard-night.md | NOT GENERATED | F04 |
| INT-02 | INTERIOR | Tap wall | Tap handle language | 4:5 | 50mm, slightly low | Warm shielded lights | BAR, GLASS | V2-06-interior-courtyard-night.md | NOT GENERATED |  |
| INT-03 | INTERIOR | Dining room | Dining atmosphere | 3:2 | 24mm, eye level | Warm 2300K practical lights, glass wall to the tank hall | FLOOR, TABLE, HALL, PEOPLE | V2-06-interior-courtyard-night.md | NOT GENERATED |  |
| CRT-01 | COURTYARD | Court at night | Night experience hero | 3:2 | 24mm, eye level under the arcade | Indigo dusk sky, warm lanterns on columns, tanks glowing in the glass hall beyond | COURT, HALL, PEOPLE | V2-06-interior-courtyard-night.md | NOT GENERATED | F12 |
| CRT-02 | COURTYARD | Court by day, families | Family daytime and heat management | 3:2 | 28mm, eye level | Hard sun outside the arcade, deep soft shade inside | COURT, PEOPLE | V2-06-interior-courtyard-night.md | NOT GENERATED |  |
| CRT-03 | COURTYARD | Live music on the stage | Music program | 3:2 | 35mm, from the crowd side | Warm stage light, indigo dusk | COURT, PEOPLE | V2-06-interior-courtyard-night.md | NOT GENERATED |  |
| CRT-04 | COURTYARD | Thunderstorm in the court | Rain protection story | 3:2 | 28mm, eye level under the arcade | Dark storm sky, warm interior light, rain streaks lit by the lamps | COURT, PEOPLE | V2-06-interior-courtyard-night.md | NOT GENERATED |  |
| NGT-01 | NIGHT | Bar at night | Night atmosphere | 3:2 | 35mm, eye level | Low amber light, tanks lit through the glass | BAR, HALL, PEOPLE, GLASS | V2-06-interior-courtyard-night.md | NOT GENERATED |  |
| PPL-01 | PEOPLE | Friends at the table | Broad-appeal social image | 3:2 | 50mm, shallow depth | Warm evening light | TABLE, GLASS, PEOPLE | V2-07-people.md | NOT GENERATED |  |
| PPL-02 | PEOPLE | Couple at the bar | Date night | 4:5 | 85mm, shallow depth | Warm bar light | BAR, GLASS, PEOPLE | V2-07-people.md | NOT GENERATED |  |
| PPL-03 | PEOPLE | Brewer and guest | Hospitality and education | 3:2 | 50mm, shallow depth | Soft window light | HALL, GLASS, PEOPLE | V2-07-people.md | NOT GENERATED |  |
| PKG-01 | PACKAGING | Can lineup | Packaging system | 3:2 | 70mm product shot | Soft raking light | CANS | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| PKG-02 | PACKAGING | Tap handles | Tap handle language | 4:5 | 85mm macro | Warm side light | BAR | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| PKG-03 | PACKAGING | Retail shelf | National shelf presence | 3:2 | 35mm eye level | Cool retail cooler light | CANS | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| MER-01 | MERCHANDISE | Apparel | Merchandise | 3:2 | 50mm, flat lay | Soft window light | TABLE | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| MER-02 | MERCHANDISE | Glass gift set | 'I want one of those glasses' | 4:5 | 85mm | Warm window light | GLASS | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| DTL-01 | DETAILS | Bar tile and rail | Material identity | 1:1 | 85mm macro | Warm side light | BAR | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| DTL-02 | DETAILS | Terrazzo and tank base | Material identity | 4:5 | 50mm low angle | Warm uplight | HALL, FLOOR | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| DTL-03 | DETAILS | Hands tearing naan into consommé | Cross-cultural gesture | 1:1 | 85mm | Warm side light, steam | TABLE | V2-08-packaging-merch-details.md | NOT GENERATED |  |
| WEB-01 | WEBSITE HERO | Tank hall glow, ultra-wide | Opening sequence | 21:9 | 24mm, symmetrical, static | Pitch dark surroundings, the six tanks warmly lit, faint steam from the deck | HALL, FLOOR | V2-09-website-heroes.md | NOT GENERATED |  |
| WEB-02 | WEBSITE HERO | Foam rising, macro | Pour animation frame | 16:9 | 100mm macro, tripod | Backlit, black background | GLASS | V2-09-website-heroes.md | NOT GENERATED |  |
| WEB-03 | WEBSITE HERO | Fire and hands | Fire section | 16:9 | 85mm | Dark kitchen, tandoor glow | TABLE, PEOPLE | V2-09-website-heroes.md | NOT GENERATED |  |
| WEB-04 | WEBSITE HERO | Court at dusk, ultra-wide | Closing sequence | 21:9 | 24mm, static | Last blue light, warm lanterns | COURT, HALL | V2-09-website-heroes.md | NOT GENERATED |  |

## Count by category

- ARCHITECTURE: 5
- BREWHOUSE: 6
- INGREDIENTS: 3
- BEER: 5
- GLASSWARE: 3
- FOOD: 9
- KITCHEN: 3
- INTERIOR: 3
- COURTYARD: 4
- NIGHT: 1
- PEOPLE: 3
- PACKAGING: 3
- MERCHANDISE: 2
- DETAILS: 3
- WEBSITE HERO: 4