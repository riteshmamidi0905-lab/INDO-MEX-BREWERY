"""Sprint 23 pages for the private NASHA site. Every page here renders from website/data/investor.json, which tools/blueprint_views.py generates from the canonical
CSV data (nothing is typed twice). Pages receive the build module as B so they reuse its layout, figures and tags.
Truth rules: no booking, ordering, location, opening date, customer, review, press, metric or market size; concept media is always labelled; the founder-prototype slot stays
empty until a real photograph is registered in visuals/FOUNDER-PROTOTYPE-MEDIA.csv."""
import csv, hashlib, html, os, re

E = html.escape
STATUS_WORDS = [
    ("DOCUMENTED", "Written down and structured. Not tested."),
    ("IN DEVELOPMENT", "Being designed and prepared for a first test."),
    ("FOUNDER PROTOTYPE", "Cooked or made by the founder, with originals preserved."),
    ("PERSONALLY TESTED", "Tasted and scored by the founder's tasters under written rules."),
    ("EXTERNAL VALIDATION PENDING", "Needs guests, buyers or vendors outside the project."),
    ("PROFESSIONAL REVIEW REQUIRED", "Needs a lawyer, brewer, chef, engineer or other qualified person."),
    ("FUTURE CAPITAL", "Needs money that does not exist yet."),
]
SLUG = lambda s: re.sub(r"[^a-z]+", "-", s.lower()).strip("-")
MECH = {"CLEANSING": "Resets the mouth between bites", "CONTRAST": "Opposite qualities that balance each other", "AROMA_BRIDGE": "A shared smell that links food and drink", "ACIDITY": "Brightness that cuts richness", "SWEETNESS": "Sweetness that softens heat", "HEAT_RELIEF": "Cold and low bitterness that calm chile", "TEXTURE": "Bubbles or body that answer the dish's texture", "BITTERNESS": "Bitterness that grips fat (and can sharpen heat)", "ROAST": "Toasty notes that echo char", "SPICE": "Spice in the glass that echoes spice on the plate"}



ACR = {"NA", "MVP", "IP", "KPI", "POS", "D-54"}
def nice(s):
    """Sentence-ish title case that keeps acronyms (NA, MVP, IP) intact."""
    return " ".join(w.upper() if w.upper() in ACR else w.capitalize() for w in s.lower().split(" "))


def plain(s):
    """Public wording: strip project-internal references (decision ids, test-sheet names, repository talk, tier codes)."""
    s = re.sub(r"\s*\((?:[^()]*\b(?:repo|sheet \d+)\b[^()]*)\)", "", s or "")
    s = re.sub(r"\s*\(gate [\d.]+\)", "", s)
    s = s.replace("T+10", "ten minutes in").replace("T+5", "five minutes in").replace("T+0", "at the start")
    s = re.sub(r"\bproposed (?:decision )?D-77\b|\bD-77\b", "the proposed gate rule", s)
    s = re.sub(r"\bD-54\b", "the no-beef, no-pork rule", s)
    s = re.sub(r"\(web sources, T1;[^)]*\)", "(from web sources; an advisor is to confirm)", s)
    s = re.sub(r"\s*\((?:see )?[\w\-/ ,]*\.csv\)", "", s)
    s = re.sub(r"decision gate BG-\d+ not passed for sale", "the gate for a paid test has not passed", s)
    s = re.sub(r"\b(?:see )?BG-\d+( plus)?", lambda m: "the earlier gates" + (" plus" if m.group(1) else ""), s)
    s = re.sub(r"\s*\((?:D|BG|PG)-\d+\)", "", s)
    s = re.sub(r"\bD-74\b", "the frozen test rules", s)
    s = re.sub(r"\bD-66\b", "the no-logo rule", s)
    s = re.sub(r"\bD-\d+\b", "a recorded decision", s)
    s = re.sub(r"\bT1\b", "web-summary level", s)
    s = re.sub(r"\s*\(?the older wording[^.)]*[.)]?\)?", "", s)
    return s.strip()


def label_tables(html_):
    """Give every body cell its column label so tables can stack as cards on phones."""
    def one(m):
        t = m.group(0); heads = re.findall(r'<th scope="col">(.*?)</th>', t, flags=re.S)
        if not heads: return t
        def row(rm):
            cells = rm.group(0); i = [0]
            def cell(cm):
                k = min(i[0], len(heads) - 1); i[0] += 1
                return f'<{cm.group(1)} data-label="{html.escape(re.sub(r"<[^>]+>", "", heads[k]).strip())}"' + cm.group(2) + ">"
            return re.sub(r'<(td|th scope="row")( ?[^>]*)>', lambda cm: cell(cm), cells)
        head, _, body = t.partition("</thead>")
        body = re.sub(r"<tr>.*?</tr>", row, body, flags=re.S)
        return head + "</thead>" + body
    return re.sub(r"<table>.*?</table>", one, html_, flags=re.S)


