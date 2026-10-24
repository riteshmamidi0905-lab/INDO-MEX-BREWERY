# Repository and integration audit

Inspection date: October 24, 2026. These are observations of checked-out files, not certification of every existing feature.

| Repository / revision | Observed capability | Reuse / boundary |
|---|---|---|
| INDO-MEX-BREWERY initial checkout `22edfd066d7f185ba3af654db2e276caca103348` | Static Python/Pillow concept site, source records, tools/validate_all.sh, Node browser QA | Original checkout left clean. Full validator returned ALL CHECKS PASSED; static build used a scratch copy to preserve tracked generated files. |
| INDO-MEX-BREWERY `career/master-directive-phase0` at `88f6ff4f12c7a713ce8ab005d92f77531cc67e23` | `lab/nasha_lab/enterprise_sim.py`, warehouse contracts/pipeline/models, PG variant, governed tenants, Growth OS, recipe/menu versions | Exact base of isolated local branch. Reuse generator and TenantPrincipal; preserve all frozen experiments. Remote branch may advance after inspection; no synchronization or writes were attempted. |
| production-ai-agent-platform observed default `7acb14706bdb5b4eb1246336a4c4c3371f78ccc1` | AgentEngine, typed ToolRegistry/ToolExecutor, ApprovalBroker, provider pool, PostgreSQL/pgvector, optional Redis, REST/SSE/WebSocket, MCP, metrics, tests and Docker Compose | Tool adapter verified against `f8ba3735204d192734d9f8db7c164efd67790a71`, the revision pinned by lab CI. No framework fork, no source edits. Full service stack not started. |
| mcp-weir at CI pin `5df274563a4a73ebbd31a6380e3a7d829b6bf4a2` | Gateway, parse_policy, persistent Store with chain verification | Installed and exercised for this extension, retaining existing policy defaults. |
| Portfolio `783ba6464e20ebf064da4448c94d5461fb358ab4` | Static portfolio, release validator, Node model/browser tests, NASHA case study | Read-only audit clone; no edit or publication. |

## Existing engineering to preserve

`lab/nasha_lab/warehouse/tenancy.py` binds principals to granted tenants and rejects routing overrides. `governed/tenants.py` provisions independent stores and authorities. `growth/service.py` and `growth/schema.py` provide actual CRM records, policies and PostgreSQL controls. `warehouse/ops_ai_weir.py`, `governed/weir_bridge.py` and Growth WEIR adapters already bridge domain tools to THE WEIR. This extension uses the same read-gateway pattern, not replacement authentication/approval engines.

`agentplatform/api/app.py` has optional shared API-key authentication. This is not evidence of a production identity provider. The showcase's injected principal and grant registry are trusted local host configuration. A future HTTP route must derive those from verified identity and existing tenant grants; clients must never supply a role or tenant authority. No public HTTP endpoint was added.

`agentplatform/telemetry.py` exposes process metrics and run spans; engine events and approval records exist. Lab evaluation/scenario suites, frozen claims/baselines and CI already exist. They were inspected, not all rerun for this additive domain change. Existing lab CI includes model, browser, PostgreSQL and WEIR dependencies; this extension adds a separate local test command without editing those workflows.

## Integration decisions

| Integration | Recommendation | Reason / current status |
|---|---|---|
| GitHub | Existing platform HTTPS proxy for reads; local version control | Clone/fetch operations succeeded without requesting tokens. No push or GitHub writes. |
| PostgreSQL | Keep existing infrastructure; new explicitly named versioned schema only | Real local PG constraint/RLS tests passed. Production database selection and authorization are future host integration work. |
| Redis | Reuse platform cache/event fan-out if deployed across processes | Not needed for deterministic fixtures or local reads; no extra daemon installed. |
| HubSpot | Defer | Existing synthetic Growth CRM suffices. Real CRM would require separately authorized credentials, consent, mapping and sandbox-only write policies. |
| Slack | Defer | No human notifications required. No messages sent and no Slack connector assumed available. |
| Runway / avatar services | Defer | No visual assets required by foundation; cost, data egress and consent need explicit assessment later. |
| MCP | Reuse existing server/tool protocols and WEIR upstream | Actual local gateway tested. Existing lab MCP servers are repository implementations, not automatically connected ChatGPT tools. |
| Paid LLM / cloud services | Unnecessary here | The simulator is deterministic and calls no providers. |

Tool discovery in this Codex session exposed cloud configuration/runtime tools and image generation. A ChatGPT connection or a historical README claim was not treated as a usable runtime integration. No new external account, subscription, secret or network allowlist was requested.
