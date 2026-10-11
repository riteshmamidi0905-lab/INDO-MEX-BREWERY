#!/usr/bin/env python3
"""Build the NASHA static site into website/dist/. Python stdlib + Pillow (images only).
Run: python3 website/build.py
Content: website/data/*.json (audited wording) and visuals/NASHA-VISUAL-MANIFEST.csv (canonical visual manifest).
Where a manifest row has a raster source file, a responsive <picture> is emitted; otherwise a drawn stand-in (website/art.py) is used."""
import csv, hashlib, html, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art, images  # noqa: E402

SRC, DATA, DIST = (os.path.join(HERE, p) for p in ("src", "data", "dist"))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(REPO, "visuals/NASHA-VISUAL-MANIFEST.csv")
BUILD_DATE = "2026-10-11"
E = html.escape

def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)

dishes, beers = load("dishes.json"), load("beers.json")
crossing, status, labs = load("crossing.json"), load("status.json"), load("labs.json")
BEER = {b["id"]: b for b in beers}
BEER_BY_NAME = {b["name"]: b for b in beers}
DISH = {d["id"]: d for d in dishes}
VIS = {r["id"]: r for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))}
RASTER_META = {}

PAGES = [("index.html", "Home"), ("experience.html", "Experience"), ("space.html", "Space"), ("food.html", "Food"),
         ("beer.html", "Beer"), ("crossing.html", "The Crossing"), ("labs.html", "Labs"), ("about.html", "About")]

DISCLOSE = ("NASHA is in development. There is no brewery, no restaurant, no truck and no menu for sale yet. "
            "Images are concept visualizations and illustrations, not photographs of NASHA.")
CONCEPT_NOTE = "Concept visualization. Final architecture is subject to professional design and site conditions."

PLATE_KIND = {"chicken-65-totopos": "totopos", "chaat-elote": "elote", "gobi-taco": "taco", "paneer-tikka-taco": "taco2",
              "butter-chicken-quesadilla": "quesadilla", "goat-birria": "birria", "cardamom-churros": "churros", "seed-chile-bowl": "veg"}
SIGNATURE = ["chicken-65-totopos", "paneer-tikka-taco", "gobi-taco", "butter-chicken-quesadilla", "goat-birria", "chaat-elote", "cardamom-churros"]
GATE_BEERS = ["hefeweizen", "mexican-lager", "vienna-amber"]

_uid = [0]
def uid(p="u"):
    _uid[0] += 1
    return f"{p}{_uid[0]}"

# ---------- figures ----------
def tag_html(kind):
    if kind == "raster":
        return ('<figcaption class="tag">Concept visualization<span class="visually-hidden">. Not a photograph of NASHA. '
                'Final architecture is subject to professional design and site conditions.</span></figcaption>')
    return '<figcaption class="tag">Concept illustration<span class="visually-hidden">. A drawing, not a photograph.</span></figcaption>'

def raster_fig(vid, cls="", eager=False, sizes="100vw"):
    row = VIS[vid]; meta = RASTER_META[vid]
    pic = images.picture_html(row, meta, E(row["alt_text"]), sizes, eager)
    st = f'--ar-d:{meta["d"]["w"]}/{meta["d"]["h"]};--ar-m:{meta["m"]["w"]}/{meta["m"]["h"]}'
    return f'<figure class="fig {cls}" data-vid="{vid}" style="{st}">{pic}{tag_html("raster")}</figure>'

def svg_fig(vid, svg, cls="", ar="16/10"):
    return f'<figure class="fig fig-art {cls}" data-vid="{vid}" style="--ar-d:{ar};--ar-m:{ar}">{svg}{tag_html("vector")}</figure>'

# ---------- layout ----------
def layout(fn, title, desc, body, head_extra="", body_class=""):
    nav = "".join(f'<li><a href="{f}"{" aria-current=\"page\"" if f == fn else ""}>{E(n)}</a></li>' for f, n in PAGES)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="noindex, nofollow">
<meta name="color-scheme" content="dark light">
<link rel="preload" href="fonts/instrument-serif-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
{head_extra}<link rel="icon" href="data:,">
<script>document.documentElement.className="js"</script>
<link rel="stylesheet" href="styles.css">
</head>
<body class="{body_class}">
<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap">
<a class="wordmark" href="index.html" aria-label="NASHA, home">NASHA</a>
<nav class="nav" aria-label="Main"><ul>{nav}</ul></nav>
<button id="theme-toggle" class="btn btn-ghost" type="button" aria-pressed="true">Light / dark</button>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-footer"><div class="wrap stack">
<p><strong>NASHA</strong> is a future Indo-Mex brewery and kitchen in Austin, Texas, in development.</p>
<p>The name was chosen by the founder. Legal clearance of the name is pending. Nothing here claims trademark ownership. There is no brewery, restaurant or truck open, and nothing is for sale. No site has been chosen.</p>
<p>In Hindi and Urdu, <em>nasha</em> means intoxication or addiction. We chose it for the feeling of being captivated by food and beer. We take that meaning seriously and will never present excess or addiction as something to admire. Cultural advisors will review the name and our language before launch.</p>
<p>Images show a possible future. The photographic-style pictures are <strong>concept visualizations</strong> made with AI tools and edited, and the drawings are illustrations. They are not photographs of NASHA, of its food, or of its beer. <a href="about.html#images">About these images</a>.</p>
<p>Menu items are designs for testing, not served food. Heat and vegetarian labels describe how a dish is designed, not a certified allergen or dietary statement. Ask before you eat if you have an allergy. If you drink, drink responsibly. Alcohol is for adults of legal drinking age.</p>
<p>The word NASHA in the header and in some pictures is a <strong>temporary typographic placeholder</strong>, set in a standard font. It is not a logo, not an official brand mark, and no trademark is claimed. No logo has been approved or released.</p>
<p>Build of {BUILD_DATE}.</p>
</div></footer>
<script src="app.js" defer></script>
</body>
</html>
'''

def chips(*items):
    return "".join(f'<span class="chip">{E(i)}</span>' for i in items if i)

def heat(n):
    dots = "".join(f'<i class="{"on" if k < n else ""}"></i>' for k in range(3))
    return f'<span class="heat" aria-hidden="true">{dots}</span><span class="visually-hidden">Heat {n} of 3</span>'

def pair_names(d):
    return ", ".join(d["pairing"])

def plate_svg(d):
    return art.plate(uid("pl"), PLATE_KIND.get(d["id"], "veg" if d["vegetarian"] else "taco"))

# ---------- cards ----------
def dish_card(d, h="h2", with_art=False):
    veg = '<span class="chip chip-veg">Vegetarian as designed</span>' if d["vegetarian"] else ""
    thumb = f'<div class="thumb">{plate_svg(d)}</div>' if with_art else ""
    return f'''<article class="card" data-item data-category="{E(d["category"])}" data-diet="{"veg" if d["vegetarian"] else "any"}" data-heat="{d["heat"]}">
{thumb}<{h}>{E(d["name"])}</{h}>
<p>{E(d["line"])}</p>
<p>{chips(d["kind"], d["status"], d["category"])}{veg}</p>
<dl class="meta"><dt>Inspiration</dt><dd>{E(d["inspiration"])}</dd>
<dt>Made with</dt><dd>{E(", ".join(d["ingredients"]))}</dd>
<dt>Heat</dt><dd>{heat(d["heat"])} · cooling: {E(d["cooling"] or "none")}</dd>
<dt>Designed to pair with</dt><dd>{E(pair_names(d))}</dd></dl></article>'''

def beer_card(b, h="h2"):
    work = '<p class="muted">Working name. May change. Style and colour are not settled, so the glass is shown as a faint outline.</p>' if b["working"] else ""
    g = art.glass(uid("bg"), b["id"], 0.86, "weizen" if b["glass"] == "Collar Weizen" else "lager", animate=False, title=f"Concept glass for {b['name']}")
    return f'''<article class="card" data-item data-group="{E(b["group"])}">
