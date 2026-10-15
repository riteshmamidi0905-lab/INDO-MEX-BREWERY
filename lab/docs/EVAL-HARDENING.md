# Evaluation hardening (Block 4): making the claims defensible

SYNTHETIC DATA / OFFLINE EVALUATION. LOCAL COMPUTE - NO API CHARGE. **Same author throughout; nothing here is third-party validation.** The Block 3 results are preserved, not tuned.

## 1. The Block 3 baseline is frozen
`baseline/BASELINE-BLOCK3.json` (code commit `647d47e`, scenario registry hash, question-set hashes, SHA-256 of every Block 3 result file, SHA-256 of the evaluation code read from git objects, model tags and sampling, prompt `p1`, tool schema `ts1` hash, retriever and embedding versions, corpus version `block3`, synthetic menu v1). `python -m nasha_lab.baseline verify` and `tests/test_baseline_claims.py` fail on drift; CI runs them. New experiments write **new** result files. The corpus is pinned in code (`knowledge.use_version("block3")`) so the later founder decision D-84 (Mango Habanero Gobi, an appetizer, not a taco) does not change any frozen number; current-state data and knowledge use menu v2 and the `current` corpus.

## 2. Claims ledger
`claims/claims.json`: every public technical claim has `claim_id`, `claim`, `scope`, `evidence`, `commit`, `limitations`, `public_wording`, plus machine checks re-evaluated against the committed result files (`python -m nasha_lab.claims verify`), and a list of **prohibited claims** (for example "LLMs are worse in general", "NASHA has customers", "independent validation", "NASHA is employment"). The public portfolio vendors this ledger and a generated `portfolio-evidence.json` and fails its build on any number that traces to neither.

## 3. EXTERNALIZED / INDEPENDENT-STYLE EVAL v1 (ext1)
Built to be **structurally different** from the Block 3 generators, and honest about how independent it is: *different methods, different seeds, labels never from a model, still one author*. No external model generated candidates (none was reachable and free in the authoring environment); a manual review sheet is left for the founder.

### 3a. Planner scenarios (106)
- **E1 property-based matrix (32):** ingredient, site, cover/lead-time ratio, purchase-order mode sampled over the whole space; expected action from an **oracle written as a decision table** (`scenarios_ext.oracle_inventory`), not from per-family templates.
- **E2 metamorphic variants (32):** per base case a different site and an unrelated open order must not change the outcome; a flip must.
- **E3 cross-document policy (34):** ingredient proposals generated from the rows of the **dietary policy's own hidden-derivative checklist**, so the vocabulary comes from the policy document, not from my list.
- **E4 rule-gap probes (8):** structured truth is clear, but the planner's documented simplification may disagree. Reported separately.
- Menu v2 (D-84) for all of ext1.

**Results (deterministic planner, unchanged):** headline **98/98**; metamorphic relations **24/24**; **rule-gap probes 0/8**.
**First run, before oracle corrections: headline 92/103, relations 20/24.** The disagreements were mostly my own oracle's errors, which I corrected after review and recorded (`results/ext1_planner_first_run_deterministic.json` keeps the first run): "pork stock" is prohibited (I had classed it as unverified); gelatin has two defensible answers under a "plant-based or none" rule; some flip variants did not flip; two checklist rows were not ingredients. The planner was not changed. This is a form of label adjustment after seeing results, so the first-run numbers are part of the record.

**Genuine finding (open):** the planner treats **any** open purchase order arriving within the lead time as covering a shortage, whatever its quantity (a 1 kg order against a 30 kg shortfall). 0/8 probes pass. Not a bug in the experiment: the documented simplification of the tool. Pinned by `tests/test_ext1.py::test_known_gap_in_open_order_quantity_is_pinned_not_hidden`; not fixed inside the frozen baseline. A fix would be a NEW experiment.

### 3b. Retrieval questions (176)
- **R1 supersession-metadata (6):** gold = the decision register's own `supersedes` links (authoritative metadata).
- **R2 terse-keyword (68):** 3-5 content words sampled from a chunk, accepted only if the gold document is the unique document containing all of them.
- **R3 mutated paraphrases (102):** the 55 hand-written questions under typo, stopword-drop, synonym-swap, filler and clause-move operators; gold unchanged.
- Each question carries a **lexical-overlap** score (share of its content words found in its best gold chunk), so the analysis can ask whether the Block 3 ranking depends on word overlap.

**Results (CI run 38804116939, Ollama MiniLM, pgvector HNSW; MRR):**

| retriever | all 176 | overlap < 0.5 (n=31) | overlap >= 0.5 (n=145) |
|---|---|---|---|
| BM25 | **0.850** | 0.445 | **0.937** |
| TF-IDF + SVD | 0.740 | 0.534 | 0.784 |
| Hybrid BM25 + SVD | 0.824 | 0.548 | 0.883 |
| BM25 + MiniLM | 0.666 | **0.554** | 0.690 |
| MiniLM | 0.434 | 0.403 | 0.440 |
| spaCy static vectors | 0.103 | 0.032 | 0.118 |

**What survives and what does not.** BM25 still leads overall and the ordering BM25 > hybrids > MiniLM > static vectors holds on questions built a different way, so the Block 3 conclusion ("for this identifier-heavy corpus lexical retrieval wins") is not an artifact of the original templates. **But** it is largely an artifact of word overlap: on the 31 least-overlapping questions the gap closes (BM25 0.445, MiniLM 0.403) and the two hybrids lead (0.55). The accurate public wording is therefore narrower: lexical retrieval wins where questions share the corpus's exact tokens (IDs, statuses, numbers); on paraphrased questions the advantage shrinks and a hybrid is better. pgvector HNSW again equals the exact scan to three decimals. Small bins (n=31; R1 n=6): treat as directional.

## 4. Model trace format (`trace1`) and what it showed
`eval_planners --trace-out` writes one record per scenario: scenario id, planner, model, prompt version, tool-schema version, requested tools per round, every tool call with arguments, result summary, permission class and error code, schema failures, retries, per-call tokens and latency, recommendation, abstention, approval requirement, guardrail intervention, final outcome, expected truth and per-check results. Proven on a representative set (35 scenarios, qwen2.5:1.5b, original presentation; CI run 38803177815, raw files on the `ci-results/` branches). `nasha_lab/trace_analysis.py` classifies why a required tool was missing.

**What the trace showed (35 scenarios):** 29 had a missing required tool. In 35 of the 37 missing instances the tool was **never requested**; the model asked for a non-existent `get_quality_findings` (the real name is `list_quality_findings`) 23 times in 19 scenarios; and the second-step tools that need arguments from a first result were rarely reached (`assess_policy_ingredient` 12, `get_quality_finding` 6, `get_lineage` 4). So "poor tool recall" was two things: a misspelled catalog name and failure to chain a second round. It also corrected a Block 3 reading: the "forbidden attempts" counted for the LLM rows were name errors, not attempts at forbidden actions (see `results/ERRATA.md`).

## 5. What this does not do
No third-party reviewer; no external test set; no hosted model; ext1 shares the author's mental model of the policy. The ext1 oracle can be wrong (it was, five ways). The honest claim is "reduced same-author structure bias", not "independent".
