# Evaluation (OFFLINE EVALUATION on SYNTHETIC data; same-author)

Protocol: seeds 1-5, 8 injected defects per type per seed (40 per type), each defect isolated on its own row; labels kept apart from the rules. Precision and recall per rule; a separate clean dataset (no injections) must produce **0** findings. Reproduce: `python -m nasha_lab.evaluate v1`.

| rule | injected | recall | precision |
|---|---|---|---|
| duplicate_order, future_timestamp, malformed_timestamp, missing_location, order_total_mismatch, orphan_item, nonpositive_qty, price_drift, unit_mismatch | 40 each | 1.0 | 1.0 |
| forbidden_protein (D-54) | 15 (3 per seed) | 1.0 | 1.0 |
| near_duplicate_order | 40 | 1.0 (v0: **0.0**) | 1.0 |
| near_duplicate_shifted (copy +1 s) | 40 | **0.0** | n/a |

**How to read this.** Perfect scores on easy, author-designed defects are expected and are **not** evidence of real-world quality. What is evidence: the evaluation can fail (v0 baseline), a failure was fixed by a specific change, one real pipeline bug was caught by the conservation invariant, tests catch deliberately broken rules, and a known gap is recorded rather than hidden.

**Failures found and handled**
1. `near_duplicate_order` undetected in v0 (recall 0.0) -> added the signature rule -> 1.0, clean run still 0 findings.
2. Dedup quarantined *both* copies of a duplicated order (found: 16 quarantined for 8 injected) -> fixed -> regression test compares order count and revenue to the clean dataset.
3. Over-broad substring matching of D-54 terms would flag "chamoy" ("ham") -> word-boundary regex + test.
4. Mutation check (manual): tolerance 0.25 -> 0.05 broke 5 tests; inverting the total check broke 6.

**Open gaps** (not fixed, deliberately): +1 s shifted duplicates (a time-window rule would add false-positive risk and needs a labelled false-positive set first); defect combinations on one row; real-world distributions; any claim about real restaurants.