def st(label):
    return f'<span class="st" data-s="{SLUG(label)}">{E(label)}</span>'


def legend():
    items = "".join(f'<div><dt>{st(w)}</dt><dd>{E(d)}</dd></div>' for w, d in STATUS_WORDS)
    return f'<dl class="st-legend">{items}</dl>'


def mech_chips(m):
    return "".join(f'<span class="chip">{E(x.replace("_", " ").lower())}</span>' for x in m.split("|"))


def load_proto(B):
    """Registered founder media (visuals/FOUNDER-PROTOTYPE-MEDIA.csv). Returns {food_id: [dict(file, stage, alt, date, iteration)]} and writes web copies without EXIF."""
    path = os.environ.get("NASHA_MEDIA_CSV") or os.path.join(B.REPO, "visuals/FOUNDER-PROTOTYPE-MEDIA.csv")
    out = {}
    if not os.path.exists(path):
        return out
    from PIL import Image
    ok = {"FOUNDER PROTOTYPE": "PROTOTYPE", "VALIDATED PRODUCT": "TESTED PRODUCT", "PROFESSIONAL FINAL": "FINAL PHOTOGRAPHY"}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["media_stage"] not in ok:
            raise SystemExit(f"prototype media {r['media_id']}: stage {r['media_stage']!r} not one of {sorted(ok)} (concept media is never registered here)")
        src = r["file"] if os.path.isabs(r["file"]) else os.path.join(B.REPO, r["file"])
        if not os.path.exists(src):
            raise SystemExit(f"prototype media {r['media_id']}: file missing: {r['file']}")
        h = hashlib.sha256(open(src, "rb").read()).hexdigest()
        if h != r["original_sha256"]:
            raise SystemExit(f"prototype media {r['media_id']}: sha256 does not match the registered original")
        im = Image.open(src); im = im.convert("RGB"); im.thumbnail((1400, 1400))
        name = f"proto-{r['media_id']}.jpg"
        im.save(os.path.join(B.DIST, "images", name), "JPEG", quality=82, optimize=True)   # re-saved without EXIF
        out.setdefault(r["food_id"], []).append(dict(file=name, stage=ok[r["media_stage"]], label=r["media_stage"], alt=r["alt_text"], date=r["captured_date"], it=r["iteration_id"], w=im.width, h=im.height))
    return out


def proto_figure(B, m):
    t, extra = B.STAGE_TAG[m["stage"]]
    return (f'<figure class="fig"><img src="images/{E(m["file"])}" width="{m["w"]}" height="{m["h"]}" alt="{E(m["alt"])}" loading="lazy" decoding="async">'
            f'<figcaption class="tag" data-stage="{E(m["stage"])}">{E(t)}<span class="visually-hidden">{E(extra)}</span></figcaption></figure>')


def media_or_slot(B, fid, concept_html):
    ms = B.PROTO.get(fid, [])
    if ms:
        return "".join(proto_figure(B, m) for m in ms)
    return concept_html + '<p class="slot" role="note">Founder photograph: not yet.</p>'


def fix_regions(body):
    """Scroll containers are landmarks: give each a unique label taken from its table caption."""
    return re.sub(r'aria-label="Table, scrolls sideways on small screens">\s*<table><caption class="visually-hidden">(.*?)</caption>', lambda m: f'aria-label="{m.group(1)} (table, scrolls sideways on small screens)"><table><caption class="visually-hidden">{m.group(1)}</caption>', body)


def subnav(cur):
    items = [("experience.html", "An evening"), ("space.html", "The hall")]
    return '<nav class="subnav" aria-label="The place">' + "".join(f'<a href="{f}"{" aria-current=\"page\"" if f == cur else ""}>{E(n)}</a>' for f, n in items) + "</nav>"


