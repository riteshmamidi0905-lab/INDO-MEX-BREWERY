#!/usr/bin/env python3
"""Builds visuals/generation-batch-01/*.md from shared geometry constants, so ARC-01, ARC-02 and BRW-01
cannot drift apart. Run from repo root: python3 visuals/tools/build_batch01.py
Source of truth for the geometry: visuals/LOCKED-SCENE-DNA.md (keep the two in sync)."""
import os
OUT="visuals/generation-batch-01"; os.makedirs(OUT,exist_ok=True)

BUILDING = (
"THE BUILDING (one specific, consistent brewery-restaurant in Central Texas, seen from the southeast entry drive looking north-northwest): "
"On the LEFT is the Tank Hall, a double-height glass-walled brewing hall about 44 ft wide and 60 ft long and about 38 ft tall, with a flat roof behind a thin board-formed-concrete parapet. Its end wall facing the viewer (south) and its long side wall facing the courtyard (east) are fully glazed with dark-bronze (not black) aluminium framing on a regular 6-ft vertical mullion rhythm, rising from a low 2-ft honed pale Texas limestone plinth (the limestone rises to full height only on the hall's solid north and west walls), with a 10-ft projecting board-formed-concrete canopy shading the south glass. "
"To the RIGHT of the hall is the Shade Court, a climate-designed outdoor room that is open to the sky in the middle: its south edge faces the viewer as a continuous arcade 14 ft deep and about 13 ft clear, made of square, warm-grey board-formed concrete columns (about 18 in, with visible horizontal formwork lines, NOT limestone) at 15-ft spacing carrying exposed cedar elm timber beams under a low-pitched dark charcoal standing-seam metal roof; between some columns stand flat, plain blackened-steel panels (about 1/4 in thick, about 5 ft wide) perforated with many simple round holes in only three controlled diameters (about 1 in, 2 in and 3 in) on a regular offset grid; the hole density varies gradually across each panel and from panel to panel so that, seen together, broad, soft, incomplete concentric arcs appear across several panels; no single panel has a centre motif, radial petals, rosette, sunburst, star, lace or any ornament; it reads as utilitarian contemporary industrial perforated metal, not a decorative screen. "
"The MAIN ENTRANCE is a 12-ft-wide, 12-ft-deep covered recess in that south arcade immediately beside the hall's southeast corner, with a cedar elm soffit, a pair of full-height glass doors in dark-bronze frames, and a plain blank blackened-steel sign panel on a board-formed-concrete plinth beside it. "
"Through the arcade openings the court is visible: decomposed-granite gravel, a shallow stone water rill about 18 in wide running east-west down the centre, long dark-pecan communal tables with benches under the arcades, a cluster of cedar elms, and at the open east end a native-grass lawn with two mature live oaks. "
"Across the court, on its north side, runs a long, low restaurant block (about 140 ft long, one storey, about 18 ft to the ridge) with pale Texas limestone walls in horizontal courses, tall deep-set dark-bronze windows (about 5 ft wide by 9 ft tall), a low-pitched charcoal standing-seam roof with deep eaves, two slim blackened-steel kitchen exhaust stacks near its centre, and in front of it a second arcade identical to the south one; a stage alcove sits at its northeast corner. A third arcade runs along the hall's east glass. "
"Materials only: pale Texas limestone, board-formed concrete, blackened steel, polished stainless steel, dark pecan and cedar elm timber, glass. "
)

TANKS = (
"THE TANK CLOISTER seen through the hall glass: exactly SIX identical polished stainless-steel conical fermenters (each about 5 ft in diameter and about 19 ft tall including legs) arranged in a HORSESHOE that opens toward the south glass: two tanks along the west wall, two along the east wall, and one on each side of a raised central brew deck at the north end. Every tank has a polished cylindrical shell, an insulated conical bottom clad in matte charcoal, four short legs, a round side manway with clamp, a sample valve, realistic tri-clamp fittings, tidy restrained piping on the inner side of the horseshoe, and exactly ONE narrow (about 6 in) deep marigold-orange sleeve, a removable powder-coated band (more orange than yellow, about hex E8870E), around the middle of the shell. No other orange on the tanks, no patterns or decoration on the stainless. "
)