<div class="beer-row"><div class="mini-glass">{g}</div><div><{h}>{E(b["name"])}</{h}>
<p>{E(b["line"])}</p><p>{chips(b["style"], b["season"], "Not brewed yet")}</p>{work}
<dl class="meta"><dt>Served in</dt><dd>{E(b["glass"])}</dd><dt>Designed to pair with</dt><dd>{E(", ".join(b["pairs"]))}</dd></dl></div></div></article>'''

def filter_inputs(name, values):
    return "".join(f'<label><input type="checkbox" name="{name}" value="{E(v)}"> {E(t)}</label>' for v, t in values)

# ---------- shared components ----------
def pairing_comp(dish_id, beer_id, label_h="h3"):
    d, b = DISH[dish_id], BEER[beer_id]
    g = art.glass(uid("pg"), beer_id, .86, "weizen" if b["glass"] == "Collar Weizen" else "lager", animate=False, title=f"Concept glass of {b['name']}")
    return f'''<article class="pair reveal" data-vid="NV-ILL-PLATES"><div class="pair-art"><div class="pair-plate">{plate_svg(d)}</div><div class="pair-glass">{g}</div></div>
<{label_h}>{E(d["name"])} <span class="amp">+</span> {E(b["name"])}</{label_h}>
<p class="chip-row">{chips("Proposed pairing", "Not sensory-tested", "Not brewed yet")}</p></article>'''

def two_pour():
    d = DISH["chicken-65-totopos"]
    g1 = art.glass(uid("tp"), "mexican-lager", .88, "lager", animate=False, title="Concept glass, first beer")
    g2 = art.glass(uid("tp"), "hefeweizen", .88, "weizen", animate=False, title="Concept glass, second beer")
    steps = [("1", "Beer one", "A cold, clean Mexican-Style Lager arrives first, as designed.", g1),
             ("2", "The dish", "Chicken 65 Totopos, a designed Chennai-style bar snack with masa chips.", f'<div class="tp-plate">{plate_svg(d)}</div>'),
             ("3", "Beer two", "Then a Hefeweizen alongside the same dish, as designed.", g2)]
    li = "".join(f'<li class="tp-step" data-step="{n}"><span class="tp-n">{n}</span><div class="tp-art">{a}</div><h3>{t}</h3><p>{p}</p></li>' for n, t, p, a in steps)
    return f'''<div class="two-pour" data-two-pour data-active="1">
<ol class="tp-steps">{li}</ol>
<div class="tp-controls" aria-label="Walk through the Two-Pour ritual"><button type="button" class="btn btn-ghost" data-tp="prev">Back</button><button type="button" class="btn" data-tp="next">Next step</button><span class="visually-hidden" role="status" aria-live="polite" data-tp-status></span></div>
<p class="tp-learn"><strong>How the experience might change:</strong> the same bite, tasted after two different beers. That is a hypothesis for a tasting, not a result. No guest has tried it, and no beer has been brewed.</p>
</div>'''

def pairs_section(h="h3"):
    combos = [("paneer-tikka-taco", "hefeweizen"), ("chicken-65-totopos", "mexican-lager"), ("goat-birria", "vienna-amber"), ("chaat-elote", "mexican-lager")]
    return "".join(pairing_comp(d, b, h) for d, b in combos)

# ---------- pages ----------
def hero_head():
    m = RASTER_META["NV-HERO-01"]
    d = [f for f in m["d"]["files"] if f["fmt"] == "avif" and f["w"] in (1600,)][0]
    mm = [f for f in m["m"]["files"] if f["fmt"] == "avif" and f["w"] == 800][0]
    return (f'<link rel="preload" as="image" type="image/avif" media="(min-width: 701px)" href="images/{d["file"]}">\n'
            f'<link rel="preload" as="image" type="image/avif" media="(max-width: 700px)" href="images/{mm["file"]}">\n')

def page_index():
    hero = raster_fig("NV-HERO-01", "fig-hero", eager=True, sizes="100vw")
    sig = [DISH[i] for i in ("chicken-65-totopos", "paneer-tikka-taco", "butter-chicken-quesadilla")]
    food = "".join(f'<article class="feature reveal"><div class="plate-big">{plate_svg(d)}</div><h3>{E(d["name"])}</h3><p>{E(d["line"])}</p><p>{chips("Proposed presentation", d["status"])}</p></article>' for d in sig)
    beer = "".join(f'<article class="feature reveal"><div class="glass-big">{art.glass(uid("hb"), b, .86, "weizen" if BEER[b]["glass"] == "Collar Weizen" else "lager", animate=True, title=f"Concept glass of {BEER[b]["name"]}")}</div><h3>{E(BEER[b]["name"])}</h3><p>{E(BEER[b]["line"])}</p><p>{chips("Not brewed yet")}</p></article>' for b in GATE_BEERS)
    motifs = "".join(f'<li class="reveal">{art.motif(m, uid("mo"))}<span>{E(l)}</span></li>' for m, l in [("smoke", "Fire"), ("acid", "Acid"), ("spice", "Spice"), ("fermentation", "Fermentation")])
    status_items = "".join(f'<li{" class=\"current\"" if it["state"] == "Designing" else ""}><span class="stage">{E(it["state"])}</span><h3>{E(it["name"])}</h3><p>{E(it["note"])}</p></li>' for it in status["items"])
    body = f'''
