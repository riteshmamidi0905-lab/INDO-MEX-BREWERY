# Validation Scoreboard and Investor-Readiness Score

**Purpose:** make it impossible to confuse polished design with validated evidence. **Status date:** 2026-10-11 (Sprint 6 update: design 42/95 = 44% in Sprint 6, 43/95 = 45% after Sprint 7 (visual direction, experience, space, food and beer references); evidence unchanged 4/95; Sprint 5; three areas added: Marketing, Capital strategy and investors, Mobile MVP and traction; Sprint 4 figures were 41% / 5% of 80). Source data: `docs/readiness/readiness.csv` (checked by `tools/validate_repo.py`). Scores are **our own transparent rubric**, not an external rating; they are deliberately conservative and move only when evidence is added.

## 1. Maturity ladder (each area is placed on it)
**CONCEPT → DESIGNED → RESEARCHED → PRIMARY VERIFIED → PROFESSIONALLY REVIEWED → PHYSICALLY TESTED → CUSTOMER VALIDATED → COSTED → READY.** Not every area needs every rung (– = not applicable). Marks: **●** achieved · **◐** partial · **○** not achieved.
| Area | Concept | Designed | Researched | Primary verified | Prof. reviewed | Physically tested | Customer validated | Costed | Ready |
|---|---|---|---|---|---|---|---|---|---|
| Concept | ● | ● | ◐ | ○ | ○ | – | ○ | – | ○ |
| Brand | ● | ◐ | ◐ | ○ | ○ | – | ○ | ○ | ○ |
| Market | ● | ◐ | ◐ | ○ | ○ | – | ○ | – | ○ |
| Customer | ● | ◐ (instrument) | ○ | – | – | – | ○ (0 interviews) | – | ○ |
| Food | ● | ● | ◐ | – | ○ | ○ (nothing cooked) | ○ | ○ | ○ |
| Beer | ● | ● | ◐ | ○ | ○ | ○ (nothing brewed) | ○ | ○ | ○ |
| Location | ◐ | ◐ | ◐ | ○ | ○ | – | – | ○ | ○ |
| Architecture | ● | ◐ | ◐ | ○ | ○ | – | – | ○ | ○ |
| Legal | ◐ | ◐ | ◐ (T1) | ○ | ○ | – | – | ○ | ○ |
| Financial | ● | ◐ (architecture) | ◐ (benchmarks) | ○ | ○ | – | – | ○ (no quotes) | ○ |
| Operations | ● | ◐ | ◐ | ○ | ○ | ○ | – | ○ | ○ |
| Supply chain | ◐ | ◐ | ○ | ○ | – | ○ | – | ○ | ○ |
| Team | ◐ | ○ | ○ | – | – | – | – | – | ○ |
| Cultural integrity | ● | ● | ◐ | ○ | ○ (no advisors) | – | ○ | – | ○ |
| IP/trademark/ownership | ◐ | ◐ (framework, registers) | ◐ (preliminary web screen) | ○ | ○ | – | – | ○ | ○ |
| Website/presentation | ● | ● | – | – | ○ | ○ | ○ | ○ | ○ (not built) |
| Marketing | ◐ | ◐ (plan) | ○ | – | – | – | ○ | – | ○ |
| Capital strategy and investors | ◐ | ◐ (ladder, stages) | ◐ | – | ○ | – | – | – | ○ |
| Mobile MVP and traction | ◐ | ◐ (strategy, schema) | ◐ (T1 permits) | ○ | ○ | ○ | ○ | ○ | ○ |

