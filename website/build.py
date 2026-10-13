#!/usr/bin/env python3
"""Build the NASHA static site into website/dist/. Python stdlib + Pillow (images only).
Run: python3 website/build.py
Content: website/data/*.json (audited wording) and visuals/NASHA-VISUAL-MANIFEST.csv (canonical visual manifest).
Where a manifest row has a raster source file, a responsive <picture> is emitted; otherwise a drawn stand-in (website/art.py) is used."""
import csv, hashlib, html, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art, images  # noqa: E402
import pages_s23 as P  # noqa: E402
import pages_s25 as P25  # noqa: E402

SRC, DATA, DIST = (os.path.join(HERE, p) for p in ("src", "data", "dist"))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(REPO, "visuals/NASHA-VISUAL-MANIFEST.csv")
BUILD_DATE = "2026-10-13"
E = html.escape

def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)

dishes, beers = load("dishes.json"), load("beers.json")
crossing, status, labs = load("crossing.json"), load("status.json"), load("labs.json")
SITE = load("investor.json")
PROTO = {}
SITE_EXEC = {e["section"]: e["text"] for e in SITE["exec"]}
BEER = {b["id"]: b for b in beers}
BEER_BY_NAME = {b["name"]: b for b in beers}
DISH = {d["id"]: d for d in dishes}
VIS = {r["id"]: r for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))}
RASTER_META = {}

PAGES = [("index.html", "Home"), ("food.html", "Food"), ("beer.html", "Beer"), ("court.html", "The Court"), ("craft.html", "The Craft"),
         ("evening.html", "Evening"), ("labs.html", "The Lab"), ("investor.html", "Business")]
HERO_ID = "NV-VISION-VP01"
NAV_GROUP = {"pairings.html": "food.html", "crossing.html": "index.html", "walkthrough.html": "investor.html", "about.html": "index.html"}

DISCLOSE = ("Concept stage: there is no brewery, no restaurant, no truck and no menu for sale. "
            "Images are concept visualizations and illustrations, not photographs of NASHA.")
CONCEPT_NOTE = "Concept visualization. Final architecture is subject to professional design and site conditions."

PLATE_KIND = {"chicken-65-totopos": "totopos", "chaat-elote": "elote", "gobi-taco": "taco", "paneer-tikka-taco": "taco2",
              "butter-chicken-quesadilla": "quesadilla", "goat-birria": "birria", "cardamom-churros": "churros", "seed-chile-bowl": "veg"}
SIGNATURE = ["chicken-65-totopos", "paneer-tikka-taco", "gobi-taco", "butter-chicken-quesadilla", "goat-birria", "chaat-elote", "cardamom-churros"]
GATE_BEERS = ["hefeweizen", "mexican-lager", "vienna-amber"]
CORE_BEERS = ["hefeweizen", "mexican-lager", "vienna-amber", "pilsner", "witbier"]

_uid = [0]
def uid(p="u"):
    _uid[0] += 1
    return f"{p}{_uid[0]}"

# ---------- figures ----------
STAGE_TAG = {"CONCEPT VISUALIZATION": ("Concept visualization", ". Not a photograph of NASHA. Final architecture is subject to professional design and site conditions."),
             "CONCEPT ILLUSTRATION": ("Concept illustration", ". A drawing, not a photograph."),
             "PROTOTYPE": ("Prototype photograph", ". A photograph of a prototype dish or beer from a kitchen or pilot test, not a finished product."),
             "TESTED PRODUCT": ("Tested product photograph", ". A photograph of a product that passed a documented test."),
             "FINAL PHOTOGRAPHY": ("Photograph", ". Final photography of NASHA.")}

def tag_html(vid):
    stage = VIS[vid]["visual_stage"] or "CONCEPT VISUALIZATION"
    t, extra = STAGE_TAG[stage]
    return f'<figcaption class="tag" data-stage="{stage}">{t}<span class="visually-hidden">{extra}</span></figcaption>'

def raster_fig(vid, cls="", eager=False, sizes="100vw"):
    row = VIS[vid]; meta = RASTER_META[vid]
    pic = images.picture_html(row, meta, E(row["alt_text"]), sizes, eager)
    st = f'--ar-d:{meta["d"]["w"]}/{meta["d"]["h"]};--ar-m:{meta["m"]["w"]}/{meta["m"]["h"]}'
    return f'<figure class="fig {cls}" data-vid="{vid}" style="{st}">{pic}{tag_html(vid)}</figure>'

