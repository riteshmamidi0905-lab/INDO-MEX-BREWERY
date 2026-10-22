# RB-SAFETY-INVARIANT: Safety invariant violation

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: SAFETY_INVARIANT_VIOLATION. Alert rules: AR-20, AR-21.

## Detection
AR-20: a mutation ran without a prior approval. AR-21: an external action was performed. These have never fired in the synthetic evaluation; the rules exist so a regression in the controls would be visible.

## Triage
- Read the trace around `tool_call permission=MUTATE_SIMULATION` and the `human_decision` event order.

## Containment
Stop the agent (pause intake). Treat every run of the affected version as untrusted.

## Recovery
Roll back to the last version that passed the gate AND re-run the full frozen evaluation; do not resume until the invariant tests pass.

## Rollback
Roll back immediately.

## Escalation
SEV1: page.
