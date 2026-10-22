# Module M03: incremental, idempotent ingestion (`nasha_lab/warehouse/ingest.py`)

Status for you: NOT ASSESSED. Do the exercises unaided before reading the answers in the code.

**A. Architecture.** Source CSVs are fingerprinted per month partition (row count + checksum of one numeric column). A partition is loaded only if new or changed. Rows are written with `_partition`; the partition becomes visible to models only when `load_partitions` says `complete`, so a crash mid-load leaks nothing and a rerun deletes and reloads it. Contract violations are quarantined; structural breaks reject the file.
**Concepts.** Idempotency, watermarks vs fingerprints, atomicity at partition grain, late-arriving corrections, right-censoring is NOT involved here (see M05), SQLite transactions and WAL, `executemany`, chunked CSV reads (bounded memory).
**B. Independent exercise.** Write a loader (any language) for one CSV into SQLite that (1) records a fingerprint per month, (2) skips unchanged months, (3) reloads a changed month atomically. Test: run twice (no change), change one row, run again.
**C. Debugging challenge.** In a copy of the repo, comment out the `DELETE FROM raw_{t} WHERE _partition=?` line and inject a crash after one partition (`fail_after_partitions=1`). Predict what the duplicate-key gate reports on the rerun, then check. Explain why `load_partitions` is written last.
**D. Interview questions.** Why fingerprint instead of comparing file hashes? What does a late correction do to downstream facts here? How would this change at 100x volume (and why would you leave SQLite)?
**E. System-design tradeoffs.** Partition grain (day vs month); full refresh vs merge; append-only raw with versioning; where to quarantine; exactly-once vs at-least-once plus idempotent writes.
**F. Evidence (fill in only when you did it unaided).** Date / task / link.
