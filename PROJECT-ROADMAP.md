# PROJECT ROADMAP

**Project:** INDO MEX BREWERY (repository/working name) · **Brand name: NASHA, founder-selected, legal clearance pending (D-62)** · **Founder:** Ritesh Mamidi · **Market:** Austin, Texas · **Branch:** `claude/loving-hypatia-jwilh1` (never merged to main)
**Last updated:** 2026-10-11 (Sprint 4). **Rules:** nothing is deleted; rejected ideas live in `docs/decisions/REJECTED.md`; every factual claim carries an evidence tag and a source ID; beer and food are R&D targets until tested; images are concept visuals; **no website code yet**.
**Operating rule (D-49):** build the concept systematically and refine visuals only when they materially help. Phases overlap. No artificial blockers.

## 0. Two parallel tracks (D-58)
**Track A, VISION:** develop the strongest future version of the business (concept, brand, experience, space, menu, beer, visuals, website, financial architecture, investor story). May be ambitious; every artifact is labelled Concept / Proposed / Illustrative / Target / Planning assumption / Founder vision / Requires validation. **Track B, EVIDENCE:** build the proof that the vision works (primary-source verification, market research, interviews, food tests, beer pilots, suppliers, legal, architecture, quotes, trademark, cultural review). **Track A must never masquerade as Track B.** Progress of each track is shown in `docs/readiness/VALIDATION-SCOREBOARD.md` (design completeness vs evidence-backed readiness).

## 1. Phases at a glance
| Phase | Name | Status | Primary files |
|---|---|---|---|
| **1** | Foundation | **Substantially complete** | `phase-one/`, `research/`, `docs/decisions/`, `visuals/VISUAL-DNA.md`, `LOCKED-SCENE-DNA.md`, ARC-01-D (canonical day exterior) |
| **2** | Product + Experience Development | **ACTIVE (v1 shipped this sprint)** | `beer/OPENING-BEER-PROGRAM-V1.md`, `food/MENU-DEVELOPMENT-MATRIX-V1.md`, `experience/GUEST-JOURNEY-V1.md`, GLS packages |
| **3** | Business Feasibility | **STARTED (skeleton + decision gates + evidence ledger)** | `business/AUSTIN-FEASIBILITY-V1.md`, `business/LICENSING-AND-FEASIBILITY-NOTES.md` |
| **4** | Brand System | **STARTED (v0 rules)** | `brand/BRAND-SYSTEM-V0.md`, `brand/PARENT-BRAND-CANDIDATES.md`, `NAMING-UNIVERSE-V2.md` |
| **5** | Spatial / Architectural Concept | **STARTED (master plan v2)** | `architecture/MASTER-PLAN-PHASE2.md`, `COURT-BREWHOUSE-V2.md`, `FAMILY-*.md`, ARC-01-D |
| **6** | Investor Package | **Next** (after Phase 3 evidence) | to create: `business/INVESTOR-PACKAGE/` |
| **7** | Website / Public Concept Experience | **Not started, by instruction** | `website/` empty |
Overlap is expected: Phase 3 evidence feeds Phase 5 sizing; Phase 4 waits on trademark knockout; Phase 6 needs Phases 3 and 5.

