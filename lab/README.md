# NASHA Enterprise AI Lab — Operations Data Platform (block 1)

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** NASHA has no restaurant, customers, sales, staff or brewery batches. Nothing here is a business result. Menu prices are placeholder inputs. The "scenario sites" are not real or planned locations. Same-author caveat: one author wrote the generator, the rules and the scoring; no independent review.

## Block 4: defensible evaluation and the public portfolio

Block 3 results are **frozen** (`baseline/BASELINE-BLOCK3.json`; `python -m nasha_lab.baseline verify`) and every public claim is machine-checked against evidence (`claims/claims.json`; `python -m nasha_lab.claims verify`). New in Block 4 (all NEW experiments, no Block 3 file changed):

| Addition | Where |
|---|---|
| Frozen baseline + claims ledger (with prohibited claims) | `baseline/`, `claims/`, `nasha_lab/baseline.py`, `nasha_lab/claims.py` |
| EXTERNALIZED / INDEPENDENT-STYLE EVAL v1: 106 scenarios + 176 retrieval questions built by different methods (still same author) | `nasha_lab/scenarios_ext.py`, `eval_ext1_planners.py`, `eval_ext1.py`, `docs/EVAL-HARDENING.md` |
| Per-scenario model trace (`trace1`) and missing-tool analysis | `eval_planners --trace-out`, `nasha_lab/trace_analysis.py` |
| One pre-registered tool-schema experiment (ts1 vs ts2) | `docs/TOOL-SCHEMA-EXPERIMENT.md`, `llm_planner.py` (`presentation="ts2"`) |
| Founder decision D-84: Mango Habanero Gobi is an appetizer, not a taco; versioned menu (v2) and corpus (`current`), frozen baseline keeps v1 / `block3` | `docs/decisions/DECISIONS.md` (D-84), `docs/decisions/item-amendments.csv`, `tests/test_menu_direction.py` |
| Portfolio evidence export (what the public portfolio vendors) | `nasha_lab/export_portfolio.py`, `portfolio/portfolio-evidence.json` |
| LinkedIn draft (not published) and resume project entry (not inserted anywhere) | `docs/LINKEDIN-DRAFT.md`, `docs/RESUME-PROJECT-ENTRY.md` |

---

## Block 3: a measured experiment (does an LLM improve the agent? do neural embeddings / pgvector pay for themselves?)

Two planners (deterministic control, LLM) behind one interface, one tool/permission/approval/trace stack and one scenario suite; plus a retrieval benchmark that compares lexical, hybrid, neural and pgvector retrieval, and abstention strategies. **Results decide the conclusion; the deterministic planner and lexical retrieval remain the baselines.** Start with [PLANNER-EXPERIMENT](docs/PLANNER-EXPERIMENT.md), [RETRIEVAL-EVALUATION](docs/RETRIEVAL-EVALUATION.md), [LLM-RUNTIME](docs/LLM-RUNTIME.md) and [results/EXPERIMENT-LOG](results/EXPERIMENT-LOG.md). The recruiter-readable pack is `evidence/index.html`.

**Headline results (synthetic, same-author, offline):** deterministic planner 259/259; Qwen2.5-1.5B 3.6-6.5% and Qwen2.5-7B 29% (35 scenarios) under the same checks, with 0 external actions in ~1,000 real-model calls; BM25 MRR 0.913 vs MiniLM 0.672 vs BM25+MiniLM 0.842; pgvector HNSW equals exact scan; mutation score 22/22. The LLM did not improve the agent; see [FAILURE-STORY](docs/FAILURE-STORY.md) for the failure that mattered.

