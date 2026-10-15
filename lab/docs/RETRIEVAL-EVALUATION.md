# Retrieval, neural embeddings, pgvector and abstention (Block 3)

**OFFLINE EVALUATION, same author, generated + hand-written questions.** Supersedes the retriever comparison in `RAG-EVALUATION.md` (kept as history). Numbers: `results/rag2_retrieval.json`, `results/abstention_*.json`.

## Question set (467)
412 **generated** (template-based from corpus metadata, structurally validated: gold documents exist, evidence terms occur in the gold chunk, expected status equals the corpus status) + 55 **hand-written** paraphrases from Block 2. 13 categories: DIRECT, MULTI_DOCUMENT, DECISION_STATUS, SUPERSEDED, UNVERIFIED, VISION, UNANSWERABLE, D54, CONFLICTING, NUMERIC, OPERATIONAL, ADVERSARIAL, OUT_OF_DOMAIN. Split: dev 318 / held-out 149. Content questions are split by **source document**; unanswerable ones by **template family** (dev and held-out share no template except the missing-decision-id family, which is split by id).

**Remaining bias, stated plainly:** generated questions copy words from their source text, which flatters lexical retrieval; one author wrote the templates and chose the unanswerable topics; the hand-written subset is small (n=45 with gold documents). Read results by source, not only in aggregate.

## Retrievers
| name | what | notes |
|---|---|---|
| `bm25` | BM25 | pure Python |
| `lsa` | TF-IDF + truncated SVD | dense but **not neural** |
| `hybrid` | RRF(BM25, LSA) | Block 2 default |
| `static_neural` | spaCy `en_core_web_md`, 300-d static word vectors, mean-pooled, L2-normalised, cosine, exact scan | a real pretrained neural embedding, **not a sentence encoder** |
| `hybrid_static` | RRF(BM25, static_neural) | |
| `pgvector_static` | the same vectors in PostgreSQL 16 + pgvector 0.6, HNSW (m=16, ef_construction=64), cosine `<=>` | proves the storage path; ANOTHER retriever, nothing depends on it |
| `minilm`, `hybrid_minilm`, `pgvector_minilm` | all-MiniLM-L6-v2 (384-d sentence embeddings) via Ollama | **CI only** (model hosts blocked in the sandbox); see the table at the end |

## Results (all 467 questions; MRR; held-out in brackets)
| retriever | MRR | Recall@1 | Recall@5 | hand-written MRR (n=45) | generated MRR | authority-correct top-1 |
|---|---|---|---|---|---|---|
| **bm25** | **0.913** (0.909) | 0.831 | 0.951 | 0.764 | 0.935 | 0.87 |
| lsa | 0.819 (0.849) | 0.696 | 0.912 | 0.739 | 0.830 | 0.73 |
| hybrid | 0.860 (0.885) | 0.760 | 0.935 | **0.794** | 0.870 | 0.80 |
| static_neural | 0.259 (0.255) | 0.202 | 0.301 | 0.106 | 0.280 | 0.21 |
| hybrid_static | 0.627 (0.650) | 0.412 | 0.883 | 0.493 | 0.646 | 0.43 |
| pgvector_static | 0.247 (0.232) | 0.194 | 0.291 | 0.094 | 0.268 | 0.20 |

Per category (MRR, BM25 / hybrid / static): DIRECT .94/.90/.23, OPERATIONAL .99/.99/.60, UNVERIFIED .95/.94/.51, VISION 1.00/1.00/.28, D54 .97/.97/.09, DECISION_STATUS .85/.81/.02, NUMERIC .84/.46/.00, SUPERSEDED .84/.81/.05, CONFLICTING .67/.67/.07, MULTI_DOCUMENT .71/.71/.08, ADVERSARIAL .17/.28/.02 (n=3). Full table: `results/rag2_retrieval.json`.

**What this says.**
1. **Static neural vectors do not justify their complexity here**: mean-pooled word vectors lose the identifiers (`D-54`, dates, statuses) that this corpus is organised around (DECISION_STATUS .02, NUMERIC .00). Fusing them with BM25 *lowers* MRR (0.86 -> 0.63 for hybrid_static vs BM25 0.91).
2. **pgvector works as a retriever** (built, indexed with HNSW cosine, queried), and its HNSW search is slightly *worse* than the exact scan of the same vectors (MRR 0.247 vs 0.259): approximate search costs recall; at 758 chunks an exact scan is faster to reason about. pgvector is justified when the corpus or concurrency grows, not at this size.
3. The Block 2 decision “hybrid beats BM25” **does not survive the larger set on generated questions** (0.86 vs 0.91) but holds on hand-written paraphrases (0.794 vs 0.764, n=45, within noise). Default left as hybrid as a judgment call; BM25 is the right default if questions look like the corpus.
4. Authority correctness (the top-1 chunk is the gold document with the expected status) is the weakest metric for every retriever (BM25 0.87): retrieval alone does not give status correctness; the status-aware filter and the answer layer do.

## Abstention (answer vs refuse)
Label: should-answer = not `must_abstain`. Eight strategies; every threshold or parameter fit on **dev only**; table is **held-out** (149 questions: 66 should refuse, 83 should answer).
| strategy | accuracy | false answers (answered, should refuse) | false abstentions |
|---|---|---|---|
| S0 built-in rules (coverage, OOV, numeric) | 0.859 | 19/66 | 2/83 |
| S1 BM25 score threshold | 0.443 | 0/66 | 83/83 |
| S2 evidence-coverage threshold | 0.671 | 10/66 | 39/83 |
| S3 rare-term coverage | 0.570 | 2/66 | 62/83 |
| S4 authority rule (authoritative evidence, no dominating non-authoritative match) | 0.852 | 12/66 | 10/83 |
| S5 combined rule (grid search) | 0.570 | 2/66 | 62/83 |
| S6 logistic regression on 14 retrieval features | 0.906 | 11/66 | 3/83 |
| **S7 S0 AND S6 (shipped)** | 0.899 | **10/66** | 5/83 |

Single thresholds collapse into “always refuse” (S1, S3, S5): the score distributions of answerable and unanswerable questions overlap. The learned gate with the built-in rules is the best trade.

**End-to-end (`ask`, held-out): false answers 28.8% -> 15.2% (19/66 -> 10/66), false abstentions 2.4% -> 6.0% (2/83 -> 5/83), accuracy 0.859 -> 0.899.** Block 2’s two known quantity-question gaps (“How many customers…”, “How many beer batches…”) are closed.

**Not settled.** (a) 15% of questions that should be refused are still answered. (b) A gate trained on generated questions over-refused hand-written paraphrases (hand-written dev accuracy .842 -> .632); it was re-selected by 5-fold CV on dev with paraphrases weighted 3x, giving hand-written dev .842 -> .789 but hand-written held-out (n=17) .824 -> .941. Small samples; the sign of the effect on paraphrases is unresolved. (c) The gate is a classifier over lexical features; neural features could change this.

## MiniLM and pgvector on MiniLM (CI)
See `results/rag2_retrieval_ci.md` once the `retrieval-eval` job has run (model-eval workflow).

## Reproducibility note (found in CI)
The first CI run reproduced everything except the **pgvector HNSW retriever**: per-category numbers differed by up to 0.5 on categories with 3–8 questions, because an approximate index builds a different graph on each build. `repro_check` now compares HNSW only at the aggregate level (tolerance 0.06); exact retrievers must match exactly (BM25) or within 0.03 (SVD / neural, library-version sensitive).