BREWHOUSE = (
"THE BREWHOUSE: on the raised brew deck (about 4 ft high, 24 ft wide, 12 ft deep, with stairs at each end and 42-in guardrails) stand TWO copper-clad brewing vessels with domed tops (a kettle and a mash/lauter tun, about 7 ft in diameter) beneath a steam hood and stack that rises to the roof, with a stainless hot-liquor tank, pumps, a valve train and coiled hoses on hooks. A grated steel catwalk with 42-in guardrails and kick plates runs at about 11 ft above the floor along the west and east legs with a cross-walk behind the brew deck, reached by stairs at each end. The production floor is a light warm-grey seamless sealed floor with stainless trench drains. "
)

COURT_NIGHT = (
"Night lighting: all artificial light is shielded and warm (about 2200-2400K appearance): linear wall-washers at column bases, small shielded downlights in the arcade soffits, narrow-beam uplights at the base of each tank, soft uplighting in the oak canopies, and reflections in the rill. "
"These shielded architectural sources are the only light sources in the scene. "
)

STYLE = "Photorealistic professional architectural photograph, as made by a specialist architectural photographer with a full-frame camera; real materials, believable scale, natural imperfections; correct vertical lines (no converging verticals); no CGI look. "

NEG_COMMON = ("cartoon, illustration, painting, obvious CGI, video-game or 3D-render look, plastic surfaces, "
"terracotta or orange walls, brass fixtures, mosaic or Moorish tile, Indian or Mexican decorative clichés, palace or temple or hacienda theme-park styling, mandalas, religious symbols, flags, "
"sombreros, turbans or traditional costume, pseudo-Devanagari or stereotypical Mexican fonts, agave as a feature plant, palm trees, resort pool, mountains in the background, "
"string lights, neon, cyberpunk or nightclub lighting, HDR halos, oversaturation, excessive symmetry, ultra-wide distortion, "
"fake logos, fake brand names, readable signage text, distorted text, fake awards, stock-photo smiles, extra or missing fingers, warped anatomy, "
"decorated or patterned fermenters, impossible brewing machinery, wrong number of tanks (must be exactly six), tanks in a straight row or a circle, customers inside the production area")

FILES = {}

