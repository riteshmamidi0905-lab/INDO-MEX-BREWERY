# Release gate: **REQUIRES_REVIEW**

HEAD `e82bc70`, evidence collected at `e82bc70`. Remote CI: **NOT_RUN** — GitHub workflows have not run remotely; no remote CI result is claimed.

| # | Gate | Result | Detail |
|---|---|---|---|
| 1 | unit_tests | **PASS** | 371 passed, 0 failed, 0 skipped (all allowed by policy) |
| 2 | integration_tests | **REVIEW** | 133 passed, 1 skipped; needs review: test_llm_planner::test_real_local_model_integration_smoke (model runtime not executed: no local model runtime and no network access to model hosts) |
| 3 | pg_reconciliation | **PASS** | PostgreSQL reconciliation + pgvector: 5/5 required tests executed and passed |
| 4 | agent_evaluation | **PASS** | 28/28 cases passed across 13 categories; 0 unauthorized actions (small synthetic set; not evidence of real-world reliability) / contradiction abstention: 2/2 required tests executed and passed |
| 5 | mutation_testing | **PASS** | 9/9 mutants killed |
| 6 | security_regression | **PASS** | security: 10/10 required tests executed and passed |
| 7 | tenant_isolation | **PASS** | tenant isolation tests: 6/6 required tests executed and passed / evaluation cross-tenant: 2 evaluation cases passed with no purchase order created |
| 8 | authorization_enforcement | **PASS** | authorization tests: 8/8 required tests executed and passed / evaluation authorization/approval: 8 evaluation cases passed with no purchase order created |
| 9 | reproducibility | **PASS** | evaluation hash identical across runs (d2821929ecbdc098); 47 warehouse tables rebuilt byte-identically |
| 10 | data_quality | **PASS** | data quality: 6/6 required tests executed and passed |
| 11 | evidence_consistency | **PASS** | evidence collected at e82bc70 (HEAD e82bc70); no code changed since; counts match junit.xml |
| 12 | portfolio_claim_validation | **PASS** | 11 portfolio claims each resolve to the evidence bundle and match exactly |

A missing or malformed required item is a FAIL, never a pass. REQUIRES_REVIEW means nothing failed but something required could not be verified in this environment.