| Addition | Where |
|---|---|
| Planner interface, LLM planner (structured output, bounded retry, fail-safe), evidence-envelope guardrail | `planners.py`, `llm_planner.py`, `llm.py` |
| 259 generated scenarios: dev 67, held-out 75, held-out B 75, adversarial 42 | `scenarios.py`, `eval_planners.py` |
| Stand-in models (scripted, NOT LLMs): rule, worst-case, parrot, taint-copier | `scripted_models.py` |
| 467 retrieval questions in 13 categories, 8 abstention strategies, learned answerability gate | `qgen.py`, `eval_rag2.py`, `answerability.py` |
| Neural (static) embeddings, PostgreSQL + pgvector HNSW retriever | `embeddings.py` |
| Untrusted MCP server + trust gateway + taint tracking | `untrusted_mcp.py`, `trust.py` |
| Reviewer identity, roles, signed grants | `identity.py` |
| Review console (accessible, XSS-tested) | `ui/review.html`, served at `/review` |
| Property-based tests, mutation testing (22/22 after closing 3 gaps) | `tests/test_properties.py`, `mutation_check.py` |
| Run records (planner, model, tokens, latency, retrieval scores, review time) | `experiments.py` |

```bash
cd lab && pip install -r requirements-dev.txt && python -m playwright install chromium
python -m pytest -q tests                                        # 267 collected; integrations that need a model/DB skip loudly (CI on 9cb7ca4: 266 passed, 1 skipped; local run without PostgreSQL: 265 passed, 2 skipped; see docs/CANONICAL-FACTS.md)
python -m nasha_lab.eval_planners deterministic out.json         # also: rule-model | worst-case | parrot | parrot+guardrail | taint-copier | ollama | ollama+guardrail
python -m nasha_lab.compare_planners a.json b.json               # paired comparison, exact sign test
python -m nasha_lab.eval_rag2 out.json                           # NASHA_PG_DSN=postgresql://... to include pgvector
python -m nasha_lab.mutation_check results/mutation.json         # mutation testing of the safety code
python -m nasha_lab.build_evidence                               # regenerates evidence/index.html
```
Dev reviewers for the console (local prototype identity, protect nothing real): `alice` (BUYER) `alice-dev-passcode`, `bob` (QUALITY_LEAD) `bob-dev-passcode`, `founder` (FOUNDER) `founder-dev-passcode`.

---

## Block 2: the applied-AI vertical slice

**A human-supervised operations agent that investigates synthetic business exceptions using structured operational data and status-aware enterprise knowledge, then stops for approval before consequential action.**

```
operational event -> typed tools (READ / ANALYZE) -> status-aware NASHA knowledge (authoritative, current, or abstain)
   -> evidence-cited proposal (DRAFT only) -> human review (approve / reject / edit / more evidence, checkpointed)
   -> approved simulation action bound to exact arguments -> full trace -> evaluation + failure injection
```
Three scenario families (9 events): **inventory exceptions** (low cover, stale or quarantined count, count variance), **data-quality incidents** (duplicate, near-duplicate, malformed record) and **D-54 policy events** (a supplier substitution that is prohibited, ambiguous or documented). The ambiguous one must end in `INSUFFICIENT VERIFIED EVIDENCE`, not a guess.

| Surface | What | Where |
|---|---|---|
| Knowledge | 758 chunks from 82 NASHA sources with status metadata; 6 retrievers compared; 55-question golden set | `nasha_lab/knowledge.py`, `eval/rag_golden.jsonl`, [RAG-EVALUATION](docs/RAG-EVALUATION.md) |
| Tools | 19 registered typed tools (17 callable, 2 registered-but-forbidden external-action placeholders), 5 permission classes, approval bound to exact arguments (see docs/CANONICAL-FACTS.md) | `nasha_lab/tools.py` |
| API | FastAPI: runs, review, traces, inventory, quality, knowledge; request ids, JSON logs, one error contract | `nasha_lab/api.py` |
| MCP | 9 read/analyze/draft tools; no mutation, SQL, filesystem or shell | `nasha_lab/mcp_server.py` |
| Agent | LangGraph state machine with interrupt/resume and SQLite checkpoints | `nasha_lab/agent.py`, [AGENT](docs/AGENT.md) |
| Evaluation | 18 scenario runs, 22 failure-injection cases, RAG metrics | `results/`, [FAILURE-LOG](results/FAILURE-LOG.md) |

