"""NASHA Founder Vision Preview: a private, self-contained, noindex family presentation of the Vision layer.
Builds website/family-dist/ (open index.html). It reuses the responsive image pipeline and the approved visual manifest, and none of the repository's internal
records appear in it. Truth boundary: a future concept; one concept notice in the footer and Our Story; no claims of a real restaurant, cooked dishes,
brewed beers, customers, a built place or name clearance.  Usage: python3 website/family.py [--check]"""
import csv, filecmp, html, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import images  # noqa: E402

E = html.escape
MANIFEST = os.path.join(REPO, "visuals/NASHA-VISUAL-MANIFEST.csv")
VIS = {r["id"]: r for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))}
META = {}
NAV = [("index.html", "Home"), ("food.html", "Food"), ("beer.html", "Beer"), ("court.html", "The Court"), ("experience.html", "The Experience"), ("story.html", "Our Story")]
NOTICE = ("NASHA is a founder's vision for an Indo-Mexican brewery and kitchen in Austin, Texas: a concept in development. The pictures are concept visualizations made with AI tools, "
          "and nothing here is open, cooked, brewed or for sale. NASHA is a working name.")


def pic(vid, sizes="100vw", eager=False, alt=None):
    row, meta = VIS[vid], META[vid]
    a = alt if alt is not None else re.sub(r"^Concept visualization( of|:)? ", "Concept image: ", row["alt_text"])
    return images.picture_html(row, meta, E(a), sizes, eager)