_FROZEN_ARC01 = dict(
id="ARC-01", title="Definitive day exterior",
purpose="Answer: WHAT DOES THIS BREWERY LOOK LIKE? Establish the massing, entrance, Shade Court, Tank Hall and the six-tank Tank Cloister in one frame. This image becomes the visual reference for every other exterior.",
aspect="16:9 (generate 3 to 4 variants; accept only the best as the reference)",
prompt=(STYLE+"FORMAT: 16:9. "+BUILDING+TANKS+
"Through the south glass the six marigold-banded tanks must read as a clear, rhythmic horseshoe, glinting but not blown out; keep glass reflections low so the tanks are legible. "
"Foreground and context: a low strip of crushed-gravel entry drive and a few ordinary parked vehicles (pickup trucks, SUVs, a sedan; no readable plates or logos) at the very bottom edge, kept small so the building dominates; native grasses and yaupon in the near planting; mature live oaks and cedar elms around and behind the building; a few small figures (a couple walking toward the entrance, a family under the arcade) in natural casual clothes, mixed ages and backgrounds, tiny in frame. "
"The building feels expensive but achievable: long, low, confident and contemporary, not a warehouse box, not a hacienda, not a palace, not a resort. "
"CAMERA: eye-level (about 5.5 ft above the drive), 24-28mm equivalent, level horizon, vertical lines perfectly straight, building spanning about 80% of the frame width, Tank Hall in the left third, entrance recess just right of it, the court arcade extending to the right. "
"LIGHT AND TIME: late afternoon in Central Texas, about 90 minutes before sunset, hard low sun from camera-left (west-southwest) raking across the limestone and concrete, crisp long shadows, deep shade under the arcades and canopy, clear dusty-blue sky with a few thin high clouds, warm highlights on stone, true colours, no HDR look. "
"No logo and no readable text anywhere; the sign panel is blank blackened steel. The marigold-orange appears ONLY as the narrow bands on the six tanks (tiny and restrained in daylight); no orange walls. "),
neg=NEG_COMMON+"; additionally avoid a visible large parking lot, a giant brewery logo, a fantasy sky or sunset glow so strong it recolours the building",
cont=[
"Tank Hall on the LEFT, glazed on south and east, ~38 ft tall, flat roof with concrete parapet; six tanks in a horseshoe open to the south.",
"Entrance recess immediately right of the hall's SE corner, with blank steel sign panel on a concrete plinth.",
"South arcade, 14 ft deep, 15-ft column spacing, cedar elm beams, ring-perforated steel screens between some columns; court visible beyond with rill, tables, cedar elms.",
"Restaurant block across the court with two slim exhaust stacks and charcoal standing-seam roof; stage alcove at the NE corner.",
"Live oaks at the east end; native grasses; no agave, palms or pool.",
"Hero camera: SE of the building, looking NNW, eye level, 24-28mm.",
"All later exteriors (ARC-02, ARC-03...) must keep this camera position and geometry unless a different view is explicitly requested."],
checklist=[
"Exactly six tanks visible in a horseshoe? Each with ONE narrow marigold band and a charcoal cone?",
"Is the Tank Hall double-height, glazed on the south end and east flank, with limestone plinth and concrete canopy?",
"Is the entrance clearly findable beside the hall's SE corner, with a blank sign?",
"Is the arcade deep (about 14 ft), with concrete columns and timber beams? Are the screens perforated steel with ring-like hole patterns (not lattice, not mandala)?",
"Do you see the Shade Court beyond: rill, communal tables, cedar elms, live oaks, lawn?",
"Materials limited to limestone, board-formed concrete, blackened steel, stainless, glass, timber? No terracotta, brass, colourful tile?",
"Verticals straight, perspective natural, light plausible for late-afternoon Texas?",
"Building looks long, low, confident, premium but buildable? Parking subordinate?",
"No readable text, no logo, no palace/hacienda/resort cues, no agave or palms?",
"Does it look like a real photograph rather than a render?"],
accept=[
"Passes every checklist item above, or only fails items that a small Photoshop/inpaint fix can resolve.",
"Tank Hall and court relationship is clear enough that ARC-02 can reuse it as a reference.",
"Founder says: 'I would visit this place' and 'this could be built in Austin'.",
"Approved image is saved as the canonical reference and logged in visuals/generated/LOG.md with prompt, tool, model, seed, date."])

FILES["ARC-02.md"] = dict(
id="ARC-02", title="Definitive night exterior",
purpose="Same building as ARC-01 at blue hour into night. Provoke: 'I NEED TO GO THERE TONIGHT.' Show the Tank Cloister glowing as the brightest large objects and the Shade Court alive.",
aspect="16:9. Attach the APPROVED ARC-01 as an image reference and keep the same camera position and framing.",
prompt=(STYLE+"FORMAT: 16:9. THIS IS THE EXACT SAME BUILDING AND CAMERA POSITION AS THE DAYTIME VIEW, photographed at blue hour as it turns to night; do not redesign anything. "+BUILDING+TANKS+COURT_NIGHT+
"Specifics: the sky is deep indigo (not black) with a faint warm-grey glow low on the horizon; the Tank Hall's south and east glass glows warm from within and the six polished-steel tanks are the brightest large objects in the picture, lit from below so their shells glow softly and their narrow marigold bands show as restrained orange rings; copper-clad vessels on the brew deck glow dimly behind them. "
"The arcades are washed by low shielded light that reveals the board-formed concrete texture and the cedar elm beams; the ring-perforated steel screens are backlit and show their hole patterns as soft glowing rings. Warm light spills from the kitchen pass windows in the north arcade, and the mouth of an enclosed wood-fired oven set into the north arcade wall glows modestly behind a stainless counter (a cook is visible at it); this is real cooking fire, small and controlled, not theatre. The rill reflects the arcade lights. The live oaks are softly uplit from below. "
"People: about 25 to 35 guests of mixed ages, backgrounds and styles, naturally dressed in everyday Austin clothes, talking and sharing food and beer at the communal pecan tables under the arcades, a few standing at the entrance recess, some walking in from the drive; slight motion blur is fine; nobody poses; staff in charcoal aprons over bone shirts. The mood is lively but calm: not a nightclub, not a festival. "
"CAMERA: identical to the day image: eye level, 24-28mm equivalent, level horizon, straight verticals, tripod long-exposure clarity, building spanning about 80% of the width. Drive and a few parked cars at the bottom edge with only soft red/white glints. "
"No logo or readable text; the sign panel is blank steel. Orange appears only as the narrow bands on the tanks and the small oven glow. "),
neg=NEG_COMMON+"; additionally avoid festival lighting, light beams, lens flares, fog machines, a black sky, over-bright blown-out windows, people inside the production area",
cont=[
"Identical massing, roofline, entrance recess, court geometry, tank positions, window rhythm, materials and landscape as ARC-01.",
"Six tanks in a horseshoe, marigold bands, charcoal cones; tanks are the brightest large objects.",
"Same hero camera (SE, eye level, NNW, 24-28mm).",
"Lighting warm 2200-2400K appearance, shielded; no string lights; oven glow and kitchen windows are the only visible fire/cooking light.",
"People naturally diverse, not grouped, no costumes."],
checklist=[
"Is it recognizably the SAME building as ARC-01 (hall left, entrance beside its SE corner, arcade, restaurant block, stacks)?",
"Six tanks, horseshoe, marigold bands visible and restrained?",
"Are the tanks the brightest large objects? Is the glass glow warm, not orange everywhere?",
"Arcade lighting shielded and architectural; ring-perforated screens read as backlit rings; no string lights?",
"Oven glow small and plausible; cook behind a counter; no giant flames?",
"Court feels alive but calm; people natural, diverse, not posed?",
"Sky deep indigo with faint horizon glow; no HDR halos, no flares?",
"Nothing readable or branded?"],
accept=[
"Matches ARC-01 geometry closely enough to be believed as the same place.",
"Founder reaction: 'I need to go there tonight.'",
"Logged with reference image = approved ARC-01."])