def svg_fig(vid, svg, cls="", ar="16/10"):
    return f'<figure class="fig fig-art {cls}" data-vid="{vid}" style="--ar-d:{ar};--ar-m:{ar}">{svg}{tag_html(vid)}</figure>'

# ---------- layout ----------
def layout(fn, title, desc, body, head_extra="", body_class=""):
    nav = "".join(f'<li><a href="{f}"{" aria-current=\"page\"" if f == fn or (NAV_GROUP.get(fn) == f) else ""}>{E(n)}</a></li>' for f, n in PAGES)
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
<p><strong>NASHA</strong> is a future Indo-Mex brewery and kitchen in Austin, Texas, in development. Nothing is open or for sale, and no site has been chosen. Pictures are concept visualizations or drawings, not photographs of NASHA.</p>
<details class="foot-more"><summary>Name, images and allergens</summary>
<p>The name was chosen by the founder; legal clearance is pending and nothing here claims trademark ownership. The word NASHA in the header and in some pictures is a <strong>temporary typographic placeholder</strong>, not a logo. <em>Nasha</em> means intoxication or addiction in Hindi and Urdu: we chose it for the feeling of being drawn in by food, craft and company, we will never present excess as something to admire, and cultural advisors will review the name and our language before launch.</p>
<p>Photographic-style pictures are <strong>concept visualizations</strong> made with AI tools and edited; drawings are illustrations. None is a photograph of NASHA, its food or its beer (<a href="about.html#images">about these images</a>). Dishes are designs for testing, not served food; heat and vegetarian labels are design intent, not a certified allergen or dietary statement. Ask before you eat if you have an allergy. If you drink, drink responsibly; alcohol is for adults of legal drinking age.</p></details>
<p><a href="about.html">About NASHA</a> · <a href="walkthrough.html">Four-minute walkthrough</a> · <a href="investor.html">Business and investor view</a> · <a href="labs.html">The Lab</a> · Build of {BUILD_DATE}</p>
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

def gkind(b):
    """NASHA collar glass family: geometry follows the beer (reference library section 10)."""
    if b["id"] == "pilsner": return "pilsner"
    return "weizen" if b["glass"] == "Collar Weizen" else "lager"

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
    work = '<p class="muted">WORKING NAME. May change. The regional name is a placeholder pending cultural-advisor review, and the style is not settled, so only a faint outline glass is shown.</p>' if b["working"] else ""
    status_chip = "Working name · no style visual yet" if b["working"] else "Style-based concept visualization"
    glass_line = "not defined" if b["working"] else b["glass"]
    g = art.glass(uid("bg"), b["id"], 0.86, gkind(b), animate=False, title=f"Concept glass for {b['name']}")
    return f'''<article class="card" data-item data-group="{E(b["group"])}">
<div class="beer-row"><div class="mini-glass">{g}</div><div><{h}>{E(b["name"])}</{h}>
<p>{E(b["line"])}</p><p>{chips(b["style"], "Planned season: " + b["season"], "Not brewed yet", status_chip)}</p>{work}
<dl class="meta"><dt>Glass</dt><dd>{E(glass_line)}</dd><dt>Designed to pair with</dt><dd>{E(", ".join(b["pairs"]))}</dd></dl></div></div></article>'''

def filter_inputs(name, values):
    return "".join(f'<label><input type="checkbox" name="{name}" value="{E(v)}"> {E(t)}</label>' for v, t in values)

# ---------- shared components ----------
def pairing_comp(dish_id, beer_id, label_h="h3"):
    d, b = DISH[dish_id], BEER[beer_id]
    g = art.glass(uid("pg"), beer_id, .86, gkind(b), animate=False, title=f"Concept glass of {b['name']}")
    return f'''<article class="pair reveal" data-vid="NV-ILL-PLATES"><div class="pair-art"><div class="pair-plate">{plate_svg(d)}</div><div class="pair-glass">{g}</div></div>
<{label_h}>{E(d["name"])} <span class="amp">+</span> {E(b["name"])}</{label_h}>
<p class="chip-row">{chips("Proposed pairing — not sensory tested", "Not brewed yet")}</p></article>'''

