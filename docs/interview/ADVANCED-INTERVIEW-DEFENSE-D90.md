# Advanced technical interview-defense package (D-90)

**Scope and honesty.** This covers one independent engineering project: the synthetic NASHA Hospitality AI Lab (a *concept* restaurant-and-brewery with no customers, no sales and no operations), plus THE WEIR (a separate MCP security-gateway repository I built). It describes what I built and tested. It does **not** describe employment experience, production systems, real users or real incidents, and none should be implied from it. Every code reference below is a repository path (optionally `::symbol`) that `lab/tests/test_interview_package.py` checks exists. Numbers cite the recorded evidence bundle (`lab/results/release-gate/`), not memory.

**Things I should say plainly in any interview:** all data is synthetic; the real language-model path has never executed here (no runtime), so the release gate verdict is `REQUIRES_REVIEW`; remote CI has never run; tenants share one process and code; the Production AI Agent Platform is a separate repository and is **not** integrated into NASHA (ideas and adapted code only).

---

## 1. Python backend architecture
**Question.** Walk me through the backend of the governed workflow. How is it structured and why?
**Expected explanation.** A small, layered Python package (`nasha_lab/governed`). `workflow.GovernedProcurement` is the orchestrator and state machine (STARTED → EVIDENCE_COLLECTED → PROPOSED → AWAITING_APPROVAL → APPROVED → EXECUTED, plus ABSTAINED / BLOCKED / REJECTED / FAILED). It owns no business logic of its own: evidence collection and the planner live in `agent.py`, policy and the write tool in `weir_bridge.py`, persistence in `ledger.py`, per-tenant wiring in `tenants.py`, HTTP in `api.py`, forensics in `incident.py`. One correlation id per run ties trace, ledger, approval store and audit together. Failures are classified (a closed set), never swallowed, and every refusal is audited. Pydantic models define the agent output contract; the HTTP layer is FastAPI with one error envelope and a request id.
**Repository evidence.** 59 workflow tests (`test_governed_workflow.py`), 6 API tests, incident tests; the full suite and gate results are in `lab/results/release-gate/summary.json`.
**Code references.** `lab/nasha_lab/governed/workflow.py::GovernedProcurement`, `lab/nasha_lab/governed/agent.py::validate_output`, `lab/nasha_lab/governed/ledger.py::Ledger`, `lab/nasha_lab/governed/api.py::create_governed_app`, `lab/nasha_lab/governed/tenants.py::provision`.
**Follow-ups.** Why a state machine rather than a workflow engine? How would you make it asynchronous? How do you test the orchestrator without the network? (Tests block sockets; the package has a test proving no module imports a network client.)
**Tradeoffs and limits.** Synchronous per request, SQLite stores, single process. A crash is recoverable (`recover`) but there is no worker queue. I would move to a queue plus PostgreSQL for a real deployment; I have not built that.

## 2. PostgreSQL
**Question.** What did you do with PostgreSQL, and how do you know it is correct?
**Expected explanation.** The analytics warehouse is built in SQLite and the same models are transpiled (sqlglot) to PostgreSQL and **reconciled table by table** (row counts and numeric sums). A real defect surfaced: `fact_brew_batch.yield_ratio` differed by rounding ties (binary float versus decimal); I fixed it by rounding in exact integer tenths and added regression tests, without loosening the tolerance. For the scenario tables I added a hardening layer: 12 primary keys, 9 foreign keys, 8 CHECK constraints and 3 indexes through a **migration runner** that pre-flights the data (counts violators and refuses), applies each migration in one transaction, adds FKs `NOT VALID` then `VALIDATE`s, and checksums applied migrations so re-runs are no-ops and edited migrations are detected.
**Repository evidence.** `test_warehouse_pg.py` (reconciliation, rounding ties), `test_pg_hardening.py` (13 tests: violations rejected by the database, pre-flight blocks, atomic rollback, idempotent re-run, plan changes), `docs/engineering/D-89-POSTGRES-HARDENING.md`.
**Code references.** `lab/nasha_lab/warehouse/pg_variant.py::reconcile`, `lab/nasha_lab/warehouse/pg_hardening.py::migrate`, `lab/nasha_lab/warehouse/pg_hardening.py::statements`, `lab/tools/pg_benchmark.py`.
**Follow-ups.** Why `NOT VALID` then `VALIDATE`? How do you roll back? What would you index and how do you prove it helps?
**Tradeoffs and limits.** The tables are small, so timings are sub-millisecond either way; I claim no speed-up. The evidence is a plan change (sequential scan to index scan) and that bad data is rejected. The governed ledger itself is SQLite, not PostgreSQL. Rollback is "the transaction did not commit", not a down-migration.