FILES["BRW-01.md"] = dict(
id="BRW-01", title="Hero Tank Cloister",
purpose="Communicate: WE MAKE THE BEER HERE. The canonical interior view of the six-tank horseshoe, the brew deck and copper vessels, as seen from the guest side.",
aspect="16:9 (3:2 acceptable). Attach approved ARC-01/ARC-02 as references for materials and tank design.",
prompt=(STYLE+"FORMAT: 16:9. INTERIOR VIEW from the guest side looking north into the brewing hall through a floor-to-ceiling interior dark-bronze-framed glass wall (the guest promenade at the south end of the hall). "
"The camera stands about 4 ft above the floor, slightly low, 28-35mm equivalent, centred on the hall's axis, vertical lines straight; in the extreme foreground edges, a sliver of bone terrazzo floor (bone with sparse red-and-black aggregate, matte-polished) and the dark-bronze glass frame, optionally two softly blurred guests at the far left edge looking in. Beyond the glass is the brewers' working floor, a light warm-grey seamless sealed floor with stainless trench drains; guests never enter it. "
"The hall is double height (about 38 ft clear) with a flat ceiling and a high clerestory strip on the north wall letting in a little soft daylight. "
+TANKS+BREWHOUSE+
"COMPOSITION: the horseshoe forms a strong recessing rhythm: tanks 1 and 2 on the left leg, tanks 3 and 4 at the back flanking the brew deck with its two copper-clad vessels at the centre of the frame, tanks 5 and 6 on the right leg. All six identical, polished stainless reflecting the hall and the glow, charcoal cones, one narrow marigold band each, small white numerals 1 to 6 near the manways only if they render cleanly (otherwise omit). "
"WORK: one brewer in a black work shirt, work trousers, rubber boots and safety glasses stands on the brew deck checking a valve; a second brewer walks the floor between the west-leg tanks with a hose over the shoulder, both busy and unposed, small in scale to emphasize the height. "
"LIGHT: warm, low, shielded about 2300K architectural light, narrow-beam uplights at the base of each tank, soft cool daylight from the north clerestory, subtle steam rising from the kettle stack; stainless gives cool reflections against the warm light; no haze effects, no god rays. "
"The scale feels monumental because of the height, the rhythm of identical tanks, the reflections and the real equipment, not decoration. No logo, no readable text, no pattern or ornament on any tank. "),
neg=NEG_COMMON+"; additionally avoid fantasy or sci-fi brewing machinery, glowing pipes, decorated or engraved tanks, tanks of different sizes or colours, five or seven tanks, a circular or straight arrangement, brass fittings, guests on the production floor, brewers posing for the camera, wet reflections that look like a hotel lobby",
cont=[
"Six identical fermenters in a horseshoe open to the south; brew deck with two copper-clad vessels at the north centre between tanks 3 and 4.",
"Charcoal cones, polished shells, one ~6 in marigold band each, side manways, tri-clamp fittings, tidy piping on the inner side.",
"Catwalk at ~11 ft, 42-in guardrails; stairs; stainless trench drains; light warm-grey production floor.",
"Bone terrazzo on the guest side; dark-bronze glazing frames (same as ARC-01).",
"Warm 2200-2400K light with tank uplights; north clerestory daylight.",
"Same Tank Hall as seen from outside in ARC-01/02 (south glass, 6-ft mullion rhythm)."],
checklist=[
"Exactly six tanks in a horseshoe with the brew deck at the back centre?",
"Do the tanks look like real production equipment (cones, legs, manways, valves, tri-clamps) rather than props?",
"Two copper-clad vessels on a raised deck with stairs and 42-in guardrails? Steam hood and stack?",
"Catwalk with guardrails, drains in the floor, hoses coiled, sensible clearances?",
"One narrow marigold band per tank and nothing else orange?",
"Guests only on the terrazzo side behind glass; brewers on the working floor?",
"Does it feel monumental through scale, rhythm, light and reflection rather than decoration?",
"Any gibberish text, logos, brass, patterns, or oddly shaped tanks?"],
accept=[
"A professional brewer or engineer would not laugh at the equipment.",
"Tank count, arrangement, bands and cones match the canonical DNA exactly.",
"Founder reaction: 'They actually make all of this here.'",
"Becomes the reference for all later brewhouse and fermentation images."])

