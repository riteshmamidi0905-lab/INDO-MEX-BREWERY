#!/usr/bin/env python3
"""Local, noindex preview of the Courtyard v3 identity (PROVISIONAL). Writes website/preview-courtyard/index.html. Not wired into the production build; never deployed."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))
from nasha_lab.recipes import model as RM, pricing as PR  # noqa: E402  (menu data comes from the same files the database is built from)
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
<header class="nav">{svg('wordmark-small','wm','NASHA')}<nav aria-label="Primary"><a href="#beverages">Beverages</a><a href="menu.html">Menu</a><a href="#kitchen">Kitchen</a><a href="#merch">Merchandise</a><a href="#story">Brand story</a><a href="#labs">NASHA Labs</a><a href="#enterprise">AI Enterprise</a><a href="#engineering">Engineering</a></nav></header>
<main id="main">
<div class="hero"><div><h1 style="margin:0">{svg('wordmark','wm','NASHA — The Courtyard (concept)')}</h1><p class="tag">The Courtyard · Brewhouse · Kitchen · Culture</p><p class="note">A concept for a brewhouse and kitchen built around a shared courtyard. Tagline copy is a working placeholder. Everything on this page is conceptual.</p></div>{crest}</div>
<section id="beverages"><h2>Beverages</h2><p class="lede">Two working concepts that share the NASHA family but not a personality. Label artwork is concept art; every specification below is a placeholder until verified.</p>
<div class="cans"><figure><img src="assets/badshah-can.webp" alt="Concept render of a dark-green BADSHAH can with gold gateway arches and a wheat ear" width="320" height="900"><figcaption class="cap"><b>BADSHAH</b> — hefeweizen (working concept). Target ABV 4.7% · provisional, not brewed or measured. Glass $9 · pitcher $31 (concept prices); provisional serving sizes 16 and 60 US fl oz, not yet validated.</figcaption></figure>
<figure><img src="assets/amba-haze-can.webp" alt="Concept render of an ivory AMBA HAZE can with mangoes and leaves" width="320" height="900"><figcaption class="cap"><b>AMBA HAZE</b> — mango-forward juicy IPA (working concept). Target ABV 6.0% · provisional, not brewed or measured. Glass $9 · pitcher $31 (concept prices); provisional serving sizes 16 and 60 US fl oz, not yet validated.</figcaption></figure></div>
<p class="cap" style="text-align:center">Procedural renders (code), not photographs. Photorealistic product plates: pending.</p></section>
<section id="kitchen" class="dark"><h2>Kitchen</h2><p class="lede">A fusion kitchen. Dishes are concepts that have not been cooked or tasted; costs are planning assumptions. No beef or pork. No halal claim. See the <a href="menu.html">concept menu</a> (approved concept prices).</p>
<div class="grid"><div class="slot">Chicken 65 Totopos — image pending</div><div class="slot t">Mango Habanero Gobi — image pending (concept dish, never prepared)</div><div class="slot s">More dishes — pending</div></div></section>
<section id="merch"><h2>Merchandise</h2><p class="lede">THE COURTYARD hoodie and a small T-shirt set — concepts only, never made or sold.</p>
<div class="grid"><div class="card"><div class="slot" style="background:var(--forest)">Hoodie photography — pending</div><p class="cap">Flat concept art lives in <code>visuals/brand-v3</code>.</p></div><div class="card"><div class="pal"><div style="background:var(--forest);color:var(--ivory)">Deep forest</div><div style="background:var(--gold);color:var(--charcoal)">Antique gold</div><div style="background:var(--terra-deep);color:var(--ivory)">Terracotta deep</div></div></div></div></section>
<section id="story" class="green"><h2>Brand story</h2><p class="lede">Two kitchens, one courtyard. Arches are the thresholds; the ember doorway is the invitation. The story is a working draft and is not approved.</p></section>
<section id="labs"><h2>NASHA Labs</h2><p class="lede">A synthetic Hospitality AI Lab: a deterministic enterprise simulator (14 sites, 24 months), a warehouse with quality gates and a publish gate, and dashboards. All data is synthetic; there are no customers and no revenue.</p></section>
<section id="enterprise" class="dark"><h2>NASHA AI Enterprise</h2><p class="lede">A read-only Ops AI over the warehouse with a default-deny authorization gate, an audit log for every call, and tests against independently recomputed values. It has a built-in gate and can also run behind THE WEIR gateway; it uses no language model.</p></section>
<section id="engineering"><h2>Engineering case studies</h2><p class="lede">Real defects, measured results and stated limits. All data is synthetic and the code was written with AI assistance; each page says what is and is not claimed.</p><div class="grid">[[CARDS]]</div></section>
</main><footer>Concept preview generated by <code>website/preview_courtyard.py</code>. Marks are provisional (D-66: exploration), not trademark-cleared. Reference mood board: user-supplied, AI-generated; not reused.</footer></body></html>"""

