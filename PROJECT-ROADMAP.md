# PROJECT ROADMAP

**Project:** INDO MEX BREWERY (working name; parent brand unresolved) · **Founder:** Ritesh Mamidi · **Market:** Austin, Texas · **Branch:** `claude/loving-hypatia-jwilh1` (never merged to main)
**Last updated:** 2026-10-10 (Phase-2 Sprint 2). **Rules:** nothing is deleted; rejected ideas live in `docs/decisions/REJECTED.md`; every factual claim carries an evidence tag and a source ID; beer and food are R&D targets until tested; images are concept visuals; **no website code yet**.
**Operating rule (D-49):** build the concept systematically and refine visuals only when they materially help. Phases overlap. No artificial blockers.

## 1. Phases at a glance
| Phase | Name | Status | Primary files |
|---|---|---|---|
| **1** | Foundation | **Substantially complete** | `phase-one/`, `research/`, `docs/decisions/`, `visuals/VISUAL-DNA.md`, `LOCKED-SCENE-DNA.md`, ARC-01-D (canonical day exterior) |
| **2** | Product + Experience Development | **ACTIVE (v1 shipped this sprint)** | `beer/OPENING-BEER-PROGRAM-V1.md`, `food/MENU-DEVELOPMENT-MATRIX-V1.md`, `experience/GUEST-JOURNEY-V1.md`, GLS packages |
| **3** | Business Feasibility | **STARTED (skeleton)** | `business/AUSTIN-FEASIBILITY-V1.md`, `business/LICENSING-AND-FEASIBILITY-NOTES.md` |
| **4** | Brand System | **STARTED (v0 rules)** | `brand/BRAND-SYSTEM-V0.md`, `brand/PARENT-BRAND-CANDIDATES.md`, `NAMING-UNIVERSE-V2.md` |
| **5** | Spatial / Architectural Concept | **STARTED (master plan v2)** | `architecture/MASTER-PLAN-PHASE2.md`, `COURT-BREWHOUSE-V2.md`, `FAMILY-*.md`, ARC-01-D |
| **6** | Investor Package | **Next** (after Phase 3 evidence) | to create: `business/INVESTOR-PACKAGE/` |
| **7** | Website / Public Concept Experience | **Not started, by instruction** | `website/` empty |
Overlap is expected: Phase 3 evidence feeds Phase 5 sizing; Phase 4 waits on trademark knockout; Phase 6 needs Phases 3 and 5.

## 2. COMPLETED
- Phase One founding vision (21 sections), Phase 1.5 research deepening and brand worlds (`brand/BRAND-WORLDS.md`: hybrid "Tank Court").
- Visual Lock: Visual DNA v2.1, Locked Scene DNA v1.3, ARC-01 series A-D; **ARC-01-D approved canonical day exterior (founder waiver 89/100, D-42)**.
- Destination expansion study: Adventure Court, Game Hall, Flagship Outlet, historical interior system, Option C+ zoning, family operations questions.
- Historical claims audit (never invent history, D-30); sources S-01..S-74.
- ARC-02 night attempts (A, B, C): **ARC-02 on hold, tool-limited (D-47)**; ARC-02-A is a night-atmosphere reference only; B and C rejected as provenance.
- BRW-01: package approved and Run 1 V1 reviewed (68/100); retained as development reference only (D-49).
- **Phase-2 Sprint 2 (D-54, D-55):** founder dietary policy recorded (**no beef, no pork; not claimed halal**) with a repo-wide audit (`docs/decisions/DIETARY-AUDIT-D54.md`, `tools/diet_audit.py`); Tandoori Lamb replaces beef; **Menu v1.1** 12-dish test set (`food/MENU-V1.1-TEST-MENU.md`); five T1 test sheets (`food/t1-test-sheets/`); three brewer-facing **pilot briefs** (`beer/pilot-briefs/`); GLS final generation package (`visuals/generation-batch-01/GLS-GENERATION-PACKAGE.md`); Austin competitor price survey structure (`research/market-survey/`); 30-interview discovery instrument, response schema and analyser (`research/customer-discovery/`).
- **Phase-2 sprint v1:** opening beer program v1; opening menu development matrix v1; guest journey v1; master-plan update; Austin feasibility skeleton; brand system v0; GLS-01/02 packages; Phase-2 research (S-76..S-118); historical audit addendum G; corrections #17-20; decisions D-49..D-53.

