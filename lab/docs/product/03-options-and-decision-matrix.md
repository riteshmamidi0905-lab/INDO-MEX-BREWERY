# 03. The non-AI baseline, the AI alternatives, and the decision per sub-task

**SYNTHETIC / ASSUMPTION-DRIVEN.** Ratings are my judgement from the cited evidence, written down so they can be disputed. "?" means no evidence exists in this repository; it is never filled with a guess. Same-author caveat applies to every lab number.

## 1. The non-AI baseline, designed to be hard to beat

A straw-man baseline ("a human squints at a spreadsheet") would make any AI look good. Three non-AI tiers are specified so the comparison is fair.

### N0. Spreadsheet and checklist (the fallback, also the manual mode of FR-15)

One sheet per site, one row per ingredient. Columns: ingredient, unit, last count date, last count quantity, receipts since, usage since (from the sales export times a recipe table, placeholder recipes), **on-hand estimate**, 14-day average daily usage, **days of cover** (on-hand / usage), supplier, lead time, minimum order, spec-sheet status, open-order quantity arriving within lead time, open-order dates.

Formulas (the same logic the lab encodes):
- Needed through lead time = usage x lead time - usable on-hand. Usable on-hand is **zero** if the count is missing, older than the staleness limit (A-19), negative, or a newer count is quarantined.
- Open orders cover the shortage only if the sum of quantities arriving **within** lead time is at least "needed through lead time". (This is the rule v2 the lab fixed after rule-gap probes went 0 of 8 to 8 of 8. The lab's own first version of this rule was wrong.)
- Flag if cover < lead time and not covered; flag if the latest count is below 0.4 or above 2.0 times the expected quantity; flag if the count is stale or missing; flag if no supplier of the item is ACTIVE.
- Suggested order quantity = max(usage x (lead time + 3 days) - on-hand - arriving, supplier minimum).

Daily checklist (10 minutes per site): refresh counts; read the red cells; for each red cell choose one of the five outcomes (recount, draft purchase, escalate supplier unavailable, escalate insufficient evidence, nothing) and write the one-line reason; for any substitution or new ingredient run the D-54 checklist (below); the founder approves any purchase.

D-54 checklist: reject on sight any of beef, pork, bacon, lard, carnitas, carne asada, gelatin, brisket, chorizo, barbacoa, sausage, ham, tallow, veal and their derivatives; treat stock, broth, bouillon, shortening, rennet, natural flavour, Worcestershire, flavour base, base and fining as **hidden-derivative** words that require a written supplier statement naming the source; "pork-free" or "no beef" in supplier text is a claim, not verification; never write that the concept is halal.

Supplier selection table: supplier, status, items, lead time, minimum, last reply time. Rule: only ACTIVE; shortest lead time that meets cover; ties go to the one with the earliest verified reply; the founder decides if two qualify.

Message template (T5): fixed sentence with five slots: supplier name, item, quantity and unit, requested delivery date, contact. Nothing else is free text.

**Strengths, stated fairly.** Zero infrastructure and zero dependencies. Fully transparent. Cannot hallucinate. At a handful of ingredients and one site it is probably the right answer today.

**Weaknesses, stated fairly.** Manual entry errors; a staleness rule that depends on someone looking; no tamper-evident trace of why a decision was made; the checklist lives in a person's head after a month; time grows with sites times ingredients (A-01: if the operation is that small, N0 wins outright and nothing else in this case is needed); formulas can be silently overwritten.

### N1. Rules engine (what the lab's deterministic planner is)

N0's logic as versioned, tested code with typed tools, permission classes, evidence-cited proposals, a trace and signed approval. Evidence: 259 of 259 synthetic scenarios (`results/planner_deterministic.json`), 98 of 98 headline and 24 of 24 metamorphic relations in the structurally different ext1 set (`results/ext1_planner_deterministic_poq2.json`), rule-gap probes 8 of 8 after the v2 rule. Same-author, and two of the four splits were seen while the planner was being fixed (`docs/PLANNER-EXPERIMENT.md`).

**Weaknesses of N1, found by me.** (a) The D-54 screen is a 14-token lexicon plus a hidden-derivative list; ten of ten beef or pork derivatives I chose outside it (suet, pepperoni, pancetta, gelatine, oxtail, ribeye, bone marrow, hamburger patty, salami, prosciutto) return NO_POLICY_SIGNAL (`05` section 7). The planner then abstains and says "do not infer that it is allowed or prohibited", so nothing is cleared automatically, but the claim line reads "no D-54 term and no hidden-derivative term" (FR-13). (b) Supplier selection is a single query with no comparison (A-21). (c) A new exception shape needs new code (`docs/PLANNER-EXPERIMENT.md`, tradeoffs). (d) It rewards a human who stops reading: 53 of 259 deterministic outcomes are `ABSTAIN_REQUIRE_REVIEW` (R-5 and A-18).

### N2. N1 plus templated drafts

N1 plus the N0 message template with slot-filling from verified evidence and a validator that rejects any draft whose number, date, item or supplier differs from the evidence (FR-14, not built). This is the recommended target.

## 2. The AI alternatives

| Option | What it is | Evidence in this repository | Main failure mode |
|---|---|---|---|
| **AI-1. LLM planner** | A local model chooses tools and the action; deterministic code only validates, authorises and traces | Qwen2.5-1.5B: 5 of 140 scenarios pass all checks, 52 of 140 correct action, 22 of 140 call the required tools, p50 28.0 s. Qwen2.5-7B: 10 of 35, 20 of 35 correct action, 15 of 35 required tools, p50 151.5 s. Paired: the model passes where the rules fail in 0 scenarios (`docs/PLANNER-EXPERIMENT.md`, `results/planner_qwen*.json`) | Skips evidence gathering; **30 of 140 silent "no action"**, all 30 in inventory events (30 of 59 actionable inventory scenarios, Wilson 95% 38% to 63%) |
| **AI-2. LLM planner plus deterministic evidence envelope** | AI-1 with the envelope forbidding any action less conservative than the evidence allows | 1.5B + envelope: 8 of 140 pass, silent all-clear 0 of 140, but correct action on only 18 of 59 actionable inventory scenarios and **every healthy scenario escalated (4 of 4)**. 7B + envelope: 11 of 35 (`results/planner_qwen1.5b_run2_guardrail.json`, `planner_qwen7b_guardrail.json`) | Safe by construction, and not useful: the envelope converts a bad planner into an over-escalator. The envelope **is** the rules engine; it adds nothing the rules do not already say |
| **AI-3. LLM drafting only** | Rules decide; a model writes the supplier message and explanation | **None.** The lab never drafted prose. The only text-quality evidence I know of is a different repository (FC-18, 8 of 19 drafts rejected after one repair for one small model), which I did not open or re-run and do not use | Wrong number, date or item in a message a human skims; tone; attacker text copied into a draft (the raw 1.5B model leaked attacker text in 2 of 24 adversarial scenarios) |
| **AI-4. Hybrid: deterministic envelope plus LLM wording behind validators** | Rules decide; model proposes wording; a deterministic validator checks every figure and name against the evidence; human approves | None for text. The pieces exist: claim grounding drops unsupported claims (0 of 29 unsupported for the raw 1.5B model after validation; 0 of 723 for rules) | Validator coverage: it catches numbers it knows to check; tone and omission are not checked |
| **AI-5. Add-only second opinion** | Rules decide; a model reads the same evidence and may only **add** an escalation, never remove one | **None directly.** The cost model (`05` section 6) shows this is the only AI variant with a plausible payoff, and only if two unmeasured quantities (what it catches, what extra false alarms it adds) are favourable | Alarm fatigue; unmeasured |

## 3. Decision matrix per sub-task

Scale: **++** strong, **+** adequate, **0** mixed, **-** weak, **--** unacceptable, **?** no evidence. "AI" means a language model doing the task; "Hybrid" means the non-AI result stands and AI is an add-only or wording layer.

### T1. Detection of the exception

| Criterion | Non-AI (rules) | AI (LLM decides) | Hybrid (rules + add-only second opinion) |
|---|---|---|---|
| Correctness | ++ on synthetic (0 silent of 119; same author); true rate unknown (A-10) | -- (silent all-clear 30 of 59 for 1.5B; 0 of 16 for 7B but interval to 19%) | + to ++ if b is positive; unmeasured |
| Auditability | ++ (rule version, inputs, trace) | - (tool choice varies; 35 of 37 missing required tools were never requested in the trace sample) | + (rules decide; model note is advisory) |
| Latency | ++ (65.5 ms) | -- (28.0 s / 151.5 s) | - (adds model time to the batch) |
| Cost | ++ (none) | 0 (no API cost; compute hours: 1,000 events at the 1.5B median is about 7.8 hours sequentially, at 7B about 42 hours) | 0 |
| Failure severity | Moderate, bounded by escalate-on-gap | **High**: the silent failure | Low: cannot remove an escalation |
| Data requirements | None | None, but needs adjudicated exceptions to know it works | Needs adjudicated rule-gap cases to know it helps |
| Maintainability | + (new shape = new rule, with tests) | - (prompt and model drift, no regression story beyond re-evaluation) | 0 |
| **Decision** | **DO NOT USE AI as the detector.** Optional AI-5 in shadow only (gate G-S) | | |

### T2. Coverage arithmetic

| Criterion | Non-AI | AI | Hybrid |
|---|---|---|---|
| Correctness | ++ once the rule is right; **the rule was wrong once (v1) and a probe set found it** | ? (not measured: the lab's models never do the arithmetic; tools do) | n/a |
| Auditability | ++ (formula and inputs) | -- (an unexplained number) | n/a |
| Latency / cost | ++ / ++ | - / 0 | n/a |
| Failure severity | High if the rule is wrong, but then it is wrong the same way every time and a test pins it | High and non-repeatable | n/a |
| Data requirements | None | None | n/a |
| Maintainability | ++ (v1 frozen, v2 added, 10 tests) | - | n/a |
| **Decision** | **DO NOT USE AI.** The requirement is exactness and reproducibility. I have no measurement of LLM arithmetic here, so this is a requirements-based decision, not a measured one. The lesson from PP-2 is that the effort belongs in testing the rule | | |

### T3. D-54 dietary check

| Criterion | Non-AI (lexicon plus checklist, human decides) | AI (LLM verdict) | Hybrid (lexicon verdict plus add-only flagger for unknown names) |
|---|---|---|---|
| Correctness | + for names in the lexicon (5 of 5 probed); **- for names outside it (0 of 10 flagged, existence probe)** | -- on the policy family: 22 of 42 acceptable actions for the raw 1.5B; 5 leaned toward "confirm" where the oracle required abstain or reject; 12 rejected where only abstain or confirm was allowed | ? (the only place AI plausibly adds value; unmeasured) |
| Auditability | ++ (term matched, basis listed) | - | + |
| Latency / cost | ++ / ++ | -- / 0 | - / 0 |
| Failure severity | **Critical** (policy breach), mitigated because nothing is auto-cleared and a human decides (A-18) | **Critical** | Critical but only additive |
| Data requirements | A maintained term list (FR-12) | Would need adjudicated derivative names | Same, plus adjudication |
| Maintainability | + if the lexicon has an owner; **-- if it does not** (A-17) | - | 0 |
| **Decision** | **DO NOT USE AI for the verdict.** Fix the real weakness with governance (FR-12, FR-13), not with a model. A model may be tried later as an add-only flagger in shadow (gate G-L) | | |

Also relevant: after the tool-presentation change the 1.5B model's correct actions on policy scenarios **fell** from 22 to 10 of 42 (`results/tool_schema_result.json`), so a better interface did not rescue this sub-task.

### T4. Supplier selection

| Criterion | Non-AI (filter and rank by stated rules) | AI | Hybrid |
|---|---|---|---|
| Correctness | + for the validity checks; the lab does not compare several suppliers (A-21) | ? | ? |
| Auditability | ++ | - | + |
| Latency / cost | ++ / ++ | -- / 0 | - / 0 |
| Failure severity | Moderate (wrong supplier, human approves) | Moderate | Low |
| Data requirements | A supplier master with status, lead time, minimum (price and reliability if multi-supplier) | Same plus unstructured terms | Same |
| Maintainability | + | - | 0 |
| **Decision** | **DO NOT USE AI.** It is a constrained filter or a scoring table. If the ingestion of unstructured supplier terms becomes the bottleneck (A-02), that is a separate intake case | | |

### T5. Drafting the supplier message

| Criterion | Non-AI (template with five slots) | AI (LLM free text) | Hybrid (template or LLM wording, deterministic validator) |
|---|---|---|---|
| Correctness | ++ (slots come from verified fields) | ? (no evidence in this repository) | + if the validator is complete |
| Auditability | ++ | - | + |
| Latency / cost | ++ / ++ | -- on CPU / 0 | - / 0 |
| Failure severity | Low to moderate (a human reads before sending; the system never sends) | Moderate (a wrong figure in prose is easy to skim past) | Low to moderate |
| Data requirements | None | None | Edit logs to judge it |
| Maintainability | ++ | - | 0 |
| **Decision** | **NOT YET: template first.** The value of an LLM here is a saving of about one to two minutes per message (A-16, `05` section 6.4), and break-even requires an undetected-error rate near 0.2% to 1% for plausible placeholders, which is only reachable if a deterministic validator bounds the error, and then the template is nearly as good. Run the LLM-drafting experiment only if the template measurably fails (gate G-D) | | |

### T6. Explaining to a human

| Criterion | Non-AI (templated headline, cited claims, uncertainties, "not proposed") | AI (LLM prose) | Hybrid (LLM paraphrase, claims re-validated) |
|---|---|---|---|
| Correctness | ++ (0 of 723 unsupported claims) | + after validation (0 of 29 for the raw 1.5B), but 2 attacker-text leaks in 24 adversarial scenarios | + |
| Auditability | ++ | - | + |
| Latency / cost | ++ / ++ | -- / 0 | - / 0 |
| Failure severity | Moderate (a misleading line can bias a tired reviewer: FR-13) | Moderate | Moderate |
| Data requirements | None | None | A reader-comprehension measure (unmeasured) |
| Maintainability | + | - | 0 |
| **Decision** | **DO NOT USE AI now.** No evidence the template fails to communicate; the known explanation defect (FR-13) is a wording fix. Reconsider only if reviewer time or comprehension in a pilot is the bottleneck (M-3) | | |

### T7. Approval

| Criterion | Non-AI (human, signed grant bound to exact arguments) | AI | Hybrid |
|---|---|---|---|
| Correctness | ++ for the mechanism (forged, replayed, retargeted, wrong-role, expired grants refused) | -- by definition | n/a |
| Auditability | ++ | -- | n/a |
| Failure severity | Depends on the human (A-18) | **Unacceptable**: an automated approver removes the control that makes every other component safe | n/a |
| **Decision** | **DO NOT USE AI.** Not a trade-off: the human approval is the control that makes AI-assisted anything tolerable, and the lab's architecture rests on it (0 external actions in about 1,000 real-model calls) | | |

## 4. Summary

| Sub-task | Decision | Principal reason |
|---|---|---|
| T1 Detection | Do not use AI (optional add-only shadow trial, gate G-S) | Silent all-clear is the dangerous failure; rules are exact and fast |
| T2 Coverage arithmetic | Do not use AI | Exactness; the risk is rule definition, found by probes, not a model |
| T3 D-54 verdict | Do not use AI for the verdict; fix the lexicon process (FR-12, FR-13); add-only flagger trial gated (G-L) | Critical severity; the real weakness is vocabulary governance |
| T4 Supplier selection | Do not use AI | A filter or scoring table |
| T5 Message drafting | Not yet: template; LLM only as a gated experiment (G-D) | No evidence; savings are minutes |
| T6 Explaining | Do not use AI now | Template works; defect is wording |
| T7 Approval | Do not use AI | It is the control |

The workflow's decision core is therefore **not AI**. The answer for the language-shaped edge is "not yet, and here is the measurement that would change it", not "never".
