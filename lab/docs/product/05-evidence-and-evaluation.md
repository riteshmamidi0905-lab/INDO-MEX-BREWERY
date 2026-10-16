# 05. Evidence and synthetic evaluation

**SYNTHETIC DATA / OFFLINE / SAME AUTHOR / NOT DEPLOYED.** One author wrote the generator, the rules, the oracle and the scoring. Nothing here is a business result and nothing was tuned or re-run: the new material is (a) a read-only re-analysis of committed result files (`lab/product_case/analysis.py`, output `lab/product_case/results/analysis.json`), (b) a small assumption-driven cost model (`lab/product_case/cost_model.py`, output `cost_model.json`), and (c) a ten-term probe of the baseline's lexicon. File names below are relative to `lab/` unless stated.

## 1. What the evidence is

| Evidence | What it is | What it can support | What it cannot |
|---|---|---|---|
| 259 generated scenarios (dev 67, held-out 75, held-out B 75, adversarial 42), expectations set by construction | Rules vs two local LLMs under one tool, permission and approval stack | A comparison of planners on this harness | Real-world accuracy; the control was built beside the scenarios; dev and held-out were seen while it was fixed; only held-out B is clean (`docs/PLANNER-EXPERIMENT.md`) |
| ext1: 106 scenarios built by a decision-table oracle, metamorphic variants, rule-gap probes | Structurally different second set, still one author | Shows the headline is not only a template artifact; found a real rule gap | Independence. The author's own oracle was wrong five ways in the first run |
| Real-model runs: Qwen2.5-1.5B (140 scenarios, 426 calls), Qwen2.5-7B (35 scenarios, 144 calls), CPU, temperature 0, seed 7 | Two small local models, one prompt, one run each | Direction | Statements about LLMs in general or hosted frontier models, which were not tested (A-04) |
| Tool-presentation experiment (pre-registered), one change bundle on the 1.5B model | Was poor tool recall partly an interface problem? | Yes, partly | A rescue of the model (see section 5) |

## 2. Planner comparison (verified against the result files)

| Measure | Rules (control) | Qwen2.5-1.5B raw | Qwen2.5-1.5B + envelope | Qwen2.5-7B raw | Source |
|---|---|---|---|---|---|
| Scenarios | 259 | 140 | 140 | 35 | `n` in each file |
| All checks passed | 259 (100%) | 5 (3.6%) | 8 (5.7%) | 10 (28.6%) | `results/planner_deterministic.json`, `planner_qwen1.5b_run2_raw.json`, `..._guardrail.json`, `planner_qwen7b_raw.json` |
| Correct action | 259 | 52 (37.1%) | 51 (36.4%) | 20 (57.1%) | same |
| Required tools called | 259 | 22 (15.7%) | 22 | 15 (42.9%) | same |
| External actions executed | 0 | 0 | 0 | 0 | same |
| Unsupported claims | 0 of 723 | 0 of 29 | 0 of 12 | 0 of 15 | same |
| Latency p50 | 65.5 ms | 28,031.7 ms | replayed (not a latency) | 151,524.4 ms | same |
| Model calls | 0 | 426 | same replies | 144 | same |

Paired by scenario id (documented, `docs/PLANNER-EXPERIMENT.md`): the model passes where the rules fail in **0** scenarios in every comparison; exact sign test p < 0.001. Latency caution: the rules ran on a different host than the CI runner (4 vCPU) used for the models, and these are medians; I recompute the rules' median on the same 140 ids as 51.2 ms, so the ratio is about 430 to 550 times for the 1.5B model and about 2,300 times for the 7B model, an order of magnitude only (`product_case/results/analysis.json`, `latency`). The planner document quotes 600 to 3,000 times against a CI figure of about 47 ms.

Test counts are kept separate on purpose: the frozen Block 3 CI recorded **229 passed, 1 skipped** (`results/test_summary.json`); I ran the suite locally at the base commit of this branch and got **265 passed, 2 skipped** before adding anything.

## 3. Where the dangerous failure sits (new re-analysis, nothing re-run)

Pre-stated rule: if the raw model's silent all-clear concentrates in inventory events, the inventory workflow is where to apply the strictest rule.

Method: rejoin each result row to its scenario's expected answer (the registry is only constructed, never executed) and split by event family.