<section class="hero" aria-labelledby="h1">
{hero}
<div class="wrap hero-copy">
<p class="eyebrow">Austin, Texas · In development</p>
<h1 id="h1">Food and beer, designed together.</h1>
<p class="lede">NASHA is a future Indo-Mex brewery and kitchen. Fire in the kitchen, fermentation in the glass hall, one long table between them.</p>
<p class="disclosure">{E(DISCLOSE)}</p>
</div></section>

<section aria-labelledby="b2"><div class="wrap grid cols-2 center">
<div class="reveal"><p class="eyebrow"><span class="beat-no">02</span> Food × Beer</p><h2 id="b2" class="statement">Each dish names the beers it is meant to meet.</h2>
<p class="lede">India and Mexico both build flavour from chile, lime, toasted spice, flatbread and fermentation. NASHA starts from what they share and lets each stay itself.</p>
<p>The food and the beer are specified together. That is a design goal we intend to test, not a result we have.</p></div>
<div class="reveal">{svg_fig("NV-ILL-PLATES", '<div class="duo"><div class="duo-plate">' + plate_svg(DISH["chicken-65-totopos"]) + '</div><div class="duo-glass">' + art.glass(uid("dg"), "mexican-lager", .88, "lager", True, "Concept glass of Mexican-style lager") + '</div></div>', "fig-duo", "4/3")}</div>
</div></section>

<section class="fire-ferment" aria-labelledby="b3"><div class="wrap">
<p class="eyebrow"><span class="beat-no">03</span> Fire × Fermentation</p>
<h2 id="b3" class="statement reveal">Food transformed by fire. Beer transformed by fermentation.</h2>
<div class="grid cols-2 ff">
<div class="reveal">{svg_fig("NV-ILL-FIRE", art.fire_scene(uid("fire")), "", "8/5")}<h3>Fire</h3><p>A clay tandoor and a flat comal: char, smoke and quick heat. This is how the kitchen is designed to cook.</p></div>
<div class="reveal">{svg_fig("NV-ILL-FERMENT", art.ferment_scene(uid("fm")), "", "8/5")}<h3>Fermentation</h3><p>Steel tanks behind glass, so the slow work is visible. Tank size and count are not decided.</p></div>
</div></div></section>

<section aria-labelledby="b4"><div class="wrap">
<p class="eyebrow"><span class="beat-no">04</span> The food</p>
<h2 id="b4">Dishes, as designed.</h2>
<p>Drawn here as proposed presentation. No dish has been cooked for guests, and these are not photographs. <a href="food.html">See the whole menu</a>.</p>
<div class="grid cols-3">{food}</div></div></section>

<section class="alt" aria-labelledby="b5"><div class="wrap">
<p class="eyebrow"><span class="beat-no">05</span> The beer</p>
<h2 id="b5">Beer briefs, not beers yet.</h2>
<p>Nothing has been brewed. These glasses are concept drawings of briefs for a head brewer to critique. <a href="beer.html">Meet the beers</a>.</p>
<div class="grid cols-3">{beer}</div></div></section>

<section class="band-indigo crossing-band" aria-labelledby="b6">{art.jali(uid("jl"))}<div class="wrap grid cols-2 center rel">
<div><p class="eyebrow"><span class="beat-no">06</span> The Crossing</p><h2 id="b6" class="statement">Where India and Mexico already meet.</h2>
<p class="lede">Chile, lime, toasted seeds, flatbread, fermentation. We separate what history supports from what is only a good comparison.</p><p><a href="crossing.html">Enter the Crossing</a></p></div>
<ul class="motifs">{motifs}</ul></div></section>

<section aria-labelledby="b7"><div class="wrap">
<p class="eyebrow"><span class="beat-no">07</span> The place</p>
<h2 id="b7">A hall we have only imagined.</h2>
<p>Stone and glass, a timber arcade, a covered court under an oak. A concept: no site is chosen and nothing is engineered. <a href="space.html">Walk through it</a>.</p>
<div class="grid cols-2">{raster_fig("NV-SPACE-EXT-DAY", "reveal", sizes="(max-width: 700px) 100vw, 50vw")}{raster_fig("NV-SPACE-PATIO", "reveal", sizes="(max-width: 700px) 100vw, 50vw")}</div></div></section>

<section class="alt" aria-labelledby="b8"><div class="wrap">
<p class="eyebrow"><span class="beat-no">08</span> The table</p>
<h2 id="b8" class="statement">Plates and pitchers for the middle of the table.</h2>
<p>Designed for sharing: five dishes, six glasses, one long table. <a href="experience.html">See an evening at NASHA</a>.</p>
{svg_fig("NV-ILL-TABLE", art.table_scene(uid("tb")), "reveal fig-wide", "960/420")}</div></section>

<section aria-labelledby="b9"><div class="wrap">
<p class="eyebrow"><span class="beat-no">09</span> We are building it</p>
<h2 id="b9">Honest status.</h2>
<ul class="path">{status_items}</ul>
<p class="muted">Nothing is in Testing or Validated yet. We will say so when that changes. <a href="labs.html">See Labs</a>. About the word <em>nasha</em> and our commitments: <a href="about.html">About NASHA</a>.</p></div></section>

