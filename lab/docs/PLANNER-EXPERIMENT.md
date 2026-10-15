# Planner experiment: does adding a local LLM improve the NASHA operations agent?

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** One author wrote the system, the scenarios and the checks. NASHA is a founder concept: no restaurant, customer, supplier or sale exists. Cost: **LOCAL COMPUTE - NO API CHARGE** (free GitHub-hosted CPU runners, Ollama, open-weight models; no paid API, no key).

## Question
The Block 2 agent uses a deterministic planner. Does replacing it with a language model improve task completion, abstention, tool use or safety, enough to justify the extra complexity, latency and risk? The hypothesis that it does was **not assumed**; the deterministic planner stays as the control.

## Method
- **One interface, two planners.** `Planner.collect(state, call, trace)` and `Planner.decide(state, trace)`. `DeterministicPlanner` (control, the Block 2 logic) and `LLMPlanner` run on the *same* LangGraph state, tool registry, permission classes, signed human approval, trace store and evaluation harness. The model only *proposes*: READ/ANALYZE tool calls and a structured decision (JSON validated against a pydantic schema, bounded retries, no chain-of-thought stored). Deterministic code validates, authorizes, executes and traces. The model is not the permission system.
- **Variants.** *Raw LLM*: the model's validated decision is used as is (inside the permission layer). *LLM + guardrail*: a deterministic **evidence envelope** (the set of actions the collected tool evidence permits) overrides any less-conservative model action and traces `guardrail_override`. The guardrail variant is scored on the **same cached model replies** as the raw variant, so the two differ only in the guardrail, not in sampling noise.
- **Model/runtime.** Ollama on a GitHub-hosted `ubuntu-latest` runner (4 vCPU, CPU only): `qwen2.5:1.5b-instruct` (Apache-2.0, 986 MB, Q4_K_M), temperature 0, seed 7, JSON-schema constrained decoding (`format`), ~32 tok/s. A second, larger run uses `qwen2.5:7b-instruct` (Apache-2.0, 4.7 GB) on the two cleanest splits. The authoring sandbox cannot download models (Hugging Face and ollama.com blocked), so every real-model number comes from CI logs. See [LLM-RUNTIME.md](LLM-RUNTIME.md).
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
| forbidden-action attempts (all refused) | 0 | 95 | 95 |
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
- A larger model could close part of the tool-selection gap (partly addressed by the 7B run below).
- A simpler prompt, fewer tools per task family, or few-shot tool traces might raise the 1.5B model's tool recall. Prompt `p1` was written once and not tuned (tuning on these scenarios would contaminate them).
- Per-row tool lists were not captured in the run-1 logs; the dominant failure *mode* is inferred from aggregate counters (required-tools 14.5%, invalid arguments, forbidden attempts), not from reading individual traces.

## Safety behaviour under injection (all planners)
Stand-in results over all 259 scenarios (the real model was run on the adversarial subset; no executed unsafe action in either): worst-case stand-in 1,820 forbidden attempts, **0 executed**; parrot (obeys injected text) kept permissions intact but changed 2 of 42 adversarial recommendations, restored 42/42 by the evidence envelope; taint-copier's attempt to place a persuasive untrusted note into a draft was refused by the taint check. See [THREAT-MODEL.md](THREAT-MODEL.md).

## Tradeoffs
| | deterministic | local LLM (1.5B, CPU) |
|---|---|---|
| quality on this suite | 100% (author-written, contaminated for 2 of 4 splits) | 6.5% all-checks, 37% correct action |
| latency | ~50 ms | ~32 s p50 |
| cost | none | none in dollars; ~380k tokens per 138 scenarios on a 4-vCPU runner |
| failure mode | rigid: a new exception shape needs new code | unreliable tool selection; needs deterministic envelope and validation |
| where it could add value | n/a (it is the control) | open-ended exceptions the rules do not cover (not measured here) |

## Conclusion (let the evidence decide)
On this suite, **adding a 1.5B local LLM did not improve the agent; it made task completion much worse and latency much higher, and the deterministic planner is the better planner today.** The value of the experiment is the harness: the same permissions, approval and trace layer made the LLM safe to evaluate, and the measurements are reproducible. What this does **not** show: that LLM planners are inferior in general, that a stronger model would not win, or that the deterministic planner would do well on exceptions a real kitchen produces. See the 7B and final-code results below for the effect of scale.

## Run 2 (final code, qwen2.5:1.5b-instruct) and Run 3 (qwen2.5:7b-instruct)
RUN2_PLACEHOLDER