# ------------------------------------------------------------------ pairings
def page_pairings(B, S):
    cards = ""
    for c in S["core5"]:
        na = c["na"]
        cards += (f'<article class="card pair-card" aria-labelledby="p-{c["id"]}"><h3 id="p-{c["id"]}">{E(c["name"])}</h3><p>{st("IN DEVELOPMENT")}</p>'
                  f'<dl class="pdl"><div><dt>Beer, first idea</dt><dd>{E(c["primary_beer"])}</dd></div><div><dt>Zero-proof, first idea</dt><dd>{E(plain(na["primary_na"]))}</dd></div></dl>'
                  f'<p class="chips">{mech_chips(na["mechanisms"])}</p><p><strong>Why it may work.</strong> {E(plain(na["why_it_may_work"]))}</p>'
                  f'<details><summary>Alternates, how it could fail, what decides it</summary><dl class="pdl"><div><dt>Beer, alternate</dt><dd>{E(c["alternate_beer"])}</dd></div><div><dt>Zero-proof, alternate</dt><dd>{E(plain(na["alternate_na"]))}</dd></div></dl>'
                  f'<p><strong>How it could fail.</strong> {E(plain(na["how_it_could_fail"]))}</p><p><strong>What decides it.</strong> {E(plain(na["deciding_test"]))}</p></details></article>')
    glossary = "".join(f"<li><strong>{E(k.replace('_', ' ').title())}.</strong> {E(v)}.</li>" for k, v in MECH.items())
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">Pairings</p><h1 id="h1">Why this plate with this glass.</h1>
<p class="lede">NASHA designs food and drink together. Each of the five core dishes has a beer, and a zero-proof drink of equal standing, chosen for a reason you can taste and argue with.</p>
<p>The reasons are simple: a cold, clean drink calms chile; something bright cuts richness; a shared aroma links plate and glass; a bitter edge can grip fat but can also sharpen heat. Each pairing names how it could go wrong and the small tasting that will decide it.</p>
<p class="disclosure">{E(B.DISCLOSE)} The pairings are proposed and not sensory tested; none has a score.</p>
</div></section>
<section class="alt" aria-labelledby="mc"><div class="wrap"><h2 id="mc">The ideas, in plain words.</h2><ul class="gloss">{glossary}</ul></div></section>
<section aria-labelledby="pc"><div class="wrap"><h2 id="pc">The five pairings.</h2><div class="grid cols-2">{cards}</div></div></section>
<section class="alt" aria-labelledby="eq"><div class="wrap stack"><h2 id="eq">Zero-proof is a pairing, not a fallback.</h2>
<p class="lede">Each non-alcoholic idea is built with the same care as the beer: acid, aroma, texture and a reason. They are categories with a flavour plan, not recipes.</p>
<p class="muted">Fresh-fruit, dairy-based and botanical drinks need a food-safety professional to review shelf life, storage and service before anything is served. No fermentation method, health claim or strength claim is made here.</p>
<p><a href="beer.html">The five beers</a> · <a href="food.html">The five dishes</a> · <a href="labs.html">How pairings will be tested</a></p></div></section>'''
    return B.layout("pairings.html", "Pairings · NASHA", "How NASHA designs food and drink together: five dishes, five beers, and zero-proof drinks of equal standing. Hypotheses, not tasted.", body)


# ------------------------------------------------------------------ lab
def page_lab(B, S):
    stages = S["lab_stages"]
    pipe = "".join(f'<li><span class="stage">{i + 1}</span>{E(s)}</li>' for i, s in enumerate(stages))
    reach = {"chicken-65-totopos": "Prototype designed; cook protocol written and frozen before cooking; ready for the first cook", "paneer-tikka-taco": "Researched and designed; first test is a heat-source comparison", "goat-birria": "Researched and designed; yield, supply and a safe cooling process are open", "gobi-taco": "Researched and designed; roast versus fry is open", "butter-chicken-quesadilla": "Researched and designed; comal load and tortilla choice are open"}
    rows = ""
    for c in S["core5"]:
        slot = (f'{len(c["media"])} registered' if c["media"] else "none yet")
        rows += f'<tr><th scope="row">{E(c["name"])}</th><td>{E(reach[c["id"]])}</td><td>{c["iterations"]} recorded</td><td>{E(slot)}</td><td>{E(c["narr"]["next_test_public"])}</td></tr>'
    path = "".join(f'<li{" class=\"current\"" if p["stage"] == "Now" else ""}><span class="stage">{E(p["stage"])}</span><h3>{E(p["title"])}</h3><p>{E(p["body"])}</p><p class="muted">Needs: {E(p["needs"])}</p></li>' for p in B.labs["path"])
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">The Lab</p><h1 id="h1">How a dish becomes real.</h1>
<p class="lede">NASHA develops food the slow way: idea, research, prototype, cook, measure, taste, learn from what fails, iterate, and only then call it validated. The Lab shows where each dish really is, including the parts that have not happened.</p>
<p class="disclosure">Today no dish has been cooked. The first home-kitchen test is written and ready; this page will gain photographs, scores, costs and failures from real cooks, in the order they happen, and nothing will be invented to fill it.</p>
<ol class="pipe" aria-label="Development stages">{pipe}</ol>
</div></section>
<section class="alt" aria-labelledby="wh"><div class="wrap"><h2 id="wh">Where each dish is.</h2>
<div class="scroll-x" tabindex="0" role="region" aria-label="Development position of each core dish"><table><caption class="visually-hidden">Development position of each core dish</caption><thead><tr><th scope="col">Dish</th><th scope="col">Position today</th><th scope="col">Iterations</th><th scope="col">Founder photographs</th><th scope="col">Next test</th></tr></thead><tbody>{rows}</tbody></table></div></div></section>
<section aria-labelledby="jr"><div class="wrap"><h2 id="jr">The prototype journal.</h2>
<p class="lede">Empty on purpose. Every real cook will add one entry.</p>
<dl class="journal-def"><div><dt>Iteration and date</dt><dd>Which attempt, and when.</dd></div><div><dt>Photo</dt><dd>An original, unedited photograph from the cook.</dd></div><div><dt>Change</dt><dd>What was changed since the last attempt.</dd></div><div><dt>Observation</dt><dd>What the cook and tasters saw, measured and said, including failures.</dd></div><div><dt>Result</dt><dd>Pass, rework, hold or cut, under rules written beforehand.</dd></div><div><dt>Next change</dt><dd>What the next attempt will change, and why.</dd></div></dl>
<p class="slot" role="note">Entry 001: waiting for the first cook.</p><p class="muted">Costs and pairings will evolve in the same journal as real receipts and real tastings arrive.</p></div></section>
<section class="alt" aria-labelledby="ml"><div class="wrap"><h2 id="ml">What kind of picture is this?</h2>
<p>Every image on this site carries its stage so a render can never be mistaken for food that was cooked.</p>
<ol class="media-life"><li><strong>Concept media.</strong> Drawings and AI-assisted visualizations. Every picture on this site is here today.</li><li><strong>Founder prototype media.</strong> Original photographs from the founder's own cooks.</li><li><strong>Validated product media.</strong> Photographs of a dish that passed its written gates.</li><li><strong>Professional final media.</strong> Professional photography of the finished product.</li></ol>
<p class="muted">The stage is set by evidence, not by how good a picture looks.</p></div></section>
<section aria-labelledby="st"><div class="wrap"><h2 id="st">The words we use for status.</h2>{legend()}</div></section>
<section class="alt" aria-labelledby="pf"><div class="wrap grid cols-2 center"><div><h2 id="pf">The path from here.</h2><ol class="path">{path}</ol></div>{B.svg_fig("NV-ILL-POPUP", B.art.popup_scene(B.uid("lp")), "", "960/500")}</div>
<div class="wrap"><p class="muted">The pop-up drawing is one possible early form. It is not a final vehicle, a booked event or a decision.</p></div></section>'''
    return B.layout("labs.html", "The Lab · NASHA", "How NASHA develops dishes and pairings, where each Core 5 dish really stands, and the prototype journal that will fill with real cooks.", body)


