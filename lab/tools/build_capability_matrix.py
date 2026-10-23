#!/usr/bin/env python3
"""Evidence-backed capability matrix (D-89 Milestone A). Statuses: IMPLEMENTED_TESTED, IMPLEMENTED_UNVERIFIED, DESIGNED_ONLY, BLOCKED, NOT_STARTED.
Every row names code paths and test names; the script FAILS if a cited path or test function does not exist, and a row may only claim IMPLEMENTED_TESTED if it cites at least one existing test.
    cd lab && python3 tools/build_capability_matrix.py      # writes docs/engineering/D-89-CAPABILITY-MATRIX.md and lab/portfolio/capability-matrix.json"""
import json
import re
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
T, U, D, B, N = "IMPLEMENTED_TESTED", "IMPLEMENTED_UNVERIFIED", "DESIGNED_ONLY", "BLOCKED", "NOT_STARTED"
ROWS = [  # objective, capability, status, code, tests (file::function), note/limitation
    ("1 Backend", "Governed procurement workflow (state machine, idempotent runs, recovery)", T, ["lab/nasha_lab/governed/workflow.py", "lab/nasha_lab/governed/ledger.py"], ["lab/tests/test_governed_workflow.py::test_end_to_end_inventory_discrepancy_to_audited_draft_po_with_the_network_blocked", "lab/tests/test_governed_workflow.py::test_crash_after_the_proposal_is_stored_leaves_no_order_and_resumes_cleanly"], "SQLite stores; single process."),
    ("12 APIs", "Versioned HTTP API (auth, tenant boundary, idempotency, pagination, error envelope, OpenAPI)", T, ["lab/nasha_lab/governed/api.py"], ["lab/tests/test_governed_api.py::test_full_flow_over_http_ends_in_a_draft_po_and_no_transmission", "lab/tests/test_governed_api.py::test_openapi_contract_is_stable_and_has_no_transmit_operation"], "No TLS, no HTTP-layer rate limit, in-process services."),
    ("12 APIs", "Background-job reliability / async workers", N, [], [], "The workflow is synchronous per request; a crash is recoverable (recover()), but there is no worker queue."),
    ("2 PostgreSQL", "Warehouse models on PostgreSQL, reconciled table by table", T, ["lab/nasha_lab/warehouse/pg_variant.py"], ["lab/tests/test_warehouse_pg.py::test_every_table_reconciles_to_sqlite", "lab/tests/test_warehouse_pg.py::test_d87_scenario_tables_reconcile_in_postgresql"], "Ingestion, contracts and gates are not re-implemented in PostgreSQL."),
    ("2 PostgreSQL", "Rounding-tie defect fixed with regression tests", T, ["lab/nasha_lab/warehouse/models/22_fact_other.sql"], ["lab/tests/test_warehouse_pg.py::test_yield_ratio_rounding_ties_are_identical_in_sqlite_and_postgresql"], ""),
    ("8 DB quality", "Ledger schema constraints (FK, CHECK, UNIQUE), transactions, hash-chained audit", T, ["lab/nasha_lab/governed/ledger.py"], ["lab/tests/test_governed_workflow.py::test_the_draft_state_column_cannot_hold_a_sent_status", "lab/tests/test_governed_workflow.py::test_audit_trail_is_tamper_evident"], "SQLite; no PostgreSQL ledger yet."),
    ("8 DB quality", "PostgreSQL constraints (12 PK, 9 FK, 8 CHECK), safe migration runner (pre-flight, atomic, idempotent, checksummed), index/query-plan evidence", T, ["lab/nasha_lab/warehouse/pg_hardening.py", "lab/tools/pg_benchmark.py"], ["lab/tests/test_pg_hardening.py::test_the_database_itself_rejects_violations", "lab/tests/test_pg_hardening.py::test_preflight_blocks_a_migration_when_data_would_violate_it_and_changes_nothing", "lab/tests/test_pg_hardening.py::test_a_failure_in_the_middle_of_a_migration_rolls_the_whole_migration_back"], "Scenario tables only; tables are small so timings are within noise and no speed-up is claimed (see docs/engineering/D-89-POSTGRES-HARDENING.md)."),
    ("3 Data engineering", "Contracts, incremental partitions, quality gates, publish gate, reproducible rebuild", T, ["lab/nasha_lab/warehouse/pipeline.py", "lab/nasha_lab/warehouse/gates.py", "lab/nasha_lab/warehouse/repro.py"], ["lab/tests/test_enterprise_sim.py::test_same_seed_same_bytes_different_seed_different_bytes"] , "SQLite engine; synthetic data."),
    ("3 Data engineering", "Inventory depletion, variance detection scored against injected anomalies, ingredient forecasts", T, ["lab/nasha_lab/warehouse/scenario.py"], ["lab/tests/test_scenario_d87.py::test_inventory_depletion_matches_an_independent_recomputation", "lab/tests/test_scenario_d87.py::test_variance_detector_finds_injected_anomalies_without_reading_them"], "Injected anomalies are few (11 cells); synthetic sales."),
    ("7 Analytics", "Menu economics, cost levers with quality floor, supplier sensitivity, menu engineering", T, ["lab/nasha_lab/recipes/pricing.py", "lab/nasha_lab/recipes/optimize.py"], ["lab/tests/test_recipes_d87.py::test_tandoori_lamb_levers_keep_the_original_scenario_and_respect_the_quality_floor"], "Planning assumptions and synthetic quotes, not real costs."),
    ("7 Analytics", "Full active-menu simulation from a versioned definition (6 dishes incl. provisional Tandoori Lamb Tacos; Goat Birria absent; historical scenario preserved)", T, ["lab/nasha_lab/recipes/menu.py", "food/menu/menu-definition.v2-2026-10-23.json", "lab/nasha_lab/enterprise_sim.py", "lab/nasha_lab/warehouse/scenario.py"], ["lab/tests/test_menu_d90.py::test_every_active_menu_item_flows_through_the_whole_simulation", "lab/tests/test_menu_d90.py::test_historical_scenario_is_reproducible_and_its_config_has_no_menu_key", "lab/tests/test_menu_d90.py::test_lamb_procurement_is_proposed_held_for_approval_and_ends_as_a_draft_only"], "Synthetic sales; popularity weights are parameters; the lamb recipe/costing is provisional (not cooked or tested); the five other dishes' costs are planning assumptions."),
    ("4 RAG", "Status-aware retrieval (BM25, hybrid, dense) and pgvector HNSW", T, ["lab/nasha_lab/knowledge.py", "lab/nasha_lab/embeddings.py"], ["lab/tests/test_retrieval_v2.py::test_pgvector_matches_the_exact_scan_and_uses_hnsw_cosine"], "pgvector test now runs on an embedded PostgreSQL (previously skipped)."),
    ("4 RAG", "Tenant-private retrieval (no cross-tenant results)", T, ["lab/nasha_lab/governed/tenants.py"], ["lab/tests/test_governed_workflow.py::test_memory_retrieval_approvals_and_audit_do_not_cross_tenants"], "BM25 over small synthetic documents."),
    ("5 Agents", "Evidence-grounded agent with validation gate (claims, numbers, proposal caps, injection)", T, ["lab/nasha_lab/governed/agent.py"], ["lab/tests/test_governed_workflow.py::test_a_model_that_obeys_an_injection_is_stopped_by_the_validation_gate", "lab/tests/test_governed_workflow.py::test_a_claim_with_a_number_that_is_not_in_the_cited_evidence_is_dropped"], "Rule planner; model planner verified only with scripted test doubles."),
    ("5 Agents", "LangGraph human-in-the-loop agent over the legacy inventory world", T, ["lab/nasha_lab/agent.py"], ["lab/tests/test_agent.py"], "Separate, earlier world; not wired to the warehouse scenario."),
    ("5 Agents", "Real language-model planner run", B, ["lab/nasha_lab/llm.py", "lab/nasha_lab/llm_planner.py"], ["lab/tests/test_llm_planner.py::test_real_local_model_integration_smoke"], "BLOCKED: no local model runtime and no network access to ollama.com / huggingface.co (HTTP 403). Test is skipped; status UNVERIFIED."),
    ("5 Agents", "Production AI Agent Platform integration", D, ["lab/docs/REUSE-AND-PROVENANCE.md"], [], "Separate repository; ideas and adapted code reused, no runtime integration."),
    ("6 Authorization", "THE WEIR per-role default-deny policy, held writes, single-use call-bound approvals (real gateway)", T, ["lab/nasha_lab/governed/weir_bridge.py"], ["lab/tests/test_governed_workflow.py::test_a_role_that_may_not_start_runs_is_denied_and_a_role_without_the_write_tool_is_blocked_by_the_weir", "lab/tests/test_governed_workflow.py::test_a_proposal_modified_after_approval_is_not_executed"], "Gateway lives in the separate mcp-weir repository (pinned); one gateway per principal."),
    ("7 Approvals", "Human approval: role check, maker-checker, expiry, replay prevention, scope binding", T, ["lab/nasha_lab/governed/workflow.py", "lab/nasha_lab/identity.py"], ["lab/tests/test_governed_workflow.py::test_an_expired_approval_cannot_be_resolved_or_consumed_later", "lab/tests/test_governed_workflow.py::test_replayed_approval_creates_nothing_new"], "Prototype identity (HMAC sessions); not an enterprise identity provider."),
    ("8 Multi-tenant", "Two tenants with separate stores, signing keys, approvals, audit, memory, retrieval", T, ["lab/nasha_lab/governed/tenants.py"], ["lab/tests/test_governed_workflow.py::test_tenants_have_separate_physical_stores_and_distinct_data", "lab/tests/test_governed_workflow.py::test_a_tenant_workflow_never_opens_another_tenants_files"], "NOT isolated: one process/code base, shared reference recipe files (asserted by test_recipe_source_files_are_shared_reference_data_not_isolated)."),
    ("9 Evaluation", "Ops AI evaluation harness with independent oracles", T, ["lab/nasha_lab/warehouse/ops_ai_eval.py"], ["lab/tests/test_ops_ai_eval.py"], "56 cases; deterministic tool layer; a perfect score is not evidence of real-world reliability."),
    ("9 Evaluation", "Governed-agent evaluation: 28 cases over 13 categories, independent oracles, metrics, reproducible result hash", T, ["lab/nasha_lab/governed/evaluation.py"], ["lab/tests/test_governed_evaluation.py::test_baseline_cases_pass", "lab/tests/test_governed_evaluation.py::test_reproducible"], "Small synthetic set; rule planner; scripted model doubles only. A perfect score is not evidence of real-world reliability."),
    ("9 Evaluation", "Mutation testing: 9 deliberately broken variants must be caught by the evaluation", T, ["lab/nasha_lab/governed/evaluation.py"], ["lab/tests/test_governed_evaluation.py::test_all_mutants_killed"], "Two initial survivors exposed weak cases (WEIR-layer role widening; forged cross-tenant token); both fixed. Nine mutants is a small, hand-chosen set."),
    ("9 Evaluation", "Contradictory-evidence abstention (planner escalates when sources disagree)", T, ["lab/nasha_lab/governed/agent.py"], ["lab/tests/test_governed_contradiction.py::test_planner_abstains_on_contradictory_evidence", "lab/tests/test_governed_contradiction.py::test_consistent_evidence_still_proposes"], "Detects one disagreement type (flag vs usage variance > 0.02)."),
    ("10 Observability", "Correlation ids, per-call latency, failure classes, secret redaction", T, ["lab/nasha_lab/governed/workflow.py", "lab/nasha_lab/trace.py"], ["lab/tests/test_governed_workflow.py::test_secrets_and_session_tokens_never_appear_in_traces_ledger_or_audit"], ""),
    ("10 Observability", "Incident investigation tooling (reconstruct who/what/why/side-effects from a correlation id)", T, ["lab/nasha_lab/governed/incident.py"], ["lab/tests/test_governed_incident.py"], "Reads the tenant's own trace, ledger and WEIR stores; no secrets in the report."),
    ("11 CI/CD", "Local CI workflow edits, skip report, reproducibility check", U, [".github/workflows/lab-ci.yml", "lab/Makefile"], [], "Never run on GitHub; local equivalents (make test/eval/repro) were run."),
    ("11 CI/CD", "Release-gate runner producing PASS / FAIL / REQUIRES_REVIEW over 12 gates (missing evidence never passes)", T, ["lab/tools/release_gate.py", "lab/tools/release-gate.config.json"], ["lab/tests/test_release_gate.py::test_complete_evidence_passes_all_twelve_gates", "lab/tests/test_release_gate.py::test_missing_evaluation_results_fail", "lab/tests/test_release_gate.py::test_stale_evidence_by_age_fails", "lab/tests/test_release_gate.py::test_incorrect_test_counts_fail"], "Run locally only. Remote CI: NOT RUN. Overall verdict is REQUIRES_REVIEW while the model-runtime test cannot execute."),
    ("13 Dashboards", "Menu economics / inventory / forecast / recommendation dashboard (synthetic)", T, ["lab/nasha_lab/warehouse/dashboards.py"], ["lab/tests/test_scenario_d87.py::test_dashboard_has_beer_levers_engineering_and_forecast_sections"], "AI-reliability and security dashboards not built."),
    ("14 Portfolio", "Replayable evidence export (8 executed scenarios, measured metrics, architecture graph with status)", T, ["lab/tools/export_portfolio_evidence.py", "lab/portfolio/nasha-governed-evidence.json"], ["lab/tests/test_governed_workflow.py::test_end_to_end_inventory_discrepancy_to_audited_draft_po_with_the_network_blocked"], "Consumed by the website candidate in the portfolio repository (local branch, not deployed)."),
    ("15 Career", "Interview-defense package", N, [], [], ""),
]


