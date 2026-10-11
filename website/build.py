#!/usr/bin/env python3
"""Build the NASHA static site into website/dist/. Python stdlib only.
Run: python3 website/build.py
Content comes from website/data/*.json (audited wording). Output is committed."""
import csv, hashlib, html, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, DATA, DIST = (os.path.join(HERE, p) for p in ("src", "data", "dist"))
REPO = os.path.dirname(HERE)
BUILD_DATE = "2026-10-11"

def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)

E = html.escape
dishes, beers = load("dishes.json"), load("beers.json")
crossing, status, labs = load("crossing.json"), load("status.json"), load("labs.json")

PAGES = [("index.html", "Home"), ("food.html", "Food"), ("beer.html", "Beer"),
         ("crossing.html", "The Crossing"), ("labs.html", "Labs"), ("about.html", "About")]

DISCLOSE = ("NASHA is in development. There is no brewery, no restaurant, no truck and no menu for sale yet. "
            "Illustrations show a concept, not a built place.")

# ---------- SVG art (original, hand-written, no raster) ----------
def hero_svg():
    tanks = ""
    for i, x in enumerate([330, 440, 550, 1050, 1160, 1270]):
        tanks += (f'<g><rect x="{x-34}" y="470" width="68" height="190" rx="10" fill="#C9CCCB"/>'
                  f'<rect x="{x-34}" y="520" width="68" height="26" fill="#E8870E"/>'
                  f'<polygon points="{x-34},660 {x+34},660 {x},720" fill="#4a4a4a"/>'
                  f'<rect x="{x-24}" y="478" width="9" height="170" fill="#ffffff" opacity=".35"/></g>')
    return f'''<svg viewBox="0 0 1600 900" role="img" aria-labelledby="hero-t hero-d" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
<title id="hero-t">Concept illustration of the NASHA hall at dusk</title>
<desc id="hero-d">A stylised glass hall at dusk with six steel fermentation tanks seen through large windows, a copper brewhouse on a deck, warm light inside, and an oak tree to the right. This is a concept drawing, not a built place.</desc>
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1A2142"/><stop offset=".6" stop-color="#2B3563"/><stop offset="1" stop-color="#C47A45"/></linearGradient>
<radialGradient id="warm" cx=".5" cy=".6" r=".6"><stop offset="0" stop-color="#E9C46A" stop-opacity=".9"/><stop offset="1" stop-color="#E8870E" stop-opacity=".25"/></radialGradient></defs>
<rect width="1600" height="900" fill="url(#sky)"/>
<circle cx="1330" cy="140" r="3" fill="#F3ECDD" opacity=".8"/><circle cx="1220" cy="90" r="2" fill="#F3ECDD" opacity=".6"/><circle cx="260" cy="110" r="2.5" fill="#F3ECDD" opacity=".7"/><circle cx="520" cy="60" r="2" fill="#F3ECDD" opacity=".5"/>
<rect y="740" width="1600" height="160" fill="#141110"/>
<g><rect x="1390" y="300" width="22" height="440" fill="#141110"/><ellipse cx="1400" cy="270" rx="150" ry="120" fill="#141110"/><ellipse cx="1320" cy="330" rx="90" ry="70" fill="#141110"/><ellipse cx="1480" cy="320" rx="90" ry="70" fill="#141110"/></g>
<rect x="190" y="400" width="1220" height="340" fill="#241E1B"/>
<rect class="glow" x="200" y="410" width="1200" height="320" fill="url(#warm)"/>
{tanks}
<g><rect x="690" y="560" width="220" height="150" rx="14" fill="#C47A45"/><rect x="690" y="560" width="220" height="26" fill="#a5612f"/><ellipse cx="800" cy="560" rx="110" ry="16" fill="#d79062"/>
<rect x="780" y="440" width="40" height="120" fill="#C47A45"/><rect x="772" y="430" width="56" height="16" fill="#a5612f"/></g>
<g fill="#F3ECDD"><circle class="steam" cx="800" cy="410" r="14" opacity=".0"/><circle class="steam" cx="812" cy="390" r="10" opacity=".0"/></g>
<g stroke="#141110" stroke-width="6" fill="none"><rect x="190" y="400" width="1220" height="340"/>
<path d="M290 400V740M390 400V740M490 400V740M590 400V740M690 400V740M790 400V740M890 400V740M990 400V740M1090 400V740M1190 400V740M1290 400V740"/>
<path d="M190 560H1410"/></g>
<rect x="150" y="360" width="1300" height="40" fill="#141110"/>
<rect x="190" y="740" width="1220" height="22" fill="#3a312c"/>
</svg>'''

