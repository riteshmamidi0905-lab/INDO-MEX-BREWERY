# NASHA Ops AI over the warehouse (SYNTHETIC)

`nasha_lab/warehouse/ops_ai.py` — a deterministic, read-only tool layer over the published marts.

- **Tools** (fixed parameterised SQL; callers never supply SQL): list_months, company_month, location_month, rank_locations, top_products, waste, daily_series.
- **Gate** (default deny): warehouse must be `published` → tool exists → role grants it → arguments pass allow-list/regex validation → `site_manager` limited to own site (and fails closed if no site) → query → audit row.
- **Audit/observability**: every call, including denials, is written to `ops_ai_audit` (user, role, site, tool, args, decision, code, rows, ms, warehouse run id, source table); `OpsAI.metrics()` gives calls, denials by code, p50/p95 latency.
- **Warehouse opened read-only** (`mode=ro`); the audit log is a separate database file.
- **Router** (`ask`): rule-based, no model; unrecognised or non-read-only requests abstain.
- **Evaluation**: `tests/test_ops_ai_warehouse.py` (14 tests) checks answers against values recomputed from fact tables by an independent query path, scope/role denials, injection strings, unpublished-warehouse refusal, audit completeness.

Limits: this is an in-repo stand-in for a policy gate in the style of THE WEIR, not an integration with THE WEIR. No LLM is involved, so no claim is made about language-model behaviour. Data is synthetic.