CASES = [
 ("data-platform", "Synthetic enterprise data platform", "A deterministic simulator feeding a contract-checked, incrementally loaded warehouse with a publish gate.",
  [("Problem", "Show warehouse engineering without real data. A seeded simulator (numpy PCG64) generates a growing multi-site hospitality business; the full profile is 14 sites over 24 months with about 2.5 million orders."),
   ("Approach", "Source contracts, month-partitioned incremental ingestion with content fingerprints, SQL models with declared lineage, raw and warehouse quality gates, and a <code>warehouse_status</code> publish gate that makes dashboards refuse to render on failure. Crash safety: models only read partitions marked complete."),
   ("Defects found and fixed", "A stale calendar dimension; a duplicate-key crash that fired before the raw quality gate could report it; quadratic joins until indexes were added."),
   ("Evidence", "<code>lab/tests/test_warehouse.py</code>, <code>test_warehouse_bi.py</code>; full-profile run recorded in <code>lab/results/enterprise_full_run.json</code>.")],
  "SQLite engine for the original build; the PostgreSQL port covers models, not ingestion or gates. Calibrated-profile numbers are low-confidence."),
 ("ci-test-count", "Why CI ran 702 tests and my laptop 708", "A reconciliation that found seven tests had never run in CI.",
  [("Symptom", "CI reported 686 passed and 16 skipped (702). A clean local checkout of the same commit collected 708 tests."),
   ("Method", "Reproduce on a fresh worktree of the same commit; compare collected tests per module; read CI's install log."),
   ("Cause", "<code>test_ops_otel_export.py</code> has 7 tests and begins with a module-level <code>importorskip</code> for the OpenTelemetry SDK. CI did not install it, so the module collapsed into <b>one</b> skip: 708 − 7 + 1 = 702."),
   ("Fix", "Install the extras in CI, run pytest with <code>-rs</code> and a JUnit file, and add a skip report that groups skips by reason against a policy with maximum counts (report-only first, strict later)."),
   ("Evidence", "<code>lab/tools/skip_report.py</code>, <code>lab/tests/skip-policy.json</code>, <code>lab/tests/test_skip_report.py</code>.")],
  "Two of CI's 16 skips are unattributed because CI had no per-test skip reasons. The workflow change was made locally and has not yet run on GitHub."),
 ("ops-ai-gate", "A default-deny gate for warehouse questions", "Fixed-SQL tools, role and site authorization, an audit row for every call, and an evaluation harness.",
  [("Design", "The caller names a tool and arguments; it never supplies SQL. Order of checks: warehouse published, tool exists, role grants it, arguments pass allow-lists, site scope (a site manager with no site gets nothing), query, audit. Denials are audited too. The warehouse is opened read-only."),
   ("Evaluation", "33 cases across answers, grounding, authorization, adversarial input and abstention. Expected values are recomputed from the <i>fact</i> tables, not from the marts the tools read. Mutation tests confirm the harness catches a wrong answer and a false allow."),
   ("Result", "33 of 33 pass on the synthetic dev profile, with zero wrong answers and zero false allows; the result hash is stable across runs (latency is excluded)."),
   ("Evidence", "<code>lab/nasha_lab/warehouse/ops_ai.py</code>, <code>ops_ai_eval.py</code>; <code>tests/test_ops_ai_warehouse.py</code> (14), <code>test_ops_ai_eval.py</code>.")],
  "A deterministic tool layer with a rule-based router. No language model is involved, so this measures nothing about model behaviour."),
 ("ops-ai-weir", "Putting the Ops AI behind THE WEIR gateway", "Two authorization layers that do not trust each other, joined by one audit key.",
  [("Layers", "THE WEIR decides first: per-tool policy, results labelled <i>internal</i>, egress denied, writes need approval, tamper-evident audit chain. Only forwarded calls reach the Ops AI gate, which applies its own role and site rules."),
   ("Audit join", "WEIR events carry a 16-hex prefix of the call hash. The upstream recomputes the same hash from the exact tool name and arguments, so each WEIR decision can be matched to the Ops AI audit row it caused, or shown to have been blocked first."),
   ("Behaviours tested", "Allowed read equals the direct answer; unknown tools never reach the Ops layer; after a warehouse read an egress tool is refused; a site manager's out-of-scope request is allowed by WEIR but denied by the Ops layer; write tools need approval and nothing executes while pending."),
   ("Evidence", "<code>lab/nasha_lab/warehouse/ops_ai_weir.py</code>, <code>tests/test_ops_ai_weir.py</code> (4 tests against the real gateway).")],
  "One gateway per principal; the WEIR package is a separate repository and must be installed; in-process only; no language model."),
 ("postgres-port", "Porting the warehouse models to PostgreSQL", "Dialect translation reconciled table by table against the original.",
  [("Approach", "Transpile the SQLite model SQL with sqlglot, hand-write the calendar, copy staged rows, then compare row counts and numeric column sums for all 22 dimension, fact and mart tables."),
   ("Bugs the reconciliation caught", "PostgreSQL has no <code>sum(boolean)</code>; two marts relied on SQLite's lax <code>GROUP BY</code>; <code>round()</code> differs: SQLite rounds half away from zero, PostgreSQL rounds doubles half to even (11 cents of waste cost differed)."),
   ("Scale check", "At about 400,000 orders and 924,000 order lines all 22 tables reconciled with no mismatch, and a rebuild was idempotent. The pgvector retrieval test also passes against the same embedded server."),
   ("Evidence", "<code>lab/nasha_lab/warehouse/pg_variant.py</code>, <code>tests/test_warehouse_pg.py</code>.")],
  "Ingestion, contracts and quality gates are not re-implemented in PostgreSQL. Results are from an embedded PostgreSQL 18.4 on one machine."),
 ("forecasting", "Demand forecasting and labor analytics with an honest backtest", "Three methods, a rolling-origin evaluation and a clear statement of what a good score means.",
  [("Methods", "Seasonal-naive, a four-week seasonal mean, and weekly additive Holt-Winters with parameters chosen on the training window only."),
   ("Evaluation", "Rolling-origin backtest (no look-ahead), scored by WAPE; the best method is chosen on the backtest and then used to forecast the next 28 days. A labor scenario converts forecast orders into hours at historical productivity."),
   ("Reading the result", "The simulator has weekly seasonality and growth by construction, so strong scores show the methods recover known structure. They say nothing about real demand."),
   ("Evidence", "<code>lab/nasha_lab/warehouse/forecast.py</code>, <code>tests/test_forecast_labor.py</code>, dashboards <code>labor.html</code> and <code>forecast.html</code>.")],
  "No external regressors (weather, events, promotions). Wages and costs are placeholders."),
 ("tenancy", "A second synthetic customer behind a tenant gateway", "Per-tenant warehouses and audits with default-deny grants.",
  [("Design", "One warehouse database and one audit database per tenant, opened read-only; explicit user-to-tenant grants; any argument that tries to name a tenant, path or data source is refused and logged."),
   ("Tests", "Two generated customers (different seed, size and site mix) return different, independently verified answers; cross-tenant access, unknown tenants and override attempts are denied; the same <code>location_id</code> resolves per tenant; audits never mix."),
   ("Evidence", "<code>lab/nasha_lab/warehouse/tenancy.py</code>, <code>tests/test_tenancy.py</code>, <code>lab/docs/SECOND-CUSTOMER-DEPLOYMENT.md</code>.")],
  "Isolation is at design level only: same process and code, trusted in-process identities, no encryption or quotas. Not a security certification."),
 ("recipe-to-analytics", "From recipe to ledger: one versioned chain", "Menu item, recipe, ingredient, supplier quote, inventory, order and cost in one warehouse, with human approval for anything that would spend money.",
  [("Problem", "A synthetic hospitality company needs its menu, recipes, inventory and cost analytics to agree. Concept prices (beer $9 glass and $31 pitcher, appetizers $13.50, mains $18.50) had to be applied without overwriting the earlier placeholder-price simulation."),
   ("Approach", "Versioned pricing configs (the earlier placeholder prices are a frozen record), recipe files with sub-recipes and a bill of materials, and <code>scn_*</code> tables built beside the historical tables. Depletion, restated revenue, menu profitability, variance, menu engineering and cost levers are SQL or documented Python; the SQL also runs on PostgreSQL and reconciles."),
   ("Governance", "An agent can only propose a reorder. THE WEIR holds the write until a person approves it, and even an approved proposal only produces a draft purchase order that is never sent. Every transition is in a hash-chained audit log."),
   ("A defect worth noting", "A PostgreSQL reconciliation showed a 0.0001 difference in a brewing yield ratio. The cause was a decimal rounding tie (0.95675) that SQLite and PostgreSQL rounded differently because of binary floating point. The model now rounds in exact integer tenths; a regression test checks tie cases in both engines. The tolerance was not changed."),
   ("Results", "37 new tests (21 recipe, pricing and approval; 16 warehouse scenario) plus 55 Ops AI evaluation cases against the scenario-enabled warehouse, all passing; table hashes of a rebuilt scenario are identical and the historical tables are unchanged."),
   ("Evidence", "<code>lab/nasha_lab/warehouse/scenario.py</code>, <code>procurement.py</code>, <code>lab/nasha_lab/recipes/</code>, <code>lab/tests/test_scenario_d87.py</code>, <code>test_recipes_d87.py</code>, <code>lab/docs/RECIPE-TO-ANALYTICS-INTEGRATION.md</code>.")],
  "Concept prices and planning-assumption costs; supplier quotes, inventory counts and the three injected anomalies are synthetic; no price elasticity; nothing was cooked, brewed or purchased; beer costs are estimates at provisional serving sizes."),
 ("reproducibility", "Reproducible builds, evaluation and CI signals", "Build twice, hash every table, and make skipped tests visible.",
  [("Rebuild check", "Generate and build the warehouse twice from scratch in separate directories, hash all 22 dimension, fact and mart tables plus the evaluation result, and fail on any difference. The environment (Python and key package versions) is recorded so a difference can be attributed."),
   ("Local commands", "A Makefile with <code>make test</code>, <code>eval</code>, <code>repro</code>, <code>pg</code>, <code>dashboards</code> and <code>lock</code>; a record of installed direct-dependency versions."),
   ("CI", "Extras installed so gated tests run; pinned THE WEIR install; a JUnit file and a skip report in the job summary; evaluation and rebuild steps added to the workflow."),
   ("Evidence", "<code>lab/nasha_lab/warehouse/repro.py</code>, <code>lab/Makefile</code>, <code>.github/workflows/lab-ci.yml</code> (edited locally; not yet run on GitHub).")],
  "The lock file records versions seen locally and is not a full dependency resolution. Nothing here has been deployed."),
]