<section class="alt" aria-labelledby="b10"><div class="wrap">
<p class="eyebrow"><span class="beat-no">10</span> Follow NASHA</p>
<h2 id="b10">Updates are not live yet.</h2>
<p>We have not set up a mailing list, domain or contact address, so we will not pretend to collect your email. This page will change when that is real.</p>
<button class="btn" type="button" disabled>Updates coming later</button></div></section>
'''
    return layout("index.html", "NASHA: Indo-Mex brewery and kitchen, in development",
                  "NASHA is a future Indo-Mex brewery and kitchen in Austin, Texas. In development. Nothing is for sale yet.", body, hero_head(), "home")

def page_experience():
    sc = [
     ("Arrival", "Curiosity", "You would see the sign first, then warm light through glass, then the tanks.", raster_fig("NV-SPACE-ENTRANCE", "", sizes="(max-width: 700px) 100vw, 50vw")),
     ("The bar", "Refreshment", "A long bar, a wall of taps and a shelf of glasses, with the brewery in sight behind it.", svg_fig("NV-ILL-BAR", art.bar_scene(uid("ba")), "", "960/500")),
     ("The table", "Belonging", "Long tables for sharing. Plates go in the middle and glasses go round.", svg_fig("NV-ILL-TABLE", art.table_scene(uid("tb")), "", "960/420")),
     ("The food", "Hunger", "Fusion dishes and our own: Chicken 65 on masa chips, tacos, a braise, charred corn. All still being designed.", svg_fig("NV-ILL-PLATES", '<div class="plates3">' + "".join(f'<div>{plate_svg(DISH[i])}</div>' for i in ("chicken-65-totopos", "paneer-tikka-taco", "goat-birria")) + '</div>', "fig-plates", "3/1")),
     ("The beer", "Refreshment", "Light and crisp, wheat, toasty. Each beer is a brief with named dishes it is meant to meet.", svg_fig("NV-ILL-GLASS", '<div class="glass-row">' + "".join(art.glass(uid("eg"), b, .86, "weizen" if BEER[b]["glass"] == "Collar Weizen" else "lager", True, f"Concept glass of {BEER[b]['name']}") for b in GATE_BEERS) + '</div>', "fig-glasses", "3/1")),
     ("The fire", "Warmth", "A tandoor and a comal in an open kitchen, so you can watch food meet fire.", svg_fig("NV-ILL-FIRE", art.fire_scene(uid("fi")), "", "8/5")),
     ("The brewery", "Wonder", "Tanks behind glass: the slow work of fermentation, in view. Size and count are not decided.", raster_fig("NV-BREWERY-GLASS", "", sizes="(max-width: 700px) 100vw, 50vw")),
     ("The patio", "Staying", "A covered court under an oak, shade and fans for the heat, lights for the evening.", raster_fig("NV-SPACE-PATIO", "", sizes="(max-width: 700px) 100vw, 50vw")),
     ("Night", "Wanting to come back", "By dusk the hall glows, the court fills, and nobody is in a hurry.", raster_fig("NV-HERO-01", "", sizes="(max-width: 700px) 100vw, 50vw"))]
    rows = "".join(f'<section class="scene{" alt" if i % 2 else ""}" aria-labelledby="sc{i}"><div class="wrap grid cols-2 center"><div class="reveal{" order-2" if i % 2 else ""}"><p class="eyebrow"><span class="beat-no">{i+1:02d}</span> {E(feel)}</p><h2 id="sc{i}">{E(t)}</h2><p class="lede">{E(txt)}</p></div><div class="reveal">{fig}</div></div></section>' for i, (t, feel, txt, fig) in enumerate(sc))
    body = f'''<section aria-labelledby="h1"><div class="wrap">
<p class="eyebrow">Experience</p><h1 id="h1">An evening at NASHA.</h1>
<p class="lede">This is what the evening is designed to feel like, from the walk up to the last pour. It is a design, written in the conditional, because NASHA does not exist yet.</p>
<p class="disclosure">{E(DISCLOSE)} Nobody has tested this evening.</p></div></section>
{rows}
<section class="band-indigo" aria-labelledby="exf"><div class="wrap grid cols-2 center"><div><h2 id="exf">Before the hall, the test.</h2><p class="lede">The path to this evening starts smaller: tastings, pop-ups, perhaps a brewery residency. Each step has to earn the next.</p><p><a href="labs.html">See the path</a></p></div>{svg_fig("NV-ILL-POPUP", art.popup_scene(uid("pu")), "", "960/500")}</div></section>'''
    return layout("experience.html", "Experience · NASHA", "What an evening at NASHA is designed to feel like. A concept, not a built place.", body)

def page_space():
    def step(i, name, emo, txt, fig):
        return f'<section class="scene{" alt" if i % 2 else ""}" id="{name.lower().replace(" ", "-")}" aria-labelledby="s{i}"><div class="wrap grid cols-2 center"><div class="reveal{" order-2" if i % 2 else ""}"><p class="eyebrow"><span class="beat-no">{i+1:02d}</span> {E(emo)}</p><h2 id="s{i}">{E(name)}</h2><p>{E(txt)}</p></div><div class="reveal">{fig}</div></div></section>'
    s = [("Exterior", "Desire to visit", "A limestone-and-glass hall with timber arcade and perforated screens, set among native grasses and oaks.", raster_fig("NV-SPACE-EXT-DAY", "", sizes="(max-width: 700px) 100vw, 50vw")),
         ("Entrance", "Curiosity", "The first view is the point: warm light, a door, and tanks you can see from outside.", raster_fig("NV-SPACE-ENTRANCE", "", sizes="(max-width: 700px) 100vw, 50vw")),
         ("Bar", "Refreshment", "Taps, a tiled front and a back bar of glassware, with a sightline to the brewery.", svg_fig("NV-ILL-BAR", art.bar_scene(uid("ba")), "", "960/500")),
         ("Brewery", "Wonder", "Equipment behind glass. Everything here is illustrative: tank size, count and layout are an open decision.", raster_fig("NV-BREWERY-HALL", "", sizes="(max-width: 700px) 100vw, 50vw")),
         ("Kitchen", "Hunger", "An open kitchen with fire at its centre: a tandoor and a comal.", svg_fig("NV-ILL-FIRE", art.fire_scene(uid("fi")), "", "8/5")),
         ("Dining", "Belonging", "Long communal tables and plates for the middle.", svg_fig("NV-ILL-TABLE", art.table_scene(uid("tb")), "", "960/420")),
         ("Patio", "Staying", "A covered court with shade and fans for Texas heat, greenery, and light for the evening.", raster_fig("NV-SPACE-PATIO", "", sizes="(max-width: 700px) 100vw, 50vw"))]
    steps = "".join(step(i, *x) for i, x in enumerate(s))
    body = f'''<section aria-labelledby="h1"><div class="wrap">
