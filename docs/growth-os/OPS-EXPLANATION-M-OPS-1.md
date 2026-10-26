# Operations explanation, milestone M-OPS-1 (offline): validator, renderer, contract findings, Codex handoff

**Status: M-OPS-1 engineering milestone, OFFLINE. No language model was called, evaluated or dispatched. Phase 2 remains `REQUIRES_REVIEW`.** Nothing here activates a capability, changes Headquarters, or touches THE WEIR, the workflow, Codex's branches or the shared platform. The objective it serves is one real, verified, read-only AI Operations explanation inside NASHA AI Headquarters; this milestone builds and proves the *checking* half of that, so that any later model output is judged by code that is independent of the model.

## 1. What was built

| Piece | File | Notes |
|---|---|---|
| Pure validator, deterministic renderer, result envelope, pipeline | `lab/nasha_lab/growth/ops_explanation.py` | Imports only the standard library and `model_boundary` (itself pure). No database, network, workflow or WEIR code (a test enforces this). |
| Codex's published contracts, vendored byte-for-byte | `lab/contracts/ops_explanation/` | Upstream `codex/phase5-integration-specification` @ `b064414`. The module loads them at import and **refuses to start** if any byte differs from the pinned hashes. Not edited. |
| Scripted matrix, rule mutants | `lab/nasha_lab/growth/ops_explanation_eval.py`, `lab/tools/ops_explanation_eval.py` | Written from the specification before the validator was run against them. Evidence: `lab/results/ops-explanation/m-ops-1-offline-matrix.json` (a test fails if it is stale). |
| Tests | `lab/tests/test_ops_explanation.py` (49), `test_ops_explanation_workflow_invariants.py` (3) | Contract compatibility, matrix, rule and source-level mutants, rendering, envelope, tenant isolation, authorization invariants, real-workflow regression. |

**Closed claim grammar, milestone profile.** An ANSWER is exactly `OBSERVE(expected_units)` + `OBSERVE(counted_units)` + `DIFFERENCE(EXPECTED_MINUS_COUNTED)` + `LIMITATION(CAUSE_NOT_ESTABLISHED)`. `COMPARISON`, `EXTREMUM`, `SCOPED_ABSENCE`, the other fields (`target_units`, `unit_cost_cents`) and the other limitation codes are valid in the published schema and **deferred here: a claim of those kinds is rejected** (fail closed). The model's output may never contain free text: the schema is closed, and the explanation is rendered from server templates using only the validated snapshot (integers and the escaped trusted alias), never the candidate's claimed values.

**All-or-nothing.** One false, unsupported, unexpected or deferred claim rejects the whole output. There is no partial acceptance (a mutant that adds it is detected; a test shows three correct claims plus one wrong is rejected whole and nothing is rendered or returned).

