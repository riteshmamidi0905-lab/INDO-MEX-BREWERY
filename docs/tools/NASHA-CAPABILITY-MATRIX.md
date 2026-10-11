# NASHA Capability Matrix (canonical; Sprint 16 update, 2026-10-11)

Correction (Sprint 15): the '618.5 ml' quoted in the Sprint 14 report was the SOLID volume (cm3) of an uncut revolved test shape, not a drinking capacity; use `tools/glass_params.py` for capacity.

Status words are earned: **INSTALLED** = install succeeded; **TESTED** = one representative operation succeeded (synthetic data counts only as TESTED); **OPERATIONAL** = used on real NASHA work. Other states: CONNECTED, AUTH REQUIRED, CONFIG REQUIRED, BLOCKED, PAID, REJECTED, NOT AVAILABLE. Tiers: A core, B specialist, C future.
Tools are leverage, not evidence: nothing here moves evidence readiness (4/95) or design completeness (43/95). Environment: cloud container, root, apt/pip/npm reachable; most other hosts blocked by the proxy (see Blocked).

| Domain | Tool | Purpose | Installed | Auth | Tested | Cost | Licence | NASHA workflow | Risk | Status | Tier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Web QA | Playwright-core, Chromium | responsive/overflow/network/focus QA | pre-existing | none | real site | free | Apache-2.0 | website/qa/run-qa.mjs | low | OPERATIONAL | A |
| Accessibility | axe-core 4.14 | WCAG automated checks (not a screen-reader test) | pre-existing | none | real site | free | MPL-2.0 | run-qa.mjs | automated only | OPERATIONAL | A |
| Performance | Lighthouse 13.5 | perf/a11y/SEO scoring | pre-existing | none | real site | free | Apache-2.0 | run-lighthouse.mjs | low | OPERATIONAL | A |
| Visual QA | pixelmatch + pngjs | visual regression | pre-existing | none | real site | free | ISC/MIT | visual-regression.mjs | low | OPERATIONAL | A |
| HTML | html-validate 11.16 | HTML/ARIA validation | Sprint 14 (website/qa devDep) | none | dist/index.html | free | MIT | npx html-validate dist/*.html | low | OPERATIONAL (found only doctype-case style) | A |
| Links | linkinator 7 | broken-link check | Sprint 14 | none | 54 links, 0 broken | free | MIT | npx linkinator dist/index.html | low | OPERATIONAL | B |
| Vector | SVGO 4.1 | SVG optimise | Sprint 14 | none | version only | free | MIT | menus/diagrams | low | INSTALLED | B |
| Vector | Inkscape 1.2.2 | SVG/PDF vector editing, export | Sprint 14 (apt) | none | version only | free | GPL-2.0+ | packaging/menu/diagrams (no logo, D-66) | low | INSTALLED | B |
| Image | Pillow 12 (AVIF+WebP), OpenCV, ImageHash | resize, metrics, perceptual hash | pre-existing + ImageHash | none | AVIF/WebP save, phash, blur metrics | free | HPND/Apache/BSD | tools/photo_ingest.py, website/images.py | low | TESTED | A |
| Image | libvips (vips CLI) | fast WebP/JPEG pipelines | Sprint 14 (apt) | none | copy op ok; AVIF encoder missing in vips | free | LGPL-2.1+ | bulk resize | low | INSTALLED (use Pillow for AVIF) | B |
| Image | sharp | Node image pipeline | Sprint 14 (devDep) | none | resize+webp ok | free | Apache-2.0 (libvips LGPL, dev only) | optional | low | TESTED | C |
| Image | ImageMagick `convert` | conversions | pre-existing | none | lists AVIF/HEIC/WebP read | free | ImageMagick | HEIC phone photos | low | INSTALLED | B |
| Image | ExifTool | metadata, provenance | Sprint 14 (apt) | none | read ImageSize | free | Perl/GPL | photo_ingest | low | TESTED | A |
| Photo QA | tools/photo_ingest.py | ORIGINAL/EDITED/WEB separation, SHA-256, blur/exposure/clip/res flags, dedupe | built | none | synthetic selftest | free | project | physical T1 photos | thresholds are screening only | TESTED (no real photos yet) | A |
| OCR | rapidocr-onnxruntime; Tesseract 5.3 | text-in-image QA | pre-existing; Sprint 14 | none | visual_qa; version | free | Apache-2.0 | visual_qa.py | low | OPERATIONAL (rapidocr) / INSTALLED (tesseract) | B |
| 3D | Blender 4.0.2 headless | glass/space renders | Sprint 14 (apt) | none | glTF export; Cycles render of glass STL OK | free | GPL | tools/render_stl.py | preview quality only; no OIDN denoise | TESTED | B |
| CAD | OpenSCAD 2021.01 | parametric solids to STL | Sprint 14 (apt) | none | revolved glass, watertight, volume | free | GPL | tools/glass_model.py | not engineered | TESTED | B |
| CAD | cadquery-ocp (OpenCascade bindings) | B-rep geometry base | Sprint 14 (pip) | none | import ok only | free | LGPL | future dimensioned glass | not CadQuery itself | INSTALLED | C |
| CAD | FreeCAD | full CAD | not installed (GUI-bound; no headless) | none | no | free | LGPL | later, on a workstation | wasted disk here | NOT INSTALLED (deferred) | C |
| 3D mesh | trimesh | volume/watertight checks | Sprint 14 (pip) | none | glass volume | free | MIT | glass_model | low | TESTED | B |
| Glass | tools/glass_model.py | profile -> STL, brimful ml, fill line | built | none | selftest + 400 ml pint-profile test | free | project | beer/GLASS-SPECIFICATION-CHECKLIST.md | MANUFACTURABILITY UNVERIFIED; test dims are not a spec | TESTED | B |
| Geospatial | GeoPandas, pyproj, Shapely, GDAL 3.8 | trade-area maths | Sprint 14 | none | used in trade_area.py selftest | free | BSD/MIT | future Austin analysis | no real data fetched; census/OSM hosts blocked | TESTED | C |
| Statistics | NumPy, pandas, SciPy, statsmodels, scikit-learn, matplotlib | analysis | pre-existing + Sprint 14 | none | scipy in experiment_stats | free | BSD | T1/sensory/pricing | tiny n | TESTED | A |
| Experiments | tools/experiment_stats.py | descriptives, bootstrap CI (n>=8), guards | built | none | selftest | free | project | T1 results | refuses inference at n<8 | TESTED | A |
| Experiments | tools/t1_randomize.py, t1_record.py | sealed plate codes; frozen D-74 recorder | Sprint 12 | none | selftests | free | project | Chicken 65 Totopos | frozen | TESTED | A |
| Food | tools/recipe_scale.py (pint) | scaling, yield, units, baker's % | built | none | selftest | free | project | sheet 13 | yields are assumptions unless measured | TESTED | A |
| Food | tools/food_costing.py | cost, allergens, D-54 | Sprint 9 | none | selftest | free | project | blank templates | no prices exist | TESTED | A |
| Menu | tools/menu_engineering.py | stars/plowhorses/puzzles/dogs from REAL sales | built | none | selftest | free | project | needs real sales | no sales exist | TESTED | C |
| Finance | tools/fin_model.py | P&L, break-even, sensitivity; refuses without inputs (exit 2) | built | none | selftest + empty-input refusal | free | project | founder assumptions | no inputs exist | TESTED | C |
| Brewing | tools/brew_calc.py | OG/FG/ABV/IBU etc. | Sprint 9 | none | selftest | free | project | beer/ | calculation aid; brewer owns production | TESTED | B |
| Search | SQLite FTS5 + tools/nasha_search.py | find canonical decisions fast | built (sqlite3 apt) | none | 2,938 passages; D-74 lookup | free | public domain | agents/founder | cache only, git-ignored | OPERATIONAL | A |
| Documents | pandoc, LibreOffice, qpdf, pdftotext, pypdf, reportlab, openpyxl, xlsxwriter | docs, PDF, XLSX | pre-existing + qpdf | none | present | free | various | vendor packs, sheets | PDF accessibility not tested | INSTALLED | B |
| Video | ffmpeg/ffprobe | encode, captions, frames | pre-existing | none | libx264 encode | free | LGPL/GPL | R&D clips | low | TESTED | B |
| Audio/transcription | openai-whisper (pip downloadable) | interview transcripts | not installed | none | no | free | MIT | future interviews | multi-GB model download unverified; no audio exists | NOT INSTALLED (deferred) | C |
| Security | bandit, pip-audit, npm audit, secret grep, licence summaries (tools/security_check.sh) | project hygiene | Sprint 14 | none | run: 0 secrets, 0 vulns, bandit clean after 3 fixes | free | Apache/MIT | before commits | not a pentest | OPERATIONAL | A |
| Licences | pip-licenses, license-checker-rseidelsohn | dependency licence inventory | Sprint 14 | none | summaries printed (node dev deps include LGPL libvips via sharp) | free | MIT | pre-launch | dev-only dep | OPERATIONAL | B |
| Units | Pint | unit conversion | Sprint 14 | none | selftest | free | BSD | recipe_scale | low | TESTED | B |
| GitHub | GitHub MCP (mcp__github__*) | repo, issues, Actions, search, security | connected | OAuth (done) | repo scoped | free | n/a | branch/commits; no PR/merge without founder | scope limit | CONNECTED | A |
| Design | Figma MCP | design files, generate_image, use_figma | connected | OAuth (done) | 10 images generated earlier | PAID credits (cap 12; 10 used, 2 held) | Figma terms (T1 review) | concept imagery | originals not downloadable here; terms unresolved | CONNECTED (spend frozen) | B |
| Design | Adobe MCP | image edit, PDF, fonts, Express | connected | OAuth (done) | not used for NASHA | account plan | Adobe terms | PDF/menus later | no generative creation here | CONNECTED | C |
| ML | Hugging Face MCP | hub search, Spaces | connected | OAuth (done) | whoami ok; hub reads | free tier | per model | image models | Gradio tools disabled (`gradio=none`) | CONFIG REQUIRED | C |
| Mail | Gmail MCP | threads/drafts | connected | OAuth (done) | not used | free | Google | vendor/advisor drafts only on founder request | outbound risk | CONNECTED (not used) | C |
| Docs | Claude Docs connector, xlsx/pptx/pdf/docx skills | documents, decks | connected | n/a | not used this sprint | free | n/a | investor/vendor docs | do not build decks on fabricated traction | CONNECTED | B |
| Research | WebSearch | discovery (T1) | built-in | none | used | free | n/a | everything, tier T1 | summaries not primary sources | OPERATIONAL | A |
| Agents | 21 specialist agents (.claude/agents) | role-routed review | built | none | 10 of the 11 new ones tested (docs/ai/AGENT-TEST-LOG.md) | tokens | project | see log | model output, not professional approval | TESTED (10/11 new) | A |

| Market data | Yelp MCP connector | Austin listing search (rating, review count, categories, price tier, address; no coordinates/hours/review text) | connected (authless) | none | 9 real searches, 49 listings | free | Yelp terms UNVERIFIED | ops/data/austin-yelp-observed.csv, tools/competitor_summary.py | storage/republication terms unknown; sample not census | OPERATIONAL (internal use only) | B |
| Literature | Consensus connector | peer-reviewed paper search (10/query free; no DOI on free tier) | connected | account (done) | crispness query, 5 papers logged | free tier (Pro not purchased) | paper-specific | research/LITERATURE-LEDGER.csv via tools/lit_ledger.py | abstracts only | OPERATIONAL | B |
| Literature | tools/lit_ledger.py | append-only citation ledger; refuses entries without DOI/URL and grade | built | none | selftest + 5 real entries | free | project | Chain A | records, never fetches | OPERATIONAL | A |
| Brewing | BeerJSON schema (vendored) + tools/beerjson_check.py + jsonschema | validate a future brewer-handoff file's structure | Sprint 15 | none | schema loads, valid/invalid docs | free | MIT (beerjson, commit 264da13) | brewer handoff | structure only; NASHA has no recipe | TESTED | C |
| Glass | tools/glass_params.py | profile + collar ring (single/double), capacity, glass mass, centre of mass, fill line, tip angle | built | none | selftest + 5 collar studies (visuals/glass-studies/) | free | project | Chain C | MANUFACTURABILITY UNVERIFIED; density/liquid assumed | TESTED | B |
| 3D | tools/render_ortho.py (Blender) | orthographic comparison montage | built | none | collar-studies-montage.png | free | project | collar studies | low-contrast preview | TESTED | B |
| Geospatial | tools/trade_area.py | straight-line radius counts on supplied points | built | none | synthetic selftest only | free | project | needs coordinates (Yelp gives none; geocoding blocked) | NOT drive time | TESTED (no real data) | C |
| Finance | tools/fin_model.py scenarios | private_tasting, popup, brewery_residency, food_trailer, food_truck, small_permanent, flagship; refuses missing inputs | built | none | selftest + empty refusal | free | project | founder inputs | no inputs exist | TESTED | C |
| Search | tools/nasha_search.py filters | --decisions/--evidence/--food/--beer/--dir | built | none | selftest, real queries | free | project | agents | cache only | OPERATIONAL | A |
| Skills | 4 project skills (.claude/skills: nasha-evidence-audit, nasha-food-rd, nasha-rights-audit, nasha-sprint-close) | repeatable audits | built | none | first three exercised by subagents; sprint-close UNTESTED | free | project | all sprints | model output, not professional review | TESTED (3 of 4) | A |
| Research | /deep-research and /skill-creator (claude.ai skills) | multi-source research; skill authoring | exposed | none | deep-research REFUSED by harness (reserved for explicit user invocation) | free | n/a | founder may invoke | cannot be run by the agent | NOT AVAILABLE TO AGENT | C |

| Pairing | tools/pairing_matrix.py (scipy assignment) | 25 food x beer PAIRING HYPOTHESES from attribute columns; coverage-constrained primaries | built | none | selftest + real matrices | free | project | food/CORE5-PAIRING-MATRIX.csv | crude heuristics; disagrees with expert picks (recorded); NOT SENSORY TESTED | TESTED | B |
| Glass | tools/core5_glasses.py (+ analytic capacity in glass_params.py) | five-glass family, calibrated brimful, mesh vs analytic check (<0.3%), fill line, COM, tip angle | built | none | 5 STL built, watertight, volumes cross-checked | free | project | visuals/glass-studies/core5/ | MANUFACTURABILITY UNVERIFIED; crude barrel profile; tall slim glasses have low static tip angles (12 deg) | TESTED | B |
| Validation | tools/validate_core5.py (called by validate_repo.py) | Core 5 structure and honesty checks | built | none | runs on every validate_repo | free | project | every sprint close | structural only | OPERATIONAL | A |
| Rights | tools/provenance_report.py | AI asset provenance and public-use blockers from the manifest | built | none | real manifest (docs/ai/ASSET-PROVENANCE-REPORT.md) | free | project | rights audits | reports, never clears | OPERATIONAL | A |
| Costing | tools/food_costing.py (NOT COSTABLE guard) | 45 Core 5 ingredient rows, all prices blank | upgraded | none | real structure, no partial costs | free | project | food/costing/ | no prices exist | OPERATIONAL (structure) | B |
| Skills | nasha-core-product-review (5th project skill) | route a Core 5 product through heritage/craft/science/ops/pairing/evidence | built | none | one adversarial test (rejected an unrecorded score) | free | project | Core 5 reviews | model output | TESTED | A |
| Design | Adobe MCP | image/PDF/Express tools | connected (briefly disconnected and reconnected this sprint) | OAuth (done) | not used for NASHA | account plan | Adobe terms | none needed now | no generative creation | CONNECTED (unused) | C |

## Candidates found in the connector/plugin catalog (not installed; need the founder to connect in claude.ai)
| Candidate | Why | Cost/auth | Verdict |
|---|---|---|---|
| Yelp | now connected and tested (see table above) | free | DONE |
| Consensus | now connected and tested (free tier) | free; Pro adds DOI/design/takeaways (not purchased) | DONE; Pro is a founder spend decision |
| PubMed (authless MCP) | food safety, nutrition, alcohol literature | free, authless | Tier B, founder connects in claude.ai (untested) |
| USAFacts government data (authless MCP) | possible Census-derived demographics | free, authless | Tier B, founder connects (untested; coverage unknown) |
| SurveyMonkey / Tally / Rally | future customer research | account | Tier C |
| IBISWorld / Yardi Matrix | industry and CRE data | paid | Tier C, record only |
| Felt Maps / TomTom Maps / GIS Cloud | trade-area maps, POI, routing | account/API key, likely paid tiers | Tier C; local GeoPandas first |
| Haloo Trademark Clearance | automated trademark search | paid account assumed | Tier C: AI search never equals attorney clearance; hold for counsel |
| Midpage / Paxton / CoCounsel / LegalZoom | US legal research / attorney review | paid | Tier C, founder + counsel decision |
| Similarweb | competitor web traffic | paid | REJECT for now (no site live) |
| Anthropic "Finance" plugin (accounting close) | bookkeeping | needs ledger data | REJECT now; revisit after real books exist |
| market-researcher (financial-services plugin) | equity-style comps | not hospitality | REJECT |
| Notion / Fibery / Craft.io (PM) | project management | account | REJECT: GitHub-native workflow suffices (D, spec §44) |
| Zomato / Uber Eats / Resy / Order by Cash App | consumer ordering/booking | consumer | REJECT (not research tools) |
| Blender MCP (community ahujasid; Blender-announced connector reported) | live Blender control | executes LLM code unguarded | REJECT here: headless scripts already work and are safer (T1 source) |
| FreeCAD MCP (community) | CAD control | needs GUI FreeCAD | Tier C, workstation only |

## Blocked in this environment (verified by connection test, 2026-10-11)
USDA FoodData Central, Crossref, OpenAlex, Internet Archive/Wayback, Overpass/OSM, Census, USPTO/TSDR, TABC, BJCP, Blender downloads: all unreachable through the sandbox proxy (no response). Therefore no live API integration is claimed; code would be untested. Only the founder's own computer or a different environment can reach them. USDA FDC (CC0, free data.gov key) and Census are the highest-value ones to wire up when reachable.

## Sprint 19 additions
| Area | Tool | Status | Sprint | Note |
|---|---|---|---|---|
| Decisions | tools/decision_register.py (register + superseded-phrase contradiction check) | TESTED (selftest and repo run; not independently reviewed) | Sprint 19 | Parses DECISIONS.md; scans current docs for superseded wording lacking a marker |
| Company | tools/founder_center.py (generated founder control center) | INSTALLED (no selftest; staleness checked by validate_company) | Sprint 19 | Reads docs/company/data/*.csv and the scoreboard |
| Company | tools/validate_company.py | INSTALLED (no selftest) | Sprint 19 | Parses company data, banners, dollar-amount and empty-template checks |
