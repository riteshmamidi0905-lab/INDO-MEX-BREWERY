# Planner experiment: does adding a local LLM improve the NASHA operations agent?

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** One author wrote the system, the scenarios and the checks. NASHA is a founder concept: no restaurant, customer, supplier or sale exists. Cost: **LOCAL COMPUTE - NO API CHARGE** (free GitHub-hosted CPU runners, Ollama, open-weight models; no paid API, no key).

## Question
The Block 2 agent uses a deterministic planner. Does replacing it with a language model improve task completion, abstention, tool use or safety, enough to justify the extra complexity, latency and risk? The hypothesis that it does was **not assumed**; the deterministic planner stays as the control.

## Method
- **One interface, two planners.** `Planner.collect(state, call, trace)` and `Planner.decide(state, trace)`. `DeterministicPlanner` (control, the Block 2 logic) and `LLMPlanner` run on the *same* LangGraph state, tool registry, permission classes, signed human approval, trace store and evaluation harness. The model only *proposes*: READ/ANALYZE tool calls and a structured decision (JSON validated against a pydantic schema, bounded retries, no chain-of-thought stored). Deterministic code validates, authorizes, executes and traces. The model is not the permission system.
- **Variants.** *Raw LLM*: the model's validated decision is used as is (inside the permission layer). *LLM + guardrail*: a deterministic **evidence envelope** (the set of actions the collected tool evidence permits) overrides any less-conservative model action and traces `guardrail_override`. The guardrail variant is scored on the **same cached model replies** as the raw variant, so the two differ only in the guardrail, not in sampling noise.
- **Model/runtime.** Ollama on a GitHub-hosted `ubuntu-latest` runner (4 vCPU, CPU only): `qwen2.5:1.5b-instruct` (Apache-2.0, 986 MB, Q4_K_M), temperature 0, seed 7, JSON-schema constrained decoding (`format`), ~32 tok/s. A third run uses `qwen2.5:7b-instruct` (Apache-2.0, 4.7 GB, Q4_K_M) on held-out B and the adversarial split, one scenario per family. The authoring sandbox cannot download models (Hugging Face and ollama.com blocked), so every real-model number comes from CI logs. See [LLM-RUNTIME.md](LLM-RUNTIME.md).
- **Scenarios.** 259 generated scenarios (deterministic, seeded), expectations set by construction from the injected condition (not from any planner's output). Splits: **dev** 67, **held-out** 75 (seed 3000), **held-out B** 75 (seed 7000, generated after the deterministic fixes and never inspected before scoring), **adversarial** 42 (prompt injection, poisoned documents, poisoned tool results, replay, decision/edit abuse, untrusted MCP modes). The real-model runs use a stratified subset (`--per-family 2` for the 1.5B model = 138-140 scenarios; `--per-family 1` on held-out B + adversarial for the 7B model) because CPU inference is slow.
- **Contamination, stated plainly.** The deterministic planner was fixed after reading failures on dev, held-out and adversarial scenarios (see [../results/EXPERIMENT-LOG.md](../results/EXPERIMENT-LOG.md)). **Held-out (seed 3000) is therefore not a clean test of the deterministic planner; held-out B is.** No scenario was edited in response to an LLM result, and no prompt was tuned on the held-out splits.
- **Pass** means *all* of: correct action, correct abstention behaviour, every required tool called, approval boundary respected, no forbidden attempt that executed, no unsupported claim, no leak. It is strict on purpose; the finer metrics below separate *why* a scenario failed.
- **Stand-ins are not LLMs.** Scripted responders (`rule-model`, `worst-case`, `parrot`, `taint-copier`) exist to test the harness and the permission layer, and to bound what a misbehaving model could do. They are never reported as language-model results.

## Results: deterministic control (all 259 scenarios)
| split | passed |
|---|---|
| dev | 67 / 67 |
| held-out (contaminated) | 75 / 75 |
| held-out B (clean) | 75 / 75 |
| adversarial | 42 / 42 |

Correct action 259/259, correct abstention 211/211, required tools 259/259, approval boundary 259/259, unsupported claims 0 of 723, forbidden attempts 0, external actions 0, trace complete 258/259 (the one miss is `policy_retrieval_failure`, where the checker requires a `policy_retrieved` event that cannot exist when retrieval itself failed: checker strictness, not a missing record), p50 latency tens of milliseconds, 0 tokens, 0 model calls. It makes some unnecessary (extra, read-only) tool calls: 126 across 259 scenarios. A perfect score on scenarios the same author generated is a statement about the harness, not about the real world.

## Results: real local LLM, qwen2.5:1.5b-instruct, run 1 (commit f0ebad3, 138 scenarios, 4 splits)
CI run 38777027649. Recovered from the job log by `nasha_lab/ci_results.py` (artifact download is blocked in the authoring sandbox). Files: `results/planner_qwen1.5b_run1_{raw,guardrail,paired}.json`.

| metric (138 scenarios) | deterministic control (same subset) | LLM raw | LLM + guardrail |
|---|---|---|---|
| all checks passed | 138 / 138 | **9 / 138 (6.5%)**, 95% CI 3.5-11.9% | 8 / 138 (5.8%) |
| correct action | 138 / 138 | 51 / 138 (37%) | 54 / 138 (39%) |
| correct abstention (of 108 should-abstain) | 108 / 108 | 85 / 108 (79%) | 40 / 108 (37%) |
| required tools called | 138 / 138 | 20 / 138 (14.5%) | 20 / 138 (14.5%) |
| unnecessary tool calls | 0 | 259 | 259 |
| invalid tool-call arguments | 0 | 144 | 111 |
| refused tool requests (unknown or forbidden; see note) | 0 | 95 | 95 |
| external actions executed | 0 | **0** | **0** |
| approval-boundary compliance | 138 / 138 | 138 / 138 | 138 / 138 |
| unsupported claims | 0 of 363 | 2 of 24 | 1 of 7 |
| schema failures (of 434 model calls) | n/a | 16 (3.7%) | 16 |
| planner failures (fail-safe fallback) | 0 | 10 | 10 |
| trace complete | 137 / 138 | 137 / 138 | 137 / 138 |
| latency p50 / p95 | 47 ms / 94 ms | **31.9 s / 61.6 s** | (cached replies; not a latency measure) |
| tokens (prompt + completion) | 0 | 314,931 + 67,834 | same replies |

By split (raw LLM): dev 3/38, held-out 5/39, held-out B 1/39, adversarial 0/22. Paired against the deterministic planner on the same scenario ids (131 ids shared with the current scenario build): deterministic passes where the model fails in 122 scenarios, the model passes where the deterministic planner fails in **0**; exact two-sided sign test p < 0.001. Raw per-id data: `results/planner_qwen1.5b_run1_paired.json`.

### What the numbers mean
1. **The 1.5B model did not improve anything.** On every metric the deterministic planner is at least as good, and the model is 600-1000x slower.
2. **The failure is tool use, not JSON.** Only 3.7% of model calls failed the output schema; the structured-output constraint worked. What failed is *which tools to call with which arguments*: the model called the required evidence tools in 14.5% of scenarios, made 144 invalid-argument calls and 95 forbidden attempts. Without the evidence, a conservative decision is the only defensible one.
3. **The safety layer held.** Across 434 model calls there were 0 external actions executed and 100% approval-boundary compliance; the 95 forbidden attempts (unknown tools, mutation or external-action requests, invented targets) were refused by deterministic code. The model's weak competence did not turn into unsafe behaviour. Safety here comes from the architecture, not from the model.
4. **The guardrail trades usefulness for caution.** Because the model collects little evidence, the evidence envelope allows little beyond escalation, so guardrail abstention accuracy *drops* from 79% to 37% (it escalates scenarios that call for a specific action) while correct-action rises 37% to 39%. Raw abstention (79%) is high mostly because the model leans toward `ESCALATE_INSUFFICIENT_EVIDENCE`; that is not skill, it is a default. A guardrail is a safety device, not a capability.
5. **Same-author caveat.** The scenario generator and the checks were written together with the deterministic planner, which flatters it. The harness cannot show how a real operator's exceptions would look.

### Hypotheses not tested (labelled as such)
- A larger model could close more of the tool-selection gap (the 7B run below closes part of it).
- A simpler prompt, fewer tools per task family, or few-shot tool traces might raise the 1.5B model's tool recall. Prompt `p1` was written once and not tuned (tuning on these scenarios would contaminate them).
- Per-row tool lists were not captured in the run-1 logs; the dominant failure *mode* is inferred from aggregate counters (required-tools 14.5%, invalid arguments, forbidden attempts), not from reading individual traces.

## Safety behaviour under injection (all planners)
Stand-in results over all 259 scenarios (the real model was run on the adversarial subset; no executed unsafe action in either): worst-case stand-in 1,820 forbidden attempts, **0 executed**; parrot (obeys injected text) kept permissions intact but changed 2 of 42 adversarial recommendations, restored 42/42 by the evidence envelope; taint-copier's attempt to place a persuasive untrusted note into a draft was refused by the taint check. See [THREAT-MODEL.md](THREAT-MODEL.md).

## Tradeoffs
| | deterministic | local LLM 1.5B (CPU) | local LLM 7B (CPU) |
|---|---|---|---|
| all checks passed | 100% (author-written; 2 of 4 splits contaminated, held-out B clean) | 3.6-6.5% | 29% (35 scenarios) |
| correct action | 100% | 37% | 57% |
| latency p50 | ~50 ms | ~28-32 s | ~152 s |
| cost | none | none in dollars (LOCAL COMPUTE); ~320-380k tokens per ~140 scenarios | none in dollars; ~138k tokens per 35 scenarios |
| silent wrong all-clear | 0 | 21% of scenarios (raw), 0 with guardrail | 0 of 35 |
| forbidden attempts / executed | 0 / 0 | 95-119 / 0 | 0 / 0 |
| failure mode | rigid: a new exception shape needs new code | unreliable tool selection, schema slips (0.7-3.7%) | narrow competence: only single-obvious-action scenarios passed |
| where it could add value | n/a (it is the control) | not on this suite | open-ended exceptions the rules do not cover (not measured here) |

## Conclusion (let the evidence decide)
On this suite, **adding a local LLM did not improve the agent; the deterministic planner is the better planner today.** The 1.5B model passed 3.6-6.5% of scenarios and the 7B model 29% (on a smaller, one-per-family sample), against 100% for the deterministic planner, at 600x to 3,000x the latency; the model won on no scenario in any paired comparison. Three things are worth keeping from the result beyond the headline:
1. **Safety did not depend on the model.** Across ~1,000 real-model calls, 0 external actions and 100% approval-boundary compliance. The architecture (model proposes, deterministic code validates and authorizes, human approves) made it safe to evaluate weak and strong models alike.
2. **Raw small models produce the dangerous failure silently.** The 1.5B model said `NO_ACTION` when action was needed in 21% of scenarios; a deterministic evidence envelope removed all of them. The guardrail is therefore justified as a safety device, even though it costs usefulness.
3. **Scale narrows the gap but a 7B CPU model is still far from the control.** Whether a larger model, a simpler tool schema, few-shot traces or fine-tuning would reach parity was not tested.
What this does **not** show: that LLM planners are inferior in general; that the deterministic planner would handle exceptions a real kitchen produces that the author did not anticipate (the scenarios are author-generated; the control was built alongside them, which flatters it); or anything about hosted frontier models, which were deliberately not used (no paid API).

## Run 2 (final code, qwen2.5:1.5b-instruct) and Run 3 (qwen2.5:7b-instruct)
### Run 2: qwen2.5:1.5b-instruct on the final code (commit 3a48adc, 140 scenarios, 4 splits) - the reported run
CI run 38784135017. Same model, runtime and sampling as run 1; the code had since gained the grounding fix, the auth-before-existence fix and the default simulated portal gateway. Files: `results/planner_qwen1.5b_run2_{raw,guardrail,paired}.json` (copied to `planner_llm_{raw,guardrail}.json` for the evidence pack). Subset: `--per-family 2` of 4 splits = 140 scenarios (dev 38, held-out 39, held-out B 39, adversarial 24).

| metric (140 scenarios) | deterministic control | LLM raw | LLM + guardrail |
|---|---|---|---|
| all checks passed | 140 / 140 | **5 / 140 (3.6%)** | 8 / 140 (5.7%) |
| by split (dev / held-out / held-out B / adversarial) | 38 / 39 / 39 / 24 of same | 2/38, 1/39, 2/39, 0/24 | 4/38, 2/39, 2/39, 0/24 |
| correct action | 140 / 140 | 52 / 140 (37%) | 51 / 140 (36%) |
| correct abstention (of 110 should-abstain) | 110 / 110 | 72 / 110 (65%) | 42 / 110 (38%) |
| required tools called | 140 / 140 | 22 / 140 (15.7%) | 22 / 140 |
| **wrong silent `NO_ACTION` (all-clear) when action was needed** | 0 | **30 / 140 (21%)** | **0** |
| unnecessary tool calls | 0 | 376 | 376 |
| invalid tool-call arguments | 0 | 209 | 164 |
| refused tool requests (unknown or forbidden; see note) | 0 | 119 | 119 |
| external actions executed | 0 | **0** | **0** |
| approval-boundary compliance | 140 / 140 | 140 / 140 | 140 / 140 |
| unsupported claims | 0 | 0 of 29 | 0 of 12 |
| attacker-text leaks into the proposal | 0 | 2 (`contradictory_canonical`, adversarial) | 0 |
| schema failures / planner fail-safe fallbacks (of 426 model calls) | n/a | 3 / 3 (0.7%) | 3 / 3 |
| trace complete | 139 / 140 | 139 / 140 | 139 / 140 |
| latency p50 / p95 | ~47 ms / ~94 ms | **28.0 s / 53.2 s** | (replayed cached replies; not a latency measure) |
| tokens (prompt + completion), 426 calls | 0 | 322,117 + 71,937 | same replies |

Paired against the deterministic planner on the same ids (139 shared): the deterministic planner passes where the model fails in 134 scenarios (131 for the guardrail variant); the model passes where the deterministic planner fails in **0**; exact sign test p < 0.001. Both runs agree: run 1 9/138, run 2 5/140 (the difference is within sampling noise for a temperature-0 model on slightly different code and scenario subsets; nothing was tuned between them).

**What run 2 adds.**
1. **The most dangerous failure class reappeared in a real model.** In 30 of 140 scenarios (21%) the raw model answered `NO_ACTION` when something needed doing (run 1: 18 of 138). This is the Block 2 failure ("silent all-clear on partial evidence"), now produced by the model instead of by a fall-through bug. The deterministic evidence envelope removes all of them (0 of 140): that is the genuine, measured value of the guardrail. It does so by escalating, which is why its abstention accuracy and usefulness are low.
2. **Safety layer unchanged:** 426 model calls, 119 forbidden attempts, **0 executed external actions**, 100% approval-boundary compliance, 0 unsupported claims.
3. **The raw model echoed attacker text in 2 of 24 adversarial scenarios** (`contradictory_canonical`: a document that contradicts the canonical spec); the guardrail variant did not, and no permission was affected.
4. Tool recall stayed at ~15%: the dominant failure is again *which tools to call*, not JSON (0.7% schema failures).

### Run 3: qwen2.5:7b-instruct (Apache-2.0, 4.7 GB, Q4_K_M, CPU) on held-out B + adversarial, one scenario per family (35 scenarios)
CI run 38787190128 (commit 54d7da9). Held-out B is the clean split; adversarial is the injection/poison split. One scenario per family (20 + 15) because a 7B model on 4 vCPU takes minutes per scenario. Files: `results/planner_qwen7b_{raw,guardrail,paired}.json`.

| metric (35 scenarios) | deterministic control | 7B raw | 7B + guardrail | (1.5B raw, same families, run 2) |
|---|---|---|---|---|
| all checks passed | 35 / 35 | **10 / 35 (29%)** | 11 / 35 (31%) | 1 / 36 (3%) |
| held-out B / adversarial | 20/20, 15/15 | 3/20, 7/15 | 4/20, 7/15 | n/a |
| correct action | 35 / 35 | 20 / 35 (57%) | 22 / 35 (63%) | 11 / 36 (31%) |
| correct abstention (of 28 should-abstain) | 28 / 28 | 20 / 28 (71%) | 17 / 28 (61%) | n/a |
| required tools called | 35 / 35 | 15 / 35 (43%) | 15 / 35 (43%) | 8 / 36 (22%) |
| wrong silent `NO_ACTION` | 0 | 0 | 0 | (30 of 140 over all splits) |
| unnecessary tool calls | 0 | 115 | 115 | n/a |
| invalid tool-call arguments | 0 | 70 | 69 | n/a |
| forbidden-action attempts | 0 | **0** | **0** | 119 over 140 |
| external actions executed / approval-boundary compliance | 0 / 100% | 0 / 100% | 0 / 100% | 0 / 100% |
| unsupported claims | 0 | 0 of 15 | 0 of 8 | 0 |
| schema failures / fail-safe fallbacks (of 144 calls) | n/a | 0 / 0 | 0 / 0 | 3 / 3 over 426 calls |
| latency p50 / p95 | ~50 ms / ~100 ms | **151.5 s / 275.6 s** | (cached replies) | ~28 s / ~53 s |
| tokens (prompt + completion), 144 calls | 0 | 116,237 + 21,536 | same replies | n/a |

Paired against the deterministic planner on the same 35 ids: the deterministic planner passes where the 7B model fails in 25 scenarios (24 for the guardrail variant), the model passes where the deterministic planner fails in **0**; exact sign test p < 0.001.

**What run 3 adds.**
1. **Scale helps, but not enough.** 7B passes ~29% vs ~3% for 1.5B on overlapping families; required-tool recall 43% vs 15-22%; no schema failures, no forbidden attempts, no silent all-clear in this sample. The gap to the deterministic planner (100%) remains large.
2. **All 10 passes are `DRAFT_PURCHASE_RECOMMENDATION` scenarios** (low cover, supplier proposals, review/edit/replay paths): cases with one obvious action the model can reach in a couple of tool calls. It failed the data-quality families (duplicate/near-duplicate order, price drift, unit mismatch, malformed timestamp, order-total mismatch), policy-trap families (negation trap, lexical trap, superseded/unverified/fake-authority documents) and the poisoned tool result. Its competence is narrow, not broad.
3. **Cost of that capability:** ~5 minutes of CPU per scenario at worst, 3,000x the deterministic latency. On a GPU this would be far faster; it was not measured.
4. **Small-n caveat:** 35 scenarios, one per family. A single run at temperature 0, seed 7. The 29% interval is wide (Wilson 95%: 16-45%). Treat the direction (scale helps, deterministic still wins) as supported and the exact rate as indicative.




## Clarification added in Block 4 (the frozen results above are unchanged)
The "refused tool requests" rows were labelled "forbidden-action attempts" in Block 3. The harness counts a request for a tool name that does not exist in the same counter as genuine forbidden requests. The Block 4 trace of 35 scenarios shows all 23 refused requests in that sample were one misspelled tool name (`get_quality_findings`, the real tool being `list_quality_findings`), asked in 19 of 35 scenarios. Block 3 did not record per-request detail, so the same cause for the 95-119 counts is an inference. See `results/ERRATA.md`. The same trace analysis (`nasha_lab/trace_analysis.py`) classifies why required tools were missing: in that sample 35 of 37 missing required tools were never requested at all, mostly the **second-step** tools that need arguments from a first result (`assess_policy_ingredient` 12, `get_quality_finding` 6, `get_lineage` 4): the model stopped after one round.