<p class="eyebrow">Space</p><h1 id="h1">A walk through the hall.</h1>
<p class="lede">From the road to the patio, in seven steps.</p>
<p class="disclosure">{E(CONCEPT_NOTE)} These are not construction plans. No site has been chosen and NASHA has no address. {E(DISCLOSE)}</p></div></section>
{steps}
<section class="band-indigo" aria-labelledby="zn"><div class="wrap grid cols-2 center"><div><h2 id="zn">How the zones relate.</h2><p>A concept diagram, not a floor plan.</p></div><div>{svg_fig("NV-ILL-ZONES", ZONE_SVG, "fig-zone", "870/370")}</div></div></section>'''
    return layout("space.html", "Space · NASHA", "A conceptual walkthrough of a future NASHA hall. Concept visualization, not construction plans.", body)

def menu_card():
    cats = ["Small", "Tacos", "Quesadillas", "Birria", "Large", "Dessert"]
    out = ""
    for c in cats:
        items = [d for d in dishes if d["category"] == c and d["wave"] == "Test set"]
        if not items: continue
        li = "".join(f'<li><div class="mi-head"><span class="mi-name">{E(d["name"])}</span>{"<span class=\"mi-v\" title=\"Vegetarian as designed\">V</span>" if d["vegetarian"] else ""}<span class="mi-heat">{heat(d["heat"])}</span></div><p class="mi-desc">{E(", ".join(d["ingredients"][:5]))}</p><p class="mi-pair">Designed to pair with {E(pair_names(d))}</p></li>' for d in items)
        out += f'<section class="mc-cat" aria-label="{E(c)}"><h3>{E(c)}</h3><ul>{li}</ul></section>'
    legend = f'<p class="mc-legend"><span class="mi-v">V</span> vegetarian as designed · {heat(1)} mild {heat(2)} medium {heat(3)} hot · pairings are proposed and untested · no prices · availability not promised</p>'
    return f'<div class="menu-card" data-vid="NV-ILL-MENU"><p class="tag-inline">Proposed menu design</p>{out}{legend}</div>'

def flight_card():
    items = [BEER[b] for b in ("mexican-lager", "hefeweizen", "vienna-amber", "dunkelweizen")]
    li = "".join(f'<li>{art.glass(uid("fl"), b["id"], .8, "weizen" if b["glass"] == "Collar Weizen" else "lager", False, f"Concept glass of {b["name"]}")}<div><strong>{E(b["name"])}</strong><br><span class="muted">{E(b["style"])}</span></div></li>' for b in items)
    return f'<div class="flight-card"><p class="tag-inline">Tasting flight · proposed · not brewed yet</p><ul>{li}</ul><p class="muted">Four small pours. Names are proposals. No prices, no availability.</p></div>'

def page_food():
    sig = [DISH[i] for i in SIGNATURE]
    hero = sig[0]
    cards = "".join(f'<article class="feature reveal"><div class="plate-big">{plate_svg(d)}</div><h3>{E(d["name"])}</h3><p>{E(d["line"])}</p><p>{chips(d["kind"], "Proposed presentation")}{"<span class=\"chip chip-veg\">Vegetarian as designed</span>" if d["vegetarian"] else ""}</p><p class="muted">Heat {heat(d["heat"])} · pairs with {E(pair_names(d))}</p></article>' for d in sig[1:])
    veg = [d for d in dishes if d["vegetarian"] and d["wave"] == "Test set"]
    vegli = "".join(f'<li>{E(d["name"])}<span class="muted"> — {E(d["line"])}</span></li>' for d in veg)
    cats = sorted({d["category"] for d in dishes})
    f = filter_inputs("category", [(c, c) for c in cats]) + filter_inputs("diet", [("veg", "Vegetarian as designed")]) + filter_inputs("heat", [(str(i), f"Heat {i}") for i in range(4)])
    body = f'''<section class="food-hero" aria-labelledby="h1"><div class="wrap grid cols-2 center">
<div><p class="eyebrow">Food · Designs for testing</p><h1 id="h1">Hunger, designed.</h1>
<p class="lede">A Chennai bar snack scooped with fresh masa chips. A braise that borrows from two kitchens. Twelve dishes are specified for a first round of kitchen tests. None are cooked for guests. None are for sale.</p>
<p class="disclosure">{E(DISCLOSE)} The drawings are proposed presentation, not our finished dishes.</p></div>
<div class="reveal"><div class="hero-plate">{plate_svg(hero)}</div><h2 class="h3">{E(hero["name"])}</h2><p>{E(hero["line"])}</p><p>{chips(hero["kind"], "Proposed presentation")}</p></div></div></section>

<section class="alt" aria-labelledby="sg"><div class="wrap"><p class="eyebrow">Signature dishes</p><h2 id="sg">The first plates we would test.</h2>
<div class="grid cols-3">{cards}</div></div></section>

<section aria-labelledby="vg"><div class="wrap grid cols-2 center"><div><p class="eyebrow">Vegetarian story</p><h2 id="vg">Vegetarian is not a side.</h2>
<p class="lede">India has a deep vegetarian cooking tradition and Mexico builds great dishes on corn, beans and chile. NASHA designs vegetarian dishes as headliners, not substitutes.</p>
<p class="muted">Labels say “vegetarian as designed”. They are not a certified dietary statement; cross-contact is not assessed yet.</p></div>
<ul class="veglist">{vegli}</ul></div></section>

<section class="fire-ferment" aria-labelledby="fr"><div class="wrap grid cols-2 center"><div><p class="eyebrow">Fire</p><h2 id="fr">Char, smoke, quick heat.</h2><p class="lede">Tandoor-style heat and a hot comal give the food its edges. Fire is how the kitchen is designed to work, and how the beer is meant to be met.</p><p><a href="crossing.html">The Crossing</a></p></div>
<div class="reveal">{svg_fig("NV-ILL-FIRE", art.fire_scene(uid("fi")), "", "8/5")}</div></div></section>

<section class="alt" aria-labelledby="pr"><div class="wrap"><p class="eyebrow">Pairing</p><h2 id="pr">Proposed pairings.</h2>
<p>Each dish names the beers it is meant to meet. These are design intentions. Nothing has been tasted together, and no beer has been brewed.</p>
<div class="grid cols-2 pairs">{pairs_section()}</div></div></section>