## 1b. Company journey (stages with dependencies; **no dates**; staged path is a hypothesis, D-60)
The end goal remains the **physical brewery-restaurant**. The mobile/pop-up vehicle is a launch platform, lab, customer-acquisition engine, revenue experiment and investor-proof generator, **not a replacement**.
| # | Stage | Entry needs | Exit criteria | Status now |
|---|---|---|---|---|
| 1 | Concept | Founder vision | Master concept, rules, canonical visuals | **Largely done** |
| 2 | Research | Stage 1 | Market, culture, law, benchmarks documented with tiers | **Done to T1-T3; primary verification pending** |
| 3 | Digital blueprint | Stages 1-2 | Brand, experience, space, menu/beer story, models, investor/website architecture, scoreboard | **Drafted (Sprints 4-5)** |
| 4 | Brand/IP foundation | Stage 3 + IP attorney | Name cleared (search + advisors), IP framework operating, asset register real, contractor agreements | **Framework only; nothing cleared** |
| 5 | Physical R&D | Suppliers, kitchen access, head brewer | T1-T4 food results; Hefeweizen pilot | Not started |
| 6 | Customer discovery | Instrument ready | 30 real interviews; price survey complete | Not started |
| 7 | Pop-ups / tastings | Stages 4-6 inputs; permits; attorney on beer arrangements | First real sessions logged in `validation/` | Not started |
| 8 | Mobile MVP | Pop-up/residency signals | Repeat demand criteria (set in advance) met; vehicle/kitchen decision | Not started |
| 9 | Revenue + traction | Stage 8 | Multi-session sales, margins, repeat customers | Not started |
| 10 | Investor readiness | Stage 9 + counsel | Evidence ≥ 3 in core areas; M3 model; proof package | Not started |
| 11 | Fundraising | Stage 10 | Capital secured (structure per counsel) | Not started |
| 12 | Site selection | Stages 4-11 inputs | Site under control; zoning/flood cleared | Not started |
| 13 | Flagship development | Stage 12 | Permit-ready design; brewer/architect/costs | Not started |
| 14 | Opening | Stage 13 | Open | Not started |
| 15 | Optimisation | Stage 14 | Stable operating metrics | Not started |
| 16 | Expansion | Stage 15 | Proven single site | Not started |
Stages may overlap (e.g. 4-6). Mapping to the capital ladder and investor audience per stage: `investor/CAPITAL-LADDER-AND-INVESTOR-STRATEGY.md` §2, §4.

## 1c. Long-term workstreams (strategic components; **not all executed now**)
| # | Workstream | Where it lives | State |
|---|---|---|---|
| 1 | Concept and research foundation | `concept/`, `research/` | Done (to T1-T3) |
| 2 | Brand and visual identity | `brand/`, `visuals/` | Architecture drafted; identity not designed |
| 3 | Premium website | `website/` | IA designed; not built |
| 4 | IP and ownership strategy | `ip/` | Framework + registers; attorney not engaged |
| 5 | Marketing system | `marketing/` | Foundation plan |
| 6 | Social/content launch | `marketing/` | Plan; nothing live |
| 7 | Low-capital real-world validation | `validation/` | Strategy + schema; nothing run |
| 8 | Food-truck / mobile concept | `validation/MOBILE-MVP-STRATEGY.md` | Strategy; permits/commissary unverified |
| 9 | Pop-ups and events | `validation/` | Not started |
| 10 | Customer traction | `validation/TRACTION-METRICS.md` | Schema only |
| 11 | Investor materials | `investor/` | Structures only |
| 12 | Investor identification and outreach | `investor/investor-universe-schema.csv` | Empty schema; **no outreach** |
| 13 | Capital strategy | `investor/CAPITAL-LADDER-AND-INVESTOR-STRATEGY.md` | Ladder without amounts |
| 14 | Site strategy | `business/AUSTIN-FEASIBILITY-V1.md` | Criteria only |
| 15 | Flagship brewery | `architecture/`, `concept/` | Concept; scale decision open |
| 16 | Long-term expansion | n/a | Not designed (after single-site proof) |