def case_page(slug, title, tagline, sections, limits):
    body = "".join(f"<h2>{h}</h2><p>{t}</p>" for h, t in sections)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{title} — NASHA engineering</title><style>{CSS}
article{{max-width:780px;margin:0 auto;padding:clamp(24px,5vw,56px) 16px}} article h1{{font:400 clamp(30px,5vw,48px)/1.1 "Instrument Serif",Georgia,serif;color:var(--forest);margin:0 0 8px}} article h2{{font-size:clamp(22px,3vw,30px);margin:28px 0 6px}} article p{{margin:0 0 8px}} code{{background:#efe7d3;padding:1px 5px;border-radius:3px;font-size:.92em}} .limits{{border-left:4px solid var(--terra-deep);padding:8px 14px;background:#fff8e8;margin-top:24px}}</style></head><body>
<a class="skip" href="#main">Skip to content</a><aside class="banner" aria-label="Preview notice">LOCAL CONCEPT PREVIEW · noindex · not published · all data synthetic · built with AI assistance</aside>
<header class="nav"><a href="../index.html" aria-label="NASHA home">{svg('wordmark-small','wm','NASHA')}</a><nav aria-label="Primary"><a href="../index.html#engineering">All case studies</a></nav></header>
<main id="main"><article><p class="cap">Engineering case study</p><h1>{title}</h1><p class="lede">{tagline}</p>{body}<div class="limits"><b>Limits and what is not claimed.</b> {limits}</div></article></main>
<footer>NASHA is a concept and a synthetic lab: no customers, no revenue, no production deployment. Code written with AI assistance; the author's own understanding is tested separately.</footer></body></html>"""


def usd(c):
    return f"${c / 100:,.2f}"


def menu_page():
    cfg = PR.load_config()
    recipes = RM.load_recipes()
    dishes = [r for r in recipes.values() if r["kind"] == "dish"]
    beers = cfg["beers"]
    px = {k: int(round(v * 100)) for k, v in cfg["prices_usd"].items()}
    sv = {"oz": cfg["serving_volumes"]["oz_to_ml"], **{k: {**cfg["serving_volumes"][k], "value_ml": cfg["serving_volumes"][k]["fl_oz"] * cfg["serving_volumes"]["oz_to_ml"]} for k in ("glass", "pitcher")}}

    def beer(b):
        return (f'<div class="card" data-beer="{b["id"]}"><h3>{b["name"]}</h3><p>{b["style"]}</p><p><b>Target ABV {b["target_abv_pct"]}%</b> · provisional, not brewed or measured</p>'
                f'<p>Glass <b data-price-cents="{px["beer_glass"]}">{usd(px["beer_glass"])}</b> · Pitcher <b data-price-cents="{px["beer_pitcher"]}">{usd(px["beer_pitcher"])}</b></p>'
                f'<p class="cap">Concept serving sizes: glass {sv["glass"]["fl_oz"]} US fl oz (about {sv["glass"]["value_ml"]:.0f} mL), pitcher {sv["pitcher"]["fl_oz"]} US fl oz (about {sv["pitcher"]["value_ml"]:,.0f} mL).</p></div>')

    def dish(r, status_label):
        c = r["menu_category"]
        return (f'<div class="card dish" data-recipe="{r["id"]}" data-category="{c}"><div class="slot img">Conceptual food image — not yet generated</div><h3>{r["name"]}</h3>'
                f'<p>{r["portion"]["description"]}. {r["portion"]["construction"]}.</p><p class="cap">Allergens (preliminary derivation, not a label): {", ".join(r["allergens_declared"]) or "none declared"} · {status_label}</p>'
                f'<p class="price"><b data-price-cents="{px[c]}">{usd(px[c])}</b></p></div>')

    def block(cat, title):
        approved = [r for r in dishes if r["menu_category"] == cat and r["menu_status"].startswith("approved")]
        cand = [r for r in dishes if r["menu_category"] == cat and r["menu_status"] == "candidate"]
        return (f'<section><h2>{title} · {usd(px[cat])}</h2><h3>Core and approved test-menu dishes</h3><div class="grid">' + "".join(dish(r, "approved concept") for r in approved) +
                '</div><h3>Candidates under review (not additions)</h3><div class="grid">' + "".join(dish(r, "candidate: needs founder decision") for r in cand) + "</div></section>")

    extra = """.dish .slot.img{aspect-ratio:16/9;background:var(--forest);font-size:13px}.price{font:400 28px "Instrument Serif",Georgia,serif;color:var(--forest);margin:0}h3{margin:6px 0}"""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>NASHA — Concept menu preview</title>
<meta name="description" content="Local concept menu preview at approved concept prices. Not published; nothing is open or on sale."><style>{CSS}{extra}</style></head><body>
<a class="skip" href="#main">Skip to content</a><aside class="banner" aria-label="Preview notice">CONCEPT MENU · approved concept prices · dishes not cooked or tasted · nothing is open, on sale or approved for sale · noindex</aside>
<header class="nav"><a href="index.html" aria-label="NASHA home">{svg('wordmark-small','wm','NASHA')}</a><nav aria-label="Primary"><a href="index.html">Home</a><a href="#beer">Beer</a><a href="#appetizer">Appetizers</a><a href="#main-dishes">Mains</a></nav></header>
<main id="main"><section><h2>Concept menu</h2><p class="lede">These are approved CONCEPT prices for planning and simulation (house beer glass {usd(px["beer_glass"])}, pitcher {usd(px["beer_pitcher"])}, appetizers {usd(px["appetizer"])}, mains {usd(px["main"])}). No restaurant is operating; no dish has been cooked or tasted; food images are not yet generated; the menu is not final.</p></section>
<section id="beer"><h2>House beer</h2><div class="grid">{"".join(beer(b) for b in beers)}</div><p class="cap">Serving sizes are provisional concept sizes: actual glassware capacity, headspace and fill lines need physical validation. Packaging and regulatory statements are not finalized. Target ABV values are targets, not measurements.</p></section>
<div id="appetizer">{block("appetizer", "Appetizers")}</div><div id="main-dishes">{block("main", "Mains")}</div>
<section class="green"><h2>How this page is made</h2><p class="lede">Prices, beer targets and dishes are read from <code>food/pricing/price-v2-2026-10-22.json</code>, <code>beer/specs/beer_specs.json</code> and <code>food/recipes/v1</code> by <code>website/preview_courtyard.py</code>: the same files the scenario database is built from. Tests compare this page with the database.</p></section></main>
<footer>Concept preview. Marks are provisional (D-66). Prices are concept prices and are not a statement that anything is for sale.</footer></body></html>"""


CARDS = "".join(f'<a class="card" href="case-studies/{c[0]}.html" style="text-decoration:none"><b>{c[1]}</b><br>{c[2]}</a>' for c in CASES)
HTML = HTML.replace("[[CARDS]]", CARDS)
cs = ROOT / "website/preview-courtyard/case-studies"
cs.mkdir(exist_ok=True)
for c in CASES:
    (cs / f"{c[0]}.html").write_text(case_page(*c))
(ROOT / "website/preview-courtyard/menu.html").write_text(menu_page())
out = ROOT / "website/preview-courtyard/index.html"
out.write_text(HTML)
print(out, len(HTML) // 1024, "KB")