**Verification, independent of the model.** Every claim is recomputed from the authorized snapshot: referenced fact exists in *this* snapshot (otherwise `UNKNOWN_EVIDENCE`, or `CROSS_TENANT_REFERENCE` when the id belongs to a known foreign tenant), subject/item/field/unit match, the fact is `PRESENT`, the value equals the stored integer, the difference equals exact integer subtraction. The snapshot is admitted only if its hash matches the specified canonical form, ids are unique, order is canonical, references resolve, strings are free of directive text (reusing the repository's directive screen), and the task and prohibited-effects constants hold; an inadmissible input is refused **before the candidate is called**.

**Abstention.** The snapshot itself determines the required reasons (missing, conflicting, incompatible units/item, insufficient scope). An ANSWER where the snapshot cannot support one is `INVENTED_COMPLETION`; an ABSTAIN must carry exactly the required reasons; an abstention on complete data is safe but flagged `UNNECESSARY_ABSTENTION` (counts against usefulness, never as an error).

**Result envelope.** Built to `ops-explanation-result.v1` and validated against the published schema plus the specification's cross-field invariants. `REJECTED` and `FAILED` carry no model output and a fixed server message. A scripted double can never produce a `LIVE_LLM` result (provider evidence of the approved tag and digest, actual non-estimated use, is required); a replay cannot carry provider metadata; there is no cache. `AUDIT_PENDING` is returned until the caller attests a complete audit record. The labelled `deterministic_replay` is a separate call and is never counted as a model result.

## 2. M-OPS-1 gates

| Gate | Result |
|---|---|
| All required offline tests pass | 52 new tests pass (49 + 3); full suite in the commit message / CI |
| Zero accepted invalid claims | **0** accepted among the 95 scripted cases; 0 false accepts, 0 false rejects, 95 of 95 exact |
| Zero cross-tenant disclosures | 4 dedicated cases plus bidirectional rendering test: tenant B's complete valid answer submitted for tenant A is rejected whole and nothing of it is rendered; 0 disclosures |
| Zero authorization bypasses | The module cannot approve, execute, write or call anything (imports enforced); no envelope or output field can carry an action, approval, tool or effect (schema scan + injection cases); against the **real** governed workflow, explanations of every kind left the proposal hash, state, agent mode and audit rows unchanged, and the approval path (requester denied, different owner executes, replay refused) behaved as before |
| Every relevant adversarial mutant rejected | 13 injection cases, 19 structure cases, 4 cross-tenant cases, 8 evidence cases all rejected; **21 of 21** rule mutants killed; **16 source-level mutants** (wrong subtraction direction, arithmetic skipped, `<=` for `==`, partial acceptance, bindings weakened, duplicate keys/floats/bool/unknown keys tolerated, deferred kinds accepted, abstention unchecked, invented completion allowed, input screen removed, renderer reading model values) all detected; a behaviour-neutral edit is correctly *not* flagged (negative control) |
| No regression in existing governed workflows | Full local suite (see the commit) and the three workflow tests above |

Scripted matrix by group: correct 6, abstention 7, evidence 8, arithmetic 10, observe 6, provenance 11, cross-tenant 4, injection 13, structure 19, claim-set 7, input 4.

**Honest note on the matrix.** Two expectations I had written were wrong and were corrected before the matrix was committed, not the validator: (1) a wrong `schema_version` is a violation of the schema constant, judged before bindings, so it yields `SCHEMA_INVALID` only; (2) my first poisoned-alias example exceeded the schema's 48-character alias limit and so failed the schema, not the directive screen; it was shortened so the directive screen is what is exercised. Everything else matched on first run.

## 3. Contract compatibility findings (documented, not silently changed)

The contracts are used exactly as published. Findings for Codex to decide:

1. **Confirmed compatible.** The 8 vendored files match Codex's own `MANIFEST.sha256`. The published example snapshot hash is reproduced exactly by the specified canonicalization. The published example answer is accepted by the validator and renders the specification's illustrative sentence verbatim. Our schema evaluator and the reference `jsonschema` library agree on every scripted output.
2. **Mismatch: validation-code case.** `result-envelope.schema.json` requires `validation_codes` items to match `^[a-z][a-z0-9:_-]{0,95}$` (lower case), while the specification names codes in upper case (`UNKNOWN_KEY`, `BINDING_MISMATCH`, ...). We keep upper case internally and emit lower case in the envelope (so the published schema validates). Codex should decide which form is normative.
3. **Gap: record hash derivation.** `provenance.record_sha256` has no stated derivation, and the example hashes are not derivable from the visible fields. The builder here uses `sha256(canonical({scenario, field, value, source_revision}))` and the validator can check hashes against a server-supplied trusted map (`trusted_record_hashes`); without one it cannot verify them. A real definition is needed before activation.
4. **Gap: arithmetic and structural codes.** The specification lists no code for a wrong difference or for these structural failures; this module adds `INCORRECT_DIFFERENCE`, `WRONG_FACT`, `CLAIM_SET_MISMATCH`, `DEFERRED_CLAIM_KIND`, `DEFERRED_FIELD`, `DEFERRED_LIMITATION`, `INVENTED_COMPLETION`, `WRONG_ABSTENTION_REASON`, `DUPLICATE_KEY`, `NON_INTEGER_NUMBER`, `NON_FINITE_NUMBER`, `INVALID_UTF8`, `OVERSIZE`, `TOO_DEEP`, `NOT_JSON` and the `INPUT_*` family. Names are ours; Codex may rename them.
5. **JSON Schema is not sufficient (pinned by a test).** The published output schema alone accepts a wrong difference (61 for 60), duplicate claim ids with different content, and `60.0` as an integer. Strict parsing and the semantic checks above close these, as the specification requires.
6. **Narrowing, compatible.** The specification allows optional extra price/comparison claims in an ANSWER; this profile requires the exact four. Every output this module accepts is valid under the published schema and specification; the converse does not hold by design.
7. **Order.** The published example's `LIMITATION.fact_ids` is not sorted; the specification asks for sorted ID arrays in the input. The validator is order-insensitive for that set.
8. **Binding echo.** The output contract requires the model to echo six bindings, including a 64-hex hash. That is long to copy exactly and a likely rejection source for a 7B model; whether it is a problem is unmeasured. A server-attached binding would avoid it but is a contract change, so it is only noted.
9. **Not covered here.** `request-envelope.schema.json` (principal, grant, idempotency, profile pins) and everything in the specification's identity, persistence and cancellation sections belong to the host and are not implemented. `LIVE_LLM` provenance is checked for structure only; its authenticity needs the host's trusted runtime registry.

## 4. Remaining blockers (none is addressed by this milestone)

* A model-backed result exists only after an approved live evaluation (M-OPS-2, proposed separately, not run).
* Headquarters integration lives in Codex's codebase: a snapshot builder from the real Phase 4 stores, the `workforce__explain_inventory` read tool, the WEIR read policy, the ledger sidecar, the endpoint and UI are Codex's to build against these contracts.
* Durable identity, reviewer grants and key custody (Codex specification section 8) are unresolved; this is why activation, as opposed to a demonstration, stays blocked.
* Latency on CPU-only hardware (run #4: median 40 s, maximum 241 s per call) may not meet the proposed 60/120/180 s targets; unmeasured for this contract.
* The record-hash derivation and the code-case question above.

## 5. Concise integration handoff for Codex

* Consume `lab/nasha_lab/growth/ops_explanation.py` as a reference, or port it: `check_input(model_input)` (admit or refuse before any provider call), `validate_output(raw, model_input, ...)` (verdict and codes), `render_answer`/`render_abstention` (templates), `explain(model_input, candidate, mode)` (envelope + audit record), `reference_output` (oracle), `deterministic_replay` (labelled replay).
* The contracts under `lab/contracts/ops_explanation/` are your published files unchanged; hashes in `UPSTREAM.sha256`.
* Build the host side against it: snapshot builder from the real Phase 4 data with a trusted record-hash map, the `Risk.READ` tool, the WEIR read policy, persistence of `record` (raw output, hash, per-claim verdicts, revisions), idempotency and cancellation.
* Please settle findings 2, 3 and 4. Until then both sides should treat the lower-case envelope codes as provisional.
* The evaluation harness for a later live run will reuse the model-live workflow, digest enforcement and recording requirements already in this repository; it is proposed in `OPS-EXPLANATION-M-OPS-2-PROPOSED-ACCEPTANCE.md` and is not approved.
