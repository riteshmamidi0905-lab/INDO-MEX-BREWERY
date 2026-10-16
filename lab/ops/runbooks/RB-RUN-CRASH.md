# RB-RUN-CRASH: Run crashed

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: RUN_CRASH. Alert rules: AR-12.

## Detection
AR-12: `ops_run_crashed`. Without the ops wrapper the stock service leaves such a run RUNNING and later restarts of the same event are ignored as duplicates (a measured finding).

## Triage
- The error type is in the event. If it is a database error see RB-DATABASE.

## Containment
Run marked FAILED; no mutation executed (mutations need a post-approval step the run never reached).

## Recovery
Fix the cause; start the event again.

## Rollback
If the crash follows a code change, roll back.

## Escalation
SEV2.
