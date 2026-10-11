# NASHA: Food and Beer Visual Reference Library

**Status:** `[DESIGN]` internal research framework for **PHOTOREALISTIC CONCEPT VISUALIZATION** of food and beer that do not yet exist. These are **development visuals, not evidence** and never "NASHA food photography". Reference photographs are **not** stored, copied or published here. Dish and beer names are the canonical names in `website/data/dishes.json` and `website/data/beers.json`; none was renamed.

## 1. The truth rule
Before any food or beer image is accepted, answer:
- **Food:** *Could a competent NASHA kitchen plausibly produce something substantially like this?*
- **Beer:** *Could a qualified brewer plausibly pour a beer of this style that substantially resembles this liquid?*
If not, **REJECT**. The future product sets the visual truth; the render does not. Visual appearance never proves recipe correctness. Real photography replaces concept images once T1 cooking and pilot brewing produce real product (generated concept → prototype dish → recipe revision → actual plating → professional photograph).

## 2. Current state (honest)
- **No photoreal food or beer image exists in the project.** This session has no image generator, and none was faked. The website therefore shows **drawn concept illustrations** of proposed presentation, informed by the references below. They are diagrams of plausible plating, not photographs. Photoreal generation is queued in `visuals/nasha-v3/PROMPT-PACK.md` with the realism rules in §5.
- References were gathered by **web search summaries (tier T1)** and the repository's own benchmark documents. Primary pages were not opened (`research/VERIFICATION-LEDGER.md` V-35..V-37). Reference **photographs were not downloaded or reused**; rights/use status for every reference is "research only; do not publish".

## 3. Dish reference table (signature set)
Classification words follow `dishes.json` (`Fusion`, `Our own dish`, `Inspired by`). Never write "a traditional Indian-Mexican dish".

| Dish (canonical) | Class | Indian reference | Mexican reference | Ingredient appearance to respect | Cooking / service characteristics | NASHA interpretation (plausible) | Source / tier | Reference rights |
|---|---|---|---|---|---|---|---|---|
| **Chicken 65 Totopos** | Fusion | Chennai-style Chicken 65: bite-size boneless chicken, deep-fried, red-orange chile-yoghurt coating, curry leaf and green chile garnish | Totopos: thick, irregular, hand-cut-looking corn masa chips, cooked in oil, uneven edges, stack loosely | Chicken pieces about 2-3 cm, crisp but not breaded-white; coating dark red-orange with sheen; chips thicker and more rustic than supermarket chips; a few curry leaves and slices of green chile | Fried to order; served immediately on a shared dish; raita-crema in a small katori; chips scoop rather than stack neatly | Mound of chicken beside, not buried under, a fan of totopos; crema in a small stainless bowl; lime wedge; restrained garnish | Repo dish spec; general culinary knowledge (T4) | Research only |
| **Paneer Tikka Taco** | Fusion | Paneer tikka: cubes of paneer marinated in yoghurt and spices, grilled with charred edges, onion and pepper pieces | Street taco: small corn tortilla(s), folded, modest filling, cilantro/onion, salsa on the side | Paneer stays pale cream with brown-black char marks and a red-orange marinade film; cubes keep their square structure; onion/pepper show char | Tortilla about 12-15 cm, warm and folded; 2-3 pieces per taco; green salsa and lime on the side | Two tacos, a few paneer cubes visible, thin red onion, cilantro, small salsa pool | Repo dish spec (T4) | Research only |
| **Gobi Taco** | Fusion | Gobi (cauliflower) fry or roast: florets with browned tips, spice coating | Fried or roasted vegetable tacos with lime slaw | Cauliflower keeps floret structure (not like fried chicken); golden-brown with darker tips; glaze glossy but not drowning | Two tacos on a plate; slaw is pale, thin shreds | Crisp spiced florets with tamarind-chile glaze, lime slaw, corn tortilla | Repo dish spec (T4) | Research only |
| **Butter Chicken & Roasted Poblano Quesadilla** | Fusion | Butter chicken (murgh makhani): orange-red, smooth, creamy tomato-butter sauce with chicken pieces | Quesadilla with rajas (roasted poblano strips) and melting cheese in a griddled flour tortilla | Sauce is an orange-red, not neon; chicken in modest pieces; poblano strips deep green with char; cheese melts and strings at the cut edge; tortilla blistered golden-brown, not burnt | Cut into 4-6 wedges; dip in a small bowl; griddle marks | Griddled flour quesadilla in wedges, visible cheese and green strips at the cut, butter-chicken dip alongside | Repo dish spec (T4) | Research only |
| **Goat Birria, Sealed-Pot Braise** | Inspired by | Dum-style sealed-pot slow cooking | Birria: slow-braised meat in a chile adobo, shredded, served in griddled red-tinged tacos with a cup of consommé | **Goat, not beef** (D-54): darker, leaner, stringier shreds than beef; brick-red adobo; orange fat sheen on the consommé; tortillas dipped and griddled, with crisp, lightly oily edges; chopped onion, cilantro, lime | Tacos folded and griddled; consommé in a cup for dipping; modest garnish | Three small red-tinged tacos, shredded goat visible, consommé cup with fat sheen, onion-cilantro and lime | Repo dish spec (T4) | Research only |
| **Chaat Elote** | Fusion | Chaat: crunchy, tangy, spiced street snack (sev, chutneys, chaat masala) | Elote / esquites: charred corn with crema, cotija, chile, lime | Charred, irregular kernels; crema/raita drizzle (not a flood); chaat masala dusting; a few crisp elements | Served in a cup or on the cob; eaten by hand | Charred corn (cup or cob), restrained crema-raita, cotija-style cheese, chaat masala, light crunch | Repo dish spec (T4) | Research only |
| **Cardamom Churros** | Fusion | Cardamom as a dessert spice | Churros: ridged star-shaped extruded dough, fried, rolled in sugar; chocolate dip | Distinct ridges; golden-brown with darker lines; sugar crust; soft, slightly hollow interior | 4-6 pieces; dark jaggery-chocolate sauce in a small bowl | Ridged churros dusted with cardamom sugar; dip alongside | Repo dish spec (T4) | Research only |
| *Tandoori Lamb Taco (conditional)* | Our own dish | Tandoori marinated lamb | Grilled-meat tacos | **Lamb cut is unresolved**; do not imply a cut or tenderness | Show only after the lamb-cut decision; keep the unresolved status visible | No image yet | Repo (open question) | n/a |