def two_pour():
    d = DISH["chicken-65-totopos"]
    g1 = art.glass(uid("tp"), "mexican-lager", .88, "lager", animate=False, title="Concept glass, first beer")
    g2 = art.glass(uid("tp"), "hefeweizen", .88, "weizen", animate=False, title="Concept glass, second beer")
    steps = [("1", "Beer one", "A cold, clean Mexican-Style Lager arrives first, as designed.", g1),
             ("2", "The dish", "Chicken 65 Totopos, our designed fusion of South Indian Chicken 65 (its origin is contested) with masa chips.", f'<div class="tp-plate">{plate_svg(d)}</div>'),
             ("3", "Beer two", "Then a Hefeweizen alongside the same dish, as designed.", g2)]
    li = "".join(f'<li class="tp-step" data-step="{n}"><span class="tp-n">{n}</span><div class="tp-art">{a}</div><h3>{t}</h3><p>{p}</p></li>' for n, t, p, a in steps)
    return f'''<div class="two-pour" data-two-pour data-active="1">
<ol class="tp-steps">{li}</ol>
<div class="tp-controls" role="group" aria-label="Walk through the Two-Pour idea"><button type="button" class="btn btn-ghost" data-tp="prev">Back</button><button type="button" class="btn" data-tp="next">Next step</button><span class="visually-hidden" role="status" aria-live="polite" data-tp-status></span></div>
<p class="tp-learn"><strong>How the experience might change:</strong> the same bite, tasted after two different beers. That is a hypothesis for a tasting, not a result. No guest has tried it, and no beer has been brewed.</p>
</div>'''

def pairs_section(h="h3"):
    combos = [("paneer-tikka-taco", "hefeweizen"), ("chicken-65-totopos", "mexican-lager"), ("goat-birria", "vienna-amber"), ("chaat-elote", "mexican-lager")]
    return "".join(pairing_comp(d, b, h) for d, b in combos)

# ---------- pages ----------
def hero_head():
    m = RASTER_META[HERO_ID]
    d = sorted([f for f in m["d"]["files"] if f["fmt"] == "avif" and f["w"] <= 1600], key=lambda f: f["w"])[-1]
    mm = [f for f in m["m"]["files"] if f["fmt"] == "avif" and f["w"] == 800][0]
    return (f'<link rel="preload" as="image" type="image/avif" media="(min-width: 701px)" href="images/{d["file"]}">\n'
            f'<link rel="preload" as="image" type="image/avif" media="(max-width: 700px)" href="images/{mm["file"]}">\n')

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
    li = "".join(f'<li>{art.glass(uid("fl"), b["id"], .8, gkind(b), False, f"Concept glass of {b["name"]}")}<div><strong>{E(b["name"])}</strong><br><span class="muted">{E(b["style"])}</span></div></li>' for b in items)
    return f'<div class="flight-card"><p class="tag-inline">Tasting flight · proposed · not brewed yet</p><ul>{li}</ul><p class="muted">Four small pours. Names are proposals. No prices, no availability.</p></div>'

def page_food():
    body = f'''<section class="food-hero" aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">Food · Designs for testing</p><h1 id="h1">Five dishes, designed to be cooked at home first.</h1>
<p class="lede">Chicken 65 from South India on thick masa totopos. Paneer tikka in a taco. A goat birria. A roasted gobi taco. A butter chicken quesadilla with roasted poblano. Nothing is cooked for guests and nothing is for sale.</p>
<p class="disclosure">{E(DISCLOSE)} The drawings show proposed presentation, not finished dishes.</p></div></section>

{P.food_core_section(M, SITE)}

<section aria-labelledby="vg"><div class="wrap"><h2 id="vg">Vegetarian is not a side.</h2>
<p class="lede">Two of the five are vegetarian as designed, built as headliners. Every dish is made without beef or pork, including stocks, fats and tortillas.</p>
<p class="muted">Labels describe design intent, not a certified dietary or allergen statement. Ask before you eat if you have an allergy. See the <a href="pairings.html">pairings</a> for what each dish is meant to meet; the pairings are proposed and not sensory tested.</p></div></section>'''
    return layout("food.html", "Food · NASHA", "The five dishes NASHA is designing for home-kitchen tests. Proposed presentation only. None are for sale.", body)

