# 04. Product requirements document and user stories

**SYNTHETIC.** This PRD describes a product for a hypothetical operation. Users are SIMULATED. Targets are DESIGN TARGETS. "Traced" means a named test exists in `lab/tests/` and passes at this commit; "UNTRACED" means no test exists and the story is not met yet. `tests/test_product_case_traceability.py` checks that every test named below exists.

## 1. Overview

**Product.** An inventory-exception assistant that detects shortages and unreliable counts, calculates coverage, screens supplier substitutions against D-54, proposes one of five outcomes with cited evidence, drafts (templated) supplier messages, and stops for a human who approves the exact action. It never contacts a supplier.

**Recommendation embodied in the PRD (see `06-decision-memo.md`).** The decision core is deterministic. AI is not in the decision path. Two AI uses are held behind experiment gates (file 07) and are not part of any release.

## 2. Goals and non-goals

| Goals | Non-goals |
|---|---|
| Zero silent all-clears on real exceptions in the acceptance window (NFR-01) | Replacing the human approver |
| Zero D-54 false clears (NFR-02) | Any claim about real demand, savings or performance |
| Proposals a reviewer can check in under 3 minutes (NFR-09) | Auto-ordering, auto-messaging, any external action |
| A manual fallback that always works (FR-15) | A learned forecaster (no real history exists; out of scope) |
| Every number traceable to a file or an assumption id | Making an LLM look good; the case tests whether one is needed |

## 3. Scope by release

| Release | Contents | Status |
|---|---|---|
| R0 (exists, synthetic) | T1 to T4, T6, T7 as rules and tools; draft as structured recommendation; signed approval; trace | Built in the lab; 259 of 259 synthetic scenarios |
| R1 (proposed) | FR-12 lexicon owner and log; FR-13 screening wording; FR-14 templated supplier message with validator; FR-15 manual fallback rehearsed; FR-16 healthy-heavy evaluation set | Not built |
| R2 (gated experiments, not releases) | G-S add-only second opinion in shadow; G-L add-only derivative flagger in shadow; G-D LLM drafting behind the R1 validator | Not started; gates in file 07 |

## 4. User stories and acceptance criteria

Format: Given / When / Then. Personas are SIMULATED.