## 4. Beer visual specifications
Canonical names and styles from `beers.json`. Colours in the website drawings follow these ranges. **No ABV, IBU, recipe, ingredient list, award or availability is stated** unless the repository holds it; working names keep their `WORKING NAME` status.

| Beer (canonical) | Style (as in repo) | Expected colour | Clarity / haze | Head | Carbonation look | Glass | Source / tier |
|---|---|---|---|---|---|---|---|
| **Hefeweizen** (gate beer) | Bavarian-style wheat beer | Pale straw to gold (repo benchmark SRM 2-6) | Cloudy-hazy, glowing; not brilliant | Very thick, moussy, long-lasting **white** head; not whipped-cream stiff | Fine, steady rise, visible in a tall vase | Tall weizen vase (Collar Weizen concept, GLS-01) | BJCP 10A, V-36 (T1); `beer/HEFEWEIZEN-BENCHMARK.md` |
| **Mexican-Style Lager** | Pale lager | Pale to deep gold | **Clear, no chill haze** | White, medium, fades to a lacing ring | Fine bubbles | Tall conical lager (Collar Lager concept) | BA via mirror, V-37 (T1); `beer/OPENING-BEER-PROGRAM-V1.md` |
| **Vienna Amber** | Vienna-style lager | Light reddish amber to copper (SRM 9-15, mirror) | Bright, clear | Large, **off-white**, persistent | Fine | Collar Lager concept | BJCP 7A, V-35 (T1) |
| **Pilsner** | German-style pilsner | Pale yellow to light gold | Brilliant | Dense white | Fine, steady | Tall pilsner/lager glass | General style knowledge (T4); verify against BJCP before generation |
| **Witbier** | Belgian-style wheat beer | Very pale straw to light gold | Very hazy, milky | Dense white | Fine | Collar Weizen concept (or a plain tumbler) | General style knowledge (T4); verify |
| **Dunkelweizen** | Dark wheat beer | Light copper to mahogany brown (SRM 14-23) | Hazy to dark clear | Thick, creamy, tan | Fine | Collar Weizen concept | BJCP Dunkles Weissbier, V-36 (T1) |
| **Deccan Sol** *(WORKING NAME)* | Wheat lager, R&D idea | **Not specified**: style not settled | n/a | n/a | n/a | n/a | Repo marks it a pilot idea; **no colour invented** |
| **Goa Baja** *(WORKING NAME)* | Coastal lager, pilot idea | **Not specified** | n/a | n/a | n/a | n/a | Same |
| **Malabar Dark** *(WORKING NAME)* | Dark wheat with pepper, pilot idea | **Not specified** | n/a | n/a | n/a | n/a | Same |

Working-name beers are drawn as a **faint outline glass**, never as a coloured beer. Serving guidance: no lime on the Mexican-Style Lager unless a future service concept specifically calls for it.

## 5. Realism checklist and rejection criteria (food and beer images)
**Food - reject if:** impossible ingredient geometry; plastic or lacquered food; excessive garnish or sauce; giant portions; floating or duplicated ingredients; fake text; impossible utensils; malformed plates; beef or pork (D-54); goat birria that reads as beef; cauliflower that reads as fried chicken; "Michelin" over-styling for an approachable concept; unrealistic steam; tortillas that cannot fold.
**Beer - reject if:** foam like whipped cream; floating bubbles; malformed rims; liquid outside the glass; impossible reflections or liquid levels; duplicated glasses; nonsensical tap handles; unreadable fake labels; all beers the same liquid; an IPA-looking Hefeweizen; wrong-colour Vienna; lime added by default.
**Both:** NASHA tableware (matte black stoneware, stainless katori, thali trays; `VISUAL-DNA.md` rule 8) and NASHA environment (warm practical light), no real people, no readable text except an approved placeholder.

## 6. Use status
References are for research. No reference photograph is stored, copied or published. Every concept image made from these specs is labelled **Concept visualization** (photographic style) or **Concept illustration** (drawn), and is replaced by real photography after T1 cooking and pilot brewing.