def zone_svg():
    zones = [(40, 40, 250, 150, "#C9CCCB", "Glass brewhouse", "Visible brewing"),
             (310, 40, 250, 150, "#C47A45", "Kitchen", "Open to the hall"),
             (580, 40, 250, 150, "#E4DAC6", "Taproom and long table", "Food and beer together"),
             (40, 210, 790, 120, "#7D9A45", "Shaded court", "Under an oak")]
    out = ""
    for x, y, w, h, c, a, b in zones:
        out += (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}" opacity=".9" stroke="#141110" stroke-width="2"/>'
                f'<text x="{x+14}" y="{y+h//2-4}" font-family="Inter,sans-serif" font-size="20" font-weight="600" fill="#141110">{a}</text>'
                f'<text x="{x+14}" y="{y+h//2+22}" font-family="Inter,sans-serif" font-size="15" fill="#141110">{b}</text>')
    return ('<svg viewBox="0 0 870 370" role="img" aria-labelledby="zone-t zone-d" xmlns="http://www.w3.org/2000/svg">'
            '<title id="zone-t">Concept zones of a future NASHA</title>'
            '<desc id="zone-d">A simple diagram of four zones: a glass brewhouse, a kitchen, a taproom with a long table, and a shaded court under an oak. A concept diagram, not a floor plan.</desc>'
            f'<rect width="870" height="370" fill="#F3ECDD"/>{out}'
            '<text x="40" y="360" font-family="Inter,sans-serif" font-size="14" fill="#4a413b">Concept diagram. Not engineered. No site chosen.</text></svg>')

def glass_svg(kind):
    w = '<path d="M14 8 Q10 30 12 56 Q14 76 24 78 Q34 76 36 56 Q38 30 34 8 Z" fill="#E9C46A" stroke="#F3ECDD" stroke-width="2"/><rect x="13" y="4" width="22" height="8" rx="3" fill="#F3ECDD"/>'
    l = '<path d="M16 8 L12 68 Q12 78 24 78 Q36 78 36 68 L32 8 Z" fill="#E9C46A" stroke="#F3ECDD" stroke-width="2"/><rect x="15" y="4" width="18" height="7" rx="3" fill="#F3ECDD"/>'
    return f'<svg class="glass" viewBox="0 0 48 84" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">{w if kind=="Collar Weizen" else l}</svg>'

# ---------- Layout ----------
def layout(fn, title, desc, body, h1_id=True):
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
<script>document.documentElement.className="js"</script>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E%3Crect width=%2732%27 height=%2732%27 fill=%27%23141110%27/%3E%3Ccircle cx=%2716%27 cy=%2716%27 r=%276%27 fill=%27%23E8870E%27/%3E%3C/svg%3E">
<link rel="stylesheet" href="styles.css">
</head>
<body>
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
<p>The name was chosen by the founder. Legal clearance of the name is pending. Nothing here claims trademark ownership. There is no brewery, restaurant or truck open, and nothing is for sale.</p>
<p>In Hindi and Urdu, <em>nasha</em> means intoxication or addiction. We chose it for the feeling of being captivated by food and beer. We take that meaning seriously and will never present excess or addiction as something to admire. Cultural advisors will review the name and our language before launch.</p>
<p>Menu items are designs for testing, not served food. Heat levels and vegetarian labels describe how a dish is designed, not a certified allergen or dietary statement. Ask before you eat if you have an allergy. If you drink, drink responsibly. Alcohol is for adults of legal drinking age.</p>
<p>Illustrations on this site are original vector drawings made for this project. See <a href="about.html#rights">how we track asset rights</a>. Build of {BUILD_DATE}.</p>
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

def dish_card(d, h="h2"):
    veg = '<span class="chip chip-veg">Vegetarian as designed</span>' if d["vegetarian"] else ""
    cats = d["category"]
    return f'''<article class="card" data-item data-category="{E(cats)}" data-diet="{"veg" if d["vegetarian"] else "any"}" data-heat="{d["heat"]}">
<{h}>{E(d["name"])}</{h}>
<p>{E(d["line"])}</p>
<p>{chips(d["kind"], d["status"], d["category"])}{veg}</p>
<dl class="meta"><dt>Inspiration</dt><dd>{E(d["inspiration"])}</dd>
<dt>Made with</dt><dd>{E(", ".join(d["ingredients"]))}</dd>
<dt>Heat</dt><dd>{heat(d["heat"])} · cooling: {E(d["cooling"])}</dd>
<dt>Designed to pair with</dt><dd>{E(", ".join(d["pairing"]))}</dd></dl></article>'''