## 2. COMPLETED (documentation, research and tooling only; nothing physical)
- Phases 1 and 1.5; Visual Lock (**ARC-01-D canonical day exterior, D-42**); destination-expansion study; historical audit; ARC-02 attempts (on hold, D-47); BRW-01 reference only (D-49).
- Phase-2 Sprint 1: beer program v1, menu matrix v1, guest journey v1, master plan, Austin feasibility skeleton, brand system v0, GLS packages, research S-76..S-118.
- Sprint 2: **D-54 (no beef, no pork; not halal-claimed)** with audit; Menu v1.1 (12-dish test set); T1 sheets (5); beer pilot briefs (3); GLS final package; market-survey and customer-discovery structures.
- **Sprint 5 (staged path, MVP, IP):** staged-company hypothesis (D-60); mobile/low-capital MVP strategy with six models compared and a proposed 8-item untested MVP menu (`validation/MOBILE-MVP-STRATEGY.md`); traction measurement design with an empty event log and analyser (`validation/`); capital ladder, investor universe by stage, proof package and an empty investor-discovery schema (`investor/`); IP and ownership framework with a founder asset register and website rights register (`ip/`); marketing and build-in-public foundation (`marketing/`); attorney/permitting question lists (`docs/decisions/ATTORNEY-QUESTIONS.md`); NASHA recorded as a founder-proposed candidate (D-59); ledger V-23..V-34; readiness expanded to 19 areas (design 41%, evidence 4%); IP attorney added to the professional roadmap (D-61).
- **Sprint 6 (NASHA visible):** NASHA recorded as founder-selected, clearance pending (D-62); brand strategy and identity system (`brand/NASHA-*.md`); architecture recommendation Model A (D-64); working static website prototype with 6 pages, original SVG art, self-hosted OFL fonts, generated rights register (D-63, `website/`); real-browser QA (axe, overflow at six widths, CLS/LCP) and `tools/validate_site.py`; visual audit and generation queue; NASHA attorney package; domain/handle inventory (unchecked: sandbox blocks lookups); marketing hooks; readiness design 44%, evidence 4% (unchanged).
- **Sprint 7 (NASHA visual world):** visual direction v3 and conflict resolution with the locked Visual DNA (D-65); logo protection directive and empty brand vault (D-66, FA-19..FA-24); concept-visualization and realism standard (D-67); food and beer reference library with beer visual specs from style references (V-35..V-37, T1); existing-image audit (3 KEEP, 1 REWORK, 6 ARCHIVE images); canonical visual manifest (51 rows: 6 rasters integrated provisionally, 12 drawn illustrations, 33 planned and not generated) and prompt pack; website rebuilt as 8 pages with a responsive AVIF/WebP pipeline, Experience and Space pages, Two-Pour, menu and flight card; QA extended (slow network, image failure, stale-result check); readiness design 45%, evidence 4% (unchanged).
- **Sprint 8 (generation blocked; execution hardening):** verified state; confirmed no image-generation capability (no images fabricated); Batch A-E generation plan with run log and QA gate (`visuals/nasha-v3/GENERATION-LOG.md`, `IMAGE-QA.md`); prompt pack hardened (blank signage only, no generator text, partial brewery views for G-6); hero kept temporarily as a one-partial-tank crop; `visual_stage` mechanism (D-68); home page journey and beer explorer; edge-frame trim; accessibility review record and QA aids; readiness design 43/95, evidence 4/95 (unchanged).
- **Sprint 9 (AI environment + first paid generation):** 10 specialist agents (3 exercised, findings applied), visual QA/brewing/costing tools, Lighthouse and visual regression, capability record; founder connected Figma/Hugging Face/Adobe; 6 Figma-generated candidates (A1, A2, A4, A5, Chicken 65 hero and truth) under a capped paid approval, **0 accepted, 0 integrated** (full-res download blocked by sandbox proxy; thumbnails archived); D-69, D-70; readiness unchanged (design 43/95, evidence 4/95).
- **Sprint 4 (Track A blueprint):** master concept; brand architecture; guest experience architecture; spatial vision; visual world and briefs; menu storytelling; beer brand experience; business-model map; financial-model architecture with a blank 70-variable assumptions register; investor story architecture; data-room map; website IA and experience; validation scoreboard and readiness score (**design 41%, evidence 5%**); brewery-scale decision analysis; validator extended; decision D-58. **No evidence was added by these documents.**
- **Sprint 3:** evidence tiers and `research/VERIFICATION-LEDGER.md` (13 entries reached T1: 10 from T3, 1 from T2, 2 new; none T0); decision-gate system (`docs/decisions/DECISION-GATES.md`); 19 LOW-confidence price observations + 10 feature rows (`research/market-survey/`); T1 protocol and test-readiness upgrades, lamb-cut comparison design (`food/t1-test-sheets/`); brewer handoff (`beer/pilot-briefs/00-BREWER-HANDOFF.md`); Compact functional program (`architecture/COMPACT-FUNCTIONAL-PROGRAM.md`); cultural-integrity audit and advisor program (`brand/CULTURAL-INTEGRITY-AND-ADVISORS.md`); trademark screening workflow and preliminary web screen (`brand/TRADEMARK-SCREENING.md`); `tools/validate_repo.py`, expanded `tools/diet_audit.py`; decisions D-56, D-57.