## 3. Data modeling
**Question.** How is the data modeled, and how do you keep derived tables honest?
**Expected explanation.** A star schema: `dim_*` (date, location, product, employee, member), `fact_*` (order, order line, returns, waste, quality, brew batch, inventory), `mart_*`. Scenario tables (`scn_*`) are a derived layer built from the published warehouse plus versioned configuration (price config, menu definition, recipes, supplier quotes). The raw historical tables are never modified (a test compares them byte-for-byte). Money is stored as integer cents; serving sizes are stored exactly from fluid ounces. A versioned menu definition decides which dishes are on the concept menu.
**Repository evidence.** `test_scenario_d87.py::test_historical_tables_are_preserved_byte_for_byte`, `test_menu_d90.py` (every active dish flows end to end; historical scenario reproducible).
**Code references.** `lab/nasha_lab/warehouse/scenario.py::build`, `lab/nasha_lab/recipes/menu.py::load`, `lab/nasha_lab/recipes/pricing.py::load_config`, `food/menu/menu-definition.v2-2026-10-23.json`.
**Follow-ups.** Why restate rather than overwrite? How do you handle a changed menu? How do you stop a retired dish creeping back?
**Tradeoffs and limits.** Synthetic sales; popularity weights are parameters, not demand. A "current" menu is a different data set from the historical one (different catalogue, so different random draws): they are comparable by method, not by number.

## 4. Data engineering
**Question.** How does data enter the warehouse safely?
**Expected explanation.** Source contracts (schema, types, ranges) per table; month-partition incremental loads; a raw gate and a warehouse gate (quality checks recorded with severity); a **publish gate** (nothing is published unless blocking gates pass; contract violations are quarantined; duplicates block publication); reconciliation of warehouse totals to source totals; lineage; crash-mid-load recovery; and a reproducibility check that rebuilds from scratch twice and compares every table hash.
**Repository evidence.** `test_warehouse.py` (full load, rerun is a no-op, incremental equals one-shot, crash recovery, late correction reloads only one partition, contract violations, tamper detection); the gate's reproducibility artifact (47 tables identical).
**Code references.** `lab/nasha_lab/warehouse/pipeline.py::run`, `lab/nasha_lab/warehouse/contracts.py::check_chunk`, `lab/nasha_lab/warehouse/gates.py::publish_status`, `lab/nasha_lab/warehouse/repro.py::table_hashes`.
**Follow-ups.** What is idempotency here? How do you handle a late-arriving correction? What would break at 100x volume?
**Tradeoffs and limits.** SQLite engine; ingestion and gates are not re-implemented in PostgreSQL. Small volumes.

## 5. AI agents
**Question.** How does the agent decide, and how do you stop it doing something wrong?
**Expected explanation.** The agent never acts. It collects **evidence** through default-deny tools (every item labelled trusted or untrusted, instruction-like text flagged), then a planner proposes structured output (Pydantic, `extra=forbid`). A **validation gate** then requires every claim to cite existing, usable evidence, every number to match the cited evidence, and the proposal to match the trusted recommendation within caps (quantity ≤ 2× recommendation, order ≤ $2,000); otherwise claims are dropped or the agent abstains after bounded retries. Disagreeing sources produce an escalation, not a purchase. The planner here is rule-based; a model planner exists and is exercised only with scripted clients.
**Repository evidence.** Hallucination, unsafe-proposal, malformed-output, injection and contradiction tests; 28 evaluation cases across 13 categories (`eval.json`).
**Code references.** `lab/nasha_lab/governed/agent.py::collect_evidence`, `lab/nasha_lab/governed/agent.py::RulePlanner`, `lab/nasha_lab/governed/agent.py::ModelPlanner`, `lab/nasha_lab/governed/agent.py::validate_output`.
**Follow-ups.** What if the model lies convincingly? What does the gate not catch? Why not let the model call the write tool?
**Tradeoffs and limits.** A real model has never run here. The gate checks grounding and bounds, not whether a purchase is a good idea. The contradiction check detects one disagreement type.

