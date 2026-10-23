# NASHA Growth OS: Phase A audit, architecture and migration plan

*Working name, not a public brand. NASHA is a proposed business; every customer, transaction, campaign, supplier and financial figure in this platform is synthetic unless independently verified. Nothing here is a commercially ready SaaS product.*

## 1. Repository audit (inspected, not assumed)

| System | Where | State at audit | Reuse for Growth OS |
|---|---|---|---|
| NASHA Enterprise AI Lab | `INDO-MEX-BREWERY`, branch `career/master-directive-phase0` (local, unpushed) | last full run recorded in the gate bundle (`lab/results/release-gate/`); latest local suite results are reported with each milestone | synthetic orders, members, menu and price configs, recipe costing, forecasting, Ops AI tools, scenario tables |
| Governed workflow + evaluation + release gate | `lab/nasha_lab/governed/`, `lab/tools/release_gate.py` | implemented and tested (state machine, THE WEIR approval, 28-case evaluation, 9 mutants, 12 gates, verdict `REQUIRES_REVIEW`) | the template for every Growth OS write workflow; the gate extends to Growth OS checks |
| PostgreSQL warehouse | `warehouse/pg_variant.py`, `pg_hardening.py` | reconciled to SQLite; 12 PK / 9 FK / 8 CHECK on scenario tables; safe migration runner | the migration runner is reused as-is for the Growth OS schema |
| THE WEIR | separate repo `mcp-weir` (pinned) | real gateway imported and tested | default-deny policy, held writes, single-use call-bound approvals; will gate every Growth OS write that has an external or financial consequence |
| Production AI Agent Platform | separate repo `production-ai-agent-platform` @ `f8ba373` | a FastAPI research-agent runtime: typed `Tool` / `ToolRegistry` with risk classes (`read`, `network`, `consequential`), planner → tools → evidence → verifier pipeline, approvals, MCP server, hybrid RAG on pgvector, 79 tests per its README | **not integrated today.** Plan: Growth OS read tools are registered as `agentplatform` tools (its `Tool`/`Risk` contract) for research/analysis agents; consequential tools are never registered there and run through the governed workflow + THE WEIR instead |
| Dashboards and evidence exporter | `export_portfolio_evidence.py`, portfolio `reliability.html` / `security.html` | metrics are claims with sources, re-checked by the gate | Growth OS metrics will use the same claim mechanism |
| Cinematic portfolio | `redesign/d90-systems-worlds` (local, unpushed) | home, flagship film, dashboards, projects, recruiter pages; QA scripted | a Growth OS case study will be added in the same design language after there is something real to show |

Other repositories noticed and **not** integrated: `experimentation-toolkit`, `product-analytics-funnel-retention`, `customer-churn-prediction`, `saas-kpi-dashboard`. They are candidates for capabilities 22 and 23 and are listed here only as candidates.

**Decision: one orchestration approach.** No second agent framework is created. Reads and analysis use the Production AI Agent Platform's tool contract; every consequential action uses the existing governed-workflow pattern (state machine, THE WEIR hold, human approval, idempotency, audit).

## 2. Shared data model (implemented in `lab/nasha_lab/growth/schema.py`)

PostgreSQL, one schema, one set of tables for all tenants. Seventeen tables now: `tenants`, `users`, `segments`, `accounts`, `contacts`, `suppression_list`, `leads`, `opportunities`, `stage_transitions`, `activities`, `products`, `prices`, `offers`, `campaigns`, `content_items`, `audit_log`, `entity_versions`, plus global `stage_rules` and `schema_migrations`. The remaining entities from the directive (competitor, market opportunity, website, landing page, email template, outreach sequence, proposal, conversion event, experiment, onboarding workflow, retention event, automation workflow, agent execution, approval) are **designed, not built**; each lands with its capability.

Rules enforced by the database (each has a test in `test_growth_foundation.py`):
* every row has `tenant_id`; primary keys are `(tenant_id, id)`; every foreign key is `(tenant_id, x_id)`, so a row cannot reference another tenant's row even by raw id;
* row-level security is enabled **and forced** on every business table; the policy compares `tenant_id` to the session's `app.tenant_id`; with no setting, a session sees nothing; the application role is a non-superuser without `BYPASSRLS`;
* contacts must use the reserved `example.invalid` domain, so real-looking addresses are rejected; `tenants.synthetic` is a CHECK that cannot be false;
* campaigns, content and offers have no `sent`, `published` or `running` state: those are unrepresentable;
* opportunity stage changes follow a global rules table enforced by a trigger (checked against an independent oracle for every stage pair); `won`/`lost` are final;
* updates bump `version` and snapshot the row to `entity_versions`; `audit_log`, `stage_transitions` and `entity_versions` are append-only by privilege; audit rows are hash-chained per tenant.

## 3. Migration plan
* Growth OS migrations `101`–`104` run through the existing checksummed, transactional runner (`pg_hardening.migrate(specs=...)`) in their own schema; re-running is a no-op and an edited migration is detected.
* The analytics warehouse (SQLite, PostgreSQL variant) is **not modified**. Growth OS reads it through adapters (`segments.py`, `pricing.py`); historical tables and the preserved historical scenario stay byte-for-byte.
* Next migrations (not yet written): proposals and approvals mirror table, experiments and exposures, workflow definitions and runs, retention events. Each ships with pre-flight checks and tests.

## 4. Tenant architecture and security boundaries
* Tenant isolation is enforced in layers: (1) PostgreSQL RLS + composite foreign keys + a non-privileged login role; (2) role-based authorization in the service layer, default deny, every denial audited; (3) THE WEIR for consequential actions (Phase D); (4) per-tenant audit chains.
* Provisioning a tenant is a privileged operation outside the application role.
* Two simulated tenants are seeded: NASHA (restaurant/brewery concept) and Meridian Fitness (a studio) with different products, prices, segments, customers and pipelines; tests probe every business table for cross-tenant visibility.
* **Known limits:** one database and one process serve all tenants (logical isolation, not physical); the embedded test server uses trust authentication for the application role; no key management, no per-tenant encryption, no external pen test. Two synthetic tenants working does not make this a commercial SaaS.
* Communication safeguards: consent status and a suppression list gate email **drafts**; there is no send method and no send state; external messaging, ad purchases and publishing are disabled by construction.

## 5. API contract plan (not yet implemented as HTTP)
Service methods are the contract today (`GrowthService`). The HTTP layer will follow the existing governed API pattern: tenant in the path, 404 for unknown tenants, one error envelope, request ids, idempotency keys, pagination, OpenAPI checked by a contract test. Until then there are no Growth OS HTTP endpoints, and the web interface (requirement 19) is not started.

## 6. Roadmap status (honest)
* **Phase A** (audit, capability mapping, data model, tenant architecture, security boundaries): done for the foundation; release-gate integration of Growth OS checks is pending.
* **Phase B** (core platform): CRM core, pricing, segmentation and offers storage implemented; UI, proposals, pipeline forecasting and dashboards not started.
* **Phases C–G:** not started except cross-cutting mutation tests (10 mutants) that already cover the database and service controls.
* Capability count by status is in `CAPABILITY-STATUS.md`; no percentage is claimed.