def beer_card(b, h="h2"):
    work = '<p class="muted">Working name. May change.</p>' if b["working"] else ""
    return f'''<article class="card" data-item data-group="{E(b["group"])}">
<div class="beer-row">{glass_svg(b["glass"])}<div><{h}>{E(b["name"])}</{h}>
<p>{E(b["line"])}</p><p>{chips(b["style"], b["season"], "Not brewed yet")}</p>{work}
<dl class="meta"><dt>Served in</dt><dd>{E(b["glass"])}</dd><dt>Designed to pair with</dt><dd>{E(", ".join(b["pairs"]))}</dd></dl></div></div></article>'''

def filter_set(gid, status_id, name, label, values, extra=""):
    inputs = "".join(f'<label><input type="checkbox" name="{name}" value="{E(v)}"> {E(t)}</label>' for v, t in values)
    return inputs

# ---------- Pages ----------
def page_index():
    beats = f'''
<section class="hero" aria-labelledby="h1">
<div class="hero-art">{hero_svg()}</div>
<div class="wrap hero-copy">
<p class="eyebrow">Austin, Texas · In development</p>
<h1 id="h1">Food and beer, designed together.</h1>
<p class="lede">NASHA is a future Indo-Mex brewery and kitchen. We are working out the food, the beer and the place in the open, before any of it exists.</p>
<p class="disclosure">{E(DISCLOSE)}</p>
</div></section>

<section aria-labelledby="b2"><div class="wrap grid cols-2">
<div><p class="eyebrow"><span class="beat-no">01</span> What NASHA is</p><h2 id="b2">Two kitchens at one table.</h2></div>
<div class="stack"><p class="lede">India and Mexico both build flavour from chile, lime, toasted spice, flatbread and fermentation. NASHA starts from what they share, and lets each stay itself.</p>
<p>The food and the beer are specified together, so each is designed to make the other better. That is a design goal we intend to test, not a result we have.</p></div>
</div></section>

<section class="alt" aria-labelledby="b3"><div class="wrap">
<p class="eyebrow"><span class="beat-no">02</span> The idea</p>
<h2 id="b3" class="statement">Made in plain sight, shared at a long table.</h2>
<p>The future hall is imagined with a glass brewhouse you can see into, a kitchen open to the room, and a shaded court under an oak.</p>
<div class="cols-3 grid">
<div class="card"><h3>See it made</h3><p>Brewing and cooking in view, not hidden behind a wall.</p></div>
<div class="card"><h3>Designed together</h3><p>Each dish names the beers it is meant to meet.</p></div>
<div class="card"><h3>Shared</h3><p>Plates and pitchers for the middle of the table.</p></div></div>
</div></section>

<section aria-labelledby="b4"><div class="wrap">
<p class="eyebrow"><span class="beat-no">03</span> The menu, as designed</p>
<h2 id="b4">A first test set of dishes.</h2>
<p>These are specifications for kitchen tests. None are for sale. <a href="food.html">See all dishes</a>.</p>
<div class="grid cols-3">{"".join(dish_card(d, "h3") for d in dishes[:3])}</div>
</div></section>

<section class="alt" aria-labelledby="b5"><div class="wrap">
<p class="eyebrow"><span class="beat-no">04</span> The beer, as designed</p>
<h2 id="b5">Beer briefs, not beers yet.</h2>
<p>Nothing has been brewed. These are briefs for a head brewer to critique. <a href="beer.html">See the beer list</a>.</p>
<div class="grid cols-3">{"".join(beer_card(b, "h3") for b in beers[:3])}</div>
</div></section>

<section class="band-indigo" aria-labelledby="b6"><div class="wrap grid cols-2">
<div><p class="eyebrow"><span class="beat-no">05</span> The Crossing</p><h2 id="b6">Where India and Mexico already meet.</h2></div>
<div class="stack"><p class="lede">Chile, lime, toasted seeds, flatbread, fermentation. We separate what history supports from what is only a good comparison.</p><p><a href="crossing.html">Read the Crossing</a></p></div>
</div></section>

<section aria-labelledby="b7"><div class="wrap grid cols-2">
<div><p class="eyebrow"><span class="beat-no">06</span> The place</p><h2 id="b7">A hall we have only drawn.</h2>
<p>This diagram shows how the four zones might relate. It is a concept. No site is chosen and nothing is engineered.</p></div>
<div>{zone_svg()}</div>
</div></section>

<section class="alt" aria-labelledby="b8"><div class="wrap">
<p class="eyebrow"><span class="beat-no">07</span> Where we really are</p>
<h2 id="b8">Honest status.</h2>
<ul class="path">{"".join(f'<li{" class=\"current\"" if it["state"] == "Designing" else ""}><span class="stage">{E(it["state"])}</span><h3>{E(it["name"])}</h3><p>{E(it["note"])}</p></li>' for it in status["items"])}</ul>
<p class="muted">Nothing is in Testing or Validated yet. We will say so when that changes. <a href="labs.html">See Labs</a>.</p>
</div></section>

<section aria-labelledby="b9"><div class="wrap">
<p class="eyebrow"><span class="beat-no">08</span> Follow along</p>
<h2 id="b9">Updates are not live yet.</h2>
<p>We have not set up a mailing list, domain or contact address, so we will not pretend to collect your email. This page will change when that is real.</p>
<button class="btn" type="button" disabled>Updates coming later</button>
</div></section>

<section class="alt" aria-labelledby="b10"><div class="wrap">
<p class="eyebrow"><span class="beat-no">09</span> A note on the name</p>
<h2 id="b10">About the word <em>nasha</em>.</h2>
<p>It means intoxication or addiction in Hindi and Urdu. We chose it for the feeling of being captivated. We will never romanticise addiction or dangerous drinking, and cultural advisors will review the name before launch. The founder chose it; legal clearance is pending.</p>
<p><a href="about.html">About NASHA</a></p>
</div></section>
'''
    return layout("index.html", "NASHA: Indo-Mex brewery and kitchen, in development",
                  "NASHA is a future Indo-Mex brewery and kitchen in Austin, Texas. In development. Nothing is for sale yet.", beats)

