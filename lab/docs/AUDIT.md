# Audit, registry and roadmap (this block)

Source: repositories under `riteshmamidi0905-lab` read and cloned read-only; test runs by this session. **PROVEN here** = I ran the tests; **README-CLAIMED** = documented but not executed by me.

## Ten-competency map
| Competency | Where | Status |
|---|---|---|
| Python / APIs | llm-eval-framework (33 tests passed here), rag-doc-qa (14 passed here), this lab (30) | PROVEN |
| LLM evaluation | llm-eval-framework; agent-runtime-bench, mcp-weir, support-escalation-copilot document real small-local-model runs | PROVEN (framework) / README-CLAIMED (model runs) |
| Embeddings | production-ai-agent-platform, support-escalation-copilot (pgvector, embedding-repro workflow) | README-CLAIMED |
| Vector DB / RAG | production-ai-agent-platform (hybrid pgvector); rag-doc-qa is TF-IDF only | PARTIAL |
| Agents | production-ai-agent-platform, support-escalation-copilot | README-CLAIMED |
| MCP | mcp-weir (153 files, 35 test files, CI) | README-CLAIMED; tests not run here (dependencies) |
| **LangGraph** | one mention in mcp-weir only | **MISSING** |
| FastAPI | llm-eval-framework, rag-doc-qa, production-ai-agent-platform | PARTIAL |
| Docker / CI-CD | production-ai-agent-platform, support-escalation-copilot (compose, ci.yml) | README-CLAIMED |
| Evaluation / observability | llm-eval-framework; Prometheus in two repos | PARTIAL |
| **Data engineering / data quality (new)** | this lab | **PROVEN (synthetic)** |

Not run here: mcp-weir and support-escalation-copilot (collection errors: `pgserver`/extras unavailable in this sandbox), production-ai-agent-platform (needs pgvector). Those are environment limits, not verdicts.

## Why this capability was chosen
No repository showed a data platform with quality gates measured against known truth, and NASHA needs a trustworthy operational substrate before any RAG or agent can be honest about it. It reuses the NASHA D-54 policy and menu, produces measurable precision/recall, and is the substrate for the capabilities the market asks for more often. Job-market check (small sample of 2026 postings, not a survey): RAG + evaluation + observability are core, LangGraph is a common preferred skill, MCP is preferred-to-required, and data quality is rarely stated explicitly. So this block is infrastructure, and the next two blocks (RAG evaluation, LangGraph agent) carry the most recruiter value.

## Project registry (canonical, short)
Flagship: support-escalation-copilot, mcp-weir, production-ai-agent-platform, agent-runtime-bench/maref, llm-eval-framework, portfolio site. New: NASHA Enterprise AI Lab. Older single-purpose repos (nlp, ocr, speech, video, translation, sign-language, face-recognition, spark, streaming) are candidates to archive-or-group; no changes were made to any repository other than this branch.

## Synthetic-data truth policy
Every dataset is labelled SYNTHETIC; injected defects have ground-truth labels; no real people, customers, revenue or production; no claim beyond "offline evaluation on synthetic data". NASHA decisions (D-54 no beef/pork, no halal claim, working name, no logo) are inputs, never modified.

## Next blocks
1. LangGraph human-in-the-loop operations agent over this platform's quarantine/findings (the missing competency), reusing mcp-weir's gateway ideas.
2. Status-aware RAG with abstention over the NASHA decision register, evaluated by Recall@K/MRR/groundedness (reuse production-ai-agent-platform retrieval).
3. FastAPI + MCP surface; demand forecast with backtests.

## Status after Block 2
LangGraph: now PROVEN (lab/nasha_lab/agent.py, 133 tests, CI green). MCP: PROVEN for a small server (9 tools, tested in-process through the official client). FastAPI, Docker, CI: PROVEN here (CI builds the image and serves the API). Vector search: still PARTIAL (no neural embeddings, no pgvector in this lab; both exist in `production-ai-agent-platform`).

## Recommended Block 3
1. Put a real model behind the planner interface (free local model or an approved key) and re-run the 22 failure-injection cases and the injection tests: the current perfect scores belong to a deterministic planner.
2. Neural embeddings plus pgvector, measured against the six retrievers on a larger, partly externally written golden set.
3. Authentication and reviewer identity on the API; a small review UI.
4. Integrate `mcp-weir` between the agent and a second, untrusted MCP server to give its information-flow rules a real use.
