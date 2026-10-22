# Repository audit (Phase 0 of the master directive, 2026-10-22)

Truth boundary: everything here was read from git and files in this session unless marked UNVERIFIED. The business is a founder concept; the lab data is synthetic.

## Inventory
| Asset | Where | State inspected | Verified result |
|---|---|---|---|
| Concept repository + Hospitality AI Lab (`INDO-MEX-BREWERY`) | github riteshmamidi0905-lab | base `claude/nasha-enterprise-ai-lab` @ e4eeb73 (PRs #1, #2 merged at 49aaac2; README commit after) | CI run 53 on 49aaac2: PASS, 275 passed / 1 skipped |
| Lab engineering (`lab/`) | same | generator, 19 registered tools (17 callable), FastAPI, MCP server, LangGraph agent, trust gateway, eval harnesses, mutation 22/22, 22 failure scenarios | see `lab/docs/CANONICAL-FACTS.md` |
| Analytics mart, forecasting, experiment (P4) | branch `career/p4-analytics-mart-clean` 2897e12 | SQLite mart, metrics, forecast, A/B experiment, prospective design | not merged; do not touch |
| Hardened service (P5) | `career/p5-hardened-service` a40f2ad | FastAPI + Postgres + JWT/RBAC + idempotency + Docker | CI green; 109 Postgres tests ran only in CI; Docker never run locally |
| Reliability policies | `career/reliability-policies` a1bf2a7 | retry/dead-letter/idempotency/authority v2 | CI green |
| Product case, stronger-model prereg | `career/p3-product-case` f6d4b9e, `career/stronger-model-prereg` b669b84 | decision evidence (no AI in the decision path; 14B 14/35 vs 32/35 bar) | CI green |
| Agent platform | `production-ai-agent-platform` career/verify-and-harden f8ba373 | async API, streaming, MCP | README says 79 tests; not re-run here (UNVERIFIED) |
| THE WEIR | `mcp-weir` career/fix-test-count-source-of-truth 2325ad0 | authorization/approval/audit gateway | 342 vs 338 explained (optional `mcp` extra); not re-run here |
| Eval framework / experimentation toolkit | `llm-eval-framework`, `experimentation-toolkit` career/verify-and-harden | READMEs corrected to real counts | not re-run here |
| Concept website prototype | `website/` (`dist/` 14 pages, `family-dist/` 6 pages), also `gh-pages` | static, Python-built, noindex, no deploy of NASHA media | QA json 2026-10-15: axe 0 violations dark+light, no overflow 320-1920; NOT done: screen-reader, real device/network |
| Personal portfolio | `riteshmamidi0905-lab.github.io` | main a90ee8a live; dev branch `career/brand-neutral-portfolio` 4ee722c | static + browser + a11y + budget tests pass on the dev branch |
| Private career files | `riteshmamidi0905-lab/career-evidence-os-private` | private, pushed | grader keys live here only |

Not inspected: the live URLs (this sandbox cannot resolve github.io; ENOTFOUND). The `gh-pages` branch and `website/dist` were inspected instead.

## Architecture map (what exists)
Concept docs/decisions (`docs/decisions`, D-numbers) -> brand (`brand/`, `website/DESIGN-SYSTEM.md`) -> synthetic world generator (3 scenario sites) -> typed tool registry -> trust gateway / MCP (trusted + untrusted) -> planners (deterministic vs LLM) -> LangGraph HITL agent -> FastAPI + trace store -> evaluation (planner, retrieval, mutation, failure injection) -> evidence export to portfolio. P4/P5 add a SQL mart and a hardened service on unmerged branches.

## Reuse plan
Reuse, do not rebuild: generator, tool registry, trust gateway, eval harnesses, P4 mart/forecast/experiment, P5 service, THE WEIR, website build/QA pipeline. New work is additive: warehouse + dbt layer, scale-up of the generator, dashboards, second customer (FDE), learning system.

## Risk register
| Risk | Severity | Mitigation |
|---|---|---|
| Public brand name: D-79/D-80 keep it internal, README (2026-10-17) says "Public name: none yet", brand-collision case on file | HIGH | name-agnostic design tokens; nothing public under the name until a founder decision |
| Core 5 food set and D-84 already decided (Chicken 65 Totopos is Session 1); directive proposes different dishes | HIGH | record as a decision request, do not overwrite |
| Claims drift (resolved for tool/test counts) | MED | `canonical_claims` generator + tests |
| Unmerged branches hold evidence that public pages cite | MED | merge per owner approval |
| Old public branch `career/p4-analytics-mart` exposes SQL answer keys | MED | owner deletes; answers not valid mastery evidence |
| Scale gap: directive wants 14 locations / 2-3M transactions; lab has 3 scenario sites | MED | generator scale-up is Phase 2 |
| dbt / Spark / Kafka absent from the repo | MED | add only where earned; label honestly |

## Dependency map
Generator -> contracts -> warehouse -> BI and product analytics -> Ops AI tools -> evaluation -> showcase. Second customer depends on adapters + validation. Brand/website is independent except for the name gate.

## Known limitations
No physical recipe, brewing or sensory result exists; Session 1 not cooked. No professional review recorded. No real customers, revenue or users anywhere.