def page_food():
    cats = sorted({d["category"] for d in dishes})
    f = (filter_set("", "", "category", "", [(c, c) for c in cats]) + filter_set("", "", "diet", "", [("veg", "Vegetarian as designed")]) 
         + filter_set("", "", "heat", "", [(str(i), f"Heat {i}") for i in range(4)]))
    body = f'''<section aria-labelledby="h1"><div class="wrap">
<p class="eyebrow">Food · Designs for testing</p><h1 id="h1">The dishes we are designing.</h1>
<p class="lede">Twelve dishes are specified for a first round of kitchen tests, with a few more held for later. None are cooked for guests. None are for sale.</p>
<p class="disclosure">{E(DISCLOSE)} Labels like “Fusion” mean a dish we invented by combining two traditions. “Inspired by” means built from a tradition without claiming to be it.</p>
<fieldset class="filters" data-filter-group="dish-list" data-status="dish-status" ><legend>Filter dishes</legend>{f}<button type="button" class="btn btn-ghost" data-reset>Clear</button></fieldset>
<p id="dish-status" class="muted" role="status" aria-live="polite"></p>
<div id="dish-list" class="grid cols-3">{"".join(dish_card(d) for d in dishes)}</div>
</div></section>'''
    return layout("food.html", "Food · NASHA", "Dishes NASHA is designing for kitchen tests. None are for sale.", body)

def page_beer():
    groups = sorted({b["group"] for b in beers})
    f = filter_set("", "", "group", "", [(g, g) for g in groups])
    body = f'''<section aria-labelledby="h1"><div class="wrap">
<p class="eyebrow">Beer · Briefs for a brewer</p><h1 id="h1">The beers we are imagining.</h1>
<p class="lede">Nothing has been brewed. Each beer is a brief for a head brewer to critique, changed, or rejected. Some names are working names.</p>
<p class="disclosure">{E(DISCLOSE)} Alcohol is for adults of legal drinking age. Any future beer sales depend on licences we have not yet obtained.</p>
<fieldset class="filters" data-filter-group="beer-list" data-status="beer-status" ><legend>Filter beers</legend>{f}<button type="button" class="btn btn-ghost" data-reset>Clear</button></fieldset>
<p id="beer-status" class="muted" role="status" aria-live="polite"></p>
<div id="beer-list" class="grid cols-3">{"".join(beer_card(b) for b in beers)}</div>
</div></section>'''
    return layout("beer.html", "Beer · NASHA", "Beer briefs for a future NASHA brewery. Nothing has been brewed.", body)

