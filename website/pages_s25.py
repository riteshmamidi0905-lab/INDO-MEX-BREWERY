"""Sprint 25 VISION pages. Layer 2 (Vision / future state) of the private NASHA site.
Everything here is a creative simulation of what NASHA could become. It is not evidence, a validated product, a professional approval, a cost, a site, a recipe or a sale.
Vision figures carry data-vision (not data-vid) and a "Vision" tag; they are listed in vision/data/VISION-ASSET-MANIFEST.csv.
Vision assumptions: vision/data/VISION-ASSUMPTIONS.csv. Pages receive the build module as B."""
import csv, html, os
import art, art_s25 as A

E = html.escape
HERE = os.path.dirname(os.path.abspath(__file__))
VDATA = os.path.join(os.path.dirname(HERE), "vision", "data")


def vrows(name):
    with open(os.path.join(VDATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def vfig(vid, svg, label, cls="", ar="16/10"):
    """A vision illustration. Always labelled; never styled as a photograph."""
    return (f'<figure class="fig fig-art vision-fig {cls}" data-vision="{vid}" style="--ar-d:{ar};--ar-m:{ar}">{svg}'
            f'<figcaption class="tag" data-stage="VISION">{E(label)}<span class="visually-hidden">. A drawing of what NASHA could become. Not a photograph, not a plan for construction.</span></figcaption></figure>')


def truth_key():
    return ('<details class="truthkey"><summary>How to read this site</summary><dl>'
            '<div><dt>Vision</dt><dd>What NASHA could become. Most of this site.</dd></div>'
            '<div><dt>Prototype</dt><dd>What the founder has physically made. Nothing yet.</dd></div>'
            '<div><dt>Validated</dt><dd>What has passed a test we defined in advance. Nothing yet.</dd></div></dl>'
            '<p>The vision is a design to aim at. The <a href="investor.html">business view</a> says what is real, what is assumed and what still needs proof.</p></details>')


def pour(a, b, c):
    """One pairing sentence in plain words."""
    return f'<p class="pourline"><strong>{E(a)}</strong> <span>{E(b)}</span> <em>{E(c)}</em></p>'


def beats_list():
    items = [("Street", "A low, quiet frontage of pale stone and glass. One tank glimpsed through the glass."),
             ("Threshold", "A covered recess. The ceiling drops and the air cools."),
             ("Compression", "A short, dim passage along the glass of the brewery. You smell malt and smoke before you see anything."),
             ("Court reveal", "The passage opens to sky, shade, an oak, a long stone channel of water and the sound of the room."),
             ("Brewhouse", "Six steel tanks behind glass, each with a thin orange band. The brewery is a neighbour, not a feature."),
             ("Bar and dining", "A long dark bar with a window into the tanks, and dining rooms that open to the court."),
             ("Patio at night", "Uplit tanks, a glowing oven mouth, warm arcades and a hum you can still talk over.")]
    return '<ol class="beats">' + "".join(f'<li><span class="beat-n" aria-hidden="true">{i}</span><div><h3>{E(n)}</h3><p>{E(t)}</p></div></li>' for i, (n, t) in enumerate(items, 1)) + "</ol>"


# ---------------------------------------------------------------- home
def page_home(B, S):
    dishes = [B.DISH[i] for i in ("chicken-65-totopos", "paneer-tikka-taco", "goat-birria")]
    food = "".join(f'<article class="feature reveal"><div class="plate-big">{B.plate_svg(d)}</div><h3>{E(d["name"])}</h3><p>{E(d["line"])}</p></article>' for d in dishes)
    gl = "".join(f'<div class="gcell">{svg}<span>{E(n)}</span></div>' for svg, n in [
        (art.glass(B.uid("hg"), "hefeweizen", .86, "weizen", True, "Concept Hefeweizen glass"), "Hefeweizen"),
        (art.glass(B.uid("hg"), "mexican-lager", .86, "lager", True, "Concept lager glass"), "Mexican-style lager"),
        (A.aromatic_glass(B.uid("hg"), "vienna-amber"), "Vienna amber"),
        (A.na_glass(B.uid("hg"), "#D45A5A", "lime"), "Zero-proof cooler")])
    body = f'''
<section class="hero" aria-labelledby="h1">
{B.raster_fig("NV-HERO-01", "fig-hero", eager=True, sizes="100vw")}
<div class="wrap hero-copy">
<p class="eyebrow">Austin, Texas · A future place</p>
<h1 id="h1">Come in. Sit down. Taste what was made to go together.</h1>
<p class="lede">A brewhouse around a shaded court, where fire cooks the food and fermentation makes the beer, and every dish is meant to be met by a beer and a zero-proof drink chosen for it.</p>
<p class="hero-note"><strong>VISION.</strong> NASHA is a concept in development. This is the place we are designing toward; nothing is built, cooked or brewed yet. {E(B.DISCLOSE.split(".")[0] + ".")}</p>
</div></section>

<section aria-labelledby="one"><div class="wrap">
<p class="eyebrow">The idea</p>
<h2 id="one" class="statement">Food and beer, designed together, around a court.</h2>
<p class="lede">A restaurant often adds a beer list, or a brewery a food menu. NASHA is meant to start from the table: five dishes, five beers and a zero-proof drink for each, made to meet in the middle.</p>
{truth_key()}
</div></section>

<section class="alt" aria-labelledby="fd"><div class="wrap">
<p class="eyebrow">Food</p><h2 id="fd">Chicken 65, corn tortillas, one kitchen.</h2>
<p>Chicken 65 on thick fried totopos. Charred paneer in a corn tortilla. Goat birria with a cup of consomme. Each is drawn here as it is meant to look; none has been cooked yet. <a href="food.html">All five dishes</a>.</p>
<div class="grid cols-3">{food}</div></div></section>

<section aria-labelledby="br"><div class="wrap">
<p class="eyebrow">Beer</p><h2 id="br">Five beers, three shapes of glass.</h2>
<p>A soft Hefeweizen, an easy Mexican-style lager, a toasty Vienna amber, a crisp Pilsner and an aromatic Witbier, each poured into a glass that suits it. The zero-proof drinks use the same glasses, with the same care. <a href="beer.html">Meet the beers</a>.</p>
<div class="gfam">{gl}</div></div></section>

<section class="alt" aria-labelledby="pr"><div class="wrap grid cols-2 center">
<div><p class="eyebrow">Pairing</p><h2 id="pr">Bright bubbles should reset your mouth after each bite.</h2>
<p>Every pairing is explained in a plain sentence, and always optional. Order what you like.</p>
{pour("Goat birria", "with a soft, banana-and-clove Hefeweizen", "or a ruby hibiscus-and-tamarind tea. We expect both to cut the richness of the consomme.")}
<p class="muted">These pairings are proposals. Nobody has tasted them yet. <a href="pairings.html">See all pairings</a>.</p></div>
<div>{B.svg_fig("NV-ILL-PLATES", '<div class="duo"><div class="duo-plate">' + B.plate_svg(B.DISH["chicken-65-totopos"]) + '</div><div class="duo-glass">' + art.glass(B.uid("dg"), "mexican-lager", .88, "lager", True, "Concept lager glass") + '</div></div>', "fig-duo", "4/3")}</div></div></section>

<section aria-labelledby="ct"><div class="wrap">
<p class="eyebrow">The court</p><h2 id="ct" class="statement">A brewhouse you walk into, and a court you walk out to.</h2>
<p class="lede">Stone, glass and shade. The tanks sit behind glass beside the court, so brewing is part of the evening. <a href="court.html">Walk in from the street</a>.</p>
<div class="grid cols-2">{B.raster_fig("NV-SPACE-EXT-DAY", "reveal", sizes="(max-width: 700px) 100vw, 50vw")}{B.raster_fig("NV-SPACE-PATIO", "reveal", sizes="(max-width: 700px) 100vw, 50vw")}</div></div></section>

<section class="alt" aria-labelledby="pe"><div class="wrap grid cols-2 center">
<div>{B.raster_fig("NV-BREWERY-GLASS", "reveal", sizes="(max-width: 700px) 100vw, 50vw")}</div>
<div><p class="eyebrow">Craft</p><h2 id="pe">You can see the work.</h2>
<p>The brewers, the cooks and the servers share one room. Steel you can see, fire you can feel, a table set simply. <a href="craft.html">The craft and the table</a>. <a href="evening.html">One evening, start to finish</a>.</p></div></div></section>

<section class="band-indigo" aria-labelledby="hw"><div class="wrap">
<p class="eyebrow">How we are building it</p><h2 id="hw" class="statement">The dream has a discipline behind it.</h2>
<p class="lede">The founder plans to test the food at home first, then cost it, before anything else is asked of anyone. <a href="labs.html">The Lab shows where each dish really is</a>. <a href="investor.html">The business view shows what is real, what is assumed and what needs proof</a>. <a href="walkthrough.html">Four minutes, start to finish</a>.</p>
</div></section>
'''
    return B.layout("index.html", "NASHA: Indo-Mex brewery and kitchen, in development",
                    "NASHA is a future Indo-Mex brewery and kitchen in Austin, Texas. A concept in development. Nothing is for sale yet.", body, B.hero_head(), "home")


# ---------------------------------------------------------------- court
def page_court(B, S):
    plan = vfig("VI-COURT-PLAN", A.court_plan(B.uid("cp")), "Vision illustration · not construction design", "fig-plan", "960/600")
    rooms = [("A date", "A corner two-top by the court window, shielded light, one shared plate and two glasses."),
             ("Two friends", "Two stools at the bar or two low seats at the court edge, food between you."),
             ("Four friends", "A four-top beside the long table; a shared tray and mixed pours."),
             ("A family", "Early evening near the court, with zero-proof drinks for everyone and room to move."),
             ("A large table", "The long pecan table in the court, dishes in the middle, servers always near."),
             ("Solo at the bar", "A stool with a view into the tanks and a bartender who will talk if you want."),
             ("A beer explorer", "A small flight at the backbar window and a short conversation about each pour.")]
    room_html = "".join(f'<li><h3>{E(n)}</h3><p>{E(t)}</p></li>' for n, t in rooms[:3])
    room_more = "".join(f'<li><h3>{E(n)}</h3><p>{E(t)}</p></li>' for n, t in rooms[3:])
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">The place · Vision</p><h1 id="h1">The Court Brewhouse.</h1>
<p class="lede">A limestone-and-glass hall with the brewery inside it, a shaded court beside it, and a kitchen that opens onto both.</p>
<p class="hero-note">VISION FLAGSHIP: an assumed design to imagine from, not construction drawings. It does not claim a site, a size, a seat count, code compliance or engineering. The place is shaped by the plan below.</p>
{truth_key()}
</div></section>
<section class="alt" aria-labelledby="walk"><div class="wrap">
<h2 id="walk">From the street to the patio at night.</h2>
<p>Seven moments, in the order you would meet them. The numbers match the plan.</p>
{plan}
{beats_list()}</div></section>
<section aria-labelledby="arr"><div class="wrap grid cols-2 center">
<div>{B.raster_fig("NV-SPACE-ENTRANCE", "reveal", sizes="(max-width: 700px) 100vw, 50vw")}</div>
<div><p class="eyebrow">Arrival</p><h2 id="arr">The first thirty seconds.</h2>
<p><strong>By day.</strong> A calm frontage of pale stone and glass. A line of shade pulls you toward a plain steel sign and a bronze-framed door. You hear the court before you see it, and smell charred corn and fresh bread.</p>
<p><strong>At night.</strong> The hall glows amber, and the tanks are the brightest large things on the street. The entrance is kept dim, so the court is a reveal. The brewery is the first thing you see; the room arrives a second later.</p>
<p class="muted">NASHA should be recognisable from its form, not its sign: a horseshoe of tanks, a perforated steel screen, a long stone channel in a gravel court.</p></div></div></section>
<section class="alt" aria-labelledby="dn"><div class="wrap">
<p class="eyebrow">Dining</p><h2 id="dn">A room for every kind of evening.</h2>
<p>We aim to design for everyone: step-free routes, comfortable chairs, a calmer side and a livelier side. An architect and accessibility reviewers will decide what is possible.</p>
<ul class="roomgrid">{room_html}</ul><details class="more"><summary>Four more ways to spend an evening</summary><ul class="roomgrid">{room_more}</ul></details></div></section>
<section aria-labelledby="bar"><div class="wrap">
<p class="eyebrow">Inside</p><h2 id="bar">A bar, a brewery and a kitchen that share one room.</h2>
<div class="grid cols-3 inside">
<div><h3>The bar</h3><p>A long dark bar with a window into the tanks. About eight handles, not thirty: the five core beers, a rotating one and two zero-proof taps. It is where food and beer are easiest to see together.</p></div>
<div><h3>The brewery</h3><p>Six stainless tanks in a horseshoe behind glass, each with a thin orange band. Guests watch from the lobby, the bar window, the court and a gallery above, and never walk on the production floor. Size and count are for a brewer to decide.</p></div>
<div><h3>The kitchen</h3><p>You see the glow of the oven mouth in the north arcade and plates leaving a pass window to the court. Frying, charring, the comal and the pass are stations, not a show.</p></div></div>
{B.raster_fig("NV-BREWERY-HALL", "reveal fig-wide", sizes="100vw")}
<p class="muted">The vessels in the picture are shown in copper; we would rather use plain stainless.</p></div></section>
<section class="alt" aria-labelledby="pt"><div class="wrap">
<p class="eyebrow">The patio</p><h2 id="pt">A court that works from lunch to late.</h2>
{B.raster_fig("NV-SPACE-PATIO", "reveal fig-wide", sizes="100vw")}
<p>Gravel underfoot, a shallow stone channel of water, shade from three arcades, cedar elms and a live-oak edge. No string lights: the light comes from low brass-warm lamps and the tanks. <a href="evening.html">See the evening</a>.</p></div></section>
<section aria-labelledby="more"><div class="wrap"><h2 id="more">More about the place.</h2>
<p><a href="space.html">A walk through the hall, step by step</a> · <a href="experience.html">An evening at NASHA</a> · <a href="craft.html">The craft and the table</a> · <a href="investor.html#assumed">What is assumed here, and what must be proved</a>.</p></div></section>'''
    return B.layout("court.html", "The Court Brewhouse · NASHA", "A vision of the NASHA flagship: a limestone-and-glass brewhouse, a kitchen and a shaded court. Concept, not construction.", body)


# ---------------------------------------------------------------- craft
def page_craft(B, S):
    gl = "".join(f'<div class="gcell">{svg}<span>{E(n)}</span><small>{E(t)}</small></div>' for svg, n, t in [
        (art.glass(B.uid("cg"), "hefeweizen", .86, "weizen", True, "Concept Signature Hefe glass"), "Signature Hefe glass", "Tall, with a raised ring. Hefeweizen."),
        (art.glass(B.uid("cg"), "mexican-lager", .86, "lager", True, "Concept lager and pils glass"), "Lager and Pils glass", "A refined cone. Lager and Pilsner."),
        (A.aromatic_glass(B.uid("cg"), "vienna-amber"), "Aromatic glass", "A short tulip. Amber and Witbier.")])
    na = "".join(f'<div class="gcell">{A.na_glass(B.uid("na"), c, g)}<span>{E(n)}</span><small>{E(t)}</small></div>' for c, g, n, t in [
        ("#E5766B", "lime", "Fruit, lime and salt", "With Chicken 65"),
        ("#C7E0A0", "herb", "Spiced citrus sparkler", "With the paneer taco"),
        ("#8E1F3E", "peel", "Hibiscus and tamarind tea", "With goat birria"),
        ("#E8F0D8", "herb", "Lime and herb cooler", "With the gobi taco"),
        ("#F2D7B5", "none", "Fruit and cultured dairy", "With the quesadilla")])
    table = vfig("VI-TABLE-TOP", A.table_top(B.uid("tt")), "Vision illustration · concept table", "fig-table", "640/460")
    tlist = ["Black stoneware plate with a raw rim", "Woven basket for tortillas or totopos", "Steel katori for a sauce", "Indigo-and-bone napkin", "Beer glass", "Zero-proof glass", "Water", "One small cruet"]
    tl = '<ol class="tlist">' + "".join(f"<li>{E(t)}</li>" for t in tlist) + "</ol>"
    menu = '''<div class="menucard" role="group" aria-label="Concept menu layout, no prices">
<div class="mc-col"><h3>Food</h3><ul><li>Chicken 65 Totopos</li><li>Paneer Tikka Taco</li><li>Goat Birria</li><li>Gobi Taco</li><li>Butter Chicken &amp; Poblano Quesadilla</li></ul></div>
<div class="mc-col"><h3>Beer</h3><ul><li>Hefeweizen</li><li>Mexican-style Lager</li><li>Vienna Amber</li><li>Pilsner</li><li>Witbier</li></ul></div>
<div class="mc-col"><h3>Zero-proof</h3><ul><li>Fruit, lime and salt</li><li>Spiced citrus sparkler</li><li>Hibiscus and tamarind tea</li></ul></div>
<p class="mc-foot">Under each dish: <em>Try it with&hellip;</em> Optional. A small flight to taste before you choose. No prices on this concept.</p></div>'''
    langs = [("Bright bubbles reset your mouth after each bite.", "Cleansing"), ("Cool and crisp against hot and rich.", "Contrast"), ("The beer smells like something already on the plate.", "Shared aroma"),
             ("A little sourness keeps rich food light.", "Acid"), ("It calms the chile without wiping it out.", "Heat relief"), ("Soft and creamy against crisp and charred.", "Texture")]
    pl = '<ul class="plain-pairs">' + "".join(f"<li><strong>{E(a)}</strong> <span class='muted'>{E(b)}</span></li>" for a, b in langs) + "</ul>"
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">Craft · Vision</p><h1 id="h1">The glass, the table, the details.</h1>
<p class="lede">NASHA should look like one company wherever you look: the plate, the glass, the apron, the sign. Structure over souvenir.</p>
<p class="hero-note">Everything here is a vision drawing. Glass makers, fabric, tableware and signage have not been chosen, and none of it is tested or approved.</p>
{truth_key()}</div></section>
<section class="alt" aria-labelledby="gl"><div class="wrap"><h2 id="gl">Three glasses tell the story better than five.</h2>
<p>A tall Signature Hefe glass, a versatile Lager and Pils glass, an aromatic option for amber and Witbier, plus a small flight tulip. This is a vision choice; the earlier five-glass concept remains in the blueprint. Whether the shapes can be made, stacked and washed is not verified.</p>
<div class="gfam">{gl}</div>
<h3>Zero-proof, equal in care</h3><p>Same clear glass, natural colour, one simple garnish. Not children's soda, not a mocktail cliché, not a garnish tower. Flavour plans only; none is tested.</p>
<div class="gfam">{na}</div></div></section>
<section aria-labelledby="rit"><div class="wrap grid cols-2 center"><div><p class="eyebrow">Ritual</p><h2 id="rit">A small moment of care.</h2>
<p>A clean glass on a coaster of ceramic or wood. For the Hefeweizen, a two-step pour at the table, only if testing shows it is worth the time. Brass and woven fibre where they have a job to do. No smoke, no dry ice, no flames, no tricks.</p></div>
<div><h3 class="sub">Say it plainly</h3>{pl}</div></div></section>
<section class="alt" aria-labelledby="tb"><div class="wrap grid cols-2 center"><div>{table}</div><div><p class="eyebrow">The table</p><h2 id="tb">Uncrowded, so it photographs naturally.</h2>{tl}</div></div></section>
<section aria-labelledby="mn"><div class="wrap"><p class="eyebrow">The menu</p><h2 id="mn">Understood in about a minute.</h2><p>Food first, beer beside it, an optional pairing under each dish, zero-proof as an equal. Discovery is a small flight, never a requirement.</p>{menu}</div></section>
<section class="alt" aria-labelledby="mw"><div class="wrap"><p class="eyebrow">The rest of the world</p><h2 id="mw">Pattern, people, signage, packaging, sound.</h2>
<p>The small things that make it one company. Each opens when you want it.</p>
<details class="more"><summary>Pattern: perforation, weave, tile</summary>
<p>Three simple structures: a screen pierced with circles, strips woven over and under, a tile grid with a broken line. Designers can find parallels for each in many cultures; none is borrowed from a specific one. It appears sparingly (the screen, a menu, a coaster) and cultural reviewers from both traditions must check it before it is used outside a drawing.</p>
{vfig("VI-PATTERN", A.pattern_set(B.uid("pt")), "Vision illustration · pattern grammar", "fig-wide", "820/260")}</details>
<details class="more"><summary>Uniforms that work, not costumes</summary>
<p>Charcoal canvas aprons over bone shirts for the floor and bar. Dark work shirts and boots for the brewers. Dark jackets for the kitchen. Nothing themed, nothing printed across the chest.</p>
{vfig("VI-UNIFORMS", A.uniforms(B.uid("un")), "Vision illustration · uniform concept", "", "860/240")}</details>
<details class="more"><summary>Signage: material first, name second</summary>
<p>A plain blackened-steel panel on a concrete plinth, a slim blade sign under the arcade, a small plaque on the door. The lettering is a placeholder. The name is not legally cleared and there is no logo, so the building is designed to work if the name changes.</p>
{vfig("VI-SIGNAGE", A.signage(B.uid("sg")), "Vision illustration · signage system · placeholder lettering", "", "900/320")}</details>
<details class="more"><summary>Takeout, coaster, bag, napkin</summary>
{vfig("VI-PACKAGING", A.packaging(B.uid("pk")), "Vision illustration · packaging concept · placeholder", "fig-wide", "860/260")}
<p class="muted">Concept drawings with no real labels. No alcohol label is shown or implied as compliant.</p></details>
<details class="more"><summary>Sound: a room you can talk in</summary>
<p>Quiet and warm by day, building gently into the evening. No stock India-plus-Mexico playlist. A small acoustic set might fit one corner. Licensing and permits are unresolved.</p></details></div></section>'''
    return B.layout("craft.html", "The craft · NASHA", "A vision of NASHA's glass, table, menu, uniforms, pattern and packaging. Drawings of what could be, not products.", body)


# ---------------------------------------------------------------- evening
def page_evening(B, S):
    scenes = [("day", "Day", "Limestone, natural light, greenery. The court is cool and quiet; the kitchen is prepping. By golden hour the low sun rakes across the court and the steel screens throw soft patterns."),
              ("night", "Night", "Brass-warm light and the brewery glowing through glass. Social energy, never nightclub lighting. In rain, the arcades become a dry ring around a dark, wet court.")]
    sc = "".join(f'<figure class="scene-card">{vfig("VI-SCENE-" + m.upper(), A.scene(m, B.uid("sc")), "Vision illustration · " + n.lower(), "", "4/3")}<h3>{E(n)}</h3><p>{E(t)}</p></figure>' for m, n, t in scenes)
    times = [("5:30", "Doors open", "Low sun across the court. A cook lights the oven. A brewer checks a tank. The first glasses come off the shelf."),
             ("6:00", "The early table", "Families arrive. A child has a cup of juice while the grown-ups share a tray of Chicken 65 Totopos. Children's drinks stay clearly apart from the beer."),
             ("7:00", "The court fills", "Friends at the long table. Gold light on the limestone. Someone asks about the birria and the server says the consomme comes in a small cup."),
             ("8:00", "The pairing hour", "Hefeweizen beside the birria. A lager beside the totopos. A couple compares a bite with a sip, and laughs. The tanks begin to glow."),
             ("9:00", "Social energy", "The arcade is warm brass. A solo guest at the bar watches the brew deck. Busy, but you can still talk."),
             ("10:00", "Late dinner and the bar", "The court quiets to small groups. A final plate of quesadilla wedges. The oven mouth glows. A brewer wipes down a valve.")]
    tl = '<ol class="evening">' + "".join(f'<li><time>{E(a)}</time><div><h3>{E(b)}</h3><p>{E(c)}</p></div></li>' for a, b, c in times) + "</ol>"
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">One evening · Vision scenario</p><h1 id="h1">An evening at NASHA.</h1>
<p class="lede">What it could feel like, from the first glass to the last plate.</p>
<p class="hero-note">VISION SCENARIO. It tells you how the evening is designed to feel. It invents no sales, guest counts, staff numbers or revenue, and nothing here has happened.</p>
{truth_key()}</div></section>
<section class="alt" aria-labelledby="tl"><div class="wrap"><h2 id="tl" class="visually-hidden">The evening, hour by hour</h2>{tl}</div></section>
<section aria-labelledby="dn"><div class="wrap"><p class="eyebrow">Day to night</p><h2 id="dn">The same place, changing.</h2>
<div class="grid cols-2">{sc}</div></div></section>
<section class="alt" aria-labelledby="ss"><div class="wrap"><h2 id="ss">Through the seasons.</h2>
<ul class="plain"><li><strong>Summer.</strong> Shade, fans, cold glasses and water. Zero-proof coolers lead.</li><li><strong>Winter.</strong> Closed-in warmth, braise and consomme, malt-forward beers, the oven mouth glowing in the north arcade.</li></ul>
<p>See also <a href="court.html">the Court Brewhouse</a> and <a href="craft.html">the craft</a>.</p></div></section>'''
    return B.layout("evening.html", "An evening at NASHA · Vision", "A vision scenario of one evening at a future NASHA, from doors open to late dinner. Not a forecast.", body)


# ---------------------------------------------------------------- walkthrough
def page_walkthrough(B, S):
    steps = [("This is NASHA.", "Food and beer designed together around a shaded court, in Austin.", "index.html", "Home"),
             ("This is the product.", "Five dishes, five beers, a zero-proof drink for each.", "food.html", "Food, then Beer"),
             ("This is the place.", "The Court Brewhouse, from the street to the patio at night.", "court.html", "The Court"),
             ("This is why food and beer belong together.", "One pairing, in plain words.", "pairings.html", "Pairings"),
             ("This is how I am developing it.", "What has been cooked and what has not.", "labs.html", "The Lab"),
             ("This is what is real today.", "A concept in development. Nothing built, cooked or sold.", "investor.html", "Business view"),
             ("This is what capital builds next.", "Proof first, then the room.", "investor.html#capital", "The capital path")]
    items = "".join(f'<li><span class="beat-n" aria-hidden="true">{i}</span><div><h2>{E(a)}</h2><p>{E(b)}</p><p><a href="{h}">{E(l)}</a></p></div></li>' for i, (a, b, h, l) in enumerate(steps, 1))
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">Walkthrough · private</p><h1 id="h1">NASHA in four minutes.</h1>
<p class="lede">A path through this site for one conversation: seven things the founder can say, and one page to show for each.</p>
<p class="hero-note">This is a concept in development, shown privately. It is not an offer and asks for no money.</p></div></section>
<section class="alt"><div class="wrap"><ol class="beats walk">{items}</ol></div></section>'''
    return B.layout("walkthrough.html", "Four-minute walkthrough · NASHA", "A four-minute path through the private NASHA site for one conversation. Concept stage.", body)


# ---------------------------------------------------------------- investor additions
def assumed_section():
    rows = vrows("VISION-ASSUMPTIONS.csv")
    r = "".join(f'<tr><th scope="row">{E(x["area"])}</th><td>{E(x["assumption"])}</td><td>{E(x["implementation_gate"])}</td></tr>' for x in rows)
    return (f'<details id="assumed"><summary>What the vision assumes ({len(rows)} choices)</summary>'
            f'<p>The pictures and the Court pages resolve open questions on purpose, so one place can be imagined. Each is a vision assumption, not a decision, and the blueprint is unchanged. Future evidence may reject any of them.</p>'
            f'<div class="scroll-x" tabindex="0" role="region" aria-label="Vision assumptions, scrolls sideways on small screens"><table><caption class="visually-hidden">Vision assumptions</caption>'
            f'<thead><tr><th scope="col">Area</th><th scope="col">What is assumed</th><th scope="col">What must happen before it is real</th></tr></thead><tbody>{r}</tbody></table></div></details>')
