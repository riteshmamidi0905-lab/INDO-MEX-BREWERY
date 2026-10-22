# Engineering case studies — DRAFT (all data synthetic; no customers, revenue or production claims)

## 1. Synthetic enterprise data platform
- **Problem:** show warehouse engineering without real data. A deterministic simulator (seeded numpy PCG64) generates 14 sites × 24 months: 2,499,173 orders, ~5.75M lines, 150k members, 450 employees (full profile; `lab/results/enterprise_full_run.json`).
- **Build:** contracts → month-partitioned incremental ingestion with fingerprints → SQL models with declared lineage → raw and warehouse quality gates → `warehouse_status` publish gate; dashboards refuse to render unless published.
- **Lessons (real defects found and fixed):** stale `dim_date`, duplicate keys crashing before the raw gate, quadratic joins until indexed.
- **Limits:** SQLite engine; a PostgreSQL variant is still to be built; calibrated profile numbers are low-confidence.

## 2. Test-count discrepancy (702 vs 708)
- **Symptom:** CI reported 702 tests, a fresh local checkout collected 708.
- **Method:** reproduced on a clean worktree of the same commit, compared module counts, read CI's install log.
- **Cause:** a module-level `importorskip` for the OpenTelemetry SDK collapsed 7 tests into 1 skip in CI (708 − 7 + 1 = 702). Those 7 tests had never run in CI.
- **Outcome / unverified:** diagnosis exact by arithmetic; the other two CI skips are unattributed because CI ran without `-rs`. Fix proposed, not applied. See `docs/master-directive/TEST-COLLECTION-DISCREPANCY.md`.

## 3. Warehouse-backed Ops AI with an authorization gate
- Read-only, fixed-SQL tools over the marts; default-deny role and site scoping; audit row for every call incl. denials; warehouse opened `mode=ro`; answers checked against independently recomputed values (14 tests passing locally).
- **Not claimed:** integration with the separate THE WEIR gateway; any LLM behaviour (the router is rule-based).
