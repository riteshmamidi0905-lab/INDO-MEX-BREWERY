# RB-SCHEMA-VIOLATION: Schema violation (model reply or tool arguments)

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: MODEL_SCHEMA_VIOLATION, SCHEMA_VIOLATION_TOOL_ARGS. Alert rules: AR-05, AR-07.

## Detection
AR-07: `schema_failure` trace event (the model reply did not validate). AR-05: `tool_error` INVALID_ARGUMENTS (a call violated its input schema).

## Triage
- One or two events per run that then succeed are transient: the planner retries up to 2 times and recovers (verified, schema_violation transient variants).
- Three or more in a row end in planner_failure and an escalation. Check the prompt/tool-schema version in `run_meta`: did the version change recently?
- INVALID_ARGUMENTS from event data (for example an unknown location id) is a data problem, not a model problem: inspect the source event.

## Containment
Invalid output never becomes an action: validation rejects it and the run escalates. No operator action is required to stay safe.

## Recovery
Transient: none. Persistent: fix the cause (prompt, schema, model), then `request_more_evidence` on the pending run. Data-caused: correct the source record; the stock service cannot repair it.

## Rollback
If the rate rose after a version change, roll back to the previous registered version and re-run the gate.

## Escalation
SEV3. Raise to SEV2 if planner_failure appears on more than a few runs in a window.
