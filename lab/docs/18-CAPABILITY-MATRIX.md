# NASHA Enterprise AI — 18-capability matrix

**Truth boundary:** NASHA is a business concept and engineering environment. Lab data/workloads are synthetic or simulated unless explicitly stated otherwise. This is independent engineering, not NASHA production employment.

Classification reflects evidence in NASHA Enterprise AI Lab, production-ai-agent-platform, and THE WEIR. Reuse wins over duplication.

| # | Capability | Classification | Existing implementation / reuse | Agent vs deterministic judgment | Genuine gap / next evidence |
|---|---|---|---|---|---|
| 1 | Operations Copilot | STRONG BUT NEEDS HARDENING | NASHA LangGraph agent, typed tools, checkpoints, HITL review, API; shared platform runtime | Agent for multi-source investigation/routing; rules for calculations/policy | Broaden from incident-specific workflow to explicit operations intents; eval each intent |
| 2 | Inventory Intelligence | SHOULD BE MERGED WITH ANOTHER CAPABILITY | NASHA inventory queries, risk assessment, DQ rules, anomaly events | **Deterministic analytics first**; agent only investigates/explains/escalates | Add reproducible anomaly/forecast metrics; expose as tools to Operations |
| 3 | Procurement Workflow | STRONG BUT NEEDS HARDENING | supplier status, draft recommendation, signed exact-argument approval grants, forbidden external actions | Agent may assemble recommendation; pricing/math deterministic; **no autonomous purchase** | Formal supplier-comparison schema + evaluation; retain explicit human boundary |
| 4 | Data Quality System | COMPLETE for prototype scope | injected-defect benchmark, deterministic rules, mutation/property tests, clean-data checks | Deterministic validation/anomaly system; agent optional for RCA | Known shifted-near-duplicate limitation remains documented; do not hide it |
| 5 | Enterprise Knowledge Agent | STRONG BUT NEEDS HARDENING | ingestion/chunking, BM25/static neural/pgvector experiments, citations, authority classes, abstention, 467-question benchmark | RAG assistant appropriate; authority/freshness/access rules deterministic | Improve adversarial/conflict retrieval and formal access-control filtering |
| 6 | Business Intelligence Agent | PARTIAL | synthetic business DB, FastAPI, analytics foundations; shared platform typed tools | Controlled agent orchestration over **read-only validated SQL** | Build SQL AST/allowlist validator, semantic metrics layer, query eval set |
| 7 | Forecasting / Decision Support | PARTIAL | analytics/data foundations and existing forecasting experience/repos can be reused | Forecast models/calculations deterministic; agent selects/explains models | Backtesting, intervals, baselines, model registry/tool contract |
| 8 | Customer Insights Agent | PARTIAL | synthetic data generation/analytics foundations; reusable NLP repos may apply | NLP pipeline deterministic/ML; agent synthesizes themes with evidence | Versioned synthetic feedback set, clustering/topic/sentiment eval |
| 9 | Experimentation Agent | MISSING | evaluation/statistics utilities are adjacent, not a business experimentation system | Statistical engine deterministic; assistant designs/explains within guardrails | Power/sample-size/significance library + scenario benchmark |
| 10 | Product / Menu Intelligence | PARTIAL | NASHA menu/product data and analytics artifacts | Deterministic metrics; agent for cross-metric synthesis | Synthetic product-performance fact model + margin/waste/repeat metrics |
| 11 | Incident Investigation Agent | PARTIAL | structured traces, failure categories, run records, runbooks/docs; platform observability | Agent appropriate for evidence collection/hypothesis ranking; telemetry deterministic | Trace/runbook tools + timeline/hypothesis schema + incident eval corpus |
| 12 | AI Evaluation System | STRONG BUT NEEDS HARDENING | planner eval, retrieval eval, DQ eval, failure injection, model probes, reproducibility checks, new release gate | Deterministic assertions primary; model judge only where objective assertion is impossible | Unify metric schema across agents; per-workflow golden sets; version comparison |
| 13 | Security / Red-Team System | STRONG BUT NEEDS HARDENING | poisoned docs/tool results, malformed outputs, forbidden actions, approval attacks, untrusted MCP tests; Weir eval suite | Deterministic adversarial harness | Cross-system red-team corpus + resource/loop/exfiltration cases |
| 14 | Governance System | STRONG BUT NEEDS HARDENING | NASHA identity/roles/signed grants + THE WEIR IFC/policy/audit/MCP controls | Deterministic enforcement; LLM must never decide authorization | Demonstrate NASHA tool call traversing Weir policy boundary; close known auth leak |
| 15 | Developer Agent | PARTIAL / LOW PRIORITY | GitHub/CI engineering workflow exists operationally; no dedicated autonomous runtime needed yet | Bounded coding assistant appropriate; deployment/merge remains human-controlled | Only build after reliability/governance foundations; avoid duplicating existing coding agents |
| 16 | Release / AI QA System | STRONG BUT NEEDS HARDENING | GitHub Actions, test/eval reproduction, Docker smoke, **release_gate.py** | Deterministic release policy | Expand to PASS/FAIL/REQUIRES_REVIEW and version deltas; archive evidence artifact |
| 17 | Observability Intelligence | STRONG BUT NEEDS HARDENING | NASHA SQLite structured traces/request IDs; platform spans/events/metrics, Redis/Postgres | Collection deterministic; agent can analyze telemetry | Normalize span schema + OTel export + offline SLO/reliability report |
| 18 | Workflow Discovery / AI Solutions | SHOULD BE DETERMINISTIC TOOLING, NOT AN AGENT | engineering decision discipline exists but not formalized | Rubric/decision model first; optional LLM explains classification | Build scored decision worksheet and test cases after core platform work |