GLASS_COMMON = ("Glass design (canonical): this glass belongs to a family of four that share one design feature, a RAISED CLEAR-GLASS RING (collar) moulded integrally into the glass about one-quarter of the way up from the base, about 5 mm proud of the surface and about 12 mm tall with softly rounded edges, never wider than the rim. "
"All glass is perfectly clear, colourless, with no print, no etching, no logo, no pattern, no colour, no metal. ")

FILES["GLS-01.md"] = dict(
id="GLS-01", title="Hero Hefeweizen glass (ring-collar), empty",
purpose="Define the iconic but manufacturable brewery glass. The silhouette must be recognizable on its own.",
aspect="4:5 (1:1 acceptable)",
prompt=("Photorealistic premium industrial-design product photograph of a single EMPTY drinking glass. FORMAT: 4:5. "+GLASS_COMMON+
"THE GLASS: a tall wheat-beer vase (Weizen form) of about 0.5 litre beer capacity (brim volume about 0.65 to 0.7 litre), about 24 to 25 cm (9.5 to 10 in) tall; a thick, stable, clear base about 1 cm thick and about 5.5 cm (2.2 in) across; a subtle gentle narrowing through the lower body to a waist about 6 cm (2.4 in) across, then a smooth, graceful widening through the upper body to a fine, thin, fire-polished drinking rim about 7.8 cm (3.1 in) across, with generous room above the beer line for a thick wheat-beer foam head; the profile is one continuous elegant curve. "
"The raised clear ring (collar) sits about 6 cm above the base, at the lower body just above the base, reading as a single crisp horizontal band that catches light; it looks like part of the moulded glass, blown or pressed as one piece, not glued on, not jewellery, with soft rounded edges that would survive a commercial dishwasher. "
"STUDIO: the glass stands upright, centred, on a honed pale Texas limestone slab (bone-coloured, fine fossil grain, matte) against a softly graded warm bone-grey background with no horizon line. Lighting: one large soft light from camera-left raking across the glass to reveal the ring, wall thickness, rim, base and curvature as clean highlights and a thin dark edge line, a subtle fill from the right, a gentle soft reflection on the stone, faint soft shadow to the right; no fingerprints or dust. "
"CAMERA: 100 to 105mm macro product lens, aperture about f/8 for full sharpness along the glass, camera at the height of the glass's midpoint, perfectly vertical glass, minimal perspective distortion, shot at 4:5. Nothing else in the frame: no beer, no props, no hands, no text."),
neg="beer, liquid, foam, condensation, printed pattern, logo, text, etching, colour tint, metal parts, handle, stem, facets or cuts, ornamental ridges, multiple rings, ring at the top or middle, ring wider than the rim, bulbous or novelty shape, flag, deity, mandala, hands, props, busy background, harsh reflections, cartoon, CGI look, warped or asymmetric glass, double rim, thick chunky rim",
cont=[
"Ring collar one-quarter up from the base, ~5 mm proud, ~12 mm tall, rounded, integral; same ring language on the other three glasses.",
"Same limestone/bone studio language will be used for GLS-02 and later beer photographs.",
"Proportions: ~24-25 cm tall, base ~5.5 cm, waist ~6 cm, rim ~7.8 cm, base thickness ~1 cm."],
checklist=[
"Is the silhouette elegant, tall and obviously a wheat-beer vase?",
"Is there exactly ONE raised ring about one-quarter of the way up?",
"Does the ring look moulded as part of the glass, with soft edges, not applied jewellery?",
"Is the rim fine and the base thick and stable?",
"Perfectly clear glass with no print, logo, colour or metal?",
"Would the rim be wider than any part of the collar (rack-safe)?",
"Does it read as manufacturable and washable hundreds of times?",
"Is it photogenic: do the highlights reveal thickness, curvature and ring?"],
accept=[
"Silhouette recognizable even as a black cut-out.",
"A glass engineer would see a plausible mould line and plausible wall thickness.",
"Founder says: 'That is the INDO MEX glass; I want one.'",
"Becomes the reference for beer photography (flagship Hefeweizen next)."])

