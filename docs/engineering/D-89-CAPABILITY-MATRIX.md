# D-89 capability matrix (Milestone A)

Generated from `lab/tools/build_capability_matrix.py` against local commit `a9e803d` (not pushed). Every cited path and test function was checked to exist. **A row says IMPLEMENTED_TESTED only if it cites at least one existing test; it does not claim the test was just re-run** — see the test report for pass counts.

| Status | Count |
|---|---|
| IMPLEMENTED_TESTED | 19 |
| IMPLEMENTED_UNVERIFIED | 1 |
| DESIGNED_ONLY | 1 |
| BLOCKED | 1 |
| NOT_STARTED | 7 |

| Objective | Capability | Status | Evidence (tests) | Limits |
|---|---|---|---|---|
| 1 Backend | Governed procurement workflow (state machine, idempotent runs, recovery) | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_end_to_end_inventory_discrepancy_to_audited_draft_po_with_the_network_blocked`<br>`test_governed_workflow.py::test_crash_after_the_proposal_is_stored_leaves_no_order_and_resumes_cleanly` | SQLite stores; single process. |
| 12 APIs | Versioned HTTP API (auth, tenant boundary, idempotency, pagination, error envelope, OpenAPI) | **IMPLEMENTED_TESTED** | `test_governed_api.py::test_full_flow_over_http_ends_in_a_draft_po_and_no_transmission`<br>`test_governed_api.py::test_openapi_contract_is_stable_and_has_no_transmit_operation` | No TLS, no HTTP-layer rate limit, in-process services. |
| 12 APIs | Background-job reliability / async workers | **NOT_STARTED** | — | The workflow is synchronous per request; a crash is recoverable (recover()), but there is no worker queue. |
| 2 PostgreSQL | Warehouse models on PostgreSQL, reconciled table by table | **IMPLEMENTED_TESTED** | `test_warehouse_pg.py::test_every_table_reconciles_to_sqlite`<br>`test_warehouse_pg.py::test_d87_scenario_tables_reconcile_in_postgresql` | Ingestion, contracts and gates are not re-implemented in PostgreSQL. |
| 2 PostgreSQL | Rounding-tie defect fixed with regression tests | **IMPLEMENTED_TESTED** | `test_warehouse_pg.py::test_yield_ratio_rounding_ties_are_identical_in_sqlite_and_postgresql` |  |
| 8 DB quality | Ledger schema constraints (FK, CHECK, UNIQUE), transactions, hash-chained audit | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_the_draft_state_column_cannot_hold_a_sent_status`<br>`test_governed_workflow.py::test_audit_trail_is_tamper_evident` | SQLite; no PostgreSQL ledger yet. |
| 8 DB quality | PostgreSQL constraints/foreign keys on scenario tables, query plans, benchmarks, migration safety | **NOT_STARTED** | — | No query-plan or benchmark evidence exists; no performance claim is made. |
| 3 Data engineering | Contracts, incremental partitions, quality gates, publish gate, reproducible rebuild | **IMPLEMENTED_TESTED** | `test_enterprise_sim.py::test_same_seed_same_bytes_different_seed_different_bytes` | SQLite engine; synthetic data. |
| 3 Data engineering | Inventory depletion, variance detection scored against injected anomalies, ingredient forecasts | **IMPLEMENTED_TESTED** | `test_scenario_d87.py::test_inventory_depletion_matches_an_independent_recomputation`<br>`test_scenario_d87.py::test_variance_detector_finds_injected_anomalies_without_reading_them` | Only 3 injected anomalies; 4 of 5 active dishes have simulated sales. |
| 7 Analytics | Menu economics, cost levers with quality floor, supplier sensitivity, menu engineering | **IMPLEMENTED_TESTED** | `test_recipes_d87.py::test_tandoori_lamb_levers_keep_the_original_scenario_and_respect_the_quality_floor` | Planning assumptions and synthetic quotes, not real costs. |
| 7 Analytics | Expand menu simulation to the full current active menu (versioned current-menu definition) | **NOT_STARTED** | — | Requires a founder-approved current-menu definition; Goat Birria retired (D-88). |
| 4 RAG | Status-aware retrieval (BM25, hybrid, dense) and pgvector HNSW | **IMPLEMENTED_TESTED** | `test_retrieval_v2.py::test_pgvector_matches_the_exact_scan_and_uses_hnsw_cosine` | pgvector test now runs on an embedded PostgreSQL (previously skipped). |
| 4 RAG | Tenant-private retrieval (no cross-tenant results) | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_memory_retrieval_approvals_and_audit_do_not_cross_tenants` | BM25 over small synthetic documents. |
| 5 Agents | Evidence-grounded agent with validation gate (claims, numbers, proposal caps, injection) | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_a_model_that_obeys_an_injection_is_stopped_by_the_validation_gate`<br>`test_governed_workflow.py::test_a_claim_with_a_number_that_is_not_in_the_cited_evidence_is_dropped` | Rule planner; model planner verified only with scripted test doubles. |
| 5 Agents | LangGraph human-in-the-loop agent over the legacy inventory world | **IMPLEMENTED_TESTED** | `test_agent.py` | Separate, earlier world; not wired to the warehouse scenario. |
| 5 Agents | Real language-model planner run | **BLOCKED** | `test_llm_planner.py::test_real_local_model_integration_smoke` | BLOCKED: no local model runtime and no network access to ollama.com / huggingface.co (HTTP 403). Test is skipped; status UNVERIFIED. |
| 5 Agents | Production AI Agent Platform integration | **DESIGNED_ONLY** | — | Separate repository; ideas and adapted code reused, no runtime integration. |
| 6 Authorization | THE WEIR per-role default-deny policy, held writes, single-use call-bound approvals (real gateway) | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_a_role_that_may_not_start_runs_is_denied_and_a_role_without_the_write_tool_is_blocked_by_the_weir`<br>`test_governed_workflow.py::test_a_proposal_modified_after_approval_is_not_executed` | Gateway lives in the separate mcp-weir repository (pinned); one gateway per principal. |
| 7 Approvals | Human approval: role check, maker-checker, expiry, replay prevention, scope binding | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_an_expired_approval_cannot_be_resolved_or_consumed_later`<br>`test_governed_workflow.py::test_replayed_approval_creates_nothing_new` | Prototype identity (HMAC sessions); not an enterprise identity provider. |
| 8 Multi-tenant | Two tenants with separate stores, signing keys, approvals, audit, memory, retrieval | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_tenants_have_separate_physical_stores_and_distinct_data`<br>`test_governed_workflow.py::test_a_tenant_workflow_never_opens_another_tenants_files` | NOT isolated: one process/code base, shared reference recipe files (asserted by test_recipe_source_files_are_shared_reference_data_not_isolated). |
| 9 Evaluation | Ops AI evaluation harness with independent oracles | **IMPLEMENTED_TESTED** | `test_ops_ai_eval.py` | 56 cases; deterministic tool layer; a perfect score is not evidence of real-world reliability. |
| 9 Evaluation | Governed-agent evaluation: contradictory evidence, hallucination, mutation tests, unsafe-proposal and approval-bypass cases, metric tracking | **NOT_STARTED** | — | The 59 workflow tests are regression tests, not a scored evaluation with mutation testing. |
| 10 Observability | Correlation ids, per-call latency, failure classes, secret redaction | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_secrets_and_session_tokens_never_appear_in_traces_ledger_or_audit` |  |
| 10 Observability | Incident investigation tooling (reconstruct who/what/why/side-effects from a correlation id) | **NOT_STARTED** | — | Data exists in traces/ledger/WEIR audit; no investigator tool or report yet. |
| 11 CI/CD | Local CI workflow edits, skip report, reproducibility check | **IMPLEMENTED_UNVERIFIED** | — | Never run on GitHub; local equivalents (make test/eval/repro) were run. |
| 11 CI/CD | Release-gate runner producing PASS / FAIL / REQUIRES_REVIEW | **NOT_STARTED** | — |  |
| 13 Dashboards | Menu economics / inventory / forecast / recommendation dashboard (synthetic) | **IMPLEMENTED_TESTED** | `test_scenario_d87.py::test_dashboard_has_beer_levers_engineering_and_forecast_sections` | AI-reliability and security dashboards not built. |
| 14 Portfolio | Replayable evidence export (8 executed scenarios, measured metrics, architecture graph with status) | **IMPLEMENTED_TESTED** | `test_governed_workflow.py::test_end_to_end_inventory_discrepancy_to_audited_draft_po_with_the_network_blocked` | Consumed by the website candidate in the portfolio repository (local branch, not deployed). |
| 15 Career | Interview-defense package | **NOT_STARTED** | — |  |

## Most important architectural gaps (highest value first)

1. **No scored evaluation of the governed agent** (independent oracles, mutation tests proving the evaluation fails when behaviour is wrong, tracked metrics). Today's evidence is regression tests plus a small Ops AI evaluation.
2. **No incident-investigation tool** over the correlation-id data that already exists.
3. **No release-gate runner**: PASS / FAIL / REQUIRES_REVIEW must be computed, and a missing required test must not count as a pass.
4. **PostgreSQL stops at analytics.** The workflow ledger is SQLite; no PostgreSQL constraints, query plans or benchmarks exist for the scenario tables.
5. **The real model path is unverified** (no runtime); the model planner is only exercised with scripted clients.
6. **Isolation is per-store, not per-process**; recipes are shared reference data.
7. **The simulation covers 4 of the 5 active dishes**; the current-menu definition after the Goat Birria retirement needs a founder decision.
