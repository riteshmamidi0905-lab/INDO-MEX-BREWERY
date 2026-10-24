# Evidence determinism: what varies, why, and what was fixed

Measured on 2026-10-24 with `lab/tools/evidence_diff.py` over four independent exports of the Milestone 3 (`nasha-governed-evidence.json`) and Milestone 3/4/5 (`growth-os-evidence.json`) evidence, each from a freshly built PostgreSQL environment. Machine-readable results: `lab/results/evidence-determinism/report.json`.

## Classification of every difference found (before the fix, engineering `f474153`)

| # | Class | What differed | Where | Verdict |
|---|---|---|---|---|
| 1 | Random identifier | supplier / run / approval / correlation / project ids (13 fields in the growth evidence, 52 in the governed evidence) | operational records, traces | no semantic meaning; kept in operational records |
| 2 | Timestamp / environment | event times, approval expiry (epoch), measured tool latencies, export duration, git commit, server version (40 and ~122 fields) | traces, `measured`, `generated_*` | truthful execution metadata; must vary |
| 3 | Provenance | `call_hash` and `proposal_hash` (8 fields): hashes over tool arguments or proposals that contain generated supplier ids | traces | truthful and id-bound; THE WEIR binds an approval to the proposal hash, so it is not rewritten |
| 4 | Ordering instability | the supplier list of a recommendation sorted by the generated supplier id (1 field); quote-comparison ties sorted by id | `launch.recommendation.suppliers`, `quote_matrix` | **defect**: order followed random ids |
| 5 | Business-result instability | the agent's retrieved evidence passages (11, 12 or 13 across databases holding identical documents), its cited claims (8 claims, different wording and suppliers) and so the computed uncertainty text (3 vs 4 lines) | `launch.trace`, `launch.walkthrough.agent_claims`, `m4.journey` | **defect**: see root cause A |
| 6 | Unexplained | none remained after classifying `call_hash` as provenance | | |

The recommendation's totals, its per-supplier costs and every financial figure were identical in all runs; what varied was ordering and the research text.

## Root causes
* **A. Approximate retrieval.** The Production AI Agent Platform ranks documents with a pgvector HNSW index (its graph is built with random level draws) and a GIN full-text index, and breaks score ties by index order. Over a corpus of a few dozen short records, equal-scoring passages straddle the top-k cut-off. Isolated experiment, same 12 supplier documents, independent agent databases: 4 databases gave 12, 11, 13 and 12 passages and different claims; with exact scans, 6 of 6 were identical.
* **B. Id-first tie-breaks.** `procurement.compare` and `supplier_intel.quote_matrix` broke cost/lead-time ties by supplier id, and per-supplier totals were sorted by id. Ids are random per database.
* **C. Evidence mixes outcomes with execution identity.** One file held both, so two correct executions could never be compared byte for byte.

## Corrections
1. `agent_research._tenant_dsn` opens the agent database with `enable_indexscan/bitmapscan/indexonlyscan=off`, so the same query is answered by an exact scan; ties then follow the deterministic ingestion order (documents are ingested in directory order: verification status, then name). An exact scan is the right trade at this corpus size; a large corpus would need the index back with a canonical re-ranking step.
2. Tie-break order is now cost, lead time, **supplier name**, then id, in `procurement.compare`, the supplier-total ordering and `supplier_intel.quote_matrix`.
3. `nasha_lab/growth/evidence_canon.py` defines a canonical view by three rules: identifiers in strings become `<id>`; the keys in `VOLATILE_KEYS` (each with its reason: times, durations, versions, commit, id-derived hashes) are removed; nothing is sorted or rounded. Both evidence files record `canonical.sha256`. `business_digest(plan)` hashes what is bought, from whom (by name), in what quantity and at what cost; it is recorded next to the operational proposal hash.
4. Operational records are unchanged: random ids, times and the id-bound proposal hash are still written, and still differ between executions.

## Result (four fresh exports after the fix)
* canonical sha256, growth evidence: `206dc3440c8d…` in all four; governed evidence: `8fc738f202cc…` in all four; business digest of the recommendation: `cb75e41b4672b3da` in all four.
* Raw differences remaining: 61 (growth) and 176 (governed): only random identifiers (13 / 52), timestamps and measurements, and id-bound hashes (8). No ordering, business-result or unexplained differences.
* Tests: `lab/tests/test_growth_reproducibility.py` (identical business inputs in two independently initialised databases give identical classification, financials, recommendation digest, stage sequence and audited history; run ids and the proposal hash legitimately differ; four independent agent databases give identical cited evidence; negative tests: five kinds of introduced instability change the canonical hash, and an id-first tie-break is detected by the digest check).
