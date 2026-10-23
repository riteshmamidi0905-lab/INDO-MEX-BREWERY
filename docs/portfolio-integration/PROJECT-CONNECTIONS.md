# How the three projects connect — actual integration status
| Project | Role in this system | Status |
|---|---|---|
| **NASHA Enterprise AI Lab** (this repository) | Synthetic business, data pipeline, scenario tables, Ops AI tools, governed workflow, API. | Implemented and tested. |
| **THE WEIR** (`mcp-weir`, separate repository, pinned commit) | Per-role default-deny policy, held writes, single-use call-bound approvals, tamper-evident gateway audit. | **Imported and exercised for real** (not mocked) by `nasha_lab/warehouse/ops_ai_weir.py` and `nasha_lab/governed/`; tests skip with a stated reason when it is not installed. |
| **Production AI Agent Platform** (separate repository) | Source of ideas and adapted code (hashing embeddings, reciprocal-rank fusion). | **Not integrated**: no import, no shared runtime, no shared database. The NASHA agent is its own small governed planner behind the WEIR. Do not present NASHA as running on the platform. |
| `rag-doc-qa` (`ragqa`) | TF-IDF retriever baseline. | Pinned dependency, used by the knowledge base. |
| `llm-eval-framework` (`llmeval`) | LLM evaluation project. | Installed locally; **not imported** by NASHA. |
