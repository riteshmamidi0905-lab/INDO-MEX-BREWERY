# NASHA Enterprise AI Lab — Operations Data Platform (block 1)

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** NASHA has no restaurant, customers, sales, staff or brewery batches. Nothing here is a business result. Menu prices are placeholder inputs. The "scenario sites" are not real or planned locations. Same-author caveat: one author wrote the generator, the rules and the scoring; no independent review.

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
| Tools | 18 typed tools, 5 permission classes, approval bound to exact arguments | `nasha_lab/tools.py` |
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
| 10 of 11 detectable defect types found with precision 1.0 and recall 1.0 over 5 seeds x 8 injections | `results/eval_v1.json` |
| 0 findings on the clean dataset (no false positives over 5 seeds) | `results/eval_v1.json` -> `clean_dataset_findings` |
| Fail-then-fix: `near_duplicate_order` recall 0.0 in baseline v0, 1.0 after adding the rule | `results/eval_v0_baseline.json` vs `eval_v1.json` |
| Honest remaining gap: a copy shifted by 1 second is NOT detected (recall 0.0) | `test_known_limitation_...`, `docs/EVALUATION.md` |
| A real bug found by the lineage report and fixed with a regression test: dedup quarantined both copies of a duplicated order | `test_regression_dedup_keeps_the_original_order` |
| Tests can fail: 2 of 2 manual mutants (tolerance 0.25 -> 0.05; inverted total check) are caught | `docs/EVALUATION.md` |

Read next: [ARCHITECTURE](docs/ARCHITECTURE.md) · [EVALUATION](docs/EVALUATION.md) · [AUDIT, registry and roadmap](docs/AUDIT.md)
