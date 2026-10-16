# RB-APPROVAL-EXPIRED: Approval expired

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: APPROVAL_EXPIRED. Alert rules: AR-11.

## Detection
AR-11: `ops_approval_expired`: the reviewer session expired (code EXPIRED) or the review sat pending longer than the ops TTL (APPROVAL_EXPIRED, design target 900 s).

## Triage
- Session expiry: the reviewer simply needs to log in again. Stale review: the evidence may be out of date.

## Containment
Nothing executes. An expired session or stale review cannot approve.

## Recovery
Session: log in again and approve. Stale review: `OpsService.reopen(run_id)` after re-checking the evidence, or reject and re-open the event.

## Rollback
Not version-related.

## Escalation
SEV3.