def layout(fn, title, desc, body, hero_id=None, preload=False):
    nav = "".join(f'<li><a href="{f}"{" aria-current=\"page\"" if f == fn else ""}>{E(n)}</a></li>' for f, n in NAV)
    pl = ""
    if preload and hero_id:
        m = META[hero_id]
        d = sorted([f for f in m["d"]["files"] if f["fmt"] == "avif" and f["w"] <= 1600], key=lambda f: f["w"])[-1]
        mm = [f for f in m["m"]["files"] if f["fmt"] == "avif" and f["w"] == 800][0]
        pl = (f'<link rel="preload" as="image" type="image/avif" media="(min-width: 701px)" href="images/{d["file"]}">\n'
              f'<link rel="preload" as="image" type="image/avif" media="(max-width: 700px)" href="images/{mm["file"]}">\n')
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
{pl}<link rel="icon" href="data:,">
<link rel="stylesheet" href="family.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="hd"><a class="mark" href="index.html" aria-label="NASHA, home">NASHA</a>
<button class="menu" type="button" aria-controls="nav">Menu</button>
<nav class="nav" id="nav" aria-label="Main"><ul>{nav}</ul></nav></header>
<main id="main">
{body}
</main>
<footer class="ft"><div class="w"><a class="mark" href="index.html" aria-label="NASHA, home">NASHA</a>
<ul>{"".join(f'<li><a href="{f}">{E(n)}</a></li>' for f, n in NAV)}</ul>
<p>{E(NOTICE)}</p></div></footer>
<script src="family.js" defer></script>
</body>
</html>
'''


def head(vid, eyebrow, h1, lede, eager=True):
    return (f'<section class="phead" aria-labelledby="h1">{pic(vid, eager=eager)}<div class="in"><p class="eyebrow">{E(eyebrow)}</p>'
            f'<h1 class="h1" id="h1">{h1}</h1><p class="lede">{E(lede)}</p></div></section>')


def bleed(vid, eyebrow, h2, p="", right=False, link=None, hid="b"):
    lk = f'<a class="link" href="{link[0]}">{E(link[1])}</a>' if link else ""
    return (f'<section class="bleed{" right" if right else ""}" aria-labelledby="{hid}">{pic(vid)}<div class="cap rv"><p class="eyebrow">{E(eyebrow)}</p>'
            f'<h2 class="h2" id="{hid}">{h2}</h2>{f"<p class=\"p\">{E(p)}</p>" if p else ""}{lk}</div></section>')


# --------------------------------------------------------------------------- data
DISHES = [
    ("chicken-65-totopos", "NV-VISION-VP05", "Chicken 65 Totopos", "South Indian Chicken 65, crisp and spiced, over thick fried corn totopos with curry leaf, a spoon of crema and a squeeze of lime.",
     "Mexican-Style Lager", "Fruit, lime and salt cooler"),
    ("paneer-tikka-taco", "NV-VISION-VP06", "Paneer Tikka Taco", "Charred paneer in a warm corn tortilla with salsa, onion, cilantro and lime. The smoke of the tandoor, built on a taqueria base.",
     "Witbier", "Spiced citrus sparkler"),
    ("goat-birria", "NV-VISION-VP07", "Goat Birria", "Goat, slow-braised in a deep chile adobo and served as small tacos, with a cup of consomme for dipping.",
     "Hefeweizen", "Hibiscus and tamarind tea"),
    ("gobi-taco", None, "Mango Habanero Gobi", "Cauliflower, still unmistakably cauliflower, with a mango and habanero glaze, shared at the table. An appetizer, not a taco. A design idea only: nothing has been cooked or tasted.",
     "Pilsner", "Lime and herb cooler"),
    ("butter-chicken-quesadilla", "NV-VISION-VP09", "Butter Chicken & Roasted Poblano Quesadilla", "A crisp griddled tortilla filled with rich butter chicken, roasted poblano and melted cheese, with a cool dip alongside.",
     "Vienna Amber", "Cultured dairy, fruit and spice drink"),
]
BEERS = [
    ("NASHA Hefeweizen", "Soft, hazy wheat beer with banana and clove. Made for rich, spiced food.", "Goat Birria"),
    ("Mexican-Style Lager", "Crisp, clean and cold. The easy one that cools the heat.", "Chicken 65 Totopos"),
    ("Vienna Amber", "Toasty and smooth. Built for char and slow cooking.", "Butter Chicken & Poblano Quesadilla"),
    ("Pilsner", "Bright and precise, with a clean bitter finish.", "Mango Habanero Gobi"),
    ("Witbier", "Hazy and citrusy, with soft wheat and orange peel.", "Paneer Tikka Taco"),
]
ZERO = [("Fruit, lime and salt cooler", "Chicken 65 Totopos"), ("Spiced citrus sparkler", "Paneer Tikka Taco"), ("Hibiscus and tamarind tea", "Goat Birria"),
        ("Lime and herb cooler", "Mango Habanero Gobi"), ("Cultured dairy, fruit and spice drink", "Butter Chicken & Poblano Quesadilla")]


# --------------------------------------------------------------------------- pages
def page_home():
    hero = (f'<section class="hero" aria-labelledby="h1">{pic("NV-VISION-VP01", eager=True)}<div class="in"><p class="eyebrow">Austin, Texas &middot; Founder Vision</p>'
            f'<h1 class="huge" id="h1">NASHA</h1><p class="sub">Food and beer, designed together.</p><p class="tag">A future Indo-Mexican brewery and kitchen</p></div>'
            f'<span class="cue" aria-hidden="true">Discover</span></section>')
    idea = ('<section class="sec indigo" aria-labelledby="idea"><div class="w"><p class="eyebrow">The idea</p><h2 class="big rv" id="idea">India &times; Mexico &times; Austin</h2>'
            '<p class="p rv">Indian fire and Mexican corn. Craft beer and zero-proof drinks. A shaded court with the brewery behind glass. NASHA imagines all of it as one meal, designed from the first idea to the last pour, '
            'and shared at long tables under Texas oaks.</p><a class="link rv" href="story.html">Our story</a></div></section>')
    court = bleed("NV-VISION-VP02", "The Court", "A brewery you walk into, a court you walk out to.", "Limestone, glass and shade, with the tanks beside the tables.", link=("court.html", "Walk the Court"), hid="c1")
    food = (f'<section class="sec light" aria-labelledby="fd"><div class="w"><div class="split"><div><p class="eyebrow">The food</p><h2 class="h2 rv" id="fd">Five dishes. Fire, corn, chile and curry leaf.</h2>'
            f'<p class="p rv">Chicken 65 on thick totopos. Charred paneer in a corn tortilla. Goat birria with a cup of consomme. Each one made to meet a beer and a zero-proof drink.</p>'
            f'<a class="link rv" href="food.html">See the food</a></div>'
            f'<div class="mosaic rv"><div class="ph a">{pic("NV-VISION-VP05", "(max-width:800px) 100vw, 40vw")}</div><div class="ph">{pic("NV-VISION-VP06", "(max-width:800px) 50vw, 25vw")}</div>'
            f'<div class="ph">{pic("NV-VISION-VP07", "(max-width:800px) 50vw, 25vw")}</div></div></div></div></section>')
    beer = bleed("NV-VISION-VP10", "The beer", "Brewed for the food.", "Five beers designed alongside the kitchen, and zero-proof drinks poured with the same care.", right=True, link=("beer.html", "Meet the beers"), hid="bw")
    eve = (f'<section class="sec pecan" aria-labelledby="ev"><div class="w"><div class="split rev"><div class="ph rv">{pic("NV-VISION-VP13", "(max-width:800px) 100vw, 55vw")}</div>'
           f'<div><p class="eyebrow">The evening</p><h2 class="h2 rv" id="ev">Warm, shared, unhurried.</h2><p class="p rv">Plates in the middle of the table. A server who knows what pairs with what. '
           f'The glow of the brewery through glass as the court fills.</p><a class="link rv" href="experience.html">A night at NASHA</a></div></div></div></section>')
    close = ('<section class="sec indigo" aria-labelledby="fv"><div class="w"><p class="eyebrow">The founder vision</p><h2 class="quote rv" id="fv">Food and beer, designed together to draw you in.</h2>'
             '<p class="p rv">Texan bones. Non-Texan details.</p><a class="link rv" href="story.html">Read the story</a></div></section>')
    return layout("index.html", "NASHA: food and beer, designed together", "Founder Vision for NASHA, a future Indo-Mexican brewery and kitchen in Austin, Texas.",
                  hero + idea + court + food + beer + eve + close, "NV-VISION-VP01", True)


def page_food():
    secs = ""
    for i, (did, vid, name, text, beer, zp) in enumerate(DISHES):
        rev = i % 2 == 1
        tone = "light" if not rev else "stone"
        img = (f'<div class="ph rv">{pic(vid, "(max-width:800px) 100vw, 55vw")}</div>' if vid else
               '<div class="ph rv" role="img" aria-label="Image pending for the new Mango Habanero Gobi direction" style="display:flex;align-items:center;justify-content:center;min-height:16rem;background:#efe6d4;color:#4a3b25;text-align:center;padding:1.5rem">'
               '<p>Image pending: the earlier concept picture showed a taco and has been withdrawn because the dish is no longer a taco.</p></div>')
        txt = (f'<div><p class="eyebrow">{i + 1:02d}</p><h2 class="dn rv" id="d{i}">{E(name)}</h2><p class="p rv">{E(text)}</p>'
               f'<p class="dmeet rv"><span>Pairing idea</span>{E(beer)} &middot; {E(zp)}</p></div>')
        secs += f'<section class="dish {tone}" aria-labelledby="d{i}"><div class="w"><div class="split{" rev" if rev else ""}">{img}{txt}</div></div></section>'
    table = bleed("NV-VISION-VP13", "At the table", "Made to be shared.", "Plates in the middle, a basket to pass, a beer for the table and a zero-proof drink for everyone.", hid="tb")
    close = ('<section class="sec indigo" aria-labelledby="hm"><div class="w"><p class="eyebrow">How it begins</p><h2 class="big rv" id="hm">Cooked at home first.</h2>'
             '<p class="p rv">Every dish starts in a home kitchen. Tasted, adjusted, tasted again, before anything else is asked of anyone.</p></div></section>')
    return layout("food.html", "Food · NASHA", "Five dishes where Indian and Mexican food cultures meet, envisioned for NASHA in Austin.",
                  head("NV-VISION-VP12", "The food", "Five dishes.", "Fire, corn, chile and curry leaf. India and Mexico at one table.") + secs + table + close, "NV-VISION-VP12", True)


def page_beer():
    rows = "".join(f'<div class="row rv"><h3>{E(n)}</h3><p>{E(t)}</p><p class="m">Meets &middot; {E(d)}</p></div>' for n, t, d in BEERS)
    zrows = "".join(f'<div class="row rv"><h3>{E(n)}</h3><p>&nbsp;</p><p class="m">Meets &middot; {E(d)}</p></div>' for n, d in ZERO)
    intro = ('<section class="sec light" aria-labelledby="bi"><div class="w"><div class="split"><div><p class="eyebrow">The idea</p><h2 class="h2 rv" id="bi">Beer designed alongside the kitchen, not apart from it.</h2></div>'
             '<div><p class="p rv" style="margin-top:0">At NASHA the beer list is not a separate menu. Each beer is chosen for the dishes it should meet: bright bubbles that reset the mouth after a bite, '
             'a soft wheat beer that answers a rich braise, a clean lager that cools the heat.</p></div></div></div></section>')
    five = (f'<section class="sec pecan" aria-labelledby="fv5"><div class="w"><p class="eyebrow">The envisioned opening family</p><h2 class="h2 rv" id="fv5">Five beers.</h2><div class="rows">{rows}</div>'
            f'<p class="p mut rv">Three of the five are shown in the picture above. Each beer is envisioned for the dish named beside it.</p></div></section>')
    zp = bleed("NV-VISION-VP11", "Zero-proof", "Poured with equal care.", "Zero-proof drinks are part of the table, not an afterthought: clear, bright and made to meet the same dishes.", hid="zp")
    zl = f'<section class="sec indigo" aria-labelledby="zl"><div class="w"><p class="eyebrow">Five ideas</p><h2 class="h2 rv" id="zl">For everyone at the table.</h2><div class="rows">{zrows}</div></div></section>'
    bar = bleed("NV-VISION-VP03", "The bar", "A bar that belongs to the food.", "A long pecan bar with a window into the tanks, built around the kitchen and the glass.", right=True, hid="br")
    return layout("beer.html", "Beer · NASHA", "Brewed for the food: the beer and zero-proof program envisioned for NASHA in Austin.",
                  head("NV-VISION-VP10", "The beer", "Brewed for the food.", "Beer and zero-proof drinks, designed together with the kitchen.") + intro + five + zp + zl + bar, "NV-VISION-VP10", True)


def page_court():
    ch = [("01", "Street", "A quiet front of pale limestone and glass. One tank glowing behind the window."),
          ("02", "Threshold", "A covered entrance lowers the ceiling and cools the air."),
          ("03", "Compression", "A short, warm passage along the brewery glass. You smell malt and woodsmoke before you see anything."),
          ("04", "Reveal", "Then it opens: sky, shade, an oak, a thin channel of water and the hum of the room."),
          ("05", "The brewery", "Steel tanks behind glass, beside the tables. The brewing is part of the evening."),
          ("06", "The long tables", "Plates in the middle, a beer for the table, a zero-proof drink for everyone."),
          ("07", "Night", "The court glows, warm and never loud.")]
    chap = "".join(f'<div class="chap rv"><b>{n}</b><div><h3>{E(t)}</h3><p>{E(p)}</p></div></div>' for n, t, p in ch)
    start = (f'<section class="sec light" aria-labelledby="st"><div class="w"><div class="split"><div><p class="eyebrow">The route</p><h2 class="h2 rv" id="st">From the street to the court.</h2>'
             f'<p class="p rv">The Court Brewhouse is envisioned as a place you move through: compressed, then released. It is built from limestone, steel, cedar and shade, '
             f'with a brewery you can see and a court you can sit in.</p></div><div class="ph rv">{pic("NV-VISION-VP01-ENTRANCE", "(max-width:800px) 100vw, 55vw")}</div></div></div></section>')
    route = f'<section class="sec stone" aria-labelledby="rt"><div class="w"><h2 class="vh" id="rt">The seven moments</h2>{chap}</div></section>'
    reveal = bleed("NV-VISION-VP02", "The reveal", "Shade, tables and the tanks beside them.", "", hid="rv2")
    inside = (f'<section class="sec pecan" aria-labelledby="in"><div class="w"><div class="split rev"><div class="ph rv">{pic("NV-VISION-VP03", "(max-width:800px) 100vw, 55vw")}</div>'
              f'<div><p class="eyebrow">Inside</p><h2 class="h2 rv" id="in">A bar, a brewery and a kitchen that share one room.</h2>'
              f'<p class="p rv">A long bar with a window into the tanks. The glow of the oven in the arcade wall. Nothing staged: the work is simply visible.</p></div></div></div></section>')
    night = bleed("NV-VISION-VP04", "After dark", "Warm, not loud.", "Low lamps, glowing tanks, a full court. A restaurant courtyard, not a nightclub.", hid="nt")
    close = ('<section class="sec indigo" aria-labelledby="fc"><div class="w"><p class="eyebrow">The future Court Brewhouse</p><h2 class="quote rv" id="fc">A place to arrive, sit down and stay.</h2>'
             '<a class="link rv" href="experience.html">A night at NASHA</a></div></section>')
    return layout("court.html", "The Court · NASHA", "The Court Brewhouse: the envisioned limestone-and-glass brewery, kitchen and shaded court for NASHA in Austin.",
                  head("NV-VISION-VP01", "The Court", "A brewery you walk into.", "A court you walk out to. Limestone, glass, shade and long tables.") + start + route + reveal + inside + night + close, "NV-VISION-VP01", True)


def page_experience():
    steps = [("Arrival", "NV-VISION-VP01-ENTRANCE", "You come in from the street and the noise drops. The room is warm and low, and the court is just ahead."),
             ("Share the table", "NV-VISION-VP12", "Plates go in the middle. Someone passes the basket. Nobody orders alone."),
             ("See the brewery", "NV-VISION-VP03", "Behind the bar a window shows the tanks. The beer is made just beyond where it is poured."),
             ("Raise a glass", "NV-VISION-VP10", "A tall glass for the wheat beer, a tapered glass for the lagers, a tulip for amber. The same glasses carry the zero-proof drinks."),
             ("Everyone included", "NV-VISION-VP11", "Zero-proof drinks are poured with the same care and meant for the same dishes."),
             ("Warm service", "NV-VISION-VP13", "A server who knows the menu and the pairings, and who stays close without hovering.")]
    secs = ""
    for i, (t, vid, p) in enumerate(steps):
        rev = i % 2 == 1
        tone = ["light", "stone"][i % 2]
        secs += (f'<section class="dish {tone}" aria-labelledby="x{i}"><div class="w"><div class="split{" rev" if rev else ""}"><div class="ph rv">{pic(vid, "(max-width:800px) 100vw, 55vw")}</div>'
                 f'<div><p class="eyebrow">{i + 1:02d}</p><h2 class="dn rv" id="x{i}">{E(t)}</h2><p class="p rv">{E(p)}</p></div></div></div></section>')
    night = bleed("NV-VISION-VP04", "The night court", "And then the court glows.", "No gimmicks and no nightclub. Warm light, good food, the brewery behind glass.", hid="nc")
    hours = [("5:30", "Doors open", "Low sun across the court. A cook lights the oven. The first glasses come off the shelf."),
             ("6:30", "Early tables", "Families arrive, with water and juice for the youngest. Plates start to move."),
             ("8:00", "The pairing hour", "A wheat beer beside the birria. A lager beside the Chicken 65. A tamarind tea at the next table."),
             ("10:00", "Late dinner", "The court quiets to small groups. A final plate of quesadilla wedges.")]
    hl = "".join(f'<li class="rv"><time>{E(a)}</time><div><h3>{E(b)}</h3><p>{E(c)}</p></div></li>' for a, b, c in hours)
    ev = (f'<section class="sec pecan" aria-labelledby="ho"><div class="w"><p class="eyebrow">One evening, imagined</p><h2 class="h2 rv" id="ho">Doors open to the last plate.</h2><ul class="hours">{hl}</ul></div></section>')
    return layout("experience.html", "The Experience · NASHA", "A night at NASHA, imagined: arrival, shared plates, the brewery behind glass and a warm court.",
                  head("NV-VISION-VP02", "The experience", "A night at NASHA.", "Arrive, share, see the brewery, raise a glass. Warm, shared and unhurried.") + secs + night + ev, "NV-VISION-VP02", True)


def page_story():
    why = ('<section class="sec light" aria-labelledby="wy"><div class="w"><div class="split"><div><p class="eyebrow">Why NASHA</p><h2 class="h2 rv" id="wy">Two food cultures in conversation, grounded in Austin.</h2></div>'
           '<div><p class="p rv" style="margin-top:0">Indian and Mexican kitchens already speak a similar language: chile, lime, toasted spice, flatbread, fermentation and fire. '
           'NASHA brings the two into conversation through food, beer and hospitality, in a city that loves both.</p>'
           '<p class="p rv">It is a founder\'s vision, and it is being developed deliberately before it opens.</p></div></div></div></section>')
    phil = ('<section class="sec indigo" aria-labelledby="ph"><div class="w"><p class="eyebrow">The philosophy</p><h2 class="quote rv" id="ph">Food and beer designed together to draw you in.</h2>'
            '<p class="big rv" style="margin-top:2.5rem;font-size:clamp(2rem,5vw,4rem)">Texan bones. Non-Texan details.</p>'
            '<p class="p rv">The bones are Texan: limestone, live oaks, shade, gravel and a long table. The details come from the food, the glass and the objects on the table.</p></div></section>')
    court = bleed("NV-VISION-VP04", "The place", "A court you can sit in.", "", hid="sc")
    how = ('<section class="sec light" aria-labelledby="hw"><div class="w"><p class="eyebrow">How it is being built</p><h2 class="h2 rv" id="hw">Carefully, before it opens.</h2>'
           '<div class="chap rv"><b>01</b><div><h3>Recipes begin at home</h3><p>Every dish starts in a home kitchen, tasted and adjusted before anything else.</p></div></div>'
           '<div class="chap rv"><b>02</b><div><h3>Beer is written as a brief</h3><p>The beers are drafted for a brewer to challenge, not decided in advance.</p></div></div>'
           '<div class="chap rv"><b>03</b><div><h3>The place is designed as a court</h3><p>The Court Brewhouse is drawn and pictured long before a site exists.</p></div></div>'
           '<div class="chap rv"><b>04</b><div><h3>Nothing opens until it has earned it</h3><p>Real cooking, real tasting and the right people come first.</p></div></div></div></section>')
    about = ('<section class="sec pecan" aria-labelledby="ab"><div class="w"><p class="eyebrow">About this preview</p><h2 class="h2 rv" id="ab">A concept in development.</h2>'
             '<p class="p rv">This is the founder\'s vision for NASHA, shared privately. The pictures are concept visualizations made with AI tools: no dish has been cooked, no beer brewed, no building built, '
             'and the people shown are not real guests. NASHA is a working name, and the name and the cultural details will be reviewed with the right advisors before anything is made public.</p>'
             '<p class="p rv">The word <em>nasha</em> means intoxication or addiction in Hindi and Urdu. It was chosen for the feeling of being drawn in by food, craft and company, and the project will never present excess as something to admire.</p>'
             '<p class="p mut rv">Founder: Ritesh Mamidi. Austin, Texas.</p></div></section>')
    return layout("story.html", "Our Story · NASHA", "Why NASHA exists: Indian and Mexican food cultures in conversation, grounded in Austin. A founder's concept in development.",
                  head("NV-VISION-VP02", "Our story", "Why NASHA.", "A founder's vision, developed deliberately before it opens.") + why + phil + court + how + about, "NV-VISION-VP02", True)


PAGES = [("index.html", page_home), ("food.html", page_food), ("beer.html", page_beer), ("court.html", page_court), ("experience.html", page_experience), ("story.html", page_story)]


def build(dist):
    if os.path.isdir(dist):
        shutil.rmtree(dist)
    os.makedirs(os.path.join(dist, "fonts")); imgdir = os.path.join(dist, "images"); os.makedirs(imgdir)
    used = sorted(set(re.findall(r'"(NV-VISION-[A-Z0-9-]+)"', open(__file__, encoding="utf-8").read())))
    for vid in used:
        META[vid] = images.build_raster(VIS[vid], imgdir)
    for fn, f in PAGES:
        open(os.path.join(dist, fn), "w", encoding="utf-8").write(f())
    shutil.copy(os.path.join(HERE, "family/family.css"), os.path.join(dist, "family.css"))
    shutil.copy(os.path.join(HERE, "family/family.js"), os.path.join(dist, "family.js"))
    for n in os.listdir(os.path.join(HERE, "src/fonts")):
        shutil.copy(os.path.join(HERE, "src/fonts", n), os.path.join(dist, "fonts", n))
    return used


if __name__ == "__main__":
    out = os.path.join(HERE, "family-dist")
    if "--check" in sys.argv:
        tmp = tempfile.mkdtemp()
        try:
            build(os.path.join(tmp, "d"))
            bad = [n for n in sorted(os.listdir(os.path.join(tmp, "d"))) if n.endswith((".html", ".css", ".js"))
                   and (not os.path.exists(os.path.join(out, n)) or open(os.path.join(tmp, "d", n), "rb").read() != open(os.path.join(out, n), "rb").read())]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if bad:
            print("STALE family-dist:", ", ".join(bad), "(run python3 website/family.py)"); sys.exit(1)
        print("family-dist fresh"); sys.exit(0)
    used = build(out)
    print("built", len(os.listdir(out)), "entries;", len(os.listdir(os.path.join(out, "images"))), "image files;", len(used), "images")
