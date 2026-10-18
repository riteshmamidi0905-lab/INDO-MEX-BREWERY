# Enterprise AI ecosystem gap analysis

Scope: NASHA Enterprise AI Lab + production-ai-agent-platform + mcp-weir. NASHA is a founder concept in development; all lab workloads are synthetic/simulated. This document does not convert independent engineering into professional employment.

| Capability | Evidence today | Status | Highest-value next move |
|---|---|---|---|
| Multi-step orchestration | NASHA LangGraph HITL graph; production platform validated state machine | Strong | Keep both: NASHA for business workflow, platform for reusable runtime |
| Tool calling / structured output | Typed tools, Pydantic schemas, deterministic + local-model planner experiments | Strong | Add cross-workflow contracts rather than another tool framework |
| RAG / retrieval quality | 467-question benchmark; BM25/hybrid/neural/pgvector comparisons; citations/abstention | Strong | Gate retrieval regressions; preserve known adversarial weaknesses |
| Memory / state | LangGraph checkpoints + SQLite; production platform Postgres run/event/conversation state | Strong | Demonstrate restart/recovery and state retention explicitly |
| MCP | NASHA trusted MCP surface; untrusted MCP test server; production platform MCP client/server; Weir gateway | Strong | Integrate governance evidence across the boundary without copying Weir |
| Human approval | Signed grants bound to run/tool/exact args; interrupt/resume | Strong | Keep sensitive external actions impossible in demo |
| Evaluation / regression | DQ, planner, RAG, failure, mutation, model and schema experiments | Strong but fragmented | **NEW: one fail-closed release contract** |
| Failure analysis | Tool-schema experiment, trace analysis, failure injection | Strong | Expand only when a new workflow introduces a new failure class |
| Tracing / observability | Structured SQLite traces + production platform spans/events/metrics | Good | Add portfolio-readable SLO/reliability summary, not fake production telemetry |
| Security / permissions | Role policy, signed grants, tool classes, Weir IFC | Strong prototype | Fix known auth-before-existence leak; document identity limitations |
| Injection / tool abuse | poisoned docs/results, taint, strict schemas, Weir flow rules | Strong research evidence | Demonstrate Weir as external governance layer in an integration test |
| API/backend | FastAPI, typed errors, request IDs, auth, readiness | Strong prototype | Add rate-limit/TLS only if deployment boundary justifies it |
| Async/event workflows | production platform async/SSE/WebSocket/Redis; NASHA graph is synchronous | Good ecosystem-level | Do not force queues into NASHA until a real workflow needs them |
| Containers | Docker/Compose; CI smoke | Strong | Preserve reproducible local path |
| CI/CD gates | pytest, Docker smoke, eval reproduction | Strong | **NEW release gate blocks portfolio-ready status on regressions** |
| Monitoring/reliability | timeouts, retries, idempotency, fallback, traces; no live SLOs | Good prototype | Define offline reliability indicators; do not claim production monitoring |
| Reusable platform components | production platform + specialized NASHA vertical + Weir boundary | Strong | Formalize ownership/interfaces; avoid repo duplication |
| Business impact/adoption | technical metrics only; NASHA has no users/revenue | Honest gap | Define *prospective* workflow KPIs and adoption instrumentation; never invent impact |

## Flagship workflow set

1. **Inventory anomaly investigation** — agent is appropriate because evidence spans inventory state, supplier state, policy and a human decision. Deterministic rules remain authoritative for calculations and policy gates.
2. **Operations knowledge / policy RAG** — retrieval + abstention, with document status and freshness. The agent never turns unverified research into authority.
3. **Management decision support** — analytics and scenario synthesis over synthetic operational data. SQL/KPI computation is deterministic; an agent is used only for evidence assembly/explanation.
4. **Supplier intelligence** is a later extension only if it adds new evidence or governance value. No autonomous supplier contact or purchasing.

## Release contract

A branch is portfolio-case-study-ready only when:
- all failure-injection cases pass;
- supported data-quality rules retain >=0.99 precision and >=0.90 recall;
- deterministic planner scenario pass rate remains >=0.99;
- BM25 retrieval MRR remains >=0.80 on the committed benchmark;
- normal tests and Docker smoke remain green.

This is **not** a production-readiness claim. It is an offline/synthetic engineering-evidence gate.

## Portfolio rule

Surface the ecosystem as one platform story: reusable runtime + NASHA applied workflows + Weir governance + measured evaluation. Internal prompt experiments, every model probe, and every historical repository should remain supporting evidence rather than separate flagship cards.