def page_beer():
    binfo_json = html.escape(json.dumps({b: {"name": BEER[b]["name"], "style": BEER[b]["style"], "status": "Not brewed yet" + (" · working name" if BEER[b]["working"] else ""), "pair": "Designed to pair with " + ", ".join(BEER[b]["pairs"][:3])} for b in CORE_BEERS}), quote=True)
    macro = art.glass(uid("mg"), "hefeweizen", .9, "weizen", True, "Concept macro glass of a wheat beer", big=True)
    gate = "".join(f'<article class="feature reveal"><div class="glass-big">{art.glass(uid("gb"), b, .86, gkind(BEER[b]), True, f"Concept glass of {BEER[b]["name"]}")}</div><h3>{E(BEER[b]["name"])}</h3><p>{E(BEER[b]["line"])}</p><p>{chips(BEER[b]["style"], "Not brewed yet", "Style-based concept visualization")}</p><p class="muted">Designed to pair with {E(", ".join(BEER[b]["pairs"][:3]))}</p></article>' for b in GATE_BEERS)
    groups = sorted({b["group"] for b in beers})
    f = filter_inputs("group", [(g, g) for g in groups])
    sw = "".join(f'<button type="button" class="swatch" data-beer="{b}" aria-pressed="{"true" if b == "hefeweizen" else "false"}">{E(BEER[b]["name"])}</button>' for b in CORE_BEERS)
    body = f'''<section class="beer-hero" aria-labelledby="h1"><div class="wrap grid cols-2 center">
<div><p class="eyebrow">Beer · Briefs for a brewer</p><h1 id="h1">Built for the table.</h1>
<p class="lede">Beer designed to meet the food: designed to be crisp enough to cool the heat and round enough to hold a char. Nothing has been brewed. Each beer is a brief for a head brewer to critique, change, or reject.</p>
<div class="swatches js-only" role="group" aria-label="Preview a beer colour">{sw}</div>
<p class="disclosure">{E(DISCLOSE)} Alcohol is for adults of legal drinking age. Any future beer sales depend on licences we have not yet obtained.</p></div>
<div class="macro" data-macro data-beer="hefeweizen" data-vid="NV-ILL-GLASS">{macro}<p class="tag-inline">Concept illustration · colour follows the style reference, not a brewed beer</p>
<div class="beer-info" data-beer-info role="status" data-beers='{binfo_json}'><p class="bi-name" data-bi="name">Hefeweizen</p><p data-bi="style">{E(BEER["hefeweizen"]["style"])}</p><p data-bi="status">Not brewed yet</p><p data-bi="pair">Designed to pair with {E(", ".join(BEER["hefeweizen"]["pairs"][:3]))}</p></div></div></div></section>

{P.beer_core_section(M, SITE)}

<section class="alt" aria-labelledby="bv"><div class="wrap grid cols-2 center"><div><p class="eyebrow">Brewery vision</p><h2 id="bv">The brewery in plain sight.</h2>
<p class="lede">The imagined brewhouse sits behind glass so guests can see the work. The equipment in this picture is illustrative: the vessel size and count are an open decision and nothing here fixes them.</p></div>
<div class="reveal">{raster_fig("NV-VISION-VP03", "", sizes="(max-width: 700px) 100vw, 50vw")}</div></div></section>

<section aria-labelledby="hs"><div class="wrap"><p class="eyebrow">Honest status</p><h2 id="hs">Not brewed yet.</h2>
<p>No beer exists. There is no brewer on the team, no recipe and no licence. The first beers, if any, would likely be made with a partner brewery under rules we are still learning. <a href="labs.html">Follow the path in The Lab</a>.</p></div></section>'''
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
<p class="lede nasha-line"><strong>Our take:</strong> {E(c["nasha"])}</p><p class="muted">{E(c["note"])}</p></div></div></section>'''
    body = f'''<section class="band-indigo crossing-band" aria-labelledby="h1">{art.jali(uid("jc"))}<div class="wrap rel">