## Duplicate systems to avoid

- Do **not** build a second orchestration framework inside NASHA; use the shared platform/runtime boundary and keep NASHA domain logic thin.
- Do **not** copy THE WEIR authorization/IFC engine into NASHA. Integrate through MCP/policy interfaces.
- Do **not** create separate “inventory agent”, “forecast agent”, and “menu agent” runtimes. Their deterministic capabilities become typed tools used by business workflows.
- Do **not** create a second evaluation framework. Consolidate NASHA and platform measurements behind one versioned result contract.
- Do **not** use an LLM to calculate SQL aggregates, forecasts, margins, experiment statistics, permissions, release policy, or telemetry.

## Ranked dependency roadmap

Scoring order considers employer relevance, learning value, reuse, differentiation, cost, and dependency.

**P0 foundation**
1. AI Evaluation System (#12) — measurement contract for everything else.
2. Release / AI QA (#16) — consumes evaluation/security/reliability evidence.
3. Security / Red Team (#13) + Governance (#14) — developed together because attack evidence must exercise real policy boundaries.
4. Observability (#17) — required to evaluate failures and support incident investigation.
5. Enterprise Knowledge/RAG (#5) — already strong; harden adversarial/conflict retrieval.
6. Operations Copilot (#1) — first applied consumer of the hardened platform.

**P1 applied reliability**
7. Incident Investigation (#11).
8. Business Intelligence (#6).
9. Inventory Intelligence (#2) + Procurement (#3) as one operational decision chain.
10. Data Quality (#4) — maintain/harden rather than rebuild.

**P2 decision/product systems**
11. Forecasting (#7).
12. Product/Menu Intelligence (#10).
13. Customer Insights (#8).
14. Experimentation (#9).
15. Workflow Discovery (#18).
16. Developer Agent (#15).

## First capability acceptance criteria — unified AI Evaluation System

The evaluation foundation is accepted only when:

1. A versioned result schema represents workflow identity, dataset/split, task success, tool selection, argument validity, structured-output validity, groundedness/citations where applicable, refusal/fallback, permission/security outcomes, latency and optional token/cost fields.
2. Existing NASHA planner, RAG, failure-injection and DQ evidence can be normalized **without changing historical raw results**.
3. Every metric declares numerator/denominator or sample count and measurement method.
4. Missing/unavailable metrics are explicit; they are never silently converted to zero or success.
5. Regression policy is deterministic and fail-closed for required metrics.
6. Known limitations remain visible (including shifted-near-duplicate DQ weakness and adversarial retrieval weaknesses).
7. CI runs unit tests, reproducibility checks and the release gate with no paid API/key.
8. Failure-injection coverage includes missing evidence, unavailable tool, malformed output, conflict, injection, permission denial, timeout, invalid schema, replay/duplicate and bounded-loop behavior.
9. Actual results are written from executed tests/evals; documentation never invents benchmark values.
10. Release status distinguishes engineering-evidence readiness from production readiness/business validation.

## Hero-workflow dependency

Do not build Executive Decision Intelligence until controlled BI/SQL, observability, unified evaluation and governance are in place. Its orchestration should call deterministic business metrics, inventory/product analytics and retrieval tools, then return evidence + uncertainty + recommendations. It must not expose hidden chain-of-thought; traces should show actions, inputs/outputs, sources, policy decisions and concise decision summaries.
