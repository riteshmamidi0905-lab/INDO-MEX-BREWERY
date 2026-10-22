# Rollback reasoning and drill procedure

**SYNTHETIC / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** There is no deployed system to roll back; this documents the decision rule and an executable drill against the synthetic lab.

## When to roll back

Roll back to the last registered version that passed the regression gate when ANY of these holds:

1. **The gate fails on the active version** (EVAL_REGRESSION, SEV2). Evidence: the gate result's `reasons` and the paired comparison against `results/ops/gate_reference.json`.
2. **A safety invariant alert fires** (SAFETY_INVARIANT_VIOLATION, SEV1): a mutation without a prior approval or an external action. Roll back immediately, stop intake, and do not resume until the frozen invariant tests pass.
3. **UNSAFE_ACTION_ATTEMPT rate rises after a version change** (forbidden, tainted or unapproved tool requests). The permission layer refuses them, but a version that asks is a worse version.
4. **MODEL_UNAVAILABLE / PLANNER_FAILURE / MODEL_SCHEMA_VIOLATION burn SLO-6 after a version change** and the cause is the version, not the runtime.
5. **A tool-schema or corpus change** (visible as a changed hash in the version id) coincides with MALFORMED_RESULT or RETRIEVAL_ABSTAIN_ANOMALY alerts.

Do **not** roll back for: a single contained fault (the controls did their job; use the runbook), latency from a degraded dependency (not version-related), or a PASS gate verdict alone being doubted without evidence (the gate is small, see below).

## What evidence to look at

* the version ids on the run records (`version_id`, prompt hash, tool-schema version, corpus hash);
* the gate result: pass-rate drop, newly failing, newly unsafe, newly leaking, adversarial regressions;
* alert and incident counts per rule before and after the change (dashboard);
* the per-run trace of a failing scenario (`python -m nasha_lab.ops trace RUN_ID`).

**Limit of the gate**: 56 scenarios and a 5-point tolerance mean a regression touching one or two ordinary scenarios can pass. The measured detection rate by severity is in `OPS-CONTROL-CENTER-EVALUATION.md`. A PASS is necessary, not sufficient; the frozen full evaluation (259 scenarios) remains the pre-merge check.

## Drill procedure (executable)

`cd lab && python -m nasha_lab.ops.versions drill` writes `results/ops/rollback_drill.json`.

1. Run the gate on the active version (`v1`). Expect PASS.
2. Switch to a safe candidate (`v2`), run the gate. Expect PASS, decision KEEP (positive control: the gate does not block good changes).
3. Return to `v1`, then switch to the bad candidate (`v3`), run the gate. Expect FAIL.
4. Evaluate alert rules on the gate result: AR-25 fires, an EVAL_REGRESSION incident opens with runbook `RB-EVAL-REGRESSION`.
5. Roll back: `Registry.activate("v1", reason)`. The switch itself is a registry write.
6. Re-run the gate. Expect PASS.
7. Run a handful of live instrumented runs on the restored version and check they complete with the expected actions.
8. Advance the incident: CONTAINED (candidate not promoted) then RESOLVED (rolled back, gate PASS).

The registry file in the repository is not modified by the drill; the drill works on an in-memory copy and records the history in the result file.

## Measured result

See `results/ops/rollback_drill.json` and the evaluation document. Times are wall-clock on the development machine; the gate run dominates (it executes 56 scenarios), the registry switch is microseconds.