FILES["GLS-02.md"] = dict(
id="GLS-02", title="Glass family (four glasses)",
purpose="Show the four canonical glasses as one industrial-design collection built around the ring-collar.",
aspect="3:2 (16:9 acceptable). Attach approved GLS-01 as reference.",
prompt=("Photorealistic premium industrial-design collection photograph of four EMPTY drinking glasses. FORMAT: 3:2. "+GLASS_COMMON+
"THE FOUR GLASSES, left to right, standing on a honed pale Texas limestone slab, evenly spaced about one glass-width apart and very slightly staggered in depth: "
"(1) HEFEWEIZEN, the tallest: about 24 to 25 cm tall, a tall wheat-beer vase, thick clear base, subtle narrowing then widening to a fine rim about 7.8 cm across, ring collar about 6 cm above the base. "
"(2) LAGER: about 20 cm tall, a tall refined conical glass, base about 5 cm, rim about 7.2 cm, thin straight-sided conical walls, ring collar one-quarter of the way up. "
"(3) RESERVE: a short stemmed tasting goblet about 17 cm tall, with a bowl about 8 cm wide featuring ONE subtle step (a gentle shoulder) in the bowl, a slim stem and a stable round foot; the raised ring sits at the junction between the bowl and the stem, echoing the others. "
"(4) FLIGHT: a small tulip tasting glass about 10 cm tall holding about 120 ml (4 oz), gently flared lip, ring collar one-quarter of the way up. "
"The four are clearly one design family because of the shared ring but are not identical; their heights step down from the Hefeweizen. All perfectly clear, empty, spotless, with no print, logo or colour. "
"STUDIO: warm bone-grey seamless background with a very subtle gradient, one large soft raking light from camera-left revealing every ring, rim and base with clean highlights and thin dark edges, gentle fill from the right, soft reflections and faint soft shadows on the stone. "
"CAMERA: 85 to 100mm lens, aperture about f/8, camera at about the height of the Hefeweizen's midpoint, minimal distortion, all four in sharp focus, composed like a professional collection catalogue with generous negative space. Nothing else in frame."),
neg="beer, liquid, foam, condensation, printed pattern, logo, text, etching, colour tint, metal parts, handles, facets, multiple rings per glass, rings in different positions randomly, identical glasses, glasses of equal height, props, hands, busy background, harsh reflections, cartoon, CGI look, warped glass, novelty shapes, cultural ornament, flag, deity, mandala",
cont=[
"Hefeweizen identical to GLS-01 (use GLS-01 as reference).",
"Same ring language on all four; collar diameters never exceed rim diameters.",
"Same limestone/bone studio, raking light from camera-left, as GLS-01.",
"Heights: Hefeweizen ~24-25 cm > Lager ~20 cm > Reserve ~17 cm > Flight ~10 cm."],
checklist=[
"Four glasses, correct types and descending heights, Hefeweizen tallest?",
"Same ring in each, clearly a family but not clones?",
"Reserve has a stem, one subtle bowl step and a ring at bowl-stem junction?",
"Flight is a small tulip with ring? Lager a tall conical?",
"No print, colour, logo, metal, beer or props?",
"Hefeweizen matches the approved GLS-01?",
"Studio lighting clean, no distortion?"],
accept=[
"A designer would read this as one collection.",
"Each glass is plausibly manufacturable and dishwasher-safe.",
"Founder approves the family and signs off the visual lock (with ARC-01, ARC-02, BRW-01, GLS-01)."])

