# RB-MALFORMED-RESULT: Malformed tool result

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: TOOL_MALFORMED_RESULT. Alert rules: AR-04.

## Detection
AR-04: `tool_error` code MALFORMED_RESULT: the tool's return value did not match its output schema.

## Triage
- Which tool? Did its implementation or schema change (tool-schema hash in the version id)?
- The untrusted supplier-portal path has its own checks (SCHEMA_MISMATCH flag); see RB-STALE-SOURCE.

## Containment
Output validation rejects the result before it can become evidence or a claim. The planner escalates.

## Recovery
Fix the tool or revert the change, then `request_more_evidence`. Verified in fault injection (malformed_tool_result).

## Rollback
If a tool-schema change caused it, roll back to the previous registered version (the version registry pins the schema hash).

## Escalation
SEV3.
