#!/usr/bin/env python3
"""Build the local-preview collection pages (Beverages, Kitchen, Merchandise, NASHA LABS, NASHA AI Enterprise) into website/collections-dist/.

Static HTML, standard library + Pillow. Separate from website/dist/ (the audited concept site is not modified). Every page is noindex, carries the
concept/synthetic disclosure, and takes its numbers from committed result files (lab/results/*.json), never from typed text.
The product name NASHA is a WORKING name (D-79/D-80): it comes from the single WORKING_NAME constant, and nothing here is for publication.
    python3 website/build_collections.py
"""
import html
import json
import shutil
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
OUT = HERE / "collections-dist"
E = html.escape
WORKING_NAME = "NASHA"
CLAIMS = json.loads((REPO / "lab/results/canonical_claims.json").read_text())
RUN_PATH = REPO / "lab/results/enterprise_full_run.json"
RUN = json.loads(RUN_PATH.read_text()) if RUN_PATH.exists() else None
BEERS = {b["id"]: b for b in json.loads((HERE / "data/beers.json").read_text())}
DISHES = {d["id"]: d for d in json.loads((HERE / "data/dishes.json").read_text())}
DISCLOSE = ("Concept stage: there is no brewery, no restaurant and nothing for sale. Images are concept illustrations drawn by code, not photographs. "
            f"{WORKING_NAME} is a working name (legal clearance pending); the wordmark is a temporary typographic placeholder, not a logo.")
PAGES = [("beverages.html", "Beverages"), ("kitchen.html", "Kitchen"), ("merchandise.html", "Merchandise"), ("labs.html", f"{WORKING_NAME} Labs"), ("enterprise.html", f"{WORKING_NAME} AI Enterprise")]
CSS = """
.cx-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:var(--s-5,1.5rem);margin:var(--s-5,1.5rem) 0}
.cx-card{border:1px solid var(--rule);background:var(--bg-alt);padding:var(--s-5,1.5rem)}.cx-card h3{margin-bottom:.4rem}
.cx-chip{display:inline-block;border:1px solid var(--rule);padding:.1rem .55rem;font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;margin:0 .4rem .4rem 0;color:var(--fg-muted)}
.cx-chip.warn{border-color:var(--accent);color:var(--accent)}.cx-fig{margin:var(--s-5,1.5rem) 0;position:relative}.cx-fig img{width:100%;height:auto;display:block;border:1px solid var(--rule)}
.cx-fig figcaption{font-size:.85rem;color:var(--fg-muted);margin-top:.4rem}.cx-tag{position:absolute;left:0;top:0;background:var(--bg);color:var(--fg-muted);font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;padding:.25rem .6rem;border:1px solid var(--rule)}
.cx-two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:var(--s-6,2rem);align-items:start}table.cx{border-collapse:collapse;width:100%;font-size:.95rem}table.cx th,table.cx td{text-align:left;padding:.45rem .6rem;border-bottom:1px solid var(--rule);vertical-align:top}
.cx-big{font-family:var(--font-display);font-size:clamp(2rem,5vw,3.2rem);line-height:1;margin:0}.cx-stat{border-top:2px solid var(--accent);padding-top:.6rem}.cx-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:var(--s-5,1.5rem);margin:var(--s-5,1.5rem) 0}
.cx-stat span{color:var(--fg-muted);font-size:.9rem;display:block}.cx-note{color:var(--fg-muted);font-size:.9rem}
"""


def img(name, alt, tag="Concept illustration", width=960, cap=""):
    src = REPO / "visuals/concepts" / name
    im = Image.open(src).convert("RGB")
    w = min(width, im.width)
    h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    stem = Path(name).stem
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    im.save(OUT / "images" / f"{stem}.webp", quality=84)
    im.save(OUT / "images" / f"{stem}.png", optimize=True)
    return (f'<figure class="cx-fig"><span class="cx-tag">{E(tag)}</span><picture><source type="image/webp" srcset="images/{stem}.webp"><img src="images/{stem}.png" width="{w}" height="{h}" alt="{E(alt)}" loading="lazy" decoding="async"></picture>'
            f'<figcaption>{E(cap)}</figcaption></figure>')