## 3. ACTIVE (work to continue now)
| Workstream | Next concrete steps |
|---|---|
| **Beer** | Hand the three pilot briefs (Hefeweizen, Mexican-Style Lager, Vienna Amber) to a licensed head brewer `[PRO]`; Hefeweizen first; Austin water lab test; decide yeast shortlist; resolve kellerbier code, Cicerone temperatures, TTB formula status for Deccan Sol/Goa Baja/Malabar Dark |
| **Food** | Cook the five T1 sheets first (Chicken 65 Totopos, Chaat Elote, Paneer Tikka Taco, Dum Goat Birria, Butter Chicken Rajas Quesadilla), then the other seven wave-1 dishes; supplier availability (goat, lamb, paneer, kokum, methi); fry-oil policy; halal is **not** claimed (needs separate review) |
| **Experience** | Cardboard walkthrough design; exit-card and observation protocol; pop-up concept |
| **Space** | Architect brief using the master plan; scale reconciliation with a brewing consultant (D-51); acoustics and heat strategy briefs |
| **Brand** | Trademark knockout on the top 5 parent names; advisor roster; naming test plan |
| **Glassware** | Package final; **not generated** (no image tool here). Founder runs GLS-01 then GLS-02 per `GLS-GENERATION-PACKAGE.md` |
| **Business** | Fill the competitor price survey (`research/market-survey/`); run the 30 interviews (`research/customer-discovery/`); quotes (brewhouse, kitchen, Compact set); attorney engagement; broker and land comps |
| **Research** | Re-open every Phase-2 source in a browser (WebFetch failed in-session); scholarly sources for the historical audit; historians' review |

## 4. NEXT (sequenced; may start before Active items finish)
1. **Phase 3 model v1:** proforma skeleton with the assumptions register (A-1..A-9) replaced by quotes/interviews.
2. **Pilot and pop-up program:** licensed-partner pilot batches; 2-4 pop-ups with 6-10 dishes and 4-6 beers; measure guest metrics (J-6).
3. **Phase 4 brand:** pick parent name after knockout; identity design; packaging concepts.
4. **Phase 5:** engage an architect for a Compact-set concept package and hall/tank-scale resolution.
5. **Phase 6 investor package:** vision, market evidence, model, risk, team, phased plan.
6. **Phase 7 website:** only after the parent name and Phase 6 outline exist.
7. **Visuals on demand:** night hall (ARC-02) when a mask-aware workflow or a strong BRW asset exists; family/history/retail visuals when they help a decision or the investor package.

## 5. BLOCKED / ON HOLD
| Item | Why | Unblocks when |
|---|---|---|
| **ARC-02 canonical night image** | Tool limitation: no workflow preserved locked pixels (D-47) | A mask-aware/reference-aware editor exists, or BRW-01 is strong enough to build the night hall without hallucinating equipment |
| **BRW-01 as canonical interior** | Attempts hold the count but fail lighting/floor/arrangement; not needed for Phase 2 | Optional retry when it materially helps (e.g. investor deck) |
| **Final parent name and logo** | Trademark knockout not done `[PRO]` | Attorney search on the shortlist |
| **Pricing, margins, capex numbers** | No quotes or Austin price data | Phase 3 evidence tasks |
| **Legal conclusions (licence path, minors, to-go, canning)** | Attorney not engaged; primary text not opened | Attorney engagement |
| **Public website** | By instruction | Founder instruction |

## 6. DECISIONS NEEDED FROM THE FOUNDER (only what cannot be made responsibly without him)
| # | Decision | Why it matters |
|---|---|---|
| FD-1 | **Budget band and funding path** (equity, debt, partners) for the first location | Gates the model, phasing and site size; the real cost is unknown and multi-million-dollar |
| FD-2 | **Authorise the first paid professionals**: Texas alcohol attorney, insurance broker, licensed head brewer/consultant, architect (Compact-set rough order of magnitude) | Licensing, liability, vessel sizing and cost cannot be resolved by research alone |
| FD-3 | **Pilot-brewing route**: partner brewery or pilot system, and openness to a collaboration (e.g. a Celis witbier) | Hefeweizen is the gate beer; nothing proceeds without real brewing |
| FD-4 | **Cultural advisors**: names/organisations (Indian-heritage and Mexican-heritage, culinary and history) | Required before names, dish text, history and imagery go public |
| FD-5 | **Parent-name shortlist go-ahead** for trademark knockout (default: top 5 by our scoring) | Phase 4 cannot finish without it |
Closed: ~~diet policy~~ (D-54). Defaults assumed, no decision needed now: family set later with Phase-A provisions (SP-1); no site assumed until a geography is given.

## 6b. What needs physical testing / a professional / money next
| Needs physical testing | Needs a professional | Costs money next |
|---|---|---|
| T1 cooking of the five test sheets then the other seven wave-1 dishes; lamb cut comparison; goat birria yield; lard-free tortilla and bean sourcing | Texas alcohol attorney (licence path, guest beer, minors, canning); insurance broker; licensed head brewer; architect/cost consultant; CPSI (later); cultural advisors | Ingredients and a test-kitchen/cook's time; pilot batches via a partner; legal consult; vendor and architect quotes; customer-interview incentives; pop-up permits and costs |

## 7. Reversible decisions made autonomously (see D-52 and each document)
Menu M-1..M-7 (M-1/M-2/M-3 superseded by D-54) · Journey J-1..J-6 · Brand BR-1..BR-4 · Beer B-1, B-2 · Site SP-1/SP-2 · Scale D-51 · Evidence caveat D-53.

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
