# Phase 2 recording requirements, format 2 (prospective)

**Status: PROPOSED, applies only to model-live runs made after the commit that introduced it.** Acceptance criteria v1.0 (`PHASE2-ACCEPTANCE-CRITERIA.md`) is unchanged and byte-identical; no historical result is rewritten. This document does not add a gate. It makes the evaluator actually check a line v1.0 already contains (S7: "every rejected claim its text") and it names what must be recorded so that a boundary rejection can be judged afterwards without another model call.

## Why

In model-live run #4 both governed-workflow model outputs were voided because the independent boundary rejected one multi-supplier comparison. The record kept the claim only to 120 characters (the audit event) and 200 characters (the comparison), the rejected report and the retrieved context were not kept, and S7 still read MET because nothing checked the governed workflow's rejected-claim text. Whether the model was wrong or the rule too strict could not be determined (see `PHASE2-RUN4-EVALUATION-REPORT.md`).

## What recording format 2 adds (recording only: no verdict, rule, prompt, retrieval or inference changed)

| Where | Addition |
|---|---|
| `model_boundary.review`, each rejected claim | `full_text`, `text_chars`, `evidence_ids`, `cited_doc_ids`, `mentioned_supplier_ids`, `detail` = {`price_binding` (the amount and the supplier it was bound to), `comparative` (verdict, reason, product, extreme, comparison set), `absence`}. The historical `text` (120 characters) and `codes` are unchanged. |
| each comparison / absence | `claim_full`, `claim_chars`, `evidence_ids`, `mentioned_supplier_ids`; comparisons also `set_detail` (supplier id, name, price in cents, unit, price class, ingredient reference of every stored quote compared). |
| workflow `agent_research` event (model runs only) | `recording_version`, `query`, `corpus_version`, `evidence_context` (per retrieved passage: id, document, title, length, SHA-256 of the text), `rejected_claims_full` (the above plus the cited passages, each capped at 600 characters with its true length), `report_reviewed` (the whole model report when it was not accepted), the platform verifier's full decision, boundary report codes and problems. The offline agent's event is unchanged. |
| battery | the same fields per governed-workflow run; per direct case `evidence_fingerprint` and `boundary.rejected_detail/comparisons/absences/problems`; the result carries `recording_version: 2`. |

Exposure: a record contains only what the tenant's own run already holds (its report, its retrieved passages, its stored-quote comparison set); the boundary is given only that tenant's directory. Passage text is capped, everything else in the context is a hash and a length. Real supplier text in the corpus is public lead data; the stored quotes are synthetic.

## What the evaluator now checks

For a result that declares `recording_version >= 2`, or when run with `--require-recording=2` (the `model-live` workflow does), S7 is INCOMPLETE unless, for every governed-workflow run: the query, corpus version and evidence context are recorded; for a rejected output: the complete reviewed report, at least one complete rejected claim (text present and `text_chars` equal to its length, so truncation is detectable), the rule code(s), the cited evidence ids and passages, the rule detail, for a comparative code the matching comparison with `claim_full` and the stored-quote set, for a price-binding code the binding that failed, and (for model-mode runs) the platform verifier's full decision; and for every direct case with a rejected claim: complete rejected detail; and C15 an evidence fingerprint. A result that omits the format marker while the workflow requires it is INCOMPLETE.

A legacy result keeps the verdict it received. Evaluated by the new code it reports `recording.enforced: false` and the list of what a format-2 evaluation would require; run #4 would be INCOMPLETE_EVIDENCE under `--require-recording=2` (tested).

## Recording limitations of run #4 (format 1), stated plainly

* The rejected claim exists in the record only as its first 120 characters (audit event) and 200 characters (comparison). The rest is **not recoverable** from the job log, the artifact (same record) or the Ollama log (request metadata only); the CI database that held the full event is gone.
* The rejected report, the query and the retrieved evidence of the governed runs were not recorded (only the evidence count); evidence for direct case C15 is recorded, so the workflow's context cannot be compared with it.
* Run #4's S7 reading of MET is preserved as it was produced; it did not check the governed workflow's rejected-claim text.
