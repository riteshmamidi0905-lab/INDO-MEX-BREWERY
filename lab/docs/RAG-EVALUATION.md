# Status-aware knowledge retrieval: design and evaluation

**OFFLINE EVALUATION. Author-written golden set (n=55) over the real NASHA corpus (758 chunks from 82 sources). Same author wrote the corpus tooling, the questions and the scorer; no independent review. Small samples: descriptive, not proof of production quality.**

## Ingestion policy (not "index the repository")
| Source | Treatment |
|---|---|
| `docs/decisions/DECISIONS.md` | one chunk per decision; status and classification from `tools/decision_register.py` (reused); supersession declared by a later decision is propagated (D-62 supersedes D-59) |
| `docs/company/data/document-map.csv` | authority class of each mapped file; **generated dashboards excluded** (derived from CSV sources) with the reason recorded in the manifest |
| `food/DIETARY-POLICY...`, `docs/company`, `docs/decisions/*.md`, `food/*.md` | CANONICAL when mapped, otherwise SUPPORTING |
| `research/*.md` | UNVERIFIED RESEARCH (never authoritative) |
| `vision/*.md` | VISION (not evidence) |
| website/, images, prompts, send packs, CSV data | excluded |

Every chunk carries `document_id, source_path, title, document_type, decision_status, verification_status, effective_status, authority_rank, updated_at (git date), supersedes/superseded_by`. Effective statuses: CURRENT, FROZEN (authoritative); PROVISIONAL, SUPPORTING (usable, always labelled); PENDING, SUPERSEDED, HISTORICAL, VISION, UNVERIFIED, INTERNAL (never the basis of an answer).

## Retrievers compared (all free, local)
| | what | note |
|---|---|---|
| A0 `tfidf` | TF-IDF index from the existing `rag-doc-qa` project, reused unmodified | baseline |
| A1 `bm25` | BM25 written for this lab | baseline |
| B1 `hashing` | signed feature-hashing dense vectors, adapted from `production-ai-agent-platform` | |
| B2 `lsa` | TF-IDF -> truncated SVD dense vectors | **not a neural embedding** |
| C `hybrid` | reciprocal-rank fusion of BM25 and LSA (RRF as in `production-ai-agent-platform`) | |
| `hybrid_hash` | BM25 + hashing | |
| D | status-aware filter and ranking, applied on top of any of the above | |

**Neural embeddings were not available**: the sandbox's model host returned 403 for a free local model download (ENVIRONMENT LIMITATION, not a code failure). The retriever interface is a single `search(query, k)` method, so a neural embedder can be added without touching the rest; the hybrid result below should be re-measured when one is.

## Results (document-level, all 55 questions unless stated)
| retriever | Recall@1 | Recall@5 | Recall@10 | MRR | nDCG@10 | top-5 non-authoritative share (status-blind) |
|---|---|---|---|---|---|---|
| tfidf (A0) | 0.52 | 0.86 | 0.90 | 0.74 | 0.75 | 0.31 |
| bm25 (A1) | 0.58 | 0.82 | 0.93 | 0.76 | 0.79 | 0.32 |
| hashing (B1) | 0.30 | 0.49 | 0.62 | 0.43 | 0.46 | 0.40 |
| lsa (B2) | 0.50 | 0.86 | 0.96 | 0.74 | 0.77 | 0.33 |
| **hybrid (C)** | **0.60** | **0.88** | 0.93 | **0.79** | **0.81** | 0.32 |
| hybrid_hash | 0.38 | 0.74 | 0.86 | 0.58 | 0.63 | 0.35 |

With the status-aware filter the non-authoritative share of the top 5 is **0.0 for every retriever** (down from 0.31 to 0.40). That is the measured benefit of using status; it is by construction an exclusion rule, so it is a property check, not a discovery.

**Decision.** Keep `hybrid` (best MRR and nDCG, best R@1/R@5). Reject hashing vectors (clearly worse). BM25 alone is within noise of hybrid on this small set (held-out test split: BM25 MRR 0.77, hybrid 0.82, n=14 answerable); the hybrid is retained because it costs about 10 ms and is the more robust choice for paraphrased questions, not because the data proves a large gap. Reranking was not added: no failure analysis pointed at it.

## Answer layer (`ask`): extractive, authoritative-only, abstains
Hybrid retriever, 55 questions: abstention accuracy 0.84; citation hit rate 0.85 (citations include a gold document); citation precision 0.40 (many extra citations: the answer cites up to 4 chunks); **status violations 0** (nothing non-authoritative was ever cited); **must-not-cite violations 0**; must-not-contain violations 0; ungrounded answers 0 (extractive, so groundedness is nearly trivial; reported for completeness); p95 latency about 10 ms.

**Unsupported-answer rate on unanswerable questions: 0.5 (5 of 10)** after the fixes below. The system answers some questions it should refuse because a lexical overlap with loosely related prose looks like support. Two of these are pinned as strict `xfail` tests (`How many customers visited NASHA last week?`, `How many beer batches ...?`). The agent layer mitigates this by taking facts from typed tools and using `ask` only for policy.

## What measurement found and what was changed
1. A first pass answered 7 of 10 unanswerable questions (`capital of France` matched "Capital and Austin market"). Added IDF-weighted question-term coverage and an out-of-vocabulary rule. Thresholds were chosen on the **dev split only** and then checked on the held-out split (final abstention accuracy: dev 0.84, held-out test 0.82, n=17).
2. Decisions still marked ACTIVE in the register but superseded by a later decision (D-59 by D-62) were returned as current. The knowledge layer now derives supersession from the `supersedes` field (test: `test_supersession_is_derived_not_just_copied`).
3. A question about a PENDING proposal (D-77) was answered from a weaker authoritative neighbour. Added an explicit-decision-id rule and a dominance rule: the answer is an abstention that names the status.
4. Accent normalisation (`consomme` == `consommé`); a numeral rule for quantity questions (an `H1` table label is not a number).
5. Gold-label corrections made after seeing results (disclosed): two evidence terms that were in headings rather than chunk text; Q53 (`approve the purchase of pork shoulder`) relabelled from "answer" to "abstain", because refusing a command is the correct behaviour.

## Limits
Lexical abstention cannot reliably separate "answerable" from "topically adjacent". No semantic contradiction detection between two CURRENT documents (precedence rule only: decisions outrank documents). The injection heuristic is a regex and misses paraphrases (documented test). Small golden set, same author.