# ------------------------------------------------------------------ food (core 5)
def core5_cards(B, S, with_details=True):
    out = ""
    for c in S["core5"]:
        n = c["narr"]; d = B.DISH.get(c["id"])
        plate = f'<div class="plate-big">{B.plate_svg(d)}</div>' if d else ""
        media = media_or_slot(B, c["id"], plate)
        det = ""
        if with_details:
            det = (f'<details><summary>The full design</summary><dl class="pdl"><div><dt>Indian side</dt><dd>{E(plain(n["indian_component"]))}</dd></div><div><dt>Mexican side</dt><dd>{E(plain(n["mexican_component"]))}</dd></div>'
                   f'<div><dt>How they join</dt><dd>{E(plain(n["fusion_logic"]))}</dd></div><div><dt>Texture target</dt><dd>{E(plain(c["texture"]))}</dd></div><div><dt>Cannot change without losing the dish</dt><dd>{E(plain(n["identity_critical_ingredients"]))}</dd></div>'
                   f'<div><dt>Beer idea</dt><dd>{E(c["primary_beer"])} (alternate: {E(c["alternate_beer"])})</dd></div><div><dt>Zero-proof idea</dt><dd>{E(plain(c["na"]["primary_na"]))}</dd></div>'
                   f'<div><dt>Biggest kitchen risk</dt><dd>{E(plain(c["holding"]))}</dd></div><div><dt>Cultural care</dt><dd>{E(plain(n["cultural_risk"]))}</dd></div><div><dt>First test</dt><dd>{E(n["next_test_public"])}</dd></div></dl></details>')
        out += (f'<article class="card core-card" aria-labelledby="f-{c["id"]}">{media}<h3 id="f-{c["id"]}">{E(c["name"])}</h3><p>{st("IN DEVELOPMENT")} <span class="chip">Proposed presentation · not cooked or tested</span></p>'
                f'<p>{E(n["what_it_is"])}</p><p class="muted">{E(plain(n["why_it_exists"]))}</p>{det}</article>')
    return out


