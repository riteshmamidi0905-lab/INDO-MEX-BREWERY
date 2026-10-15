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
RESULTS_PLACEHOLDER