def page_crossing():
    rows = ""
    for c in crossing:
        rows += (f'<div class="cross"><div class="theme">{E(c["theme"])}<br><span class="chip">{E(c["evidence"])}</span></div>'
                 f'<div><small>India</small>{E(c["india"])}</div><div><small>Mexico</small>{E(c["mexico"])}</div>'
                 f'<div><small>NASHA</small>{E(c["nasha"])}<p class="muted"><small>Note</small>{E(c["note"])}</p></div></div>')
    body = f'''<section class="band-indigo" aria-labelledby="h1"><div class="wrap">
<p class="eyebrow">The Crossing</p><h1 id="h1">India and Mexico at one table.</h1>
<p class="lede">We look for real overlaps and say how sure we are. “Supported” means the history is well established. “Analogy” means a good comparison, not a claim of shared origin. “Unresolved” means we do not know.</p></div></section>
<section aria-labelledby="h2"><div class="wrap"><h2 id="h2" class="visually-hidden">Themes</h2>{rows}
<p class="muted">NASHA is an Indo-Mex kitchen in the sense of a designed fusion. We do not claim any dish is traditional to either country.</p></div></section>'''
    return layout("crossing.html", "The Crossing · NASHA", "Where Indian and Mexican cooking overlap, with honest notes on how sure we are.", body)

def page_labs():
    path = "".join(f'<li{" class=\"current\"" if p["stage"] == "Now" else ""}><span class="stage">{E(p["stage"])}</span><h3>{E(p["title"])}</h3><p>{E(p["body"])}</p><p class="muted">Needs: {E(p["needs"])}</p></li>' for p in labs["path"])
    method = "".join(f"<li>{E(m)}</li>" for m in labs["method"])
    entries = ("<p>No entries yet. Labs publishes only real tests, with results, including failures. When there is a first test, it will appear here.</p>"
               if not labs["entries"] else "")
    body = f'''<section aria-labelledby="h1"><div class="wrap">
<p class="eyebrow">Labs</p><h1 id="h1">Tests, in public.</h1>
<p class="lede">Labs is where NASHA will publish real tests and what we learn from them. It is empty today because nothing has been tested.</p>
{entries}
<h2>How Labs works</h2><ul>{method}</ul>
<h2>The path from here</h2><ol class="path">{path}</ol>
</div></section>'''
    return layout("labs.html", "Labs · NASHA", "Where NASHA will publish real tests and results. Empty until there is something real to publish.", body)