def food_core_section(B, S):
    return f'''<section class="alt" aria-labelledby="c5"><div class="wrap"><p class="eyebrow">The Core 5</p><h2 id="c5">Five dishes, designed to be tested first.</h2>
<p>Every card is a design. Nothing here has been cooked for guests, and the drawings are not photographs. Each card reserves a space for the founder's first real photograph.</p>
<div class="grid cols-2">{core5_cards(B, S)}</div></div></section>'''


# ------------------------------------------------------------------ beer (core 5)
def beer_core_section(B, S):
    cards = ""
    for b in S["beers"]:
        extra = f'<p class="muted">{E(plain(b["non_brewer_note"]))}</p>' if b["id"] == "hefeweizen" else ""
        cards += (f'<article class="card core-card" aria-labelledby="b-{b["id"]}"><h3 id="b-{b["id"]}">{E(b["name"])}</h3><p>{st("IN DEVELOPMENT")} <span class="chip">Not brewed yet</span></p>'
                  f'<p>{E(plain(b["style_in_plain_words"]))}</p><dl class="pdl"><div><dt>Its job on the list</dt><dd>{E(plain(b["role_on_the_list"]))}</dd></div><div><dt>Flavour intent</dt><dd>{E(plain(b["flavor_intent"]))}</dd></div><div><dt>With food</dt><dd>{E(plain(b["food_role"]))}</dd></div></dl>'
                  f'<details><summary>Why it earns a tap, and what is undecided</summary><p>{E(plain(b["why_it_earns_a_tap"]))}</p><p class="muted">{E(plain(b["what_remains_undecided"]))}</p></details>{extra}</article>')
    lp = next(b for b in S["beers"] if b["id"] == "mexican-lager"); hf = next(b for b in S["beers"] if b["id"] == "hefeweizen")
    return f'''<section class="alt" aria-labelledby="b5s"><div class="wrap"><p class="eyebrow">The Core 5 beers</p><h2 id="b5s">Five briefs, in plain words.</h2>
<p>Nothing has been brewed and there is no recipe. These are briefs for a qualified brewer to challenge, written so a non-brewer can follow them. A brewer decides every process choice. Style-based concept visualization: any glass drawn on this page shows the style, not a brewed beer.</p>
<div class="grid cols-2">{cards}</div></div></section>
<section aria-labelledby="lvp"><div class="wrap grid cols-2"><div><h2 id="lvp">Mexican-Style Lager or Pilsner: a real question.</h2>
<p>Both are pale, crisp lagers. The question is not only taste. Would they attract different guests? Go with different dishes? Need meaningfully different brewing and tank time? Would one take sales from the other? Nobody can answer that from a desk, so the plan keeps both and lets a side-by-side tasting and, later, sales decide.</p>
<p class="muted">{E(plain(lp["non_brewer_note"]))}</p></div>
<div><h2 id="hfp">Why the Hefeweizen is the proof beer.</h2><p>{E(plain(hf["non_brewer_note"]))}</p><p class="muted">This is a proposal the founder has not yet confirmed.</p></div></div></section>'''


