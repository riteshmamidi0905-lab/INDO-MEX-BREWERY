# Retrieval evaluation v2 - CI numbers (GitHub Actions run 38786430242, commit cd6078d)

SYNTHETIC DATA / OFFLINE EVALUATION. 467 questions (412 generated + 55 hand-written), 13 categories. Free runner: Ollama all-minilm (46 MB), spaCy en_core_web_md, pgvector 0.8.7 on PostgreSQL 16 (HNSW m=16, ef_construction=64, cosine). LOCAL COMPUTE - NO API CHARGE.
Recovered from the job log (artifact download is blocked in the authoring sandbox).

| retriever | R@1 | R@5 | MRR | nDCG@10 | held-out R@5 | held-out MRR | hand-written MRR | generated MRR | authority-correct | ms/query |
|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.831 | 0.951 | 0.913 | 0.925 | 0.954 | 0.909 | 0.764 | 0.935 | 0.87 | 7.34 |
| lsa (SVD, not neural) | 0.696 | 0.912 | 0.819 | 0.844 | 0.95 | 0.849 | 0.739 | 0.83 | 0.731 | 6.95 |
| hybrid (bm25+tfidf+hash RRF) | 0.76 | 0.935 | 0.86 | 0.882 | 0.95 | 0.885 | 0.794 | 0.87 | 0.796 | 5.43 |
| static_neural (spaCy md 300d) | 0.202 | 0.301 | 0.259 | 0.282 | 0.326 | 0.255 | 0.106 | 0.28 | 0.207 | 8.21 |
| hybrid_static (bm25+static) | 0.412 | 0.883 | 0.627 | 0.702 | 0.862 | 0.65 | 0.493 | 0.646 | 0.431 | 8.04 |
| pgvector_static (HNSW) | 0.202 | 0.301 | 0.259 | 0.282 | 0.326 | 0.255 | 0.106 | 0.28 | 0.207 | 9.05 |
| minilm (all-MiniLM-L6-v2, 384d) | 0.574 | 0.749 | 0.672 | 0.69 | 0.803 | 0.691 | 0.553 | 0.689 | 0.601 | 333.33 |
| hybrid_minilm (bm25+minilm RRF) | 0.733 | 0.933 | 0.842 | 0.866 | 0.959 | 0.854 | 0.713 | 0.861 | 0.762 | 4.5 |
| pgvector_minilm (HNSW) | 0.574 | 0.749 | 0.672 | 0.69 | 0.803 | 0.691 | 0.553 | 0.689 | 0.601 | 6.38 |

Per-category MRR (categories with a gold document; UNANSWERABLE / OUT-OF-DOMAIN have no gold doc and are scored by abstention, see `abstention_end_to_end.json`):

| retriever | ADVERSARIAL | CONFLICTING | D54 | DECISION_STATUS | DIRECT | MULTI_DOCUMENT | NUMERIC | OPERATIONAL | SUPERSEDED | UNVERIFIED | VISION |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.173 | 0.667 | 0.974 | 0.846 | 0.942 | 0.706 | 0.842 | 0.985 | 0.844 | 0.948 | 1.0 |
| lsa | 0.306 | 0.7 | 0.851 | 0.784 | 0.826 | 0.767 | 0.27 | 0.99 | 0.875 | 0.942 | 0.986 |
| hybrid | 0.281 | 0.667 | 0.965 | 0.813 | 0.904 | 0.707 | 0.456 | 0.985 | 0.812 | 0.94 | 1.0 |
| static_neural | 0.022 | 0.067 | 0.092 | 0.019 | 0.231 | 0.079 | 0.004 | 0.604 | 0.052 | 0.506 | 0.281 |
| hybrid_static | 0.079 | 0.28 | 0.6 | 0.442 | 0.606 | 0.561 | 0.297 | 0.905 | 0.625 | 0.819 | 0.708 |
| minilm | 0.12 | 0.205 | 0.782 | 0.294 | 0.798 | 0.425 | 0.239 | 0.952 | 0.362 | 0.903 | 0.941 |
| hybrid_minilm | 0.196 | 0.667 | 0.921 | 0.605 | 0.896 | 0.726 | 0.731 | 0.974 | 0.667 | 0.962 | 1.0 |

pgvector rows equal their exact-scan counterparts to three decimals (HNSW at this corpus size loses no recall).