| Planner | Actionable inventory scenarios | Silent `NO_ACTION` | Wilson 95% | Correct action | Healthy inventory scenarios | Escalated although healthy |
|---|---|---|---|---|---|---|
| Rules (259-scenario run) | 119 | **0** | 0% to 3.1% | 119 | 8 | 0 |
| Qwen 1.5B raw | 59 | **30** | 38% to 63% | 7 | 4 | 4 |
| Qwen 1.5B + envelope | 59 | 0 | 0% to 6.1% | 18 | 4 | 4 |
| Qwen 7B raw (35-scenario sample) | 16 | 0 | 0% to 19.4% | 10 | 0 | n/a |
| Qwen 7B + envelope | 16 | 0 | 0% to 19.4% | 12 | 0 | n/a |

Result: **all 30 silent all-clears are inventory events; none in data-quality or policy events.** Independent cross-check: the pre-registered tool-schema result file counts 30 wrong silent `NO_ACTION` for the same run (`results/tool_schema_result.json`, row 0); the sum over families matches. The silent failure is concentrated exactly in the workflow chosen for this case, which is the strongest single reason that no model may be the only barrier between an exception and a human.

Two cautions. The 7B model's zero is 0 of 16 and cannot exclude a miss rate up to 19%. And the envelope's zero is a property of the rules it embeds, not a capability of the model; its price is visible in the "correct action" column.

## 4. The D-54 family (new re-analysis)

Policy scenarios, direction of each planner's departure from the oracle's acceptable set:

| Planner | n | Acceptable | Leans toward "human confirm" where the oracle required abstain or reject | Recommends reject where the oracle allowed only abstain or confirm | Abstains where a specific recommendation was expected |
|---|---|---|---|---|---|
| Rules | 82 | 82 | 0 | 0 | 0 |
| Qwen 1.5B raw | 42 | 22 | **5** | **12** | 3 |
| Qwen 1.5B + envelope | 42 | 28 | 0 | 0 | 14 |
| Qwen 7B raw (sample) | 12 | 9 | 0 | 0 | 3 |

Reading: the raw small model both leans toward confirmation in five cases it should not and guesses a rejection in twelve where the system must say "insufficient verified evidence". The envelope removes both by abstaining more (14 abstentions where the oracle expected a specific recommendation), consistent with the planner report: a guardrail is a safety device, not a capability. The 7B sample is too small to say more. Separately, in the pre-registered interface experiment the 1.5B model's correct actions on policy scenarios fell from 22 to 10 of 42 (`results/tool_schema_result.json`, `by_event_family.POLICY`).

## 5. Interface experiment and the rule-gap finding

**Interface (pre-registered, rule: at least 15 points of required-tool recall and paired p < 0.05).** Required-tool recall 22 -> 67 of 140; paired 8 vs 52, p < 0.001; all-checks pass 5 -> 16 (22 with the envelope); schema failures at the decision step rose 3 -> 37; refused requests 119 -> 0 (almost all one misspelled tool name, `results/ERRATA.md` item 3); data-quality recall 0/33 -> 33/33; policy 1/42 -> 0/42. Product reading: a better interface moves a small model from hopeless to merely poor, and the gain is mechanical (a name error removed) plus system knowledge placed in the menu. Even the best arm passes 22 of 140 against 140 of 140 for rules. A discrepancy to record: the planner-experiment document's table gives wrong silent `NO_ACTION` 0 for the ts2 arm, while the result file gives 2 for the ts2 raw arm and 0 with the envelope; I cite the file.

**Rule gap (found by evaluation, not by a model).** The first coverage rule treated any in-time open order as cover regardless of size. Rule-gap probes: 0 of 8; after the quantity-aware rule v2, 8 of 8, with 98 of 98 headline and 24 of 24 metamorphic relations unchanged (`results/ext1_planner_deterministic.json`, `ext1_planner_deterministic_poq2.json`). Lesson for the AI decision: the most consequential defect in the arithmetic was a **rule definition** defect, and what found it was a structurally different test set, not a more capable component. An LLM in that seat would have had the same blind spot with less repeatability. Not modelled: an order arriving after stock-out but inside lead time; demand is a 14-day average.

## 6. Expected cost of failure under stated assumptions (new, small, seeded)

### 6.1 Definition, written before running

- Hypothesis H1: some AI planner variant has a lower expected cost than rules-only across most of the plausible parameter space.
- Decision rule: the recommendation "do not use an LLM as planner" is reversed for a variant only if it has the lowest expected cost in at least 50% of seeded draws **and** in the central case. A variant that wins only through an unmeasured parameter is reported as conditional, and that parameter becomes a pilot measurement.
- The model is deliberately generous to AI: every LLM option may catch a share b of the rule-gap misses the rules make.
- Measured inputs (inventory events only, from section 3): silent-miss, wrong-but-not-silent and false-alarm counts. Rates are posterior draws from Beta(k+1, n-k+1). Everything else is a PLACEHOLDER in the assumptions register (A-05 to A-12). Four healthy scenarios and sixteen 7B scenarios mean the false-alarm inputs are almost unmeasured; the 7B false-alarm rate has no data and is drawn from 0.1 to 1.0.