# ------------------------------------------------------------------ business / investor
def page_business(B, S):
    ex = {e["section"]: e for e in S["exec"]}
    def e(k): return f'<h3>{E(ex[k]["heading"])}</h3><p>{E(ex[k]["text"])}</p>'
    nav = [("sum", "Summary"), ("stage", "Where it stands"), ("brewery", "Why a brewery"), ("austin", "Why Austin"), ("model", "How it makes money"), ("capital", "Capital"), ("risks", "Risks"), ("faq", "Questions"), ("team", "Team"), ("room", "Data room")]
    toc = "<nav class=\"toc\" aria-label=\"On this page\"><ul>" + "".join(f'<li><a href="#{a}">{E(t)}</a></li>' for a, t in nav) + "</ul></nav>"
    done = "".join(f"<li>{E(x)}</li>" for x in [t.strip() for t in re.split(r"; ", ex["done"]["text"].rstrip("."))] if x)
    hh = "".join(f"<li>{E(x)}</li>" for x in ex["hasnt_happened"]["text"].split("|")); dx = "".join(f"<li>{E(x)}</li>" for x in ex["doesnt_exist"]["text"].split("|"))
    comp = "".join(f'<tr><th scope="row">{E(nice(c["area"]))}</th><td>{c["digital"]} of 4</td><td>{c["real"]} of 4</td><td>{c["pro"]} of 3</td><td>{E(c["next"])}</td></tr>' for c in S["completeness"])
    groups = {"OBSERVED FACT": "Search-based observations (small samples, not verified)", "PUBLIC RESEARCH": "Public sources (summaries, not primary documents)", "HYPOTHESIS": "Hypotheses to test"}
    aus = ""
    for k, t in groups.items():
        items = [a for a in S["austin"] if a["class"] == k]
        aus += f'<details><summary>{E(t)} ({len(items)})</summary><ul class="aus">' + "".join(f'<li><strong>{E(plain(a["statement"]))}</strong><br><span class="muted">What must be true: {E(plain(a["must_be_true"]))} Limit: {E(plain(a["limit"]))}</span></li>' for a in items) + "</ul></details>"
    comps = "".join(f'<tr><th scope="row">{E(c["segment"])}</th><td>{E(plain(c["learn"]))}</td><td>{E(plain(c["hypothesis"]))}</td><td>{E(plain(c["unknown"]))}</td></tr>' for c in S["competitors"])
    rest = [c for c in S["chain"] if c["chain"] == "RESTAURANT"]; brew = [c for c in S["chain"] if c["chain"] == "BREWERY"]
    flow = lambda items: '<ol class="flow">' + "".join(f'<li><strong>{E(nice(i["node"]))}</strong><span>{E(i["relationship"].split(";")[0])}</span></li>' for i in items) + "</ol>"
    path = '<ol class="flow flow-path">' + "".join(f"<li><strong>{E(a)}</strong><span>{E(b)}</span></li>" for a, b in [("Product validation", "Do the dishes work, and what do they cost?"), ("MVP", "Will people pay, and how fast can a kitchen run?"), ("Repeatability", "Do guests come back?"), ("Permanent site", "Does a fixed site make money?"), ("Brewery scale", "Does house beer justify its capital?")]) + "</ol>"
    stages = "".join(f'<li class="stagecard"><span class="stage">Stage {k}</span><h3>{E(nice(c["name"]))}</h3><p><strong>True first.</strong> {E(plain(c["true_first"]))}</p><p><strong>Capital unlocks.</strong> {E(plain(c["unlocks"]))}</p><p><strong>Risk removed.</strong> {E(c["risk"])}</p></li>' for k, c in enumerate(S["stages"], 1))
    gates = "".join(f'<tr><th scope="row">{E(g["commitment"])}</th><td><strong>{E(nice(g["stop"]))}</strong></td><td>{E(plain(g["pass"]))}</td></tr>' for g in S["gates_full"])
    risks = "".join(f'<tr><th scope="row">{E(nice(r["risk"]))}</th><td>{E(plain(r["why"]))}</td><td>{E(plain(r["test"]))}</td><td>{E(plain(r["decision"]))}</td></tr>' for r in S["risks"])
    mind = "".join(f'<tr><th scope="row">{E(nice(c["thesis"]))}</th><td>{E(plain(c["believe"]))}</td><td>{E(plain(c["evidence"]))}</td></tr>' for c in S["change_mind"])
    first = ["What is the biggest risk?", "What has actually been tested?", "What exactly would investment fund?", "What happens if NASHA cannot use the name?"]
    order = sorted(S["faq"], key=lambda q: (first.index(q["q"]) if q["q"] in first else 99))
    faq = "".join(f'<details{" open" if i == 0 else ""}><summary>{E(q["q"])}</summary><p>{E(plain(q["a"]))}</p></details>' for i, q in enumerate(order))
    team = "".join(f'<li><strong>{E(t["role"])}</strong>: {E(plain(t["gap"]))}</li>' for t in S["team"] if t["founder"].upper().startswith(("NO", "NOT", "PARTIAL")))
    funds = "".join(f'<li><strong>{E(nice(u["category"]))}</strong>: {E(plain(u["unlocks"]))}</li>' for u in S["use_of_funds"])
    absent = "".join(f"<li><strong>{E(a['item'])}</strong>: {E(plain(a['why']))}.</li>" for a in S["absent"])
    cats = []
    for d in S["dataroom"]:
        if d["category"] not in cats: cats.append(d["category"])
    room = "<dl class=\"room\">" + "".join(f'<div><dt>{E(c[3:])}</dt><dd>' + "; ".join(E(d["item"]) for d in S["dataroom"] if d["category"] == c) + "</dd></div>" for c in cats) + "</dl>"
    v = S["version"]
    body = f'''<section aria-labelledby="h1"><div class="wrap stack">
<p class="eyebrow">Business and investor view · private</p><h1 id="h1">What exists, what does not, and what money would solve.</h1>
<p class="lede">NASHA is a concept for an Indo-Mex brewery and kitchen in Austin. Nothing has been cooked, brewed or sold. The founder used the pre-capital period to remove as much uncertainty as possible, at no cost, before asking capital to solve the expensive problems.</p>
<p><strong>Next gate: cook and cost Chicken 65 Totopos at home. No capital is needed until that has happened.</strong></p>
<p class="facts"><span>Concept stage</span><span>Austin, Texas</span><span>Indo-Mex brewery and kitchen</span><span>No amount set</span></p>
<p>This private view is not an offer and asks for no money; no investor has been approached. If someone sent you this page, reply to them directly: there is no public contact.</p>
<p>{st("IN DEVELOPMENT")} {st("EXTERNAL VALIDATION PENDING")}</p>
{toc}
<details class="legend"><summary>What the status words mean</summary>{legend()}</details>
</div></section>
<section class="alt" id="sum" aria-labelledby="s-sum"><div class="wrap"><h2 id="s-sum">The idea in one page.</h2><div class="grid cols-2"><div>{e("concept")}</div><div>{e("product")}{e("risks")}</div></div></div></section>
<section id="stage" aria-labelledby="s-stage"><div class="wrap"><h2 id="s-stage">Where it stands.</h2><p class="lede">{E(ex["stage"]["text"])}</p>
<div class="grid cols-2"><div class="card"><h3>Done</h3><ul class="plain">{done}</ul></div><div class="card"><h3>Has not happened</h3><ul class="plain">{hh}</ul><h3 class="sub">Does not exist</h3><ul class="plain">{dx}</ul></div></div>

<p class="muted">Concept stage. The design baseline was frozen on {E(v["date"])}; that is a document milestone, not a validated business.</p></div></section>
<section class="alt" id="brewery" aria-labelledby="s-brew"><div class="wrap"><h2 id="s-brew">Why a brewery at all.</h2>
<p class="lede">The thesis, untested: beer designed with the food and poured at the same table is something guests cannot get by assembling food from one place and beer from another.</p>
<p>The test that would disprove it: if a host brewery, a collaboration or a partner's beer sells and pairs as well as NASHA's own would, a house brewhouse is not justified and the brewery stays unbuilt. That is why it is the last capital gate. Nobody has run this test, and no brewer has reviewed the idea.</p></div></section>
<section id="austin" aria-labelledby="s-austin"><div class="wrap"><h2 id="s-austin">Why Austin: facts, research and hypotheses, kept apart.</h2>
<p>Austin is the founder's chosen first market, not a proven one. Indian food, Mexican food, fusion, breweries and experiential hospitality all exist there; NASHA's hypothesis is the combination and the execution.</p>{aus}
<details><summary>What the market teaches</summary><div class="scroll-x" tabindex="0" role="region" aria-label="Market lessons"><table><caption class="visually-hidden">Market lessons</caption><thead><tr><th scope="col">Part of the market</th><th scope="col">What we can learn</th><th scope="col">NASHA's hypothesis</th><th scope="col">What we do not know</th></tr></thead><tbody>{comps}</tbody></table></div></details></div></section>
<section class="alt" id="model" aria-labelledby="s-model"><div class="wrap"><h2 id="s-model">How it could make money.</h2>
<p>A decision model, not a forecast. Every input is unknown today and labelled by how well it is known; there is no revenue, cost, margin or demand figure.</p>
<h3 class="sub">The restaurant</h3>{flow(rest)}<h3 class="sub">The brewery</h3>{flow(brew)}<h3 class="sub">The order of proof</h3>{path}
<p class="muted">The cheapest format that answers the next question comes first: a private tasting, an invited event, a commissary pop-up or a brewery residency, a trailer, and only then a fixed site.</p></div></section>
<section id="capital" aria-labelledby="s-cap"><div class="wrap"><h2 id="s-cap">The capital path.</h2><p>Six stages. No amount is set; amounts will follow real quotes. Sources to consider much later (none approached): hospitality investors, strategic and brewery partners, angels and later debt.</p>
<ol class="stagecards">{stages}</ol>
<details><summary>What money would unlock, in the order it is needed</summary><ol class="plain">{funds}</ol></details>
<details><summary>Gates that stop spending (none has passed)</summary><div class="scroll-x" tabindex="0" role="region" aria-label="Capital gates"><table><caption class="visually-hidden">Capital gates</caption><thead><tr><th scope="col">Commitment</th><th scope="col">Until it is true, the answer is</th><th scope="col">What has to pass</th></tr></thead><tbody>{gates}</tbody></table></div></details></div></section>
<section class="alt" id="risks" aria-labelledby="s-risk"><div class="wrap"><h2 id="s-risk">Risks, the cheapest test, and what would change the plan.</h2>
<div class="scroll-x" tabindex="0" role="region" aria-label="Risks"><table><caption class="visually-hidden">Risks</caption><thead><tr><th scope="col">Risk</th><th scope="col">Why it matters</th><th scope="col">Cheapest test</th><th scope="col">What would change the plan</th></tr></thead><tbody>{risks}</tbody></table></div>
<p class="muted">The name: NASHA is the founder's working name. A same-name restaurant has been reported in Austin, so the name needs an attorney's review before any name-dependent spend. Nothing here claims clearance, ownership or exclusivity.</p>
<details><summary>What would change our mind</summary><div class="scroll-x" tabindex="0" role="region" aria-label="What would change our mind"><table><caption class="visually-hidden">What would change our mind</caption><thead><tr><th scope="col">Thesis</th><th scope="col">What we believe today</th><th scope="col">Evidence that would change direction</th></tr></thead><tbody>{mind}</tbody></table></div></details></div></section>
<section id="faq" aria-labelledby="s-faq"><div class="wrap"><h2 id="s-faq">The hard questions.</h2>{faq}</div></section>
<section class="alt" id="team" aria-labelledby="s-team"><div class="wrap"><h2 id="s-team">The team, and what the company needs.</h2><p class="lede">{E(ex["founder"]["text"])}</p>
<p><strong>Next proofs the founder is working toward.</strong> {E(ex["milestones"]["text"])}</p>
<h3 class="sub">Capabilities the company needs and the founder does not yet show</h3><ul class="plain">{team}</ul><p class="muted">These are needs, not people who have agreed to join; no advisor or partner is claimed.</p></div></section>
<section id="room" aria-labelledby="s-room"><div class="wrap"><h2 id="s-room">The data room.</h2><p>Organised by topic. The founder shares documents if and when the founder decides to show this to someone; statuses are the project's own labels, not outside certification.</p>{room}
<details><summary>What is deliberately not in it</summary><ul class="plain">{absent}</ul></details></div></section>'''
    return B.layout("investor.html", "Business and investor view · NASHA", "A private, honest view of what NASHA is, what exists, the capital path and the risks.", fix_regions(body))


