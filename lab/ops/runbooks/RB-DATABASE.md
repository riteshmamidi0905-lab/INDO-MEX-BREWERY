# RB-DATABASE: Database unavailable

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: DATABASE_UNAVAILABLE. Alert rules: AR-02, AR-13.

## Detection
AR-02: a tool failed with a database error (OperationalError/ProgrammingError). AR-13: a run crashed with a database error.

## Triage
- Mid-run failure (tools fail, the run escalates) or at-start failure (the run crashes and is marked FAILED).
- Check disk, locks, file permissions of the SQLite file.

## Containment
Mid-run: the failed reads become gaps and the run escalates; no draft is created. Crash: the ops wrapper marks the run FAILED and records `ops_run_crashed`, so the event is not blocked.

## Recovery
Restore the database. Mid-run: `request_more_evidence`. Crash: start the event again; it is not treated as a duplicate because the failed run is FAILED. Verified (database_failure).

## Rollback
Not version-related. A schema migration failure rolls back (GAP-08 test) and leaves the store at its previous version.

## Escalation
SEV2. Page the platform owner.
