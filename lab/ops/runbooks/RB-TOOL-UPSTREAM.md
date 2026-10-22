# RB-TOOL-UPSTREAM: Tool upstream failure

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: TOOL_UPSTREAM_FAILURE. Alert rules: AR-03, AR-24.

## Detection
AR-03: `tool_error` code UPSTREAM_FAILURE whose message is not a database error. AR-24: tool failure rate above 5% over the last 10 runs.

## Triage
- Is the message a database error? Then the class is DATABASE_UNAVAILABLE (RB-DATABASE).
- Which tool and how often?

## Containment
Same as TOOL_TIMEOUT: failed check -> gap -> escalation. Short cover with an unconfirmed supplier escalates (FC-03).

## Recovery
Fix the upstream, then `request_more_evidence`.

## Rollback
As RB-TOOL-TIMEOUT.

## Escalation
SEV3; SEV2 if AR-24 stays firing.