def test_exists(spec):
    path, _, fn = spec.partition("::")
    p = REPO / path
    if not p.exists():
        return False
    return (not fn) or re.search(rf"def {re.escape(fn)}\b", p.read_text()) is not None


def main():
    bad, out = [], []
    for obj, cap, st, code, tests, note in ROWS:
        for c in code:
            if not (REPO / c).exists():
                bad.append(("code", c))
        for t in tests:
            if not test_exists(t):
                bad.append(("test", t))
        if st == T and not tests:
            bad.append(("claim", cap))
        out.append(dict(objective=obj, capability=cap, status=st, code=code, tests=tests, note=note))
    if bad:
        print("MISSING EVIDENCE:", bad)
        sys.exit(1)
    counts = {s: sum(r["status"] == s for r in out) for s in (T, U, D, B, N)}
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()
    md = ["# D-89 capability matrix (updated at Milestone E)", "", f"Generated from `lab/tools/build_capability_matrix.py` against local commit `{commit}` (not pushed). Every cited path and test function was checked to exist. **A row says IMPLEMENTED_TESTED only if it cites at least one existing test; it does not claim the test was just re-run** — see the test report for pass counts.", "",
          "| Status | Count |", "|---|---|", *[f"| {k} | {v} |" for k, v in counts.items()], "", "| Objective | Capability | Status | Evidence (tests) | Limits |", "|---|---|---|---|---|"]
    for r in out:
        ev = "<br>".join(f"`{t.split('/')[-1]}`" for t in r["tests"]) or "—"
        md.append(f"| {r['objective']} | {r['capability']} | **{r['status']}** | {ev} | {r['note']} |")
    md += ["", "## Most important architectural gaps (highest value first)", "",
           "1. **The workflow ledger is SQLite**; PostgreSQL hardening covers the scenario tables only.",
           "2. **The real model path is unverified** (no runtime); the model planner is only exercised with scripted clients. The release gate therefore stays at REQUIRES_REVIEW.",
           "3. **Remote CI has never run**: the release gate and workflows are validated locally only.",
           "4. **Isolation is per-store, not per-process**; recipes are shared reference data.",
           "5. **Menu**: the current definition (D-90) is simulated end to end, but sales are synthetic and the lamb recipe/costing is provisional.",
           "6. **Evaluation breadth**: 28 cases and 9 mutants on synthetic data with a rule planner; contradiction detection covers one disagreement type.",
           "7. **No interview-defense package, AI-reliability or security dashboards yet**; AI-reliability/security dashboards and the interview package are being built (see D-90)."]
    (REPO / "docs/engineering").mkdir(exist_ok=True)
    (REPO / "docs/engineering/D-89-CAPABILITY-MATRIX.md").write_text("\n".join(md) + "\n")
    (LAB / "portfolio/capability-matrix.json").write_text(json.dumps(dict(commit=commit, pushed=False, counts=counts, rows=out), indent=1))
    print(counts)


if __name__ == "__main__":
    main()