## 6. RAG
**Question.** What retrieval did you build and how is it evaluated?
**Expected explanation.** A status-aware knowledge base over the repository's own documents (decision register, amendments, claims): BM25, a hashing-dense retriever, LSA, hybrid fusion, an answerability gate loaded from versioned JSON, and a pgvector HNSW index checked against an exact scan. Retrieval respects document status (superseded vs current) and tenants get private document stores. The evaluation questions are generated, split by source document (not by question) to avoid leakage, with labels from corpus metadata rather than circular model output.
**Repository evidence.** `test_retrieval_v2.py` (determinism, 13 categories, document-level splits, non-circular labels, gate trade-off, pgvector matches exact scan and uses HNSW cosine; it runs on an embedded PostgreSQL).
**Code references.** `lab/nasha_lab/knowledge.py::KnowledgeBase`, `lab/nasha_lab/knowledge.py::BM25`, `lab/nasha_lab/embeddings.py::PgVectorIndex`, `lab/nasha_lab/answerability.py`.
**Follow-ups.** How do you evaluate retrieval honestly? Hybrid vs dense? How do you avoid train/test leakage?
**Tradeoffs and limits.** Small synthetic corpora; no hosted embedding model ran; retrieval feeds the agent only as labelled evidence, not as an authority.

## 7. MCP
**Question.** Where does MCP appear, and what are the trust boundaries?
**Expected explanation.** Two places. (1) An MCP server exposing a deliberately small read/analyze/draft tool surface with no SQL, no filesystem, no shell and no mutation. (2) THE WEIR, my separate MCP gateway repository, which sits between an agent and upstream MCP servers and enforces policy. NASHA imports the real gateway (pinned) and uses it for both read tools and the procurement write tool. An **untrusted MCP server** simulator injects failures (malformed, extra fields, injection, stale, wrong metadata, timeout, oversize, persuasive) to test classification and taint tracking.
**Repository evidence.** `test_api_mcp.py` (allowlisted tools only, structured errors, draft tool creates no order), `test_trust.py` (every failure mode classified, taint blocks untrusted values), `test_governed_workflow.py` (gateway tests).
**Code references.** `lab/nasha_lab/mcp_server.py`, `lab/nasha_lab/untrusted_mcp.py`, `lab/nasha_lab/trust.py`, `lab/nasha_lab/governed/weir_bridge.py::make_upstreams`.
**Follow-ups.** Why a gateway and not a client library? What does "untrusted integrity" mean for a tool result? How do you handle a tool that lies?
**Tradeoffs and limits.** The gateway lives in a separate repository (pinned commit). One gateway per principal. No real remote MCP server was contacted.

## 8. Tool calling
**Question.** How are tools defined, validated and called?
**Expected explanation.** One typed registry with permission classes (READ, ANALYZE, DRAFT, MUTATE); arguments validated against typed schemas; output validated; timeouts; every call traced. The Ops AI tools are fixed-SQL read tools with role and site gates and an audit row per call; table and column names are never taken from input (an adversarial test passes SQL in an argument and is rejected). The governed workflow classifies a tool call's failure as timeout, bad response, error or denied, and never assumes success after a lost response: it **reconciles against the ledger**.
**Repository evidence.** Timeout, invalid-response, lost-response and database-failure tests (listed on the reliability dashboard).
**Code references.** `lab/nasha_lab/tools.py`, `lab/nasha_lab/warehouse/ops_ai.py::OpsAI`, `lab/nasha_lab/governed/workflow.py::GovernedProcurement._call`.
**Follow-ups.** How do you make a write tool idempotent? What do you do with a timed-out write?
**Tradeoffs and limits.** Tool latencies are in-process; real network tools would add failure modes I have not exercised.

