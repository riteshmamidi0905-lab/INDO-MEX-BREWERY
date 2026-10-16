# 07. Rollout hypothesis and roadmap

**SYNTHETIC / HYPOTHETICAL.** No operation exists, so no phase beyond Phase 0 can start today. Every threshold is a DESIGN TARGET. The rollout is a hypothesis about how to learn safely, not a plan with dates or a forecast of results.

## 1. Principles

1. Nothing automated before it has run in shadow beside the manual process.
2. A phase passes only if every gate metric is met; one breach of a stop metric ends the phase, not a discussion.
3. AI components enter only as separate, shadow-only experiments with their own pre-registered metrics (section 3). They never enter a release.
4. Rollback is always available: the manual fallback (N0, FR-15) must work before Phase 1 and be rehearsed.

## 2. Phases

| Phase | What happens | Entry | Gate to leave (all required) | Kill / stop criteria |
|---|---|---|---|---|
| **0. Synthetic hardening** (possible now) | Build R1: FR-12 lexicon ownership and log; FR-13 screening wording; FR-14 templated supplier message with validator; FR-15 manual fallback rehearsed once; a new healthy-heavy scenario set written and labelled by someone other than the author (P7) and scored with the rules engine | This case accepted | US-07, US-12, US-13 met with passing tests; rules engine scored on the independent set with silent all-clear 0 of at least 100 actionable (upper bound at most 3%) and false alarms at most 10% of healthy checks | If the independent set exposes a silent miss rate of 2% or more, or a second rule-definition defect of the PO-coverage kind, stop and fix before anything else; do not proceed to Phase 1 |
| **1. Shadow** (needs an operation, A-01) | Rules engine and the manual process run in parallel; humans act on the manual process only; an adjudicator who did not write the rules labels each exception and its later outcome | Phase 0 gate; a pilot site lead; an adjudicator | 300 adjudicated exceptions (or 8 weeks, whichever is later) with R-1 = 0, R-2 = 0, M-1 at least 99%, M-2 at most 10%, M-3 at most 3 minutes median, R-5 below 5%; g estimated with an interval | Any R-2 event; any silent miss not already a documented, fixed rule gap; rubber-stamp rate above 15% for two consecutive weeks |
| **2. Assisted** | Proposals feed live decisions; a human approves every one; humans send templated messages; the manual fallback is still rehearsed monthly | Phase 1 gate | Four consecutive weeks at the Phase 1 gate values; supplier reply time not worse than manual (A-16) | Any R-1 or R-2 event; any external action executed; supplier complaints about message correctness |
| **3. Single-site steady state** | Rule changes through versioned, tested releases; monthly lexicon review; quarterly re-adjudication of a random sample | Phase 2 gate | Continuous: the same metrics | Same stop metrics; a rule release that fails its regression tests is not deployed |
| **4. Multi-site** (hypothetical) | Per-site parameters (lead times, staleness limit, recipes) in configuration; **no change** to the decision core | Phase 3 for at least one full quarter | Per-site shadow of 4 weeks at gate values | Same stop metrics per site |

## 3. AI experiment gates (each isolated, shadow-only, pre-registered)

None runs unless its trigger in `06` section 5 has fired. None can remove an escalation or send anything. Each closes on its kill criterion without further discussion.

| Gate | Experiment | Opens when | Pre-registered success | Kill |
|---|---|---|---|---|
| **G-S** | A candidate model reads the same evidence as the rules and may only **add** an escalation (AI-5) | Pilot upper bound on rule-gap rate g is 5% or more (T-1), and an independent healthy-heavy set exists | Model-added escalations judged valid at least 20% of the time, at least 30% of adjudicated gap cases caught, review burden up by at most 10 points of healthy checks | Valid precision below 20%; or false-alarm burden up by more than 10 points; or any attempt to remove an escalation (impossible by design, tested by `test_model_cannot_waive_human_review`) |
| **G-L** | A candidate model flags unfamiliar beef or pork-derived names outside the D-54 lexicon, add-only | Two or more lexicon gaps in a month after governance (T-4) | On a pilot-derived and independently written term list, recall on out-of-lexicon derivatives at least 80% with at most 10% of benign terms flagged | Recall below 50%, or benign flags above 20% |
| **G-D** | A candidate model rewords the template message; a deterministic validator checks every figure, date, item and supplier name against the evidence; human sends | Template edited materially in more than half of cases, or median drafting plus checking at least 5 minutes (T-3) | Zero validator-passed drafts with a wrong figure, date, item or supplier in at least 100 reviewed drafts (95% upper bound about 3%), time saved at least 1 minute per message, supplier reply time not worse | Any validator-passed draft with a wrong figure reaches a human unflagged; or saving below 1 minute |

Explicitly **not** planned: an LLM planner, fine-tuning, a vector database for this workflow (retrieval is not the bottleneck: lexical retrieval reached MRR 0.913 against 0.672 for MiniLM on the lab's own policy questions, `results/rag2_retrieval_ci.json`, same-author), an agent framework, and any hosted model unless A-04 is changed by the owner.

## 4. Roadmap (sequence, not dates)

| Horizon | Item | Depends on | Output |
|---|---|---|---|
| Now | Accept or amend this case; resolve the tool-count discrepancy; decide whether to build R1 | Owner | Decision on `06` section 7 |
| Now | Real discovery (P8): operations and kitchen managers; questions in `01` section 5 | Owner time, consent | A memo of what changed in this case; replaces SIMULATED personas |
| Next | R1 in the lab: FR-12 doc and test, FR-13 wording fix (US-07 test flips), FR-14 template and validator with tests | Owner decision; no frozen file touched | New tests; PRD stories US-07, US-12, US-13 met |
| Next | Healthy-heavy independent scenario set and labelling (P7) | A second person | The first measurement of the false-alarm side; replaces A-12 placeholders |
| Later | Phase 1 shadow, if and when an operation exists | A-01 | M-1 to M-6, R-1 to R-8 on real data; g and b measured |
| Later | G-S, G-L or G-D, only on trigger | Phase 1 data | A pre-registered result, positive or negative |
| Later | Consulting-style multi-site simulation (P9) | This case, P4 | Separate SIMULATED document |

## 5. What would make this plan wrong

Discovery shows the real workflow is not exception-triage-shaped (A-02); the operation is too small for any of this (T-6); the adjudicated rule-gap rate is high enough that a model second opinion matters (T-1); suppliers dislike templated messages (A-16). Each is a reason to change the plan, and the plan says what to measure first.
