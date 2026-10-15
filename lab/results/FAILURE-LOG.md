# Failure log (Block 2)

First execution of the failure-injection suite: **20 / 22 passed, 2 failed.** Both were investigated; one was a real defect, one was a wrong test expectation.

| # | Failing case | Cause | Verdict | Fix | Regression test |
|---|---|---|---|---|---|
| 1 | `supplier_lookup_failure` | With goat cover (2.6 d) below the 5-day lead time, the supplier-status tool failed. The planner required the supplier list to propose a draft, skipped that branch, and fell through to **`NO_ACTION`**: a silent "all clear" on partial evidence while stock was short. | **Real implementation weakness** | A short-cover result with no confirmed supplier now escalates (`ESCALATE_INSUFFICIENT_EVIDENCE`, abstain). `NO_ACTION` is impossible whenever any non-injection tool gap exists. | `tests/test_agent.py::test_supplier_lookup_failure_never_becomes_no_action` and the suite case of the same name |
| 2 | `edit_path_validates_and_reviews_again` | The review loop was capped at 3 human decisions; the test used 3 edits plus an approval. | Test expectation vs. design parameter | Cap raised to 5 (still bounded); the bound itself is tested (`more_evidence_round_is_bounded`). | same suite case |

Earlier in the block (knowledge layer), the same discipline found and fixed: superseded decisions still ACTIVE in the register (D-59 -> D-62), OOV-term paraphrase false abstentions (accent normalisation), and a status question being answered from a weaker authoritative neighbour (explicit-decision rule). See `docs/RAG-EVALUATION.md`.
