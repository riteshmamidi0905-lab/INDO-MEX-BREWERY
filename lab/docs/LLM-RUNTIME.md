# Local model selection and environment

**Rule for this block:** free and local only. No paid API, no credits, no hosted database.

## What the authoring sandbox offers
4 vCPU, 15 GB RAM, no GPU, no Docker daemon. No local model runtime was installed (no Ollama, llama.cpp, Transformers, PyTorch). Model hosts are blocked by the egress policy: `huggingface.co` returns 403 (also for the free `fastembed` download), `ollama.com` and `registry.ollama.ai` are unreachable, GitHub release downloads of **spaCy** models work. So a credible LLM and a sentence-embedding model **cannot run in the sandbox**: ENVIRONMENT LIMITATION, not a code failure. The planner adapter, the structured-output schema, the bounded retry policy and the whole harness are tested here with a stub Ollama HTTP server and scripted stand-ins; the real-model integration test is marked `INTEGRATION UNAVAILABLE` and skips loudly.

## Where a real model runs: GitHub-hosted runner (free for public repositories)
`model-eval.yml` installs the **Ollama** runtime on an `ubuntu-latest` runner (4 vCPU, 16 GB, no GPU), pulls the model, and runs the same harness. It is **not** part of the fast CI (trigger: manual, or a change to `lab/eval-trigger/model-eval.txt`). Probe result (run 38774221889): Ollama 0.40.4 installs in ~40 s; `qwen2.5:1.5b-instruct` (986 MB download) answers a schema-constrained request at ~32 tokens/s; `all-minilm` returns 384-d vectors.

## Model chosen: Qwen2.5-1.5B-Instruct
| | |
|---|---|
| model / tag | `qwen2.5:1.5b-instruct` (Alibaba Qwen team) |
| licence | Apache-2.0 |
| size | 986 MB on disk (4-bit quantisation, see the model card printed by `ollama show` in the run log) |
| runtime | Ollama, CPU only, temperature 0, fixed seed, grammar-constrained JSON (`format` = JSON schema), 6144-token context |
| why | smallest instruction model that handles JSON schemas and short tool-selection prompts at a speed that makes 100+ scenarios feasible on 4 vCPU; permissive licence |
| rejected | `qwen2.5:0.5b` (too weak for tool choice), `qwen2.5:3b` (Qwen-research licence, non-commercial), `qwen2.5:7b` was not rejected but is slow on 4 vCPU (median 152 s per scenario): it was run once on 35 scenarios (held-out B + adversarial, one per family) as a scale probe, see [PLANNER-EXPERIMENT.md](PLANNER-EXPERIMENT.md) |

Second model: `qwen2.5:7b-instruct` (Apache-2.0, 4.7 GB, Q4_K_M, same runtime and sampling), run 38787190128. A 1.5B model is a deliberately weak LLM. The result answers “does a *small free local* model beat a deterministic planner here?”, not “can any LLM?”.

## Embedding models
| name in reports | what it is | where measured |
|---|---|---|
| `dense_hashing`, `dense_lsa` | hashing / LSA vectors. **Not neural embeddings.** | sandbox + CI |
| `static_neural` | spaCy `en_core_web_md` (MIT), 300-d **static** word vectors, mean-pooled, L2-normalised, cosine, exact scan | sandbox + CI |
| `minilm` | `all-minilm` = sentence-transformers all-MiniLM-L6-v2 (Apache-2.0), 384-d sentence embeddings via Ollama, L2-normalised, cosine, exact scan | CI only |
| `pgvector_*` | the same vectors stored in PostgreSQL 16 + pgvector (0.6 in the sandbox, 0.8.7 in CI), HNSW (m=16, ef_construction=64), cosine `<=>` | sandbox (apt Postgres) and CI (service container) |

Chunking for all of them: heading-split markdown, at most 1,800 characters, title and heading path prepended.