<section aria-labelledby="mn"><div class="wrap"><p class="eyebrow">The menu</p><h2 id="mn">A proposed menu design.</h2>
<div class="grid cols-2 menu-grid"><div class="reveal">{svg_fig("NV-ILL-MENU", art.menu_cover(uid("mc")), "fig-menu", "420/580")}{flight_card()}</div><div class="reveal">{menu_card()}</div></div></div></section>

<section class="alt" aria-labelledby="all"><div class="wrap">
<p class="eyebrow">Full development menu</p><h2 id="all">Every dish in the test plan.</h2>
<fieldset class="filters" data-filter-group="dish-list" data-status="dish-status"><legend>Filter dishes</legend>{f}<button type="button" class="btn btn-ghost" data-reset>Clear</button></fieldset>
<p id="dish-status" class="muted" role="status" aria-live="polite"></p>
<div id="dish-list" class="grid cols-3">{"".join(dish_card(d, "h3", False) for d in dishes)}</div>
<p class="muted">“Fusion” means a dish we invented by combining two traditions. “Inspired by” means built from a tradition without claiming to be it. The lamb dish depends on an unresolved cut decision.</p></div></section>'''
    return layout("food.html", "Food · NASHA", "Dishes NASHA is designing for kitchen tests. Proposed presentation only. None are for sale.", body)

def page_beer():
    macro = art.glass(uid("mg"), "hefeweizen", .9, "weizen", True, "Concept macro glass of a wheat beer", big=True)
    gate = "".join(f'<article class="feature reveal"><div class="glass-big">{art.glass(uid("gb"), b, .86, "weizen" if BEER[b]["glass"] == "Collar Weizen" else "lager", True, f"Concept glass of {BEER[b]["name"]}")}</div><h3>{E(BEER[b]["name"])}</h3><p>{E(BEER[b]["line"])}</p><p>{chips(BEER[b]["style"], "Not brewed yet")}</p><p class="muted">Designed to pair with {E(", ".join(BEER[b]["pairs"][:3]))}</p></article>' for b in GATE_BEERS)
    groups = sorted({b["group"] for b in beers})
    f = filter_inputs("group", [(g, g) for g in groups])
    sw = "".join(f'<button type="button" class="swatch" data-beer="{b}" aria-pressed="{"true" if b == "hefeweizen" else "false"}">{E(BEER[b]["name"])}</button>' for b in GATE_BEERS)
    body = f'''<section class="beer-hero" aria-labelledby="h1"><div class="wrap grid cols-2 center">
<div><p class="eyebrow">Beer · Briefs for a brewer</p><h1 id="h1">Built for the table.</h1>
<p class="lede">Beer designed to meet the food: crisp enough to cool the heat, round enough to hold a char. Nothing has been brewed. Each beer is a brief for a head brewer to critique, change, or reject.</p>
<div class="swatches js-only" role="group" aria-label="Preview a beer colour">{sw}</div>
<p class="disclosure">{E(DISCLOSE)} Alcohol is for adults of legal drinking age. Any future beer sales depend on licences we have not yet obtained.</p></div>
<div class="macro" data-macro data-beer="hefeweizen" data-vid="NV-ILL-GLASS">{macro}<p class="tag-inline">Concept illustration · colour follows the style reference, not a brewed beer</p></div></div></section>

<section class="alt" aria-labelledby="gt"><div class="wrap"><p class="eyebrow">Gate beers</p><h2 id="gt">The three we would brew first.</h2>
<div class="grid cols-3">{gate}</div></div></section>

<section aria-labelledby="ex"><div class="wrap"><p class="eyebrow">Beer explorer</p><h2 id="ex">All nine briefs.</h2>
<fieldset class="filters" data-filter-group="beer-list" data-status="beer-status"><legend>Filter beers</legend>{f}<button type="button" class="btn btn-ghost" data-reset>Clear</button></fieldset>
<p id="beer-status" class="muted" role="status" aria-live="polite"></p>
<div id="beer-list" class="grid cols-3">{"".join(beer_card(b, "h3") for b in beers)}</div>
<p class="muted">No ABV, IBU, recipe, award or availability is stated because none exists. Names marked “working name” may change.</p></div></section>

<section class="alt" aria-labelledby="pp"><div class="wrap"><p class="eyebrow">Pairings</p><h2 id="pp">Proposed pairings.</h2>
<div class="grid cols-2 pairs">{pairs_section()}</div></div></section>

<section aria-labelledby="tp"><div class="wrap"><p class="eyebrow">The Two-Pour ritual</p><h2 id="tp">One dish. Two beers.</h2>
<p class="lede">A proposed way to eat: the same dish after two different pours. It is a design idea to test in tastings.</p>{two_pour()}</div></section>

<section class="alt" aria-labelledby="bv"><div class="wrap grid cols-2 center"><div><p class="eyebrow">Brewery vision</p><h2 id="bv">The brewery in plain sight.</h2>
<p class="lede">The imagined brewhouse sits behind glass so guests can see the work. The equipment in this picture is illustrative: the vessel size and count are an open decision and nothing here fixes them.</p></div>
<div class="reveal">{raster_fig("NV-BREWERY-GLASS", "", sizes="(max-width: 700px) 100vw, 50vw")}</div></div></section>

<section aria-labelledby="hs"><div class="wrap"><p class="eyebrow">Honest status</p><h2 id="hs">Not brewed yet.</h2>
<p>No beer exists. There is no brewer on the team, no recipe and no licence. The first beers, if any, would likely be made with a partner brewery under rules we are still learning. <a href="labs.html">Follow the path in Labs</a>.</p></div></section>'''
    return layout("beer.html", "Beer · NASHA", "Beer briefs for a future NASHA brewery, built for the table. Nothing has been brewed.", body)

def page_crossing():
    secs = ""
    vis = {"smoke": ("NV-ILL-FIRE", art.fire_scene(uid("cf")), "8/5"), "fermentation": ("NV-ILL-FERMENT", art.ferment_scene(uid("cm")), "8/5")}
    for i, c in enumerate(crossing):
        v = vis.get(c["id"])
        side = svg_fig(*v[:2], "", v[2]) if v else f'<div class="motif-big">{art.motif(c["id"], uid("mt"))}</div>'
        secs += f'''<section class="cross-sec{" alt" if i % 2 else ""}" aria-labelledby="c{i}"><div class="wrap grid cols-2 center"><div class="reveal{" order-2" if i % 2 else ""}">{side}</div>