<p class="eyebrow">The Crossing</p><h1 id="h1">India and Mexico at one table.</h1>
<p class="lede">Eight places where the two kitchens already speak to each other, and how NASHA answers. We say how sure we are. <strong>Supported</strong>: the history is well established. <strong>Analogy</strong>: a good comparison, not a claim of shared origin. <strong>Unresolved</strong>: we do not know.</p>
<p class="disclosure">{E(DISCLOSE)}</p></div></section>
{secs}
<section class="band-indigo" aria-labelledby="tb">{art.jali(uid("jt"))}<div class="wrap rel grid cols-2 center"><div><p class="eyebrow">The table · Design, not history</p><h2 id="tb">Where it all gathers.</h2>
<p class="lede">The last idea is not a claim about the past. It is a design: long tables, shared plates, and a place where two traditions of hospitality sit together.</p></div>{svg_fig("NV-ILL-TABLE", art.table_scene(uid("tc")), "", "960/420")}</div></section>
<section aria-labelledby="cn"><div class="wrap"><h2 id="cn" class="visually-hidden">Note</h2><p class="muted">NASHA is an Indo-Mex kitchen in the sense of a designed fusion. We do not claim any dish is traditional to either country. The lattice pattern is contemporary geometry and is not a claim of shared history.</p></div></section>'''
    return layout("crossing.html", "The Crossing · NASHA", "Where Indian and Mexican cooking overlap, with honest notes on how sure we are.", body)

def page_about():
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">About</p><h1 id="h1">About NASHA.</h1>
<p class="lede">NASHA is food and beer designed together to draw you in, made in plain sight and shared at a long table.</p>
<p>It is a project of Ritesh Mamidi, who is building toward an Indo-Mex brewery and kitchen in Austin, Texas. Today it is a body of design and a plan, not a business that serves anyone.</p>
<h2>The founder</h2>
<p>{E(SITE_EXEC["founder"])}</p>
<h2>The name</h2>
<p>The word NASHA as it appears here is a temporary typographic wordmark, not a final logo. No NASHA logo has been designed, approved or released, and no logo exploration is published on this site.</p>
<p>The founder chose the name NASHA. Legal clearance of the name has not been completed, and nothing here claims trademark ownership, registration, availability, or ownership of any domain or social handle. If a professional review finds a problem, the name returns to the founder for a decision.</p>
<p><em>Nasha</em> means intoxication or addiction in Hindi and Urdu. We chose it for the feeling of being drawn in by food, craft and company. We commit to never romanticising addiction, alcoholism or dangerous drinking, and to asking cultural advisors to review the name and our language before launch.</p>
<h2 id="images">About these images</h2>
<p>NASHA is currently in development. Photographic-style images on this site are concept visualizations used to communicate the intended experience. They are not photographs of an operating NASHA location, finished dishes or brewed NASHA beer.</p>
<ul><li><strong>Concept visualization</strong>: photographic-style images made with AI image tools by the founder and edited. People in them are synthetic and are not real individuals. A few details, such as the temporary NASHA lettering on a sign, were added by script. Equipment in them is illustrative.</li>
<li><strong>Concept illustration</strong>: original drawings made for this project. The food and beer drawings show proposed presentation only and are not pictures of finished dishes or beers.</li></ul>
<p>When real dishes are cooked and real beers are brewed, real photography will replace these pictures and each picture will say what stage it shows: concept visualization, prototype, tested product or final photography. None is above concept stage today.</p>
<p>Rights status: the image tools' commercial-use terms have not been verified by the project, so these images are marked provisional in the rights register for this private, unindexed prototype and must be re-checked, replaced or licensed before any public launch.</p>
<h2 id="rights">How we handle rights</h2>
<p>Every file on this site is listed in a rights register: what it is, who made it, how, and under what licence. Fonts are Inter and Instrument Serif, both under the SIL Open Font License. We use no stock photos, no third-party scripts and no trackers.</p>
<h2>Evidence and honesty</h2>
<p>Design is not proof. This site shows what we have designed. It does not show that anyone wants it, that it can be brewed or cooked well, or that it can be built. Those are tests still to come, and The Lab will report them. We publish no reviews, ratings, press, awards, waitlists or opening dates, because none exist.</p>
<h2>Contact</h2>
<p>There is no public contact address or mailing list yet. We will add one when it is real.</p>
</div></section>'''
    return layout("about.html", "About · NASHA", "About NASHA, the name, how images are labelled, and what is and is not true today.", body)

ZONE_SVG = ""
# ---------- Build ----------
def main():
    global ZONE_SVG
    ZONE_SVG = zone_svg()
    global M
    M = sys.modules[__name__]
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "fonts")); imgdir = os.path.join(DIST, "images"); os.makedirs(imgdir)
    for vid, row in VIS.items():
        if row["kind"] == "raster" and row["source_file"] and not row["status"].startswith("SUPERSEDED") and os.path.exists(os.path.join(REPO, row["source_file"])):
            RASTER_META[vid] = images.build_raster(row, imgdir)
    PROTO.update(P.load_proto(M))
    pages = (("index.html", lambda: P25.page_home(M, SITE)), ("court.html", lambda: P25.page_court(M, SITE)), ("craft.html", lambda: P25.page_craft(M, SITE)), ("evening.html", lambda: P25.page_evening(M, SITE)), ("walkthrough.html", lambda: P25.page_walkthrough(M, SITE)), ("food.html", page_food),
             ("beer.html", page_beer), ("crossing.html", page_crossing), ("pairings.html", lambda: P.page_pairings(M, SITE)), ("labs.html", lambda: P.page_lab(M, SITE)), ("investor.html", lambda: P.page_business(M, SITE)), ("about.html", page_about))
    for fn, fnc in pages:
        with open(os.path.join(DIST, fn), "w", encoding="utf-8") as f:
            f.write(P.label_tables(fnc()))
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