## 9. Authorization
**Question.** Explain the authorization model and what stops privilege escalation.
**Expected explanation.** Layers, each sufficient: (1) identity (HMAC-signed sessions, per-tenant secret, expiry); (2) role check before any tool runs; (3) a per-role default-deny policy in THE WEIR (a quality lead's policy does not contain the write tool, so the call is blocked before anything runs); (4) human approval for the write; (5) the procurement upstream re-validates against the ledger and warehouse and refuses a write that did not come through the approval path; (6) the schema cannot represent a sent order. A regression test found that `est_cost_usd` was not bound into the approved call; it is now bound and re-checked.
**Repository evidence.** Authorization, scope-tamper (every field), no-bypass tests; evaluation categories `authorization_failure`, `approval_bypass`; mutants that remove each control are caught.
**Code references.** `lab/nasha_lab/identity.py::Authority`, `lab/nasha_lab/governed/weir_bridge.py::policy_for`, `lab/nasha_lab/governed/weir_bridge.py::ProcurementUpstream`, `lab/nasha_lab/governed/ledger.py::Ledger`.
**Follow-ups.** Why defence in depth? What is the confused-deputy risk here? How would you add per-resource ABAC?
**Tradeoffs and limits.** Prototype identity, not an enterprise IdP. No TLS, no HTTP-layer rate limiting in the API (an in-workflow limiter exists).

## 10. THE WEIR
**Question.** What is THE WEIR and what does it guarantee?
**Expected explanation.** A policy gateway for MCP tool calls: default deny, per-tool effect classes (read / write), egress denied, writes held for approval, results labelled with confidentiality and integrity. Approvals are bound to the session and the call hash, expire (injectable clock in tests), and are consumed once; creation is idempotent. It records a hash-chained audit. It is the real library imported from a separate repository, pinned by commit in CI.
**Repository evidence.** `test_ops_ai_weir.py` (both layers), governed tests (hold, approve, expire, replay, tamper, unknown/egress tools blocked before any upstream).
**Code references.** `lab/nasha_lab/governed/weir_bridge.py::policy_for`, `lab/nasha_lab/warehouse/ops_ai_weir.py`, `lab/tests/test_governed_workflow.py::test_unknown_and_egress_tools_are_blocked_by_the_weir_before_any_upstream`.
**Follow-ups.** What does it not protect against? Where is the trust root? How is the audit chain verified?
**Tradeoffs and limits.** Separate repository; a gateway cannot judge whether a legitimate approved action is wise; it enforces policy it is given.

## 11. Multi-tenant security
**Question.** How are tenants isolated, and what is not?
**Expected explanation.** Two synthetic tenants with separate warehouse, ledger, approval store, trace store, memory, private documents and **signing secret** (a token from another tenant fails signature verification; a forged token signed with another tenant's key is rejected). Unknown tenants return 404 so callers cannot probe which tenants exist. **Not isolated:** one process and code base, and shared reference recipe files (a test asserts this explicitly so it cannot be quietly claimed otherwise).
**Repository evidence.** Nine asset classes asserted separate; `cross_tenant` evaluation cases; the mutant "all tenants share one signing secret" is caught only after I added the forged-token case.
**Code references.** `lab/nasha_lab/governed/tenants.py::make_authority`, `lab/nasha_lab/governed/tenants.py::TenantEnv`, `lab/tests/test_governed_workflow.py::test_recipe_source_files_are_shared_reference_data_not_isolated`.
**Follow-ups.** Row-level vs database-per-tenant? Noisy neighbours? Key rotation?
**Tradeoffs and limits.** Per-store isolation, not per-process or per-network. No key rotation.

## 12. Human approval
**Question.** How does the human-in-the-loop step work, and how do you stop rubber-stamping or replays?
**Expected explanation.** The agent's proposal is stored with a hash; THE WEIR holds the write; a **different** authorised person (maker-checker) approves the exact call; the approval is bound to supplier, quote, quantity and estimated cost, expires, and works once. Changing any field after approval needs re-approval; an expired approval cannot be consumed later; replay creates nothing new; concurrent executions of the same approval create exactly one draft. The result is a **draft** order (`DRAFT_NOT_SENT`); nothing is transmitted.
**Repository evidence.** Maker-checker, expiry (two phases), replay, scope-tamper and concurrency tests (security dashboard lists them).
**Code references.** `lab/nasha_lab/governed/workflow.py::GovernedProcurement.decide`, `lab/nasha_lab/governed/workflow.py::GovernedProcurement.execute_approved`, `lab/nasha_lab/identity.py::Authority`.
**Follow-ups.** Approval fatigue? What does the approver actually see? Who approves the approver?
**Tradeoffs and limits.** The approver UI is a replay/demo; there is no real approval user interface or notification path.

## 13. Agent evaluation
**Question.** How do you evaluate an agent, and why should I trust the numbers?
**Expected explanation.** 28 cases across 13 categories (correct answer, source attribution, hallucination, unsafe proposal, missing data, abstention, contradictory evidence, retrieval failure, prompt injection, authorization, cross-tenant, approval bypass, tool failure). Expected values are **independent oracles** regenerated from the raw simulation, recipe files and the supplier-quote file, not read from the tables the system reads. Metrics are computed from case rows, the result hash is reproducible across independent runs, and the report states its scope: a small synthetic set; a perfect score is not evidence of real-world reliability.
**Repository evidence.** `test_governed_evaluation.py`; `eval.json` and the reliability dashboard.
**Code references.** `lab/nasha_lab/governed/evaluation.py::Oracle`, `lab/nasha_lab/governed/evaluation.py::build_cases`, `lab/nasha_lab/governed/evaluation.py::metrics`, `lab/nasha_lab/governed/evaluation.py::full_report`.
**Follow-ups.** How would you scale it? LLM-as-judge risks? How do you detect eval overfitting?
**Tradeoffs and limits.** Rule planner and scripted doubles; latency numbers are wall times on one machine.

## 14. Mutation testing
**Question.** What is mutation testing doing here?
**Expected explanation.** A mutant is a deliberately broken variant (validation never drops claims; proposal checks removed; planner inflates numbers; quality-lead policy gains the write tool; WEIR write gate off; upstream trusts a forged context; tenants share one secret; approved call no longer binds the amount; maker-checker removed). The evaluation must **fail in the mutant's target category**. Two of my first mutants *survived*: widening only the policy did nothing because a second layer still blocked, and a cross-tenant test could not see a shared secret. Both exposed weak cases; I fixed the cases (not the mutants) so 9 of 9 are caught. An earlier, separate mutation check targets the legacy tool layer.
**Repository evidence.** `test_governed_evaluation.py::test_all_mutants_killed`; release-gate mutation gate; reliability dashboard grid.
**Code references.** `lab/nasha_lab/governed/evaluation.py::mutation_report`, `lab/nasha_lab/mutation_check.py`.
**Follow-ups.** What is an equivalent mutant? How do you pick mutants? What does a 100% kill rate not tell you?
**Tradeoffs and limits.** Nine hand-chosen mutants; not generated or exhaustive.

## 15. Observability
**Question.** How would you investigate an incident?
**Expected explanation.** One correlation id per run links the trace (every stage, tool call with latency, failure class, auth and approval events), the ledger (proposal, draft, hash-chained audit) and the approval store. The incident investigator answers: who asked, which tenant, what the agent attempted, which tools ran, what evidence was retrieved and its trust labels, which policy applied, why an action was blocked, and whether any side effect occurred. Reports never contain tokens or secrets (a test asserts it); logs are redacted.
**Repository evidence.** `test_governed_incident.py`; the security dashboard's incident explorer (recorded synthetic scenarios, not real incidents).
**Code references.** `lab/nasha_lab/governed/incident.py::investigate`, `lab/nasha_lab/trace.py::Trace`, `lab/nasha_lab/governed/workflow.py::redact`.
**Follow-ups.** Metrics and alerting? OpenTelemetry? Sampling?
**Tradeoffs and limits.** No metrics backend, alerting or distributed tracing; observability is per-run forensics.

## 16. CI/CD
**Question.** How is quality gated?
**Expected explanation.** A local **release gate** computes PASS / FAIL / REQUIRES_REVIEW over 12 gates (unit, integration, PostgreSQL reconciliation, agent evaluation, mutation, security regression, tenant isolation, authorization, reproducibility, data quality, evidence consistency, portfolio-claim validation). A missing, stale, malformed or inconsistent required item **fails**; it never defaults to pass. Staleness is by age and by code changed since collection. Every published number is a claim with a source pointer the gate re-resolves. The current verdict is `REQUIRES_REVIEW` because the real-model test has not executed; I did not weaken the gate. GitHub workflows exist but have **never run remotely**, and the report says so.
**Repository evidence.** `test_release_gate.py` (31 tests including each negative case).
**Code references.** `lab/tools/release_gate.py::evaluate`, `lab/tools/release-gate.config.json`, `.github/workflows/lab-ci.yml`, `lab/tools/skip_report.py`.
**Follow-ups.** Why fail on skipped tests? How do you stop a test being quietly deleted? What does remote CI add?
**Tradeoffs and limits.** Local only; a gate is only as good as its configured requirements.

## 17. Reliability
**Question.** What happens when things fail mid-flight?
**Expected explanation.** Failures are classified; operations are idempotent (run idempotency keys, a unique proposal key, idempotent draft creation); a write timeout after approval does not create a second draft and recovers exactly once; a lost response is reconciled against the ledger rather than retried blindly; a database failure during the draft write rolls back and recovery needs re-approval; a crash after the proposal is stored resumes cleanly; a read-tool timeout abstains safely; model unavailability fails safe; a rate limiter blocks bursts without side effects.
**Repository evidence.** The eight tool-failure tests plus recovery tests (reliability dashboard).
**Code references.** `lab/nasha_lab/governed/workflow.py::GovernedProcurement.recover`, `lab/nasha_lab/governed/ledger.py::Ledger`, `lab/nasha_lab/governed/workflow.py::RateLimiter`.
**Follow-ups.** Exactly-once vs at-least-once? Poison messages? Backpressure?
**Tradeoffs and limits.** Single node; fault injection is in-process hooks, not network faults.

## 18. Reproducibility
**Question.** How do you show results are reproducible?
**Expected explanation.** Deterministic seeded simulators (same seed, same bytes; per-draw seeding by hashed tags); a from-scratch warehouse rebuild twice with every table hash compared (47 tables identical); evaluation results hashed and compared across independent runs; dependency versions recorded; the historical scenario is preserved and reproducible beside the current one (the default config serialises exactly as before so old manifests stay byte-identical).
**Repository evidence.** `test_enterprise_sim.py::test_same_seed_same_bytes_different_seed_different_bytes`, `test_menu_d90.py::test_historical_scenario_is_reproducible_and_its_config_has_no_menu_key`, `repro.json` in the gate bundle.
**Code references.** `lab/nasha_lab/warehouse/repro.py::table_hashes`, `lab/nasha_lab/enterprise_sim.py::generate`, `lab/nasha_lab/governed/evaluation.py::result_hash`.
**Follow-ups.** Floating-point determinism across machines? Lockfiles? Containerisation?
**Tradeoffs and limits.** Reproducible on this environment's Python and library versions; not tested across platforms.

---

### Questions I should expect that probe honesty
* *"Is this used in production?"* No. It is a synthetic, independent project; nothing here is deployed or has users.
* *"Did a real model run?"* No. The real-model test needs a runtime I could not provide; it is the reason the gate says `REQUIRES_REVIEW`.
* *"Did CI run on GitHub?"* No; local equivalents ran.
* *"Is the Production AI Agent Platform part of this?"* It is a separate repository; NASHA reuses ideas and adapted code (hashing embeddings, RRF), not the platform.
* *"What would you do next?"* Provide a model runtime and run the real-model test; run CI remotely; move the ledger to PostgreSQL with a queue; add real identity; widen the evaluation and mutants.