def shot(name, alt, cap):
    src = HERE.parent / "visuals/concepts/dashboards" / name
    if not src.exists():
        return ""
    im = Image.open(src).convert("RGB")
    im = im.crop((0, 0, im.width, min(im.height, 1500)))
    w = 1000
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    stem = Path(name).stem
    im.save(OUT / "images" / f"dash-{stem}.webp", quality=80)
    im.save(OUT / "images" / f"dash-{stem}.png", optimize=True)
    return (f'<figure class="cx-fig"><span class="cx-tag">Synthetic dashboard screenshot</span><picture><source type="image/webp" srcset="images/dash-{stem}.webp"><img src="images/dash-{stem}.png" width="{w}" height="{im.height}" alt="{E(alt)}" loading="lazy" decoding="async"></picture>'
            f'<figcaption>{E(cap)}</figcaption></figure>')


def page(fname, title, desc, h1, lede, body):
    nav = "".join(f'<li><a href="{f}"{" aria-current=\"page\"" if f == fname else ""}>{E(t)}</a></li>' for f, t in PAGES)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(title)} · {WORKING_NAME} (working name)</title><meta name="description" content="{E(desc)}">
<meta name="robots" content="noindex, nofollow"><meta name="color-scheme" content="dark light"><link rel="icon" href="data:,"><script>document.documentElement.className="js"</script>
<link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="collections.css"></head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap"><a class="wordmark" href="beverages.html" aria-label="{WORKING_NAME}, working name, collections home">{WORKING_NAME}</a><nav class="nav" aria-label="Collections"><ul>{nav}</ul></nav><button id="theme-toggle" class="btn btn-ghost" type="button" aria-pressed="true">Light / dark</button></div></header>
<main id="main"><section><div class="wrap stack"><p class="eyebrow">{E(title)} · local preview</p><h1>{E(h1)}</h1><p class="lede">{E(lede)}</p><p class="disclosure" role="note">{E(DISCLOSE)}</p></div></section>
{body}</main>
<footer class="site-footer"><div class="wrap stack"><p><strong>{WORKING_NAME}</strong> is a working name for a future concept. Nothing is open or for sale; no payment is accepted anywhere on this site. All business data are synthetic.</p>
<p class="cx-note">Local development preview. Not deployed, not published, noindex. Allergens: dishes are designs for testing, not served food; ask before you eat if you have an allergy. If you drink, drink responsibly; alcohol is for adults of legal drinking age.</p></div></footer>
<script src="app.js" defer></script></body></html>"""


def sec(h, inner, alt=False, id_=None):
    i = id_ or h.lower().replace(" ", "-")[:24]
    return f'<section{" class=\"alt\"" if alt else ""} aria-labelledby="{i}"><div class="wrap"><h2 id="{i}">{E(h)}</h2>{inner}</div></section>'


def chips(*items, warn=()):
    return "".join(f'<span class="cx-chip{" warn" if i in warn else ""}">{E(i)}</span>' for i in items)


def beverages():
    core = ["hefeweizen", "mexican-lager", "vienna-amber", "pilsner", "witbier"]
    cards = "".join(f'<article class="cx-card"><h3>{E(BEERS[i]["name"])}</h3>{chips(BEERS[i]["style"], "Core 5 · designing")}<p>{E(BEERS[i]["line"])}</p><p class="cx-note">Glass: {E(BEERS[i]["glass"])}. Pairs with {E(", ".join(BEERS[i]["pairs"]))}.</p></article>' for i in core)
    body = sec("The five beers we are designing", f'<p>Style targets only: nothing has been brewed or measured. A qualified brewer owns every real decision.</p><div class="cx-grid">{cards}</div>')
    body += sec("Two concepts in development", '<div class="cx-two">' + img("can-concepts-amba-haze-badshah.png", "Two illustrated beer cans: an orange can labelled AMBA HAZE, mango hazy IPA, working name, with nested arches and a leaf, and a straw-coloured can labelled BADSHAH, hefeweizen, with a wheat ear.", cap="Packaging presentation concept: illustration, not a photograph, never brewed.") +
                '<div><article class="cx-card"><h3>BADSHAH · hefeweizen</h3>' + chips("Existing identity", "Hefeweizen", warn=("Name not cleared",)) +
                '<p>The recorded identity for the Bavarian-style wheat beer: hazy gold, banana and clove in balance, creamy body, dry finish. Spec ranges follow the repository benchmark (OG 1.044-1.053, ABV 4.8-5.4% target window) and are hypotheses.</p></article>'
                '<article class="cx-card"><h3>AMBA HAZE · experimental mango hazy IPA</h3>' + chips("Experimental concept", "Working name", warn=("Not in the Core 5",)) +
                '<p>A mango-forward hazy IPA kept separate from the hefeweizen. Open design questions: puree against aroma hops (refermentation risk), oxidation and haze stability, and which mango beer survives (an existing wheat-ale idea overlaps). Outside the Core 5 and the no-IPA-at-opening decision until the founder reopens it.</p></article></div></div>', alt=True, id_="two")
    body += sec("How these specifications were made", '<p>The beer concepts were researched from the repository records and public style guidelines, then reviewed for naming risk. All names here are internal working names. The research notes live in <code>beer/concepts/</code>; names are screened for conflicts there, not cleared.</p>')
    return page("beverages.html", "Beverages", "Concept beverages: five designed beers and two concepts in development. Nothing is brewed or for sale.", "Beer designed first on paper.", "Five beer styles to pair with the food, and two concepts that are still arguments rather than recipes.", body)


def kitchen():
    core = ["chicken-65-totopos", "paneer-tikka-taco", "gobi-taco", "butter-chicken-quesadilla", "goat-birria"]
    cards = "".join(f'<article class="cx-card"><h3>{E(DISHES[i]["name"])}</h3>{chips(DISHES[i]["kind"], DISHES[i]["status"], "Vegetarian" if DISHES[i]["vegetarian"] else "Contains chicken or goat")}<p>{E(DISHES[i]["line"])}</p><p class="cx-note">Heat {DISHES[i]["heat"]} of 5 (design intent). Pairing ideas: {E(", ".join(DISHES[i]["pairing"]))}.</p></article>' for i in core)
    body = sec("The Core 5", '<p>Designed to be cooked at home first. Chicken 65 Totopos is the first test dish. No beef and no pork on any menu; no dietary or religious-compliance claim is made.</p>' + f'<div class="cx-grid">{cards}</div>')
    cand = ('<div class="cx-grid"><article class="cx-card"><h3>Chicken tikka on corn chips</h3>' + chips("R&D candidate", "Working label", warn=("Overlaps Chicken 65 Totopos",)) + '<p>Dry-charred yogurt-marinated chicken on fried corn chips with green salsa and pickled onion. It does the same job as the first test dish, so it waits for those results.</p></article>'
            '<article class="cx-card"><h3>Mughlai-style enchiladas</h3>' + chips("R&D candidate", "Working label", warn=("Name needs advisor review",)) + '<p>Corn tortillas in a silky, mild gravy with whole spices, cashew-free by default. Risks: tortillas soften under sauce, gravy can split on hold, and it may taste like butter chicken in a tortilla.</p></article></div>'
            '<p class="cx-note">Mango Habanero Gobi is already one of the Core 5 (a shareable appetizer); new ideas for it are test variables, not a second dish. Nothing here has been cooked or tasted.</p>')
    body += sec("R&D candidates", cand, alt=True, id_="rnd")
    body += sec("Why designs, not menus", '<p>Every dish carries a status. A dish becomes real only after a person cooks it, scores it against a frozen protocol and records what failed. The research notes are in <code>food/candidates/</code>.</p>')
    return page("kitchen.html", "Kitchen", "Five dishes designed for home testing and two R&D candidates. Nothing has been cooked for guests.", "Dishes that have to earn their place.", "An Indian and Mexican kitchen starts as a test protocol, not a menu.", body)


def merchandise():
    body = sec("Two hoodies", '<div class="cx-two"><div>' + img("hoodie-01-courtyard-back.png", "Back graphic for Hoodie 01: five nested arches in limestone and indigo, a single marigold patch of daylight on the floor, and a plan view of square thresholds, on black.", cap="Hoodie 01 · The Courtyard: back graphic, concept art drawn by code.") +
                '<h3>Hoodie 01 · The Courtyard</h3><p>The room with no roof. Round hacienda-style arches open into multifoil ones; the only colour is the daylight on the floor. Front: one small arch outline, no wordmark.</p></div><div>' +
                img("hoodie-02-two-worlds-back.png", "Back graphic for Hoodie 02: a botanical plate with a curry-leaf spray, mango leaf, marigold bloom, chile plant, maize leaf and roselle calyx drawn at one scale with a ruler beneath.", cap="Hoodie 02 · Two Worlds: back graphic, concept art drawn by code.") +
                '<h3>Hoodie 02 · Two Worlds</h3><p>Two floras on one plate at one scale, with a ruler and no claims. A single marigold bloom, used once and not as an altar or offering.</p></div></div>')
    body += sec("Garment specification (options to test with a mill sample)", '<table class="cx"><tr><th>Choice</th><th>Options and trade-offs</th></tr><tr><td>Weight</td><td>380-450 GSM heavyweight; confirm against a physical sample</td></tr><tr><td>Fabric</td><td>Brushed-back fleece (warmer, pills more) or unbrushed French terry (drapes better)</td></tr><tr><td>Colour</td><td>Garment dye (worn-in depth, shade varies) or piece dye (consistent)</td></tr><tr><td>Decoration</td><td>Water-based screen print for the back plate; small embroidery for the front detail (digitising proof)</td></tr><tr><td>Packaging</td><td>Recycled tissue and a care card; blank neck label until a name is cleared</td></tr></table>', alt=True, id_="spec")
    body += sec("Graphic tees", '<p>Six original ideas are briefed (courtyard from above, receding thresholds, three spice plates, a roselle calyx in section, two botanical plates, a leaf count). None is drawn yet.</p><p class="cx-note">Concept merchandise: no cart, no price, nothing to buy. Artwork is original, drawn from scratch, and needs a cultural review, a similarity sweep and a written rights assignment before any use beyond this preview.</p>')
    return page("merchandise.html", "Merchandise", "Two concept hoodies and a small tee set. Nothing is made or for sale.", "Two hoodies and a few shirts.", "Concept merchandise that tells the brand story without a logo.", body)


def labs():
    c, p = CLAIMS, CLAIMS["planner"]
    stats = "".join(f'<div class="cx-stat"><p class="cx-big">{E(v)}</p><span>{E(k)}</span></div>' for k, v in [
        ("tools registered (callable / trusted MCP)", f'{c["tools"]["registered"]} ({c["tools"]["exposed"]} / {c["tools"]["mcp"]})'), ("deliberate code faults caught by the safety tests", f'{c["mutation"]["killed"]}/{c["mutation"]["valid"]}'),
        ("injected data-defect types detected", f'{c["data_quality"]["detected_precision_recall_1"]}/{c["data_quality"]["injected_defect_types"]}'), ("failure scenarios handled as designed", str(c["failure_injection_scenarios"]))])
    body = sec("An operating lab for a business that does not exist", '<p>The hospitality concept needs software to operate it. The lab builds that software against synthetic data and measures whether it works: a typed tool registry, a trust gateway, human approvals, retrieval, a planner and an evaluation harness.</p>' + f'<div class="cx-stats">{stats}</div><p class="cx-note">Counts come from <code>lab/results/canonical_claims.json</code>, generated from the code and result files. Synthetic scenarios, offline evaluation, no production deployment.</p>')
    body += sec("What failed", f'<p>A rules-based planner passed {E(p["deterministic_pass"])} scenarios. A small local language model, given the same tools and checks, passed {E(p["qwen1.5b_raw_pass"])} ({E(p["qwen1.5b_guardrail_pass"])} with a deterministic safety envelope); a 7B model passed {E(p["qwen7b_raw_pass"])} ({E(p["qwen7b_guardrail_pass"])}). Simplifying how tools were presented lifted required-tool recall from {E(p["qwen1.5b_ts1_required_tools"])} to {E(p["qwen1.5b_ts2_required_tools"])}.</p>'
                f'<p>The dangerous failure was silence: the small model said "nothing to do" when action was needed in {p["wrong_silent_no_action_ts1_raw"]} scenarios with the original tool menu and {p["wrong_silent_no_action_ts2_raw"]} after the change. The design decision that followed: keep AI out of the decision path for these cases.</p><p class="cx-note">Small local models, one prompt, CPU only, author-written scenarios: a result about this harness, not about language models in general.</p>', alt=True)
    body += sec("Where AI belongs here", '<p>Business first, then data, then AI, if it earns its place. The agent can draft, retrieve and explain; rules and people decide. Every tool call passes a permission check enforced in code, and a denied call never executes.</p>')
    return page("labs.html", f"{WORKING_NAME} Labs", "Engineering lab behind the concept: synthetic data, agents, evaluation, failures.", "The lab tests what the business would need.", "Software evidence is software evidence; business ideas stay hypotheses.", body)


def enterprise():
    if not RUN:
        return page("enterprise.html", f"{WORKING_NAME} AI Enterprise", "Synthetic enterprise simulation and data platform.", "A synthetic company to run real software on.", "", sec("Run not recorded", "<p>Run the simulator and the warehouse pipeline, then <code>nasha_lab.warehouse.record_run</code>.</p>"))
    s, f = RUN["source"], RUN["first_full_run"]
    stats = "".join(f'<div class="cx-stat"><p class="cx-big">{E(v)}</p><span>{E(k)}</span></div>' for k, v in [
        ("synthetic orders", f'{s["orders"]:,}'), ("synthetic order lines", f'{s["order_lines"]:,}'), ("fictional locations", str(s["locations"])), ("scenario days (24 months)", str(s["scenario_days"])),
        ("fictional loyalty profiles", f'{s["loyalty_profiles"]:,}'), ("fictional employee records", str(s["employees"])), ("seconds to generate (4 cores)", f'{s["generation_seconds"]:.0f}'), ("seconds, full pipeline run", f'{f["seconds"]:.0f}')])
    gates_ok = sum(g["count"] for g in RUN["gates"] if g["passed"])
    gates_all = sum(g["count"] for g in RUN["gates"])
    body = sec("The synthetic company", f'<p>Fourteen fictional locations growing over 24 months, with orders, loyalty members, staff, inventory, waste, quality events, brewing batches and concept merchandise. Generated deterministically from one seed; every number below is synthetic.</p><div class="cx-stats">{stats}</div>'
               f'<p class="cx-note">Prices, wages and costs are placeholders and volumes are uncalibrated against any industry benchmark. {E(RUN["disclaimer"])}</p>')
    body += sec("The data platform", '<p>Source files are checked against data contracts, loaded in monthly partitions that become visible only when complete, modelled into dimensions and facts with SQL, reconciled against an independent recomputation, and published only if the blocking quality gates pass.</p>'
                f'<p><strong>{gates_ok} of {gates_all}</strong> recorded quality checks passed in the first full run, including exact reconciliation of order counts and totals by month and by location. A rerun with no new data loaded nothing and rebuilt nothing. Details: <code>lab/docs/DATA-PLATFORM.md</code>.</p>', alt=True, id_="platform")
    body += sec("Dashboards", shot("executive.png", "Executive dashboard: key figures and monthly trend lines for net sales, orders, margin and labor, all labelled synthetic.", "Executive view (synthetic data).") + shot("stores.png", "Store operations dashboard: bar chart of net sales per labor hour by site and a table of site metrics, labelled synthetic.", "Store operations view (synthetic data)."), id_="dash")
    body += sec("Honest experiments", '<p>The experimentation layer reports what happened: one clear win, one inconclusive test that needs a far larger sample, one null, one harmful change to roll back, and one invalid test rejected for a broken split. Promotions in the simulation show no lift in basket size, because the simulation models no behavioural response.</p>', alt=True, id_="exp")
    return page("enterprise.html", f"{WORKING_NAME} AI Enterprise", "A synthetic multi-location enterprise, its data platform, dashboards and experiments.", "A synthetic company to run real software on.", "Real code, real tests, invented business: the data are labelled synthetic wherever they appear.", body)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    dist = HERE / "dist"
    for f in ("styles.css", "app.js"):
        shutil.copy(dist / f, OUT / f)
    shutil.copytree(dist / "fonts", OUT / "fonts")
    (OUT / "collections.css").write_text(CSS)
    for fn, fnc in (("beverages.html", beverages), ("kitchen.html", kitchen), ("merchandise.html", merchandise), ("labs.html", labs), ("enterprise.html", enterprise)):
        (OUT / fn).write_text(fnc())
    print("built", sorted(p.name for p in OUT.glob("*.html")))


if __name__ == "__main__":
    main()