FILES["ARC-01-B.md"] = dict(
id="ARC-01-B", title="Corrected day exterior (refinement of ARC-01-A)",
purpose="Refine ARC-01-A, not replace it: same brewery, same massing and materials, with corrected ring-free industrial screens, a readable six-tank horseshoe, a stronger entrance and more photographic realism. ARC-01 remains the BREWERY HERO: no play, game, history or retail elements.",
aspect="16:9 (generate 4 variants; attach ARC-01-A as an optional composition reference but obey the corrections below)",
prompt=(STYLE+"FORMAT: 16:9. THIS IS A REFINEMENT OF AN EXISTING DESIGN: the same brewery as the earlier candidate, with the corrections listed at the end. "+BUILDING+TANKS+
"HALL HEIGHT AND CONTRAST: the Tank Hall is a tall industrial volume, its parapet about 2.5 times the height of the arcade eave beside it, acting almost like the brewery's visual tower without being a tower; the arcade, entrance and restaurant block are clearly low hospitality volumes. "
"TANK READABILITY (critical): the camera is turned more obliquely so the hall's south glass and east glass are both clearly visible, the south face at about 35 to 40 degrees to the picture plane (about 55 percent of the visible hall width is south glass, 45 percent east-flank glass). Through the glass the SIX tanks must read as a U-shaped room of equipment, not a row: the two west-leg tanks at the far left of the south glass, the two back tanks flanking a raised brew deck whose copper-clad vessels are visible at the centre of the depth, and the two east-leg tanks seen nearest through the east glass at a steep angle. The tanks are at different depths and different sizes in perspective, which creates depth. Interior narrow-beam uplights on the far tanks make them pop against a slightly darker interior; the glass is clear and low-reflectance so reflections of trees do not hide the tanks. Each tank: polished stainless shell, a matte CHARCOAL insulated cone (clearly darker than the shell), four legs, a visible round manway, and ONE narrow (about 6 in) deep marigold band (more orange than yellow). "
"ENTRANCE (clear hierarchy without any sign): immediately beside the hall's southeast corner the south arcade steps in to a deeper recess about 12 ft wide and 14 ft deep with a lowered cedar elm soffit, two shielded downlights, a pair of full-height dark-bronze glass doors with an accessible door, a wall change to honed limestone inside the recess, paving that changes to larger pale limestone pavers leading in from the drive, and clusters of muhly grass and yaupon on either side framing the opening. The blank blackened-steel monument panel on its board-formed-concrete plinth stands beside the approach path, not in front of any column. A couple walk toward the entrance. "
"ARCADE SCREENS (corrected): flat plain blackened-steel perforated panels as described, reading as industrial perforated metal; through the holes the viewer sees the shaded greens of the court, not a golden glow; no panel has a centre motif or radial pattern. "
"PEOPLE AND CONTEXT: a family group under the arcade, a few small diners at communal pecan tables in the court, a couple at the entrance: small, natural, unposed. Vehicles (a pickup, an SUV, a sedan) appear only as low, partial, cropped shapes at the extreme bottom corners with no readable plates; the gravel entry drive and native grasses (little bluestem, muhly, inland sea oats, yaupon, Texas sage) occupy the foreground; a live oak branch frames the upper left without covering the tanks; cedar elms and live oaks around and behind. "
"CAMERA: eye level (about 5.5 ft), 24-28mm equivalent, level horizon, perfectly straight verticals, about 150 to 170 ft from the hall, building about 75 to 80 percent of the frame width, Tank Hall in the left third, entrance centre-left, court extending right. "
"LIGHT AND PHOTOGRAPHIC REALISM: late afternoon in Central Texas, about 60 to 90 minutes before sunset, hard sun from camera-left (west-southwest) with crisp long shadows and strong material texture, deep shade under the arcade, clear dusty-blue sky with a few thin cirrus; neutral true-colour grade (not sunset-orange, no golden haze, no glowing backlit foliage, no glowing holes in the screens), natural lens falloff and fine film grain, believable fine detail in the limestone coursing, board-formed concrete lines, trench of the rill and the gravel; avoid the smooth, over-saturated AI look. "
"No logo and no readable text anywhere. Marigold-orange appears only as the six narrow tank bands. "),
neg=NEG_COMMON+"; additionally avoid radial or sunburst or medallion screen patterns, golden glow through the screens, a straight row of four tanks, silver or stainless cones, thick yellow tank bands, limestone columns in place of concrete columns, a recess-less flush entrance, a monument sign in front of columns, large cars filling the frame, orange sunset haze, any play structures, game machines, retail signage or historical displays",
cont=[
"Identical building to ARC-01-A: tall glazed Tank Hall at left, deep arcade and Shade Court at right, restaurant block with two stacks behind, rill, communal pecan tables, oaks, native grasses.",
"Corrections: ring-free industrial perforated panels; six tanks in a horseshoe with charcoal cones and narrow deep-marigold bands; clearer, deeper entrance recess; board-formed concrete columns; dark-bronze mullions; hall visibly taller than the arcade.",
"Camera: SE of the building looking NNW, eye level, 24-28mm, more oblique so the east glass shows.",
"Nothing from the family/game/history/retail expansion appears in this image."],
checklist=[
"Do the screens read as plain perforated industrial panels with three hole sizes and NO centre motifs, sunbursts or medallions?",
"Do the six tanks read as a U-shaped horseshoe (two west, two back around the brew deck, two east) rather than a row? Can you count six?",
"Charcoal cones clearly different from the polished shells? Narrow deep-marigold bands?",
"Is the Tank Hall visibly taller than the arcade, and is the east glass visible?",
"Can a stranger find the entrance at a glance (recess, soffit, lights, paving, planting) without a sign?",
"Are the columns concrete and the mullions dark bronze? No terracotta, brass or decoration?",
"Natural colour grade, no golden haze, no glowing screen holes; does it read as a photograph?",
"Are vehicles low and subordinate? No readable text, no logo?"],
accept=[
"Score >= 90 on the ARC-01 rubric with no hard fail.",
"Six tanks believable in a horseshoe, or regenerate.",
"Founder approval required before it is called canonical."])

