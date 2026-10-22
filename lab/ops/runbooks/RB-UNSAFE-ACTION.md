# RB-UNSAFE-ACTION: Unsafe action attempt

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: UNSAFE_ACTION_ATTEMPT. Alert rules: AR-08, AR-09.

## Detection
AR-08: a tool_error with FORBIDDEN_EXTERNAL_ACTION, UNKNOWN_TOOL, TAINTED_ARGUMENT or APPROVAL_REQUIRED. AR-09: a proposed mutation was rejected by the validator.

## Triage
- Which planner/version asked? A model that requests external actions or invents record keys is the failure; the permission layer is the control that held (FC-01).
- Was the request influenced by injected text? Look for `injection_flagged` events.

## Containment
Refused and counted. External actions never execute; mutations need a signed grant bound to run, tool and exact arguments.

## Recovery
No run repair needed. Fix the planner/prompt; verify with the gate.

## Rollback
A version that makes forbidden attempts should not be promoted; roll back if already active.

## Escalation
SEV2. A SEV1 SAFETY_INVARIANT alert on the same run means a control failed: stop.
