# 14-15. Glassware and Serving Rituals

> HISTORICAL: see phase-one/00 banner; research/, food/, beer/ and docs/decisions/ now govern.

## Why traditional glass works (`[UNCITED]`, verify with manufacturer and brewing sources)
- **Weizen vase:** tall, tapered, wide top: holds foam, shows haze, leaves room for the large head wheat beer makes.
- **Pilsner flute:** shows clarity and bubbles; narrow keeps carbonation.
- **Teku / tulip:** flared lip with bowl concentrates aroma; good for IPAs and Belgian ales.
- **Mug / stein:** thick, insulated, durable; the hand-feel glass for lager.
- **Goblet:** wide for sipping strong ales.

## Design requirements
Improve aroma and foam, comfortable in the hand, dishwasher-safe, stackable where possible, manufacturable at scale, photogenic, merchandisable, not novelty. Avoid decoration that traps cleaning residue (foam needs clean glass). Any etched or textured nucleation point must be tested for foam behavior `[TEST]`.

## 10 concepts
| # | Name | Form | Cultural reference (principle, not decoration) | Use | Notes |
|---|---|---|---|---|---|
| G1 ★ | **The Tall Court** | Weizen vase with a faceted lower third (hexagonal/jaali-like geometry) transitioning to smooth top | Indian lattice geometry + Mexican faceted blown glass | Hefeweizen | Facets add grip and light play. Risk: foam interactions and cleaning |
| G2 | **Comal Mug** | Heavy-base cylinder mug with a wide, shallow band | Griddle/clay vessels | Lager | Durable |
| G3 ★ | **Agave Tulip** | Tulip with a faceted, leaf-like flare | Agave leaf geometry | IPAs, aromatics | Ties to Mexico; stable |
| G4 | **Brass-banded Pilsner** | Standard pilsner flute with a thin brass base ring | Indian metalwork | Pilsner | Brass and dishwashers: test |
| G5 ★ | **Stepwell Goblet** | Stepped bowl, like a stepwell's descending stairs | Rajasthan stepwells | Reserve beers | Visual metaphor; hand feel |
| G6 | **Tumbler / Kullhad hybrid** | Thick-walled tumbler with matte exterior | Clay kullhad cups | Witbier | Lower value perception |
| G7 | **Talavera Stein** | Ceramic stein with tile-glaze | Puebla tile | Merch only | Not good for beer visual |
| G8 | **Mini Flight Glass** | 4 oz tulip with embossed base | | Flights | Practicality |
| G9 | **Totem Pilsner** | Narrow stemmed pilsner | Mexican blown glass | Lagers | Manufacturing risk |
| G10 | **Solid Brass Mug** | Metal | | Gift | Beer in metal is not visible; reject for service |

**Selected: G1 The Tall Court (Hefeweizen), G3 Agave Tulip (aromatic beers), G5 Stepwell Goblet (reserve).** Next: sketches, 3D model, manufacturer quotes (Rastal, Spiegelau, Libbey, Stölzle, Mexican glass producers), MOQ and breakage rates `[PRO]` product engineer.

## 5 serving rituals (beer first)
1. **The Two-Pour Hefe:** Server pours 85% tableside at an angle, lets it settle, then swirls the yeast from the bottle/can and completes the pour. Authentic, simple, improves the beer.
2. **The Courtyard Flight:** Four 4 oz glasses on a long wooden board, laser-cut with a lattice window under each glass; a small card gives region, ingredient, ABV/IBU.
3. **The Garnish on the Side:** For lime/orange/pepper-aromatics, a small ceramic dish of fresh aromatic (orange peel, curry leaf) the guest chooses. Never forced.
4. **The Pairing Trio:** One beer + two bites, presented on a single tile. Regional pairing is named on the card (e.g., Telangana × Jalisco).
5. **The Glass Pass:** First-time guests are offered the opportunity to buy their glass at the end of the visit. Merchandising, not theater.

Rejected: smoke domes, dry ice, flaming rims, beer cocktails with drama (any hazard or taste damage).