<div class="reveal"><p class="eyebrow">{E(c["theme"])} · <span class="ev ev-{E(c["evidence"].lower())}">{E(c["evidence"])}</span></p><h2 id="c{i}">{E(c["nasha"].split(":")[0] if False else c["theme"])}</h2>
<div class="cross-pair"><div><h3>India</h3><p>{E(c["india"])}</p></div><div><h3>Mexico</h3><p>{E(c["mexico"])}</p></div></div>
<p class="lede nasha-line"><strong>NASHA:</strong> {E(c["nasha"])}</p><p class="muted">{E(c["note"])}</p></div></div></section>'''
    body = f'''<section class="band-indigo crossing-band" aria-labelledby="h1">{art.jali(uid("jc"))}<div class="wrap rel">
<p class="eyebrow">The Crossing</p><h1 id="h1">India and Mexico at one table.</h1>
<p class="lede">Eight places where the two kitchens already speak to each other, and how NASHA answers. We say how sure we are. <strong>Supported</strong>: the history is well established. <strong>Analogy</strong>: a good comparison, not a claim of shared origin. <strong>Unresolved</strong>: we do not know.</p>
<p class="disclosure">{E(DISCLOSE)}</p></div></section>
{secs}
<section class="band-indigo" aria-labelledby="tb">{art.jali(uid("jt"))}<div class="wrap rel grid cols-2 center"><div><p class="eyebrow">The table · Design, not history</p><h2 id="tb">Where it all gathers.</h2>
<p class="lede">The last idea is not a claim about the past. It is a design: long tables, shared plates, and a place where two traditions of hospitality sit together.</p></div>{svg_fig("NV-ILL-TABLE", art.table_scene(uid("tc")), "", "960/420")}</div></section>
<section aria-labelledby="cn"><div class="wrap"><h2 id="cn" class="visually-hidden">Note</h2><p class="muted">NASHA is an Indo-Mex kitchen in the sense of a designed fusion. We do not claim any dish is traditional to either country. The lattice pattern is contemporary geometry and is not a claim of shared history.</p></div></section>'''
    return layout("crossing.html", "The Crossing · NASHA", "Where Indian and Mexican cooking overlap, with honest notes on how sure we are.", body)

def page_labs():
    path = "".join(f'<li{" class=\"current\"" if p["stage"] == "Now" else ""}><span class="stage">{E(p["stage"])}</span><h3>{E(p["title"])}</h3><p>{E(p["body"])}</p><p class="muted">Needs: {E(p["needs"])}</p></li>' for p in labs["path"])
    method = "".join(f"<li>{E(m)}</li>" for m in labs["method"])
    entries = "<p>No entries yet. Labs publishes only real tests, with results, including failures. When there is a first test, it will appear here.</p>" if not labs["entries"] else ""
    body = f'''<section aria-labelledby="h1"><div class="wrap">
<p class="eyebrow">Labs</p><h1 id="h1">Tests, in public.</h1>
<p class="lede">Labs is where NASHA will publish real tests and what we learn from them. It is empty today because nothing has been tested.</p>
{entries}
<div class="grid cols-2 center"><div><h2>How Labs works</h2><ul>{method}</ul></div>{svg_fig("NV-ILL-POPUP", art.popup_scene(uid("lp")), "", "960/500")}</div>
<p class="muted">The pop-up drawing is one possible early form. It is not a final vehicle, a booked event or a decision. It shows the idea: test small, learn, then build.</p>
<h2>The path from here</h2><ol class="path">{path}</ol>
</div></section>'''
    return layout("labs.html", "Labs · NASHA", "Where NASHA will publish real tests and results. Empty until there is something real to publish.", body)

def page_about():
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">About</p><h1 id="h1">About NASHA.</h1>
<p class="lede">NASHA is food and beer designed together to captivate you, made in plain sight and shared at a long table.</p>
<p>It is a project of Ritesh Mamidi, who is building toward an Indo-Mex brewery and kitchen in Austin, Texas. Today it is a body of design and a plan, not a business that serves anyone.</p>
<h2>The name</h2>
<p>The word NASHA as it appears here is a temporary typographic wordmark, not a final logo. No NASHA logo has been designed, approved or released, and no logo exploration is published on this site.</p>
<p>The founder chose the name NASHA. Legal clearance of the name has not been completed, and nothing here claims trademark ownership, registration, availability, or ownership of any domain or social handle. If a professional review finds a problem, the name returns to the founder for a decision.</p>
<p><em>Nasha</em> means intoxication or addiction in Hindi and Urdu. We chose it for the feeling of being captivated by food and beer. We commit to never romanticising addiction, alcoholism or dangerous drinking, and to asking cultural advisors to review the name and our language before launch.</p>
<h2 id="images">About these images</h2>
<p>NASHA does not exist yet, so there are no photographs of it. This site uses two kinds of picture, and both are labelled on the page.</p>
<ul><li><strong>Concept visualization</strong>: photographic-style images made with AI image tools by the founder and edited. They show a possible future place. They are not photographs of a real place, real guests, real food or real beer. A few small details, such as the sign, were added by script. People in them are synthetic and are not real individuals.</li>
<li><strong>Concept illustration</strong>: original drawings made for this project. The food and beer drawings show proposed presentation only and are not pictures of finished dishes or beers.</li></ul>
<p>Rights status: these images are for this private, unindexed prototype. Commercial-use terms of the image tools have not been verified by the project, so the images are marked provisional in the rights register and must be re-checked, replaced or licensed before any public launch. As real dishes are cooked and real beers brewed, real photography will replace generated and drawn pictures.</p>
<h2 id="rights">How we handle rights</h2>
<p>Every file on this site is listed in a rights register: what it is, who made it, how, and under what licence. Fonts are Inter and Instrument Serif, both under the SIL Open Font License. We use no stock photos, no third-party scripts and no trackers.</p>
<h2>Evidence and honesty</h2>
<p>Design is not proof. This site shows what we have designed. It does not show that anyone wants it, that it can be brewed or cooked well, or that it can be built. Those are tests still to come, and Labs will report them. We publish no reviews, ratings, press, awards, waitlists or opening dates, because none exist.</p>
<h2>Contact</h2>
<p>There is no public contact address or mailing list yet. We will add one when it is real.</p>
</div></section>'''
    return layout("about.html", "About · NASHA", "About NASHA, the name, how images are labelled, and what is and is not true today.", body)