## 3. READY FOR EXECUTION (documentation done; needs a person to act)
| Item | Needs | Files |
|---|---|---|
| T1 cooking: five sheets, then the other seven wave-1 dishes | A cook, ingredients, 5+ tasters, scale/thermometers, supplier statements | `food/t1-test-sheets/`, `food/MENU-V1.1-TEST-MENU.md` |
| Lamb-cut comparison | Butcher/supplier, cook, blind panel | `food/t1-test-sheets/06-lamb-cut-comparison.md` |
| Customer interviews (30) | Interviewer(s), recruiting | `research/customer-discovery/` |
| Competitor price survey completion | Someone to open official menus (or an environment that can) | `research/market-survey/` |
| Brewer engagement | Founder authorisation (F-2) | `beer/pilot-briefs/00-BREWER-HANDOFF.md` |
| GLS-01 then GLS-02 generation | An image tool (founder runs it) | `visuals/generation-batch-01/GLS-GENERATION-PACKAGE.md` |
| Primary-source re-verification | Network access to the blocked hosts, or a person | `research/VERIFICATION-LEDGER.md` |
| Permit/commissary check for pop-ups and a mobile unit | A person to call/visit DSHS, Austin Public Health, Austin Fire, a shared kitchen | `validation/MOBILE-MVP-STRATEGY.md` §2, `ATTORNEY-QUESTIONS.md` §C |
| Contractor/advisor agreements before any creative or advisory work | IP attorney templates | `ip/IP-OWNERSHIP-FRAMEWORK.md` §5 |

## 4. NEEDS FOUNDER DECISION (details, options and recommendations in `docs/decisions/DECISION-GATES.md`)
| # | Decision | Recommendation (not a decision) |
|---|---|---|
| F-1 | Budget band and funding posture | Price scenario A (core) first; state a funding posture and a comfort ceiling as assumptions |
| F-2 | First paid professionals and order | Attorney + head brewer first (scoped), broker next, architect after their constraints |
| F-3 | Pilot-brewing route / collaboration | Partner-brewery pilot designed by the head brewer; Celis is an idea only (no outreach) |
| F-4 | Cultural advisors | Approve criteria and start outreach by role |
| F-5 | Trademark clearance of **NASHA** (founder-selected, D-62); shortlist is fallback | Authorise IP attorney using `ip/NASHA-TRADEMARK-ATTORNEY-PACKAGE.md`; get advisor view on the meaning (intoxication/addiction in Hindi-Urdu) |
| G-13 | Staged path / MVP route | Run interviews and T1 first; verify permits and a brewery/commissary partner; trailer only after repeat evidence |
Other gates (G-6..G-13) belong to professionals or have defaults (SP-1 family later; B-2 no IPA, reversible).

## 5. NEEDS PROFESSIONAL
Texas alcohol attorney (licence path, guest beer, minors/arcade, canning, pilot serving, beer arrangements for a food-only brand) · **IP/trademark attorney** (searches, filing, copyright/contractor assignment, AI provenance, trade secrets, website rights; D-61) · licensed head brewer/consultant (vessel size, pilot, water, QC) · architect/cost consultant (Compact ROM, MEP, code) · insurance broker · cultural advisors and food historian · CPSI/acoustician/mechanical engineer (later) · suppliers (lard-free tortillas and beans, rennet, goat, lamb, stocks).

