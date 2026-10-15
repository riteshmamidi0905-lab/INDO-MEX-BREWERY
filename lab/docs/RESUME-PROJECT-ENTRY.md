# Resume project entry (NOT inserted into any resume; prepared for later tailoring)

Every bullet below is derived from a committed result or the claims ledger (`claims/claims.json`). Project, not employment: keep it under "Projects", never under an employer. Do not add metrics that are not in the ledger.

**NASHA AI Operations Lab: Independent Applied AI Project (synthetic enterprise simulation)** | Python, FastAPI, LangGraph, MCP, RAG, PostgreSQL/pgvector, Ollama (Qwen2.5), pytest, Docker, GitHub Actions

- Built a human-supervised AI operations agent over a synthetic enterprise: typed tools in five permission classes, signed human approval bound to exact arguments, a trusted and an untrusted MCP server behind a taint-tracking gateway, and a LangGraph state machine with checkpointed interrupt/resume.
- Compared a deterministic planner with local Qwen2.5-1.5B/7B planners under identical tools, permissions and checks: deterministic 259/259 scenarios vs 5/140 (1.5B) and 10/35 (7B); 0 executed external actions across ~1,000 real model calls; a deterministic evidence guardrail removed every silent "no action" error (30 of 140 scenarios raw).
- Benchmarked lexical vs neural retrieval on 467 questions in 13 categories (BM25 MRR 0.913 vs MiniLM 0.672; pgvector HNSW matched the exact scan), then rebuilt a differently-structured 176-question set that showed the lexical lead depends on word overlap.
- Found and fixed a circular-trust defect (model arguments counted as grounding evidence) via adversarial evaluation; raised a targeted mutation suite from 19/22 to 22/22 killed; froze the baseline with hashes and a machine-checked claims ledger; 229 tests in CI.
- Disclosed limits: synthetic data, same-author evaluation, small local models only, no production deployment.

Short form (one line): *Built and measured a human-supervised AI operations agent (FastAPI, LangGraph, MCP, RAG/pgvector); a deterministic planner outperformed local Qwen LLM planners on 259 synthetic scenarios, with a safety layer that executed 0 unauthorized actions in ~1,000 model calls.*