## 2. Investor-readiness score (two numbers, never merged)
| Area | Design completeness (0-5) | **Evidence level (0-5)** | Basis for evidence level |
|---|---|---|---|
| Concept | 4 | **1** | background research T1-T3 |
| Brand | 3 | **0** | name founder-selected, clearance pending; strategy and identity proposed; no logo; no advisors |
| Market | 2 | **1** | secondary research; 19 LOW observations |
| Customer | 2 | **0** | zero interviews |
| Food | 3 | **0** | nothing cooked |
| Beer | 3 | **0** | nothing brewed |
| Location | 1 | **0** | no site |
| Architecture | 2 | **0** | no architect |
| Legal | 1 | **1** | T1 summaries; no attorney |
| Financial | 2 | **0** | all assumptions blank |
| Operations | 2 | **0** | no operating plan |
| Supply chain | 1 | **0** | no supplier contact |
| Team | 1 | **0** | founder only |
| Cultural integrity | 3 | **0** | no advisor review |
| IP/trademark/ownership | 3 | **1** | preliminary web screen only; framework and registers, no attorney |
| Website/presentation | 4 | **0** | local prototype built and measured (axe 0 violations, no overflow); not deployed; build quality is not business evidence |
| Marketing | 2 | **0** | hooks and domain checklist only |
| Capital strategy and investors | 2 | **0** | ladder and stages designed; no investors identified or contacted |
| Mobile MVP and traction | 2 | **0** | strategy and empty schema; no event |
| **Total (of 95)** | **43 = 45%** | **4 = 4%** | |
**Reading (Sprint 6):** design rose from 41% to 45% (Sprint 6: 44%) because a brand direction and working website now exist; **evidence did not move (4%)** because a beautiful, accessible site is not evidence that anyone wants the product. The concept is **well designed (45%)** and **almost entirely unvalidated (4%)**. That gap is the honest state of the project: **not investor-ready**.
**Rubric:** Design 0 none · 1 sketch · 2 structured draft · 3 detailed working version · 4 reviewed by someone qualified · 5 complete. Evidence 0 none · 1 secondary/weak (T1-T3, LOW observations) · 2 broad secondary or limited primary · 3 primary (T0), tested, or real data at small scale (**requires primary/external evidence = yes and a real evidence file**) · 4 professionally reviewed or customer-validated with adequate sample · 5 costed/quoted and ready. The validator rejects any evidence score ≥ 3 without those conditions.

## 3. What most blocks investor-readiness (highest impact first)
1. **No customer evidence** (0 interviews, no pop-up). 2. **No physical evidence** (nothing cooked, nothing brewed). 3. **No costs** (no quotes; model blank). 4. **No professional input** (attorney, brewer, architect, broker, advisors). 5. **No primary-source verification** (legal facts are T1). 6. **Brewery scale mismatch unresolved** (`docs/decisions/BREWERY-SCALE-DECISION-ANALYSIS.md`). 7. **No name/trademark clearance.**

## 4. Update rules
Scores change only when a file in `evidence_ref` shows new evidence; each change is logged in the commit message and `DECISIONS.md` if material. Raising a score by rewriting prose is not allowed.

**Sprint 15 and 16 (no change):** design stays 43/95 and evidence 4/95. The Core 5 matrices, pairing hypotheses, glass family, pilot briefs and cost/allergen structures keep Food and Beer at design 3 (detailed working version): rubric level 4 needs review by someone qualified (a chef, brewer, glass vendor or advisor), which AI agent reviews are not. The Yelp sample and 5 + 3 literature abstracts are secondary (evidence level 1 for Market already). No physical, customer or professional input exists.

**Sprint 17 (no change):** design stays 43/95 and evidence 4/95. Sessions 2-5 protocols, brewer handoff, Glass V2, pairing v2 and the capacity exercise are planning artifacts; no cook, brew, tasting or qualified review occurred.

**Sprint 18 (no change):** design stays 43/95 and evidence 4/95. Founder-mode card, control center, review forms, pairing hypotheses, scale and MVP frameworks, finance/costing field readiness and visual QA of lossy image copies are preparation; no cook, brew, tasting, quote or professional review occurred.

**Sprint 19 (no change):** design stays 43/95 and evidence 4/95. The founder control center, stage model, validation ladder, customer-validation templates, market map, regulatory question tree, scenario fields, decision register and professional-review pipeline are Lane B planning artifacts; no cook, brew, tasting, quote, professional review or customer contact occurred. One external finding (a restaurant named Nasha in Austin, T1 search results) raises a name-conflict RISK (D-78); it is not a legal conclusion.