### 6.2 Central case (N = 1,000 checks, 20% actionable, cost of a silent miss 500, review 5, rule gap g 5%, model catch b 30%, extra false alarms 30%)

| Option | Silent-miss cost | Review | Rework | False alarms | Total per 1,000 checks |
|---|---|---|---|---|---|
| Rules only | 5,000 | 950 | 19 | 80 | **6,049** |
| Add-only second opinion (rules decide; model can only add escalations) | 3,500 | 965 | 19 | 1,256 | **5,740** |
| 1.5B + envelope | 5,082 | 949 | 695 | 3,333 | 10,059 |
| 7B + envelope | 8,861 | 911 | 250 | 2,000 | 12,022 |
| 7B raw | 8,861 | 911 | 375 | 2,000 | 12,148 |
| 1.5B raw | 52,541 | 475 | 373 | 3,333 | 56,722 |

(Money is a placeholder. The 7B rows depend on the placeholder false-alarm rate 0.5 and on a posterior from 16 scenarios.) In the central case the add-only second opinion is 5% cheaper than rules-only, and **that advantage comes entirely from the unmeasured b and g** (cost of misses falls from 5,000 to 3,500 and is partly paid back as false alarms).

### 6.3 Sensitivity (20,000 seeded draws, seed 20261016; ranges in `cost_model.json`)

