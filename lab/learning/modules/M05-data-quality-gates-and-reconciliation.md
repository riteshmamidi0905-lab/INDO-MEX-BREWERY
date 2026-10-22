# Module M05: data quality gates and reconciliation (`warehouse/gates.py`, `contracts.py`)

Status for you: NOT ASSESSED.

**A. Architecture.** Contracts at the door; a raw gate (duplicate keys, referential integrity, quarantine rate) before any model runs; a warehouse gate that recomputes totals from the source files with pandas and compares them with the warehouse by month and by month x location; blocking vs warning severities; a `published` status that dashboards and analytics refuse to run without.
**Concepts.** Completeness, uniqueness, validity, referential integrity, reconciliation (control totals), independent recomputation, blocking gates vs warnings, false confidence from checks that share code with the pipeline.
**B. Independent exercise.** Write three reconciliation checks between a source CSV and a table built from it, and make each fail with a deliberate fault.
**C. Debugging challenge.** In a copy, change one order's `subtotal_cents` in the source by +100. Predict which gates fail and which pass (hint: `total == subtotal - discount` is a row rule; reconciliation compares sums). Run it. The repo's test `test_late_correction_reloads_only_the_changed_partition` does this: explain what it proves.
**D. Interview questions.** Why recompute from source rather than from the raw table? What is a good quarantine-rate threshold and who decides? How do you avoid alert fatigue from warnings?
**E. Tradeoffs.** Fail the run vs quarantine rows; gate placement; cost of full reconciliation at 100x volume (sampling, partition checksums).
**F. Evidence.** Date / task / link.
