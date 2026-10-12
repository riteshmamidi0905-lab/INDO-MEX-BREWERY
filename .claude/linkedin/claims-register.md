# Claims register (the only numbers any skill may use)

Every figure below was checked by string match against the source file at the pinned commit on 2026-10-12.
They are **transcribed from Ritesh's own documentation**. Test suites were **not re-executed** for this register.
If a claim is not in this file, no skill may state it. Use `{{your number}}` and ask.

Label meanings (from Ritesh's own profile): VERIFIED = tested/measured in the public repo at the pinned commit;
SIMULATED = scripted stand-in plays the model/approver; LIMITATION = known gap, stated on purpose.
**Always carry the caveat with the number.**

## Independent open-source work (synthetic data, never deployed, not employer or client work)

| ID | Claim (exact scope) | Label | Source @ commit | Must travel with it |
|---|---|---|---|---|
| C1 | Support Escalation Copilot: 489 automated tests pass; 92/92 catalogued attacks have executable tests | VERIFIED | support-escalation-copilot/README.md @1d69a02 | Fictional customer, synthetic data, never deployed |
| C2 | Copilot, one real-model run (small local model, one pass): 10 of 22 cases reached the frozen expected outcome (not accuracy); failures were at the interface (schema, evidence handles, action parameters, drafts) while the four deterministic invariants held | VERIFIED | same | One pass, one small model. Default model is a rule-based stand-in, approvers simulated |
| C3 | Agent runtime + ARB-1: one small model, 43/48 tasks passed the frozen oracles | VERIFIED | agent-runtime-bench/README.md, docs/RESULTS.md @679fa28 | One small model, author-written tasks |
| C4 | Runtime's 7 controls held in 240/240 agent-mode runs across six run sets | VERIFIED | same | Did not cover MT-02 |
| C5 | MT-02: a permitted read tool returned a secret and the model wrote it into its answer while every control held. Lesson: action safety is not information-flow safety | LIMITATION (a finding) | same | The strongest story: a failure found and reported |
| C6 | llmeval: 14 built-in deterministic metrics, 33 tests pass | VERIFIED | llm-eval-framework/README.md @99e6121 | Hand-written cases; not an evaluation of any model |
| C7 | MAREF held-out test: 33/33 labelled failures detected, 36/154 clean runs flagged, 151/187 overall agreement. Pre-registered verdict: MIXED | VERIFIED (same-author) | maref/README.md @1c00c90 | Not independent validation; test split spent; did NOT beat stronger baselines (always-pass 154/187, local 4B judge 166/187); no trajectory-specific advantage shown |
| C8 | MAREF vs llmeval hard gates: pre-registered comparison passed; real clean-run false alarms 30/112 (~27%) vs 65/112 (~58%) | VERIFIED (same-author) | same | Same caveats as C7 |
| C9 | Weir (MCP gateway): 342 tests pass in CI | VERIFIED | mcp-weir/README.md @5df2745 | Research prototype |
| C10 | Weir, scripted evaluation with careful simulated approver: a plain session rule (R-UNTRUSTED-READ) was first-listed on the first stopped attack call 47.3% vs 13.9% for the content tracker (R-FLOW-CONF); ranking reverses if the approver approves everything | SIMULATED | mcp-weir/docs/evaluation.md @5df2745 | Synthetic world, one small model, same author (AI-assisted), no independent review. "First-listed" is an accounting convention, not causal |
| C11 | Weir: 1,650 attacks; 7.3% reached the goal with Weir + careful approver (all via the model's answer, which Weir cannot see) | SIMULATED | mcp-weir/README.md | Same as C10 |
| C12 | Experimentation toolkit: A/B analysis from power/MDE to ship/kill decision, CUPED, guardrails, FDR; 11 tests | VERIFIED (tests) | experimentation-toolkit/README.md | Seeded synthetic experiment |
| C13 | Product-analytics toolkit: funnel, retention, cohorts, channel-LTV proxy; 6 tests | VERIFIED (tests) | product-analytics-funnel-retention/README.md | Seeded synthetic data; LTV is a proxy |
| C14 | Production AI Agent Platform: plan/tools/retrieval(pgvector+FTS)/verify/eval regression gate; latency baseline stored | STRUCTURE only | production-ai-agent-platform/README.md @7acb147 | Default provider is a deterministic heuristic, not an LLM. Quote no latency figure without re-reading the file |

## Professional history (as reported on Ritesh's own résumé; not independently verified by anyone here)

| ID | Claim | Source | Must travel with it |
|---|---|---|---|
| P1 | Data & AI Analyst, Apple (client engagement), Austin TX, Sep 2025 to present: validates LLM/ML outputs against policy and quality rubrics; QA/QC frameworks and reporting in Python, SQL, Power BI | résumé PDF, recruiter.html | Engagement details beyond the public résumé: **ask first** (confidentiality unknown) |
| P2 | Results "18% improvement in investigation efficiency, 30% reduction in operational escalations" | résumé | Self-reported on résumé; contribution, not sole credit. Confirm permission before using in a post |
| P3 | Heart Hospitality LLC, Business/Data Analyst, Jan 2024 to Aug 2025: ETL/reporting (-55% manual effort), forecasting/classification (+22% planning accuracy) | résumé | Self-reported |
| P4 | Liberated Monks Pvt. Ltd. (India), Jan 2022 to Dec 2023: ETL, Tableau; segmentation/propensity models associated with +18% engagement | résumé | Self-reported; "associated with" |
| P5 | MS Business Analytics (St. Francis College); M.Tech (Integrated) Software Engineering (VIT); IBM AI Engineering and Google Advanced Data Analytics certificates (Coursera) | résumé, profile README | |

## Binding presentation rules (from the source repos' own CLAIM.md)
- C7: `33/33` is never shown without `36/154` flagged and `151/187` agreement beside it, plus the words "research prototype, same-author, MIXED".
- C8 may only be quoted with C7's caveat that stronger baselines were not beaten.

## Never claim

- Any project is deployed, in production, used by customers, or independently validated.
- That a rule-based stand-in is an LLM, or that a result generalises beyond one small model and synthetic data.
- Any number not in this file. Any employer outcome beyond P1-P4. Any title, salary, or offer.
- Work authorization, visa status, or clearance (not on record anywhere; see jobsearch/profile).
