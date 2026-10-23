# Preventing Audit-Chain Corruption Under Concurrent Requests

An engineering investigation, not a benchmark. Every figure below is a recorded test result; reproduce with `python lab/tools/audit_concurrency_incident.py` (writes `lab/results/audit-concurrency/incident.json`).

## What failed
At engineering commit `cb4ae79` the full suite passed (795 passed, 1 skipped), but pytest also reported three **unhandled thread exceptions** in
`test_two_concurrent_conversions_of_the_same_lead_produce_exactly_one_opportunity`:

```
psycopg.errors.UniqueViolation: duplicate key value violates unique constraint "audit_log_pkey"
  convert_lead -> _write (Blocked) -> self._audit(..., "deny", ...) -> INSERT INTO audit_log
```

Three of the six racing requests could not write the audit row that records their refusal.

## How it was found
Not by an assertion. It was a warning in the test output of a run whose result line said "passed". The warning was investigated rather than dismissed because it touched the audit trail.

## Root cause
`_audit` extends a per-tenant hash chain: take `pg_advisory_xact_lock`, read the last `(seq, hash)`, insert `seq+1`. A transaction-scoped advisory lock lives until the **transaction** ends. On the success path that is correct: `_write` runs `_audit` inside `with self.con.transaction()`. On the refusal path (a `Blocked` rolled the write back, or `_authorize` denied) `_audit` ran on a connection in **autocommit**, where each statement is its own transaction, so the lock was released the instant the `SELECT pg_advisory_xact_lock` statement finished. The read and the insert were then unprotected, and concurrent refusals read the same chain head and inserted the same `seq`; the primary key stopped the corruption, but the loser's refusal was lost (and its request failed with a database error instead of a clean refusal).

Classification: **product defect** (not an environment issue, not flaky infrastructure). The failure itself is timing-dependent, which is why it did not appear in earlier runs.

## Why the original test missed it
The test counted outcomes: exactly one `ok` and one opportunity row. The losing threads died with `UniqueViolation` inside the worker thread, so they never appended to the result list, and the assertions on "one ok, one opportunity" still held. Pytest turned the dead threads into warnings only.

## Fix
`_audit` now runs lock, read and insert inside `with self.con.transaction():` — one transaction on the refusal path, a savepoint when already inside a write. No assertion, privilege, or release requirement was relaxed.

## Regression-test improvements (`tests/test_growth_audit_guarantee.py`)
* Worker exceptions are captured and re-raised in the caller (`run_all`); the conversion test now fails on any non-`Blocked` error, requires 1 success + 5 blocked, a valid chain, and at least 5 recorded denials.
* `test_concurrent_denials_…`: 16 concurrent refusals produce exactly 16 deny rows, unique contiguous `seq`, `prev_hash` linkage, valid chain.
* `test_mixed_allow_deny_blocked_storm_…` (5 rounds): allows, denials and a lead-conversion race together; one audit row per outcome.
* `test_a_failed_write_rolls_back_completely_…`: a write that fails after inserting its row leaves no row and exactly one deny record.
* `test_the_chain_lock_is_held_from_the_read_of_the_last_row_to_the_insert`: **deterministic**. Writer 1 is paused between reading the head and inserting; the test observes (via `pg_locks`) writer 2 waiting on the advisory lock and checks it has not read the head; then both are released and must take consecutive sequence numbers. No sleeps decide the outcome.

## Before and after (recorded)
Same test file, same selection, with the pre-fix `_audit` re-installed by `tools/legacy_audit_plugin.py` (source untouched):

| | runs | result |
|---|---|---|
| before fix | 3 | 8 failed, 2 passed in every run (including the deterministic lock test) |
| after fix | 10 | all passed |

Full suite after the fix (`a2f4581`): 795 passed, 1 skipped, 0 failed, no unhandled-thread or UniqueViolation warnings. The final suite run for the evidence bundle is recorded in `lab/results/release-gate/summary.json`.

## Remaining limitations
* One PostgreSQL instance and one process; no multi-node, failover or connection-pooler behaviour is claimed.
* The hash chain makes tampering detectable, not impossible (unchanged from the audit guarantee design).
* The legacy behaviour is reproduced by a plugin, not by the historic commit itself.
* No throughput or latency measurement was made, and none is claimed.
