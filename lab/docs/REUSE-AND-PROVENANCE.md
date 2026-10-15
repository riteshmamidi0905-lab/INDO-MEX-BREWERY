# Reuse decisions (what was taken from existing projects, and what was not)

| Component | Source | Decision |
|---|---|---|
| TF-IDF retriever (baseline A0) | `rag-doc-qa` (`ragqa.index.TfidfIndex`) | **Reused unmodified** as a pinned dependency (`@6e44f13`). Stronger to measure the existing implementation than to rewrite it. |
| Feature-hashing dense vectors (B1) | `production-ai-agent-platform/agentplatform/retrieval/embeddings.py` | **Adapted** (words + bigrams + char trigrams, signed hashing). Re-implemented synchronously, without the provider/DB interfaces. Measured: clearly weakest; rejected for the default. |
| Reciprocal-rank fusion (C) | `production-ai-agent-platform/agentplatform/retrieval/hybrid.py` | **Idea reused** (RRF, k=60). Its PostgreSQL/pgvector implementation was **not** reused: it needs a database service, and SQLite/in-memory is sufficient for 758 chunks. Boundary kept so pgvector can replace the dense leg later. |
| Decision register parser | this repository, `tools/decision_register.py` | **Imported** (single source of status truth). |
| D-54 term list | this repository, `tools/diet_audit.py` | **Kept in sync by test** (`test_forbidden_terms_are_a_superset_of_the_repo_diet_audit`). |
| Permission/exposure ideas | `mcp-weir` | **Concept only** (separate trust classes, refuse by default). The Weir gateway itself was **not** integrated: it solves information-flow control between untrusted MCP servers, which this single-server prototype does not have. Integration is a candidate for a later block. |
| Evaluation metrics | `llm-eval-framework` | **Not reused.** Its metrics target free-text LLM output (faithfulness, ROUGE); this lab's checks are structural (tool selection, citations, status, approval boundary). Wrapping them would add dependency without information. |
| Agent runtime benchmark | `agent-runtime-bench` | **Not reused.** It measures a real local model inside a different runtime; this lab has no model in the loop. |

Nothing was copied from a repository without being listed here.