| ID | Story (SIMULATED persona) | Acceptance criteria | Trace |
|---|---|---|---|
| US-01 | As the operations manager I want a shortage flagged when cover is below lead time and no sufficient order is coming, with a draft quantity | Given cover below the supplier lead time and no open order, when the event is processed, then the action is DRAFT_PURCHASE_RECOMMENDATION with a quantity not below the supplier minimum and nothing is sent | `tests/test_tools.py::test_scenario_a1_low_cover_has_a_draftable_quantity`; `tests/test_agent.py::test_each_scenario_proposes_the_expected_action_and_stops_for_a_human` |
| US-02 | As the operations manager I do not want an order of any size to hide a shortage | Given an open order smaller than the need through lead time, when assessed, then the shortage is not resolved and the draft accounts for the order; a late order never counts; several in-time orders are summed; equality covers | `tests/test_po_coverage.py::test_partially_covering_po_does_not_and_the_draft_accounts_for_it`, `::test_late_po_never_counts_however_large`, `::test_multiple_pos_are_summed_but_only_those_arriving_in_time`, `::test_boundary_equal_quantity_covers_and_a_hair_less_does_not`; `tests/test_ext1.py::test_block45_quantity_aware_rule_closes_the_rule_gap_probes_and_keeps_the_rest` |
| US-03 | As the kitchen lead I want a specific recount request when a count is stale, missing, wildly off or superseded by a quarantined one, not a purchase | Given such a count, when assessed, then the action is REQUEST_RECOUNT and usable stock is treated as zero | `tests/test_tools.py::test_scenario_a2_stale_and_quarantined_count_is_flagged`, `::test_scenario_a3_count_variance_is_detected`; `tests/test_po_coverage.py::test_stale_or_quarantined_inventory_is_not_usable_and_asks_for_a_recount_instead_of_no_action` |
| US-04 | As the founder-approver I never want "no action" when a check failed | Given a failed or missing check, when the proposal is formed, then NO_ACTION is impossible and the action is an escalation naming the failed check | `tests/test_agent.py::test_supplier_lookup_failure_never_becomes_no_action`; `tests/test_planner_units.py::test_missing_supplier_evidence_escalates_even_when_no_gap_was_recorded`, `::test_a_recorded_gap_blocks_no_action_even_when_the_data_looks_healthy` |
| US-05 | As the founder-approver I want a draft that is valid and plainly a draft | Given a draft request, then the supplier must be active and supply the item, the quantity must be at least the minimum, and the status is DRAFT_NOT_SUBMITTED | `tests/test_tools.py::test_draft_rules`; `tests/test_agent.py::test_draft_purchase_is_a_draft_not_an_order` |
| US-06 | As the founder-approver I want substitutions screened against D-54 and never auto-cleared | Given a proposal text, then a listed term gives PROHIBITED; a negated claim is a claim; a hidden-derivative word needs a written source; a term the lexicon does not know yields an abstention, never a recommendation to confirm; nothing is approved without a human | `tests/test_tools.py::test_policy_screening_verdicts`, `::test_hidden_derivative_terms_come_from_the_dietary_specification`; `tests/test_product_case_stories.py::test_us06_out_of_lexicon_derivative_is_never_cleared_by_the_system`, `::test_us06_even_with_a_supplier_statement_naming_a_permitted_source_the_outcome_is_human_confirmation_not_approval` |
| US-07 | As the founder-approver I want the screening line to say "the lexicon found nothing; this is not a clearance" | Given NO_POLICY_SIGNAL, then the claim line says so in words | **NOT MET.** Pinned gap: `tests/test_product_case_stories.py::test_us07_GAP_the_screening_claim_for_an_unknown_term_still_reads_like_a_clean_result` (must fail when fixed and be replaced) |
| US-08 | As the founder-approver I want every statement in a proposal tied to evidence | Given a proposal, then each claim cites ids that resolve and each number appears in the cited evidence; others are dropped | `tests/test_agent.py::test_claims_are_grounded_in_evidence`, `::test_claim_validator_drops_claims_without_resolvable_evidence`, `::test_claim_grounding_check_catches_a_number_not_in_the_evidence` |
| US-09 | As the founder-approver I want my approval to apply only to what I saw | Given an approval, then it is bound to run, tool, argument hash, role and expiry; a wrong role, changed arguments, replay or second resume does nothing | `tests/test_identity.py::test_wrong_role_cannot_approve_and_nothing_executes`, `::test_grant_replay_wrong_run_changed_arguments_and_wrong_tool`; `tests/test_agent.py::test_approval_resumes_and_executes_only_the_approved_simulation_action`, `::test_rejection_resumes_and_executes_nothing`, `::test_a_run_cannot_be_resumed_twice` |
| US-10 | As the founder-approver I want nothing sent to a supplier by the system | Given any approval, then external-action tools are refused and the exposed tool surface is read, analyse and draft only | `tests/test_tools.py::test_external_actions_always_refused_even_with_approval`, `::test_mcp_surface_contains_only_read_analyze_draft` |
| US-11 | As the operations manager I want supplier-portal text unable to steer the system | Given untrusted supplier text, then it cannot change the recommendation, is quoted as unverified, and is never a claim | `tests/test_trust.py::test_untrusted_server_cannot_change_the_recommendation_for_either_planner_family`, `::test_note_content_is_quoted_as_unverified_and_never_a_claim`; `tests/test_agent.py::test_injection_heuristic_misses_paraphrase_but_planner_never_obeys_it` |
| US-12 | As the operations manager I want a ready supplier message with correct figures | Given an approved draft, then a message is produced from the template with slot values equal to the evidence and no free-text figures; a mismatch blocks it | **UNTRACED, NOT BUILT** (FR-14) |
| US-13 | As the ops data owner I want to add a derivative name to the D-54 list and see it tested | Given a gap report, then the term is added with a test and a change-log entry within the agreed time | **UNTRACED, NOT BUILT** (FR-12). The gap is pinned by `tests/test_product_case_analysis.py::test_nonai_baseline_lexicon_gap_is_pinned_not_hidden` |
| US-14 | As the founder I want any model that is ever tried to be unable to widen its own powers | Given a model proposal, then it cannot waive review, cannot propose actions outside the allowed set, cannot cross the permission boundary and cannot invent a target | `tests/test_llm_planner.py::test_model_cannot_waive_human_review`, `::test_action_outside_the_allowed_set_is_refused`, `::test_worst_case_model_cannot_cross_the_permission_boundary`, `::test_invented_mutation_targets_are_rejected_before_review` |
| US-15 | As the product owner I want every number in this case reproducible | Given the committed result files, then the re-analysis and the cost model regenerate byte for byte and never write into the frozen results directory | `tests/test_product_case_analysis.py::test_committed_analysis_json_equals_a_fresh_derivation`, `::test_analysis_never_writes_into_the_frozen_results_directory`; `tests/test_product_case_cost_model.py::test_committed_cost_model_json_equals_a_fresh_run` |
| US-16 | As the operations manager I want few false alarms on healthy items | Given a healthy-heavy evaluation set, then at most 10% of healthy checks produce a review item | **UNTRACED.** The synthetic suite has 8 healthy scenarios of 259; the measurement requires a new set (file 07, phase 0b) |

Counts: 16 stories; 12 traced to passing tests (US-01 to US-06, US-08 to US-11, US-14, US-15), 1 not met and pinned as a gap (US-07), 3 untraced and not met (US-12, US-13, US-16; US-13 has only a test that pins the underlying gap).

## 5. User experience notes

The reviewer sees, in this order: the headline (including "INSUFFICIENT VERIFIED EVIDENCE" when that is the truth), cited claims, uncertainties, what the system **did not** propose ("approving", "rejecting on inference", "contacting the supplier"), and the four decisions: approve, edit, reject, ask for more evidence (up to five rounds, bounded). Supplier-controlled text is quoted and marked untrusted. The R1 additions: the NO_POLICY_SIGNAL line (FR-13), a visible rule version, and the template preview for the supplier message.

## 6. Instrumentation (for a pilot, not built)

Events: exception detected (class, rule version); proposal opened; evidence expanded; decision taken (kind, seconds); edit made (field changed: number, date, item, supplier, wording); draft sent by the human; outcome later adjudicated (true exception, healthy, rule-gap). These feed M-1 to M-6 and R-1 to R-8.

## 7. Dependencies and open questions

Dependencies: an independent adjudicator (P7), a real or realistic exception log (P8 and a pilot), an owner for the D-54 lexicon. Open questions for the owner are in `06-decision-memo.md` section 7.

## 8. Release criteria for R1 (DESIGN TARGETS)

All of: US-07, US-12 and US-13 met with tests; manual fallback rehearsed once end to end; a healthy-heavy synthetic set built and scored with the rules engine; the case reviewed by someone other than the author. R1 makes no AI claim.