ZONE_SVG = ""
# ---------- Build ----------
def main():
    global ZONE_SVG
    ns = {}
    exec(open("/tmp/zone_svg.py").read() if False else "", ns)
    ZONE_SVG = zone_svg()
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "fonts")); imgdir = os.path.join(DIST, "images"); os.makedirs(imgdir)
    for vid, row in VIS.items():
        if row["kind"] == "raster" and row["source_file"] and os.path.exists(os.path.join(REPO, row["source_file"])):
            RASTER_META[vid] = images.build_raster(row, imgdir)
    pages = (("index.html", page_index), ("experience.html", page_experience), ("space.html", page_space), ("food.html", page_food),
             ("beer.html", page_beer), ("crossing.html", page_crossing), ("labs.html", page_labs), ("about.html", page_about))
    for fn, fnc in pages:
        with open(os.path.join(DIST, fn), "w", encoding="utf-8") as f:
            f.write(fnc())
    for n in ("styles.css", "app.js"):
        shutil.copy(os.path.join(SRC, n), os.path.join(DIST, n))
    for n in os.listdir(os.path.join(SRC, "fonts")):
        shutil.copy(os.path.join(SRC, "fonts", n), os.path.join(DIST, "fonts", n))
    write_rights()
    print("built", len(os.listdir(DIST)), "entries in dist/;", len(os.listdir(imgdir)), "image files")

def zone_svg():
    zones = [(40, 40, 250, 150, "#C9CCCB", "Glass brewhouse", "Visible brewing"), (310, 40, 250, 150, "#C47A45", "Kitchen", "Open to the hall"),
             (580, 40, 250, 150, "#E4DAC6", "Taproom and long table", "Food and beer together"), (40, 210, 790, 120, "#7D9A45", "Shaded court", "Under an oak")]
    out = ""
    for x, y, w, h, c, a, b in zones:
        out += (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}" opacity=".9" stroke="#141110" stroke-width="2"/>'
                f'<text x="{x+14}" y="{y+h//2-4}" font-family="Inter,sans-serif" font-size="20" font-weight="600" fill="#141110">{a}</text>'
                f'<text x="{x+14}" y="{y+h//2+22}" font-family="Inter,sans-serif" font-size="15" fill="#141110">{b}</text>')
    return ('<svg class="art" viewBox="0 0 870 370" role="img" aria-labelledby="zone-t zone-d" xmlns="http://www.w3.org/2000/svg">'
            '<title id="zone-t">Concept zones of a future NASHA</title>'
            '<desc id="zone-d">A simple diagram of four zones: a glass brewhouse, a kitchen, a taproom with a long table, and a shaded court under an oak. A concept diagram, not a floor plan.</desc>'
            f'<rect width="870" height="370" fill="#F3ECDD"/>{out}'
            '<text x="40" y="360" font-family="Inter,sans-serif" font-size="14" fill="#4a413b">Concept diagram. Not engineered. No site chosen.</text></svg>')

CODE_DESC = {"styles.css": "Site stylesheet written for this project", "app.js": "Site script written for this project"}
def write_rights():
    """Regenerate the website asset rights register from dist/ and the visual manifest so every shipped asset is covered."""
    rows = []
    def add(page, typ, name, src, meth, lic, ok, evid, st, note):
        rows.append([f"WA-{len(rows)+1:03d}", page, typ, name, src, meth, lic, ok[0], ok[1], ok[2], ok[3], evid, st, note])
    for dp, _, fs in os.walk(DIST):
        for n in sorted(fs):
            rel = os.path.relpath(os.path.join(dp, n), DIST).replace(os.sep, "/")
            if rel.startswith("images/"): continue
            h = hashlib.sha256(open(os.path.join(DIST, rel), "rb").read()).hexdigest()[:16]
            if rel.startswith("fonts/LICENSE"):
                add("all", "licence text", f"Licence {n}", "Font project authors", "copied unmodified", "SIL OFL 1.1", ("yes", "yes", "yes", "yes"), "website/build.py; sha256 " + h, "in use", "Licence notice distributed with the font.")
            elif rel.startswith("fonts/"):
                fam = "Inter" if n.startswith("inter") else "Instrument Serif"
                add("all", "font", f"{fam} ({n})", f"{fam} Project Authors via the @fontsource npm package", "third-party open font, unmodified", "SIL OFL 1.1", ("yes", "yes", "yes", "no"), "website/build.py; sha256 " + h, "in use", "Self-hosted latin subset. OFL permits commercial use and embedding.")
            elif rel.endswith(".html"):
                add(rel, "page", rel, "Founder project, authored with an AI coding assistant", "AI-assisted, human-directed; original code and text", "Owned by project; no third-party licence", ("yes", "yes", "yes", "no"), "website/build.py; sha256 " + h, "in use", "Generated page. AI-assisted authorship; see ip/IP-OWNERSHIP-FRAMEWORK.md.")
            else:
                add("all", "code", rel, "Founder project, authored with an AI coding assistant", "AI-assisted, human-directed; original code", "Owned by project; no third-party licence", ("yes", "yes", "yes", "no"), "website/build.py; sha256 " + h, "in use", CODE_DESC.get(rel, "") + ". AI-assisted authorship.")
    for vid, r in VIS.items():
        if r["kind"] == "raster" and vid in RASTER_META:
            add(r["page"], "image", vid, r["tool"], r["creation_method"], "UNVERIFIED: image-tool terms not checked by the project", ("unverified", "yes", "unverified", "no"), r["source_inputs"] + "; visuals/NASHA-VISUAL-MANIFEST.csv", "provisional-local-only", r["unresolved_restrictions"])
        elif r["kind"] == "vector":
            add(r["page"], "illustration", vid, r["tool"], r["creation_method"], "Owned by project; no third-party licence", ("yes", "yes", "yes", "no"), "website/art.py; visuals/NASHA-VISUAL-MANIFEST.csv", "in use", r["commercial_use_status"] + ". " + r["unresolved_restrictions"])
    hdr = next(csv.reader(open(os.path.join(REPO, "ip/website-asset-rights-register.csv"))))
    with open(os.path.join(REPO, "ip/website-asset-rights-register.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(rows)

if __name__ == "__main__":
    main()
