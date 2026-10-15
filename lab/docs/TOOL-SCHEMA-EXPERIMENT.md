# Tool-schema experiment (Block 4): was poor tool recall partly an interface-design problem?

SYNTHETIC DATA / OFFLINE EVALUATION / same author. LOCAL COMPUTE - NO API CHARGE. This is a NEW experiment; it does not alter any Block 3 result (see `baseline/BASELINE-BLOCK3.json`).

## Question
In Block 3 the Qwen2.5 planners called the required evidence tools in only ~15% (1.5B) and 43% (7B) of scenarios. Was that partly the way the tools were presented to the model, rather than only model capability? This is **not** an attempt to make the LLM win; one controlled change, one model, one run, and the result is reported whatever it is. No hyper-parameter or model search follows.

## Pre-registration (written before the run)
- **Model/runtime:** the same as Block 3 run 2: `qwen2.5:1.5b-instruct`, Ollama on a GitHub-hosted 4-vCPU runner, temperature 0, seed 7, JSON-schema constrained output, same retry policy. The weakest model is used because it has the most room to show an interface effect; a null result on it does not say anything about larger models.
- **Held constant:** scenario truth and expectations, the 140 scenario ids of run 2 (`--per-family 2`, all four splits), permission policy, tool implementations, evaluation criteria and scoring code, the decision (second) call's prompt and schema, retries, round and call limits.
- **Changed (only the collect-phase presentation), `ts1` -> `ts2`:**
  1. *Scoped menu:* the model is shown only the tools relevant to the event family (inventory / data quality / policy) instead of all ten. Which tools are relevant is the same table the harness already uses to define "unnecessary" calls; the model still cannot call anything it is not shown, and anything it asks for still goes through the same permission layer.
  2. *Flat signatures:* each tool is one short line with a plain-language purpose and a **call skeleton** with `<placeholders>` for the required arguments (no scenario values are filled in).
  3. *Flat event view:* the event payload is shown as `key=value` pairs instead of compact JSON (same information).
  4. *One instruction:* "request every relevant tool in your first round; several tool_calls together are fine".
  The prompt version label changes from `p1` to `p2`; no scenario-specific hint is added.
- **Control arm (ts1):** run 2 of Block 3 (same model, seed, ids; code at commit `3a48adc`). A fresh ts1 re-run on a 35-scenario subset (held-out B + adversarial, one per family) with the new trace format checks that the control reproduces and proves the trace format.
- **Primary metric:** required-tool recall (`required_tools_ok`) over the 140 scenarios, paired by scenario id. **Secondary:** all-checks pass, correct action, correct abstention, invalid-argument calls, forbidden attempts, schema failures, wrong silent `NO_ACTION`, unnecessary tool calls, latency, tokens.
- **Decision rule:** the interface counts as "partly the problem" if primary recall improves by at least **15 percentage points** with exact paired sign-test p < 0.05. Otherwise the answer is "no meaningful interface effect on this model". Either result is published as is.
- **Not done:** no second prompt variant, no tuning on any split, no larger model, no few-shot examples.

## Results
**Run:** CI run 38803177815 (commit d69c89b), qwen2.5:1.5b-instruct Q4_K_M (Ollama model id `65ec06548149`, 986 MB), 140 scenarios, 4 splits, temperature 0, seed 7. Raw per-scenario traces: `results/traces/ts2_1.5b_140_raw.jsonl`. Summary: `results/tool_schema_result.json` (`python -m nasha_lab.tool_schema_report`). Paired on 139 shared ids (one scenario id is duplicated in the Block 3 set, see `results/ERRATA.md`).

| | ts1 (original, Block 3 run 2) | ts2 (simplified) | ts2 + evidence guardrail |
|---|---|---|---|
| required tools called (primary) | 22 / 140 (16%) | **67 / 140 (48%)** | 67 / 140 |
| passed in full | 5 / 140 | 16 / 140 (11%) | 22 / 140 (16%) |
| correct action | 52 / 140 | 74 / 140 | 86 / 140 |
| invalid tool arguments | 209 | 72 | 65 |
| refused tool requests (unknown / forbidden names) | 119 | **0** | 0 |
| wrong silent `NO_ACTION` | 30 | 0 | 0 |
| schema failures (decision step) | 3 | **37** | 37 |
| median latency | 28.0 s | 33.5 s | cached replies |

Paired (ts1 vs ts2, 139 ids, exact sign test): required tools 8 vs 52 (p < 0.001); passed in full 4 vs 15 (p = 0.019); correct action 22 vs 44 (p = 0.009).

By event family (required-tool recall, ts1 -> ts2): **data quality 0/33 -> 33/33**, **inventory 21/64 -> 33/64**, **policy 1/42 -> 0/42**; correct action: data quality 22 -> 30, inventory 8 -> 34, **policy 22 -> 10**.

**Answer: yes, partly. By the pre-registered rule (>= 15 points and p < 0.05) the poor tool recall was partly an interface-design problem for this model.** But read it with its structure:
1. **The gain is narrow and mostly mechanical.** The trace (not available in Block 3) shows the original run asked for a tool name that does not exist (`get_quality_findings`) in 19 of 35 sampled scenarios; call skeletons removed that error entirely (refused requests 119 -> 0), which is where data-quality recall went from 0 to 33 of 33. Part of inventory improved the same way.
2. **Policy scenarios did not improve and got worse in correct action (22 -> 10).** With a flat event view showing only a proposal id, the model concluded "no details provided", requested no tool and abstained; identical prompts gave identical (cached) answers across policy scenarios. A scoped menu does not make a model take a first step it has decided not to take.
3. **A new cost appeared:** schema failures in the decision step rose from 3 to 37, mostly where no evidence had been collected.
4. **The scoped menu encodes knowledge** of which tools matter per event family (the same table the harness uses). That is a legitimate interface design, and it also means part of the "gain" is the system telling the model what to look at.
5. Even the best arm (ts2 + guardrail) passes 22 of 140; the deterministic planner passes all of them. This does not change the Block 3 conclusion; it explains part of why the small model failed.

Not done (by design): no second prompt variant, no tuning, no larger model, no change to scenario truth, permissions or scoring.