```bash
cd lab && pip install -r requirements.txt
python -m pytest -q tests                                  # 133 passed, 2 xfailed (documented gaps)
python -m nasha_lab.eval_rag /tmp/rag.json                 # retrieval + answer metrics
python -m nasha_lab.eval_agent /tmp/agent.json             # scenario evaluation
python -m nasha_lab.eval_failures /tmp/failures.json       # 22 failure-injection cases
PYTHONPATH=. uvicorn --factory nasha_lab.serve:app         # API on :8000 (OpenAPI at /docs)
python -m nasha_lab.mcp_server                             # MCP over stdio
docker compose up --build                                  # same API in a container (verified in CI, not in the authoring sandbox)
```
More: [REUSE-AND-PROVENANCE](docs/REUSE-AND-PROVENANCE.md) · [THREAT-MODEL](docs/THREAT-MODEL.md) · [CASE-STUDY](docs/CASE-STUDY.md)

---

# Block 1: operations data platform

## What it is
A deterministic synthetic NASHA operations dataset **with labelled, injected defects**, and a layered pipeline that must find them:

`raw CSV -> staging (typing, rejects) -> validated (11 data-quality rules, quarantine, severities) -> modeled (SQLite star schema) -> analytics views`, with a lineage table, a row-conservation invariant, and a publish gate that fails on a D-54 violation (beef/pork/derivatives in a menu record).

```bash
cd lab && python -m pip install pytest && python -m pytest -q tests      # 30 tests
python -m nasha_lab.run --seed 1 --out lab_out                          # one run; exit 3 when the publish gate fails
python -m nasha_lab.evaluate v1 | diff - results/eval_v1.json           # evaluation must reproduce byte for byte
```

## Evidence (all re-runnable; numbers are from this repository's committed results)
| Claim | Evidence |
|---|---|
| Block 1: 30 tests pass | `tests/test_platform.py`; also run in `.github/workflows/lab-ci.yml` and `tools/validate_all.sh` |
| 11 of 12 injected defect types detected with precision 1.0 and recall 1.0 over 5 seeds x 8 injections (the 12th, a copy shifted by 1 s, is a recorded undetected gap) | `results/eval_v1.json` |
| 0 findings on the clean dataset (no false positives over 5 seeds) | `results/eval_v1.json` -> `clean_dataset_findings` |
| Fail-then-fix: `near_duplicate_order` recall 0.0 in baseline v0, 1.0 after adding the rule | `results/eval_v0_baseline.json` vs `eval_v1.json` |
| Honest remaining gap: a copy shifted by 1 second is NOT detected (recall 0.0) | `test_known_limitation_...`, `docs/EVALUATION.md` |
| A real bug found by the lineage report and fixed with a regression test: dedup quarantined both copies of a duplicated order | `test_regression_dedup_keeps_the_original_order` |
| Tests can fail: 2 of 2 manual mutants (tolerance 0.25 -> 0.05; inverted total check) are caught | `docs/EVALUATION.md` |

Read next: [ARCHITECTURE](docs/ARCHITECTURE.md) · [EVALUATION](docs/EVALUATION.md) · [AUDIT, registry and roadmap](docs/AUDIT.md)

## AI Operations Control Center and reliability evidence (P1/P2)

SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED. Additive package `nasha_lab/ops/` (telemetry, alert rules, incidents, SLO design targets, version registry, regression gate, failure injection, resilience wrappers, static dashboard). Start with `docs/OPS-CONTROL-CENTER.md`; measured results and misses in `docs/OPS-CONTROL-CENTER-EVALUATION.md`; every failure-catalog entry mapped in `docs/RELIABILITY-MATRIX.md`; runbooks in `ops/runbooks/`; data in `results/ops/`.