def md(f,d):
    o=[f"# {d['id']}: {d['title']}","",
    f"- **ID:** {d['id']}",f"- **TITLE:** {d['title']}",f"- **PURPOSE:** {d['purpose']}","- **STATUS:** NOT GENERATED",
    f"- **RECOMMENDED ASPECT RATIO:** {d['aspect']}",
    "- **Concept label (record in metadata/caption, do not render in the image):** Concept visual, not an operating business.","",
    "## MASTER PROMPT (self-contained; paste whole)","", "```", d['prompt'].strip(), "```","",
    "## NEGATIVE CONSTRAINTS (paste into the negative-prompt field, or append as 'Avoid: ...')","", "```", d['neg'], "```","",
    "## CONTINUITY REQUIREMENTS",""]+[f"- {c}" for c in d['cont']]+["","## REVIEW CHECKLIST (founder)",""]+[f"- [ ] {c}" for c in d['checklist']]+["","## ACCEPTANCE CRITERIA",""]+[f"- {c}" for c in d['accept']]+["",
    "## LOG ENTRY TO COMPLETE (also in visuals/generated/LOG.md)","","asset ID / tool / model / date / prompt version / reference image / seed / version / status / founder approval / notes",""]
    open(f"{OUT}/{f}","w").write("\n".join(o))
for f,d in FILES.items(): md(f,d)
print("built",list(FILES))
