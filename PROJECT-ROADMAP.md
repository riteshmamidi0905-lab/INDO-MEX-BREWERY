# PROJECT ROADMAP

**Project:** INDO MEX BREWERY (working name; parent brand unresolved) · **Founder:** Ritesh Mamidi · **Market:** Austin, Texas · **Branch:** `claude/loving-hypatia-jwilh1` (never merged to main)
**Last updated:** 2026-10-11 (Phase-2 Sprint 3). **Rules:** nothing is deleted; rejected ideas live in `docs/decisions/REJECTED.md`; every factual claim carries an evidence tag and a source ID; beer and food are R&D targets until tested; images are concept visuals; **no website code yet**.
**Operating rule (D-49):** build the concept systematically and refine visuals only when they materially help. Phases overlap. No artificial blockers.

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

## 2. COMPLETED (documentation, research and tooling only; nothing physical)
- Phases 1 and 1.5; Visual Lock (**ARC-01-D canonical day exterior, D-42**); destination-expansion study; historical audit; ARC-02 attempts (on hold, D-47); BRW-01 reference only (D-49).
- Phase-2 Sprint 1: beer program v1, menu matrix v1, guest journey v1, master plan, Austin feasibility skeleton, brand system v0, GLS packages, research S-76..S-118.
- Sprint 2: **D-54 (no beef, no pork; not halal-claimed)** with audit; Menu v1.1 (12-dish test set); T1 sheets (5); beer pilot briefs (3); GLS final package; market-survey and customer-discovery structures.
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

## 4. NEEDS FOUNDER DECISION (details, options and recommendations in `docs/decisions/DECISION-GATES.md`)
| # | Decision | Recommendation (not a decision) |
|---|---|---|
| F-1 | Budget band and funding posture | Price scenario A (core) first; state a funding posture and a comfort ceiling as assumptions |
| F-2 | First paid professionals and order | Attorney + head brewer first (scoped), broker next, architect after their constraints |
| F-3 | Pilot-brewing route / collaboration | Partner-brewery pilot designed by the head brewer; Celis is an idea only (no outreach) |
| F-4 | Cultural advisors | Approve criteria and start outreach by role |
| F-5 | Trademark knockout for top 5 names | Authorise attorney search; expect Latitude 23 and Marigold to need alternatives |
Other gates (G-6..G-12) belong to professionals or have defaults (SP-1 family later; B-2 no IPA, reversible).

## 5. NEEDS PROFESSIONAL
Texas alcohol attorney (licence path, guest beer, minors/arcade, canning, pilot serving, trademark) · licensed head brewer/consultant (vessel size, pilot, water, QC) · architect/cost consultant (Compact ROM, MEP, code) · insurance broker · cultural advisors and food historian · CPSI/acoustician/mechanical engineer (later) · suppliers (lard-free tortillas and beans, rennet, goat, lamb, stocks).

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