def page_about():
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">About</p><h1 id="h1">About NASHA.</h1>
<p class="lede">NASHA is food and beer designed together to captivate you, made in plain sight and shared at a long table.</p>
<p>It is a project of Ritesh Mamidi, who is building toward an Indo-Mex brewery and kitchen in Austin, Texas. Today it is a body of design and a plan, not a business that serves anyone.</p>
<h2>The name</h2>
<p>The founder chose the name NASHA. Legal clearance of the name has not been completed, and nothing here claims trademark ownership, registration, availability, or ownership of any domain or social handle. If a professional review finds a problem, the name returns to the founder for a decision.</p>
<p><em>Nasha</em> means intoxication or addiction in Hindi and Urdu. We chose it for the feeling of being captivated by food and beer. We commit to never romanticising addiction, alcoholism or dangerous drinking, and to asking cultural advisors to review the name and our language before launch.</p>
<h2 id="rights">How we handle rights</h2>
<p>Every file on this site is listed in a rights register: what it is, who made it, how, and under what licence. Illustrations are original vector drawings made for this project. Fonts are Inter and Instrument Serif, both under the SIL Open Font License. We use no stock photos, no third-party scripts and no trackers. No photographs are shown, because we do not yet have rights-clean ones of a place that does not exist.</p>
<h2>Evidence and honesty</h2>
<p>Design is not proof. This site shows what we have designed. It does not show that anyone wants it, that it can be brewed or cooked well, or that it can be built. Those are tests still to come, and Labs will report them.</p>
<h2>Contact</h2>
<p>There is no public contact address or mailing list yet. We will add one when it is real.</p>
</div></section>'''
    return layout("about.html", "About · NASHA", "About NASHA, the name, the rights approach, and what is and is not true today.", body)

# ---------- Build ----------
def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "fonts"))
    for fn, fnc in (("index.html", page_index), ("food.html", page_food), ("beer.html", page_beer),
                    ("crossing.html", page_crossing), ("labs.html", page_labs), ("about.html", page_about)):
        with open(os.path.join(DIST, fn), "w", encoding="utf-8") as f:
            f.write(fnc())
    for n in ("styles.css", "app.js"):
        shutil.copy(os.path.join(SRC, n), os.path.join(DIST, n))
    for n in os.listdir(os.path.join(SRC, "fonts")):
        shutil.copy(os.path.join(SRC, "fonts", n), os.path.join(DIST, "fonts", n))
    write_rights()
    print("built", len(os.listdir(DIST)), "entries in dist/")

DESC = {
 "index.html": ("page", "Home page, generated from website/build.py and website/data/*.json"),
 "food.html": ("page", "Food page"), "beer.html": ("page", "Beer page"), "crossing.html": ("page", "The Crossing page"),
 "labs.html": ("page", "Labs page"), "about.html": ("page", "About page"),
 "styles.css": ("code", "Site stylesheet written for this project"), "app.js": ("code", "Site script written for this project"),
}
def write_rights():
    """Regenerate the website asset rights register from dist/ so every file is covered."""
    rows = []
    for dp, _, fs in os.walk(DIST):
        for n in sorted(fs):
            rel = os.path.relpath(os.path.join(dp, n), DIST).replace(os.sep, "/")
            if rel.startswith("fonts/LICENSE"):
                typ, who, how, lic, note = "licence text", "Font authors", "Copied from the font package", "SIL OFL 1.1 text", "Licence notice distributed with the font."
                nm = f"Licence {n}"
                src = "Font project authors"; meth = "copied unmodified"; lic = "SIL OFL 1.1"; ok = ("yes", "yes", "yes", "yes")
            elif rel.startswith("fonts/"):
                fam = "Inter" if n.startswith("inter") else "Instrument Serif"
                typ, nm, src = "font", f"{fam} ({n})", f"{fam} Project Authors via the @fontsource npm package"
                meth, lic, ok = "third-party open font, unmodified", "SIL OFL 1.1", ("yes", "yes", "yes", "no")
                note = "Self-hosted latin subset. OFL permits commercial use and embedding. Reserved font names apply to modified versions only. Recheck when adding scripts."
            else:
                typ, d = DESC[rel]; nm = rel
                src = "Founder project, authored with an AI coding assistant"
                meth = "AI-assisted, human-directed; original code and text"
                lic = "Owned by project; no third-party licence"; ok = ("yes", "yes", "yes", "no")
                note = d + ". AI-assisted authorship: copyright position unsettled for AI-generated material; founder review and edit recommended (see ip/IP-OWNERSHIP-FRAMEWORK.md). Embedded SVG art is original vector drawing created for this project." if rel == "index.html" else d + ". AI-assisted authorship; see ip/IP-OWNERSHIP-FRAMEWORK.md."
            page = rel if typ == "page" else "all"
            rows.append([f"WA-{len(rows)+1:03d}", page, typ, nm, src, meth, lic, ok[0], ok[1], ok[2], ok[3],
                         "website/build.py; sha256 " + hashlib.sha256(open(os.path.join(DIST, rel), "rb").read()).hexdigest()[:16],
                         "in use", note])
    for nm, page, d in (("Hero illustration (inline SVG)", "index.html", "Original vector concept drawing of the hall at dusk, written as SVG code in build.py"),
                        ("Concept zone diagram (inline SVG)", "index.html", "Original vector diagram of four concept zones"),
                        ("Beer glass icons (inline SVG)", "beer.html; index.html", "Two simple original glass icons")):
        rows.append([f"WA-{len(rows)+1:03d}", page, "illustration", nm, "Founder project, authored with an AI coding assistant",
                     "AI-assisted, human-directed original vector code; not an AI image generator output", "Owned by project; no third-party licence",
                     "yes", "yes", "yes", "no", "website/build.py", "in use", d + ". Copyright position of AI-assisted work unsettled; commission or founder redraw recommended before brand use."])
    hdr = next(csv.reader(open(os.path.join(REPO, "ip/website-asset-rights-register.csv"))))
    with open(os.path.join(REPO, "ip/website-asset-rights-register.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(rows)

if __name__ == "__main__":
    main()