## 6. NEEDS MONEY (all costs `TBD`; no quotes exist)
Attorney consult(s); head-brewer engagement and pilot batches; architect/cost-consultant ROM; vendor quotes (brewhouse, kitchen); insurance broker (likely free to quote); trademark search; test-kitchen ingredients and cook time; customer-interview incentives; pop-up permits and costs; advisor honoraria; domain/handle purchases (only after a name clears).

## 6b. NEEDS REAL-WORLD TESTING
Food T1/T2 (flavour, yield, hold, lamb cut); beer pilots (Hefeweizen gate first); customer interviews; competitor menu observation; supplier validation (lard, rennet, stocks, goat/lamb availability); water test; heat/shade tests (later); pop-up pilot.

## 6c. BLOCKED
| Item | Why | Unblocks when |
|---|---|---|
| ARC-02 canonical night image | No mask-aware workflow (D-47) | Such a workflow exists or a strong BRW asset |
| Any T0 verification of legal/regulatory facts | Primary hosts blocked in this environment | Founder allows the hosts, or a person opens the pages |
| Final parent name and logo | No trademark search yet | F-5 |
| Pricing, margins, capex numbers | No quotes or observed prices | F-2 deliverables, survey completion |
| Legal conclusions | Attorney not engaged | F-2 |
| Halal positioning | No sourcing/certification review | G-8 |
| Public website | By instruction | Founder instruction |

## 7. Reversible decisions made autonomously (see D-52 and each document)
Menu M-1..M-7 (M-1/M-2/M-3 superseded by D-54) · Journey J-1..J-6 · Brand BR-1..BR-4 · Beer B-1, B-2 · Site SP-1/SP-2 · Scale D-51 · Evidence D-53/D-56.

## 8. Top unresolved risks
1. **Capex scale** vs revenue; the full concept is multi-million-dollar and unquoted (`AUSTIN-FEASIBILITY-V1.md` §10).
2. **Wheat/lager-first in an IPA market** (R2); no Austin price or demand data yet.
3. **Scale mismatch** between canonical tanks and demand (D-51).
4. **Liability, minors, insurance** for play and arcade near alcohol (unresolved law and cost).
5. **Licensing misstep** (guest beer, canning, self-distribution) until an attorney reviews.
6. **Cultural accuracy** without named advisors.
7. **Evidence quality**: Phase-2 facts are search-extract level (D-53).
8. **Night hall visual** remains unsolved (tool-limited).

## 9. Repository map (current)
| Area | Paths |
|---|---|
| Decisions | `docs/decisions/{DECISIONS,CORRECTIONS,REJECTED,OPEN-QUESTIONS}.md` |
| Beer | `beer/{PORTFOLIO-V2,HEFEWEIZEN-BENCHMARK,OPENING-BEER-PROGRAM-V1,GLASSWARE-V2}.md` |
| Food | `food/{OPENING-MENU-V2,SAUCE-SYSTEM,MENU-DEVELOPMENT-MATRIX-V1}.md` |
| Experience | `experience/GUEST-JOURNEY-V1.md`, `architecture/EXPANDED-GUEST-JOURNEY.md` |
| Space | `architecture/{MASTER-PLAN-PHASE2,COURT-BREWHOUSE-V2,FAMILY-DESTINATION-EXPANSION,FAMILY-ZONING-OPTIONS,OPERATIONAL-FLOW}.md`, `interior/` |
| Business | `business/{AUSTIN-FEASIBILITY-V1,LICENSING-AND-FEASIBILITY-NOTES,FAMILY-EXPERIENCE-OPERATIONS}.md` |
| Brand | `brand/{BRAND-SYSTEM-V0,BRAND-WORLDS,NAMING-UNIVERSE-V2,PARENT-BRAND-CANDIDATES}.md` |
| Research | `research/{SOURCES,HISTORICAL-CLAIMS-AUDIT,RESEARCH-BACKLOG,AUSTIN-COMPETITIVE-LANDSCAPE,...}.md` |
| Visuals | `visuals/{VISUAL-DNA,LOCKED-SCENE-DNA}.md`, `visuals/generation-batch-01/`, `visuals/generated/` (ARC-01-D canonical; LOG.md), `visuals/tools/` |
