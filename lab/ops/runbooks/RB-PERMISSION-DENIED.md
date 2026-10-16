# RB-PERMISSION-DENIED: Reviewer permission denied

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: PERMISSION_DENIED. Alert rules: AR-10.

## Detection
AR-10: `ops_approval_denied` trace event (role not permitted, bad credentials or token).

## Triage
- Which role tried what? Dietary-policy flags on supplier proposals need FOUNDER; flags on orders need QUALITY_LEAD or FOUNDER.
- Repeated denials from one reviewer id may be a mistake or probing.

## Containment
No grant is minted, nothing executes, the run stays awaiting a permitted reviewer. Verified: the database is unchanged after a denied approval.

## Recovery
A permitted reviewer opens the run and approves; the grant is bound to the exact arguments.

## Rollback
Not version-related.

## Escalation
SEV3. Many denials in a short window: SEV2 security review (no rate limiting on login exists beyond the API limiter).