# ------------------------------------------------------------------ experience / space data sections
def journey_section(B, S):
    rows = "".join(f'<li><span class="stage">{i + 1}</span><div><h3>{E(j["stage"].title())}</h3><p>{E(j["experience"])}</p></div></li>' for i, j in enumerate(S["journey"][:13]))
    extra = "".join(f'<li><strong>{E(j["stage"].title())}.</strong> {E(j["experience"])}</li>' for j in S["journey"][13:])
    return f'''<section class="alt" aria-labelledby="gj"><div class="wrap"><h2 id="gj">How the guest journey is designed.</h2>
<p class="lede">From discovery to return, written as service principles rather than scripts. Proposed, and not yet tested with a single guest.</p>
<ol class="journey-list">{rows}</ol><h3 class="sub">Also designed in</h3><ul class="plain">{extra}</ul></div></section>'''


def space_section(B, S):
    rows = "".join(f'<tr><th scope="row">{E(t["space"].title())}</th><td>{E(t["intent"])}</td><td>{E(t["family"])}</td></tr>' for t in S["space"])
    return f'''<section class="alt" aria-labelledby="rq"><div class="wrap"><h2 id="rq">What each space has to do.</h2>
<p>Requirements for a future architect, not a design. Every picture of the hall is conceptual and illustrative.</p>
<div class="scroll-x" tabindex="0" role="region" aria-label="Table, scrolls sideways on small screens"><table><caption class="visually-hidden">Spaces and intent</caption><thead><tr><th scope="col">Space</th><th scope="col">Intent</th><th scope="col">Family and accessibility intent</th></tr></thead><tbody>{rows}</tbody></table></div><p class="muted">Not claimed anywhere: a site, square footage, seat or tank counts, equipment, code compliance, accessibility compliance or approval by any professional.</p></div></section>'''
