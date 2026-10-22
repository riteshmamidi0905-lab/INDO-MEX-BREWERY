#!/usr/bin/env python3
"""Local, noindex preview of the Courtyard v3 identity (PROVISIONAL). Writes website/preview-courtyard/index.html. Not wired into the production build; never deployed."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "brand/tools"))
import brand_v3_art as A
import logo_courtyard_v2 as L

P = A.PAL
LK = L.lockups()


def svg(name, cls, label):
    inner, w, h = LK[name]
    return f'<svg class="{cls}" viewBox="-4 -4 {w + 8} {h + 8}" role="img" aria-label="{label}">{inner}</svg>'


crest = f'<svg class="crest" viewBox="0 0 100 100" role="img" aria-label="NASHA arch-and-botanical crest (concept)">{A.crest("currentColor", None, "currentColor", P["terra"])}</svg>'
CSS = f"""
@font-face{{font-family:"Instrument Serif";src:url("../dist/fonts/instrument-serif-latin-400-normal.woff2") format("woff2");font-display:swap}}
@font-face{{font-family:"Instrument Serif";font-style:italic;src:url("../dist/fonts/instrument-serif-latin-400-italic.woff2") format("woff2");font-display:swap}}
@font-face{{font-family:Inter;font-weight:100 900;src:url("../dist/fonts/inter-latin-wght-normal.woff2") format("woff2");font-display:swap}}
:root{{--forest:{P['forest']};--forest-deep:{P['forest_deep']};--gold:{P['gold']};--gold-lt:{P['gold_lt']};--ivory:{P['ivory']};--terra:{P['terra']};--terra-deep:{P['terra_deep']};--charcoal:{P['charcoal']};--saffron:{P['saffron']}}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}
@media (prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}*{{animation:none!important;transition:none!important}}}}
body{{margin:0;background:var(--ivory);color:var(--charcoal);font:17px/1.6 Inter,system-ui,sans-serif}}
a{{color:inherit}}
.skip{{position:absolute;left:-999px}}.skip:focus{{left:12px;top:12px;background:var(--ivory);padding:8px 12px;z-index:9}}
.banner{{background:var(--charcoal);color:var(--gold-lt);font-size:14px;padding:8px 16px;text-align:center}}
header.nav{{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px max(16px,4vw);background:var(--ivory);position:sticky;top:0;z-index:5;border-bottom:1px solid #d8ceb4}}
.nav .wm{{width:110px;color:var(--forest)}}.nav nav{{display:flex;gap:20px;flex-wrap:wrap}}.nav nav a{{text-decoration:none;font-size:15px;padding:6px 2px}}.nav nav a:focus-visible,.nav nav a:hover{{text-decoration:underline;text-underline-offset:5px}}
.hero{{background:var(--forest);color:var(--ivory);padding:clamp(40px,8vw,110px) max(16px,4vw);display:grid;grid-template-columns:1.3fr .7fr;gap:40px;align-items:center}}
.hero .wm{{width:min(100%,720px);color:var(--ivory)}}.hero .crest{{width:min(100%,260px);color:var(--gold);justify-self:center}}
.hero p.tag{{letter-spacing:.3em;text-transform:uppercase;color:var(--gold-lt);font-size:14px;margin:28px 0 8px}}
.hero p.note{{color:#cfd9cf;max-width:60ch;margin:0}}
section{{padding:clamp(40px,6vw,84px) max(16px,4vw)}}
h2{{font:400 clamp(32px,4.5vw,52px)/1.1 "Instrument Serif",Georgia,serif;margin:0 0 12px;color:var(--forest)}}
.lede{{max-width:62ch;margin:0 0 32px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}}
.card{{background:#fff8e8;border:1px solid #dccfae;padding:20px}}
.card img{{width:100%;height:auto;display:block}}
.cans{{display:flex;gap:28px;justify-content:center;flex-wrap:wrap;background:#e7dfcb;padding:28px}}
.cans figure{{margin:0;text-align:center;max-width:240px}}.cans img{{width:100%;height:auto}}
.cap{{font-size:13px;color:#5a5249;margin-top:8px}}
.slot{{background:var(--charcoal);color:var(--ivory);aspect-ratio:4/3;display:grid;place-items:center;text-align:center;padding:20px;font-size:15px}}
.slot.t{{background:var(--terra-deep)}}.slot.s{{background:var(--saffron);color:var(--charcoal)}}
.dark{{background:var(--charcoal);color:var(--ivory)}}.dark h2{{color:var(--gold-lt)}}
.green{{background:var(--forest);color:var(--ivory)}}.green h2{{color:var(--gold-lt)}}
.pal{{display:flex;gap:12px;flex-wrap:wrap}}.pal div{{width:130px;height:90px;display:flex;align-items:flex-end;padding:8px;font-size:12px;border:1px solid #0002}}
footer{{background:var(--forest-deep);color:#cfd9cf;padding:32px max(16px,4vw);font-size:14px}}
@media (max-width:760px){{.hero{{grid-template-columns:1fr}}.nav nav{{gap:12px}}}}
"""
HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>NASHA — Courtyard preview</title>
<meta name="description" content="Local concept preview of the NASHA Courtyard identity. Not published, not final."><style>{CSS}</style></head><body>
<a class="skip" href="#main">Skip to content</a>
<aside class="banner" aria-label="Preview notice">LOCAL CONCEPT PREVIEW · noindex · not published · NASHA is a working name pending legal clearance · nothing is open, on sale, or approved</aside>
<header class="nav">{svg('wordmark-small','wm','NASHA')}<nav aria-label="Primary"><a href="#beverages">Beverages</a><a href="#kitchen">Kitchen</a><a href="#merch">Merchandise</a><a href="#story">Brand story</a><a href="#labs">NASHA Labs</a><a href="#enterprise">AI Enterprise</a><a href="#engineering">Engineering</a></nav></header>
<main id="main">
<div class="hero"><div><h1 style="margin:0">{svg('wordmark','wm','NASHA — The Courtyard (concept)')}</h1><p class="tag">The Courtyard · Brewhouse · Kitchen · Culture</p><p class="note">A concept for a brewhouse and kitchen built around a shared courtyard. Tagline copy is a working placeholder. Everything on this page is conceptual.</p></div>{crest}</div>
<section id="beverages"><h2>Beverages</h2><p class="lede">Two working concepts that share the NASHA family but not a personality. Label artwork is concept art; every specification below is a placeholder until verified.</p>
<div class="cans"><figure><img src="assets/badshah-can.webp" alt="Concept render of a dark-green BADSHAH can with gold gateway arches and a wheat ear" width="320" height="900"><figcaption class="cap"><b>BADSHAH</b> — hefeweizen (working concept). ABV · volume · ingredients: to be confirmed.</figcaption></figure>
<figure><img src="assets/amba-haze-can.webp" alt="Concept render of an ivory AMBA HAZE can with mangoes and leaves" width="320" height="900"><figcaption class="cap"><b>AMBA HAZE</b> — mango-forward juicy IPA (working concept). Specs to be confirmed.</figcaption></figure></div>
<p class="cap" style="text-align:center">Procedural renders (code), not photographs. Photorealistic product plates: pending.</p></section>
<section id="kitchen" class="dark"><h2>Kitchen</h2><p class="lede">A fusion kitchen. Dishes below are concepts that have not been cooked, tasted or costed. No beef or pork. No halal claim.</p>
<div class="grid"><div class="slot">Chicken 65 Totopos — image pending</div><div class="slot t">Mango Habanero Gobi — image pending (concept dish, never prepared)</div><div class="slot s">More dishes — pending</div></div></section>
<section id="merch"><h2>Merchandise</h2><p class="lede">THE COURTYARD hoodie and a small T-shirt set — concepts only, never made or sold.</p>
<div class="grid"><div class="card"><div class="slot" style="background:var(--forest)">Hoodie photography — pending</div><p class="cap">Flat concept art lives in <code>visuals/brand-v3</code>.</p></div><div class="card"><div class="pal"><div style="background:var(--forest);color:var(--ivory)">Deep forest</div><div style="background:var(--gold);color:var(--charcoal)">Antique gold</div><div style="background:var(--terra-deep);color:var(--ivory)">Terracotta deep</div></div></div></div></section>
<section id="story" class="green"><h2>Brand story</h2><p class="lede">Two kitchens, one courtyard. Arches are the thresholds; the ember doorway is the invitation. The story is a working draft and is not approved.</p></section>
<section id="labs"><h2>NASHA Labs</h2><p class="lede">A synthetic Hospitality AI Lab: a deterministic enterprise simulator (14 sites, 24 months), a warehouse with quality gates and a publish gate, and dashboards. All data is synthetic; there are no customers and no revenue.</p></section>
<section id="enterprise" class="dark"><h2>NASHA AI Enterprise</h2><p class="lede">A read-only Ops AI over the warehouse with a default-deny authorization gate, an audit log for every call, and tests against independently recomputed values. It has a built-in gate and can also run behind THE WEIR gateway; it uses no language model.</p></section>
<section id="engineering"><h2>Engineering case studies</h2><div class="grid"><div class="card"><b>Data platform</b><br>Contracts, incremental ingestion, gates, lineage.</div><div class="card"><b>702 vs 708 tests</b><br>Why a module-level skip hid 7 tests in CI.</div><div class="card"><b>Ops AI gate</b><br>Fixed SQL, role and site scoping, audit.</div></div></section>
</main><footer>Concept preview generated by <code>website/preview_courtyard.py</code>. Marks are provisional (D-66: exploration), not trademark-cleared. Reference mood board: user-supplied, AI-generated; not reused.</footer></body></html>"""
out = ROOT / "website/preview-courtyard/index.html"
out.write_text(HTML)
print(out, len(HTML) // 1024, "KB")
