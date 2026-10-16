# 06. Decision memo: should the inventory-exception workflow use AI?

**SYNTHETIC / ASSUMPTION-DRIVEN. Decision record for a hypothetical operation.** NASHA has no operation, customers, suppliers or sales. The evidence is same-author, offline and synthetic. Nothing in this memo is a business result or an estimate of real value.

| | |
|---|---|
| Decision owner | Ritesh Mamidi (author of the case; accountable for the concept) |
| Status | PROPOSED, for the owner to accept, amend or reject |
| Date | 2026-10-16 |
| Decision | **Do not use AI in the decision path. Build deterministic rules with a human approver and templated drafts. Hold two narrow AI uses behind experiment gates.** |

## 1. Question and context

Which parts of inventory-exception triage and reorder or escalation (detection, coverage arithmetic, D-54 dietary check, supplier selection, supplier messages, explanation, approval) should use AI, if any? Constraints: no paid API (D-81), D-54 binding with no halal claim, a human approves every consequential step, synthetic data only.

## 2. Options considered

N0 spreadsheet and checklist; N1 rules engine; N2 rules plus templated drafts; AI-1 LLM planner; AI-2 LLM planner plus deterministic envelope; AI-3 LLM drafting only; AI-4 deterministic decisions with LLM wording behind validators; AI-5 add-only second opinion. Detail in `03`.

## 3. Recommendation

1. **Detection, coverage arithmetic, supplier selection, approval: do not use AI.** Rules, with the human approval mechanism the lab already tests.
2. **D-54 verdict: do not use AI.** Fix the actual weakness, which is vocabulary governance and wording (FR-12, FR-13), not a missing model.
3. **Explanation: do not use AI now.** The templated, evidence-cited explanation is adequate on the evidence; its one known defect is a wording fix.
4. **Supplier messages: not yet.** Ship the template (N2). An LLM drafts only if the template measurably fails (gate G-D) and only behind a deterministic validator.
5. **Two gated shadow experiments, never releases:** an add-only second opinion on detection (G-S) and an add-only flagger of unfamiliar derivative names (G-L). Both can only add escalations.

## 4. Why (the evidence, with limits)

| Reason | Evidence | Limit |
|---|---|---|
| Rules beat two small local models on every measure and the models never beat them | 259 of 259 vs 5 of 140 (1.5B raw) and 10 of 35 (7B raw); the model passed where rules failed in 0 scenarios (`docs/PLANNER-EXPERIMENT.md`, `results/planner_*.json`) | Same-author; two of the four splits were seen when the rules were fixed; two small models; no hosted model (A-04, A-13) |
| The dangerous failure is silent and sits in this workflow | 30 of 140 silent `NO_ACTION`, all 30 inventory (30 of 59 actionable inventory scenarios) (`product_case/results/analysis.json`) | One model, one run; 7B showed 0 of 16 with an interval to 19% |
| A safety envelope fixes the silent failure and removes the usefulness | Envelope: 0 silent, correct action 18 of 59 on actionable inventory; every healthy scenario escalated (4 of 4) | The envelope is the rules engine; healthy sample is 4 |
| A better interface helps a little and not where it matters | Required-tool recall 22 to 67 of 140; policy correct actions 22 to 10 of 42 (`results/tool_schema_result.json`) | One model, a bundle of changes |
| The arithmetic defect that mattered was a rule definition, found by a test set | PO coverage probes 0 of 8 to 8 of 8 (`results/ext1_planner_deterministic*.json`) | Probes are author-built |
| Latency and compute are not decisive but are far apart | 65.5 ms vs 28.0 s vs 151.5 s medians; 1,000 checks would take about 7.8 h (1.5B) or 42 h (7B) sequentially | Different hosts; a daily batch hides much of this (A-15) |
| In the cost model no LLM planner wins; an add-only second opinion wins only conditionally | 20,000 seeded draws: LLM planners 4.1% (pessimistic) and 0% (optimistic) of draws; add-only 33.5% and 73% | Placeholder money; unmeasured g and b |
| AI approval is not a trade-off | The control that makes every other component tolerable | Design principle (A-03) |

