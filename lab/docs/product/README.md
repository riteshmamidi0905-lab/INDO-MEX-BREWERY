# P3 AI product case: should NASHA's inventory-exception workflow use AI at all?

**SYNTHETIC ENTERPRISE / ASSUMPTION-DRIVEN / SAME AUTHOR / NOT DEPLOYED.** NASHA is an independent founder concept: no restaurant, customer, supplier, interview, revenue or deployment exists. Personas are SIMULATED and are not evidence of demand. Money and volumes are placeholders. Targets are DESIGN TARGETS. Mango Habanero Gobi is an untested design hypothesis and plays no role here.

## The answer

**For the decision core: no.** Detection, coverage arithmetic, the D-54 dietary verdict, supplier selection and approval should be deterministic rules plus a human approver. For the language edge (supplier messages, explanations): **not yet**; ship a template, and let a language model in only as a gated, shadow-only experiment that has to beat it on pre-registered measures.

| Sub-task | Decision | Principal reason |
|---|---|---|
| Detection | Do not use AI (add-only second opinion is a gated experiment) | The dangerous failure is a silent all-clear |
| Coverage arithmetic | Do not use AI | Exactness; the defect that mattered was a rule definition, found by a test set |
| D-54 check | Do not use AI for the verdict; fix lexicon governance and wording | Critical severity; the real gap is vocabulary |
| Supplier selection | Do not use AI | A filter or scoring table |
| Supplier message | Not yet: template first; LLM only if the template fails | No evidence; the saving is minutes |
| Explaining to a human | Do not use AI now | The cited template works; one wording defect |
| Approval | Do not use AI | It is the control that makes everything else tolerable |

## The evidence behind it (every number is traced in `09-evidence-map.md`)

- On 259 synthetic scenarios the rules pass 259; Qwen2.5-1.5B passes 5 of 140 and Qwen2.5-7B 10 of 35; the model passed where the rules failed in 0 scenarios (`results/planner_*.json`).
- The 1.5B model answered "no action" when action was needed in 30 of 140 scenarios. My re-analysis shows **all 30 are inventory events: 30 of 59 actionable inventory scenarios** (`product_case/results/analysis.json`). The deterministic envelope removes them (0) at the price of over-escalating, including 4 of 4 healthy scenarios.
- Tool presentation (pre-registered) lifted required-tool recall from 22 to 67 of 140 but left policy correct actions at 10 of 42, down from 22 (`results/tool_schema_result.json`).
- The first purchase-order coverage rule was wrong (probes 0 of 8, then 8 of 8 after a quantity-aware rule): the defect was in a rule, and a test set found it (`results/ext1_planner_deterministic*.json`).
- Median latency 65.5 ms (rules) vs 28.0 s (1.5B) vs 151.5 s (7B), different hosts, order of magnitude.
- A seeded cost model with placeholder money (20,000 draws): no LLM planner variant is cheapest in more than 4.1% of draws; an add-only second opinion wins 33.5% (pessimistic) to 73% (optimistic) of draws, **conditional on two unmeasured rates** (`product_case/results/cost_model.json`).
- The no-AI baseline is not flawless: ten of ten beef or pork derivatives I chose outside its 14-token D-54 lexicon return NO_POLICY_SIGNAL (existence probe, not a rate). The system abstains rather than clears, but the claim line reads clean; that is a requirement gap (FR-13), not a model gap.

## What would reverse it

A pilot rule-gap rate with upper bound of 5% or more, together with a model that, on a new independent healthy-heavy set, adds escalations with at least 20% precision and catches at least 30% of gap cases; template drafts that fail (median 5 minutes or half materially edited); lexicon gaps recurring monthly; a relaxed local-models-only constraint followed by a re-test. If the rule-gap rate is near zero, or the operation is tiny, the answer is a spreadsheet. See `06-decision-memo.md` section 5.

## Not claimed

Any real demand, customer, cost, saving or market size; that LLMs are inferior in general (two small local models, CPU, one prompt were measured; hosted models were not); independent validation; that the rules would handle exceptions the author did not anticipate; a tool count (README and registry disagree, under investigation); a halal claim.

## Files

`01` problem, workflow choice vs two alternatives, SIMULATED stakeholders, current state, pain points, JTBD. `02` requirements, constraints, success and risk metrics. `03` non-AI baseline (N0 to N2), AI alternatives, decision matrix per sub-task. `04` PRD, 16 user stories traced to tests. `05` evidence and synthetic evaluation, cost model, pilot design. `06` decision memo. `07` rollout, kill criteria, roadmap. `08` assumptions register (A-01 to A-22). `09` evidence map.

Reproduce (from `lab/`; nothing re-runs a frozen benchmark): `python3 -m product_case.analysis && python3 -m product_case.cost_model && python3 -m pytest -q -p no:cacheprovider tests`.
