# RB-EVAL-REGRESSION: Evaluation regression

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: EVAL_REGRESSION. Alert rules: AR-25.

## Detection
AR-25: the regression gate returned FAIL against the frozen reference (`results/ops/gate_reference.json`).

## Triage
- Read the gate reasons: pass-rate drop, newly unsafe scenarios, newly leaking scenarios, newly failing adversarial scenarios.
- Which version differs from the reference? Prompt hash, tool-schema version, corpus hash, planner id.
- The gate suite is small (56 scenarios): a failure that touches one scenario can pass the gate (measured misses at low severity). Treat PASS as necessary, not sufficient.

## Containment
Do not promote the candidate. If it is already active, treat as SEV2 and roll back.

## Recovery
Roll back (`Registry.activate(previous)`), re-run the gate until PASS, then fix the candidate offline.

## Rollback
Drill procedure (also in OPS-ROLLBACK.md): switch to the candidate, run the gate, on FAIL activate the previous version, re-run the gate, run a few live instrumented runs. Last drill: results/ops/rollback_drill.json.

## Escalation
SEV2.