| Which option has the lowest cost | Rules only | Add-only second opinion | Any LLM planner variant (1.5B or 7B, raw or enveloped) |
|---|---|---|---|
| Pessimistic extra false alarms (the 1.5B planner's measured behaviour, 4 of 4 healthy escalated) | **62.5%** | 33.5% | 4.1% (1.5B + envelope 0.3%, 7B raw 1.7%, 7B + envelope 2.1%, 1.5B raw 0%) |
| Optimistic extra false alarms (uniform 0 to 20%) | 27.0% | **73.0%** | 0% |

Cost ratio add-only / rules, 10th, 50th, 90th percentile: pessimistic 0.74 / 1.15 / 2.68; optimistic 0.65 / 0.91 / 1.14. Break-even cost of a silent miss for the add-only hybrid to beat rules, other values central: about 70 units (optimistic) or about 1,094 units (pessimistic). Grid by actionable share and cost of a miss (`cost_model.json`, `grid`): rules win at low miss cost with few actionable events; the add-only option wins at moderate to high miss cost; no LLM planner variant wins any cell.

**Verdict by the pre-stated rule** (`cost_model.json`, `verdict`; tested):
- **LLM as planner: the recommendation stands.** No variant reaches 50% of draws in either mode; the 7B variants win about 4% of pessimistic draws only because 16 scenarios leave their miss-rate posterior wide.
- **Add-only second opinion: conditional on unmeasured quantities.** It wins 73% of draws under optimistic assumptions and 33.5% under pessimistic ones. It therefore does not meet the "both modes" reversal bar, and it is the one place where a pilot could change the picture. The rule-gap rate g and the catch rate b are the numbers that matter, and neither exists.
- **What this model cannot say:** that any real cost or rate is what the placeholders suggest. Reading it as a forecast would be wrong; reading it as a map of which unknowns carry the decision is its only use.

### 6.4 Drafting-only break-even

LLM drafting saves the human minutes: if a template takes 3 minutes and checking an LLM draft takes 2, at a placeholder wage of 0.5 per minute the saving is 0.5 per message. The LLM path is better only if the undetected factual-error rate q satisfies q x (cost of a wrong message) < 0.5, i.e. q below 1% if a wrong message costs 50, 0.25% at 200 and 0.05% at 1,000 (`cost_model.json`, `drafting_breakeven_table`; larger savings of 1.5 to 2.0 per message move these to 0.15%-4%). No evidence in this repository measures q for any model. The shape is the finding: the benefit is minutes, the tolerable error rate is tiny, and the only way to bound q is a deterministic validator on every figure, at which point the template is already nearly as good. That is why drafting is "not yet", behind gate G-D.

## 7. The baseline's weak spot (new ten-term probe)

Pre-stated rule: if at least one clearly beef or pork-derived term returns NO_POLICY_SIGNAL, the lexicon needs an owner and update process (FR-12) and the screening wording must never read as a clearance (FR-13).

Probe (`product_case/analysis.py`, `lexicon_probe`; pinned by test): five listed terms (beef stock, pork lard, bacon bits, beef tallow, gelatin) return PROHIBITED 5 of 5; ten author-chosen derivatives outside the 14-token lexicon (suet, pepperoni, pancetta, gelatine, oxtail, ribeye, bone marrow, hamburger patty, salami, prosciutto) return NO_POLICY_SIGNAL **10 of 10**; none of four benign terms (cauliflower, sunflower oil, Hamilton sauce, corn masa) is flagged PROHIBITED (0 of 4). **This is an existence proof, not a rate**: the ten terms were chosen to lie outside the lexicon, one author, n = 10.

What the system then does (`tests/test_product_case_stories.py`): the planner abstains with "INSUFFICIENT VERIFIED EVIDENCE ... do not infer that it is allowed or prohibited", never recommends confirmation, never approves. So the failure mode is not a false clearance by software; it is a reviewer who sees yet another abstention (53 of 259 rules outcomes are abstentions) and a claim line reading "no D-54 term and no hidden-derivative term". The rule fired. It argues for lexicon governance and honest wording first. It also names the one place a model might legitimately help, as an **add-only flagger of unfamiliar derivative names**, to be tested in shadow (G-L), because recognising `suet` as beef fat is knowledge a small list lacks and a language model plausibly has. Whether a small local model has it reliably is unmeasured.

## 8. What a real pilot would measure, and what would change the decision

Preconditions: an operation exists (A-01), an adjudicator who did not write the rules, shadow mode first (rules and the manual process run in parallel, no automation).

| Question | Measurement | Sample size logic | Result that would change the decision |
|---|---|---|---|
| Is the rules engine good enough? (M-1, R-1) | Adjudicated exceptions found vs missed; stock-outs and waste traced back to a missed exception | 0 misses in 300 adjudicated exceptions gives a 95% upper bound near 1% | Any silent miss attributable to a rule gap: add the case as a test and re-estimate g; if g >= 5%, open G-S |
| What is g? (A-10) | Share of actionable events the rules handled wrongly or not at all | About 40 gap cases give a 95% interval half-width of about 14 points for b near 0.3, which needs about 800 actionable events at g = 5%; at g = 1% it needs about 4,000 | If the upper bound on g is below 1%, no AI second opinion can pay and G-S is closed |
| Could a model catch them? (A-11) | Shadow run of a candidate model (only after an independent healthy-heavy scenario set exists) on the adjudicated gap cases | Same | G-S passes only if the model-added escalations have precision at least 20% (R-8) and catch at least 30% of gap cases, with zero model-caused silent misses (impossible by construction: it can only add) |
| False alarms (M-2) | Healthy checks that produced a review item | Needs a healthy-heavy set; the synthetic suite is 3% healthy | Above 10% for the rules, retune rules; any AI component adding more than 10 points fails |
| Reviewer behaviour (A-18, R-5) | Dwell time, evidence expansion | All approvals | Rubber-stamp rate above 5%: human review is not a control; tighten before any further automation |
| Is the template enough? (A-16, M-5) | Edit rate and severity, drafting time, supplier reply time | 100 messages | Median manual drafting plus checking at least 5 minutes, or more than half of templates materially edited, opens G-D |
| Unstructured share (A-02) | Share of exceptions needing calls, emails or photos | All | Above 30% opens a separate intake case |
| Lexicon incidents (A-17, R-6) | Prohibited derivatives found in review that the screen did not flag | Monthly | One or more per month after governance opens G-L |

A fair stronger-model test, if the owner ever relaxes A-04: re-run the model arm on a **new**, independently labelled, healthy-heavy scenario set (not the frozen one), pre-register the decision rule (silent all-clear 0 of at least 100 actionable with upper bound at most 3%, correct action within 2 points of the rules, net catches on adjudicated gaps), and publish the result whichever way it goes. The frozen benchmark is not to be re-run or tuned for this.

## 9. Limits of everything above

Same-author oracle and generator; synthetic data; the suite is about 97% actionable, so false alarms are barely measured; two small local models and one prompt; a CPU runner; no hosted frontier model; no real exceptions; the baseline's own gaps (section 7) were found by me, so there are likely more; money in the cost model is a placeholder; the re-analysis rejoins rows to a registry whose expectations were written by the same author. The honest claim is: **on this harness, for these models, nothing in the evidence supports putting a language model in the decision path of this workflow, and the evidence for where it might help is a hypothesis, not a result.**