The baseline is not flawless. My own probe found that ten of ten beef or pork derivatives outside the 14-token lexicon return NO_POLICY_SIGNAL, and the supplier-selection logic does not compare suppliers. The recommendation is that these are fixed by process and design, and that the only AI hypotheses worth testing are those aimed at exactly these gaps.

## 5. What would reverse or change this decision

Each is a measurable trigger, and none can be met by synthetic evidence alone.

| Trigger | Measurement | Effect |
|---|---|---|
| T-1 The rules miss real exceptions at a material rate | Pilot rule-gap rate g with upper 95% bound at or above 5% | Open G-S (add-only second opinion in shadow) |
| T-2 A candidate model meets the pre-registered bar on a new independent healthy-heavy set | Silent all-clear 0 of at least 100 actionable (upper bound at most 3%); correct action within 2 points of rules; net catches on adjudicated gaps | Allow the add-only role, still never as planner |
| T-3 Template drafts fail | Median drafting plus checking time at least 5 minutes or more than half of templates materially edited | Open G-D (LLM drafting behind a validator) |
| T-4 Lexicon gaps recur after governance | One or more unflagged prohibited derivatives per month | Open G-L (add-only derivative flagger) |
| T-5 Exceptions are mostly unstructured | More than 30% need calls, emails or photos | New case for AI-assisted intake; decisions on T1 to T7 unchanged |
| T-6 The operation is tiny | A handful of ingredients at one site | Stop at N0 (spreadsheet); nothing to build |
| T-7 Budget or policy changes (A-04) | Hosted models become permitted | Re-run the model arm on the new set before changing anything; the current finding does not transfer |
| T-8 The founder allows auto-ordering (A-03) | Policy change | Zero-tolerance requirements apply to every component; AI stays out of the path |

Reversal of the "no AI in the decision path" statement for T1 to T4 and T7 would need T-2 **and** a clean shadow period; I do not expect any near-term result to justify it.

## 6. Residual risks and what is NOT CLAIMED

Residual risks: the deterministic 259 of 259 flatters the rules (A-13); the false-alarm side is unmeasured (8 healthy scenarios of 259); reviewers may rubber-stamp (A-18); the D-54 lexicon is a single point of failure until FR-12 exists; supplier selection is not modelled beyond validity (A-21); the central cost-model result depends on unmeasured g and b.

NOT CLAIMED:
- That any customer, operator or supplier wants this, or that any interview or survey happened. None did; personas are SIMULATED.
- Any market size, revenue, saving, or real cost.
- That LLMs are inferior in general. Two small open-weight models, CPU, one prompt, scenarios written by the author were measured; hosted frontier models were not.
- That the deterministic planner would handle real exceptions the author did not anticipate. It is rigid by design, and the author's own first version of one rule was wrong.
- Independent validation. Everything is same-author.
- Anything about Mango Habanero Gobi beyond its place in the synthetic menu. It is an untested design hypothesis.
- A tool count. The README and the registry disagree and this is under investigation, so none is stated.
- A halal claim of any kind.

## 7. Decisions needed from the owner

1. Accept, amend or reject the recommendation in section 3.
2. Whether to build R1 (FR-12 lexicon ownership, FR-13 wording, FR-14 template and validator) in the lab as new code with new tests, without touching frozen files.
3. Whether to relax A-04 (local models only) for a one-off stronger-model test on a new set, and who writes that set (an independent labeller, P7).
4. Whether to commission real discovery (P8) before any build; this case is only as good as its assumptions.
5. Whether the central cost-model placeholders (A-05 to A-12) are acceptable to show to others, or should be hidden behind the sensitivity table.
6. Resolve the tool-count discrepancy (README versus registry) before any public use.
