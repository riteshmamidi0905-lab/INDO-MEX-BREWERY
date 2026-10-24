# Engineering Playbook plan

This is an evidence-driven reference plan, not a claim that the eventual showcase already exists. Each chapter must link source paths and immutable commit IDs, identify what was inspected or executed, and label synthetic business stories separately.

| Chapter | Actual evidence to curate | Work remaining |
|---|---|---|
| Origins and evolution | Root README, PROJECT-ROADMAP.md, decision register, lab/docs/CANONICAL-FACTS.md, existing commit history | Reconcile dated milestones against commits; do not infer outcomes from sprint prose |
| Architecture | Existing lab/docs/ARCHITECTURE.md, DATA-PLATFORM.md, governed and Growth docs; showcase/docs/ARCHITECTURE.md | Publish a diagram only after host integration is verified |
| Python and software engineering | enterprise_sim.py, warehouse contracts, this domain extension, tests | Explain tradeoffs with runnable examples and actual failure cases |
| SQL/PostgreSQL | Existing warehouse models/pg_variant.py, Growth schema, showcase/schema.sql and postgres.py | Explain star schemas versus domain records; document exact constraints and RLS trust assumptions |
| Agents and LLM orchestration | agentplatform/orchestrator/engine.py, tools/base.py, executor.py, lab planner experiments | Curate existing real-model results; never present fictional staff as executed LLM agents |
| Prompt engineering | Existing versioned agentplatform/prompts and lab planner schemas; USER-DIRECTIVE.txt | Recover historical prompts only from actual records; mark missing prompts unavailable |
| MCP integrations | Existing lab MCP server, WEIR upstreams and new read adapter | Distinguish implementation from installed connection and tested authorization |
| RAG and retrieval | knowledge.py, retrieval benchmarks, frozen claims and result files | Verify referenced result files/versions; do not rerun costly model suites unnecessarily |
| Security and THE WEIR | Gateway policy, governed approvals/authorities, isolation tests | Threat-model authenticated host session binding and deployment roles before HTTP exposure |
| Testing and evaluation | Actual pytest reports, frozen baseline, mutation tests and this tamper suite | Keep passed, skipped, failed and unrun results distinct; no invented test counts |
| CI/CD and Docker | Existing workflows, Dockerfiles and Compose | Add new showcase test job in a later explicitly scoped integration change; no deployment in this task |
| Data engineering and analytics | Source contracts, warehouse lineage, scenario event/journal reconciliation | Add derived department views only when they can be traced to source records |
| Failures and fixes | Lab failure logs; onboarding missing Python packages; full-cost showcase loss | Retain failures with context; do not rewrite historical evidence to fit a story |
| Tools and skills | Existing project capability matrix plus this handoff | Separate historical connections from currently available Codex tools |
| Interview preparation | Evidence-backed explanations of isolation, cash reconciliation, denied actions and replay | Questions should ask for tradeoffs, limits and reproducible demonstrations; no fabricated accomplishments |

Editorial rule: a business event such as a fictional sale belongs to simulation history. A command that actually passed belongs to engineering evidence. An AI-generated narrative cannot promote one into the other.
