# RB-TOOL-TIMEOUT: Tool timeout

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: TOOL_TIMEOUT. Alert rules: AR-01.

## Detection
AR-01: `tool_error` code TIMEOUT. The tool exceeded `tool_timeout_s` (default 2 s; recorded in `run_meta`).

## Triage
- Which tool? A single tool points to that dependency; all tools point to the platform (see RB-LATENCY).
- Compare the tool's p95 latency on the dashboard with its history.
- Retries are OFF by default. If the retry layer is on, the sample shows `attempts` > 1.

## Containment
The failed check becomes a gap and the planner escalates rather than concluding no-action (FC-03 regression test). Do not approve a NO_ACTION or a draft that predates the failure.

## Recovery
Fix or restart the dependency; reviewer chooses `request_more_evidence`. Verified in fault injection (tool_timeout).

## Rollback
Not version-related unless the tool schema version changed; if so see RB-EVAL-REGRESSION.

## Escalation
SEV3. If SLO-2 burns, escalate to the dependency owner.
