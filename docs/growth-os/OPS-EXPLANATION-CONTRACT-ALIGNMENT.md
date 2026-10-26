# Operations explanation: contract alignment (approved joint baseline D1-D8) and golden-vector handoff

**Offline. No model was called, no live inference or M-OPS-2 run was dispatched. Phase 2 remains `REQUIRES_REVIEW`.** M-OPS-1 (commit `06fc273`, lab-ci green) is complete and its evidence is preserved byte-for-byte; this milestone aligns the implementation with the joint baseline Codex and the owner approved. Codex's published schemas are **unchanged** (the eight vendored files still match the upstream manifest).

> **Correction (documentation only, after Codex's independent verification of the vectors).** The first version of this document wrote the hashed record-profile literal as `ops-record-hash.v1` and did not state the accepted-result preimage's schema version. The correct literal is `record-hash.v1` (what the code, the vectors and both verifiers use), and the accepted-result preimage uses `ops-explanation-output.v1`. No vector, implementation behaviour or evidence changed.

## 1. Version identifiers (all in `identifiers.json` of the vector package)

| Item | Value |
|---|---|
| Vector package | `ops-golden-vectors.v1`, `lab/contracts/ops_explanation_vectors/v1/`, identity = SHA-256 of its `MANIFEST.sha256` = `14f526e71a5e76eb7f7287e7e313934d9cf32c0c0af6cf0ca8cd21fca2e59e2f` |
| Canonical JSON | `canonical-json.v1`: UTF-8, keys sorted by code point, separators `(',',':')`, `ensure_ascii=false`, integers only (no floats, NaN, duplicate keys) |
| Record hash, live | `record-hash.v1` |
| Record hash, historical | `record-hash.v0` (golden-vector verification only) |
| Snapshot hash | unchanged: canonical JSON of `{as_of, entities, facts, comparison_groups, completeness}`, collections sorted by id |
| Accepted-result hash | `accepted_result_sha256` = SHA-256 of the canonical JSON of `{schema_version, analysis_id, snapshot_sha256, claims, rendered_explanation, validator_revision, renderer_revision}` where `schema_version` is the literal **`ops-explanation-output.v1`** (the OUTPUT schema version, not the result envelope's `ops-explanation-result.v1`); `claims` are the verified model claims and `rendered_explanation` the server-rendered text |
| Diagnostics | `ops-diagnostics.v1` (44 codes, lower-case) |
| Validator / renderer | `ops-validator-v1.1-m-ops-contract-1` / `ops-renderer-v1.0-m-ops-1` (renderer text unchanged) |
| Contract pin set | `codex-phase5-spec@b064414b0773681c9b2af046e1458ce0c1c7f343` (8 files, hashes in `identifiers.json`) |

## 2. What changed (behaviour-preserving except where named)

1. **D4 lower-case diagnostics** from one explicit table (`DIAGNOSTICS`: code -> class). Schema enums (`reason_codes`, `LIMITATION.code`, `status`, `kind`, availability, units) keep their published upper-case spelling. The M-OPS-1 spellings map through `LEGACY_UPPER` (reading old records only).
2. **Provenance disambiguation.** `MISSING_PROVENANCE` -> `source_provenance_missing` (the host's trusted record hash is absent; source side, REJECTED at admission). `PROVENANCE_MISSING` -> `provider_provenance_missing` (live result lacks evidence of the approved model and non-estimated use; provider side, FAILED).
3. **D6 admission-time provenance and staleness.** `check_input` (and `explain`, before the provider is called) now verifies record hashes, the host's `trusted_record_hashes`, and snapshot age (`now`, `max_age_seconds`; a snapshot dated after `now` is refused). `LIVE_LLM` additionally **requires** the trusted map (else `input_refused` + `source_provenance_missing`; the provider is not called). This moved checks out of the post-model stage: an unverifiable snapshot no longer costs an inference or blames the model.
4. **D2 record hashing.** `record-hash.v1` preimage = canonical JSON of `{profile:"record-hash.v1", tenant_scope_id, source_kind, source_ref, record_id, source_revision, subject_id, inventory_item_id, field, availability, value, unit, as_of}`. The `profile` value is exactly the literal `record-hash.v1` (the same string that names the profile everywhere else, and the value the vectors and the independent verifier check) and is part of the hashed bytes. **Downgrade guard:** the profile is a server constant; nothing in the snapshot, the model output or a caller's arguments can select it (no public parameter; a smuggled `record_hash_profile` key is rejected by the closed schemas); the host's pin `record_hash_profile` must equal v1 or the result is `FAILED` `record_hash_profile_unsupported` before the snapshot is read; a snapshot with v0 hashes, mixed profiles or another tenant's hashes is refused (`source_hash_mismatch`); `validate_historical_vector` is the only v0 path, is marked `historical_vector`, and is unreachable from `explain` (AST-tested).
5. **D5 REJECTED vs FAILED.** The table's class decides: provider and configuration classes -> `FAILED`; admission, source, parse, schema, binding, claim and abstention classes -> `REJECTED`. `make_envelope` refuses a status that contradicts its codes.
6. **Provider truncation.** `ProviderTruncated` raised by the host adapter, or `finish_reason` other than `stop` as a third tuple element (`length` -> `provider_truncated`, anything else -> `provider_error`) is `FAILED`. **Limit, stated:** truncated JSON delivered with no finish reason is indistinguishable from a bad answer and stays `REJECTED not_json`; the host must pass `finish_reason`. The published provider object is closed, so no field was added to it.
7. **Previously untested codes** `input_oversize` and `not_json_text` are now exercised (a non-text, non-JSON value handed to `validate_output` is `not_json_text`). A test asserts every table code is exercised.
8. **D8.** The original evidence `results/ops-explanation/m-ops-1-offline-matrix.json` is untouched (SHA-256 pinned in a test, upper-case spelling retained); the new evidence is `results/ops-explanation/m-ops-contract-1-offline-matrix.json`.

**Safety.** No guarantee is weaker: the same claim recomputation, one-bad-claim-rejects-all, closed schemas, directive screen, tenant binding and purity (no WEIR/workflow/DB/network import) hold; the added checks only refuse earlier or more. THE WEIR, tenant isolation and approval behaviour are unchanged (the real-workflow regression tests pass).

## 3. Results

* Matrix: **102 scripted cases, 102 exact, 0 false accepts, 0 false rejects**; **22 of 22** rule mutants killed (new rule `record_hash`); the 16 M-OPS-1 source-level mutants and **11 new source-level mutants** of the aligned behaviour (truncation ignored, status classes collapsed, profile pin dropped, live without trusted hashes, staleness removed, v0 accepted as fallback, ...) are all detected; neutral-edit negative controls pass.
* Golden vectors: generator is deterministic (`--check`); the **standard-library-only verifier** (`python3 -I verify_vectors.py`, imports nothing from the repository) prints `ALL VECTORS VERIFIED`; **12 tamper tests** show it fails when any vector is altered; the package is also consumed back as a conformance suite (all 102 verdicts and all envelopes reproduced by the reference implementation). The Amara payload transcription equals Codex's real `operations.explain` output for all 8 tenant x scenario items (checked once against `codex/amara-readonly-operations@cb71397`, read-only).

## 4. Key expected values (full set in the package)

| Vector | Value |
|---|---|
| Codex example snapshot hash | `126d338b08c11d840352cb85ec3703fa8bae9ad60ea10bb88df9d88bdc86f47e` (reproduced) |
| v0, example facts | counted `c5e5e415...`, expected `de9e676b...`, target `2ba1aaa3...` = `sha256(canon({subject_id,field,value,unit}))` (reproduced) |
| v1, nasha-brewery / count-gap / counted_units | `edbbc5d978b421be31de7554657d10fea5cb92201eb31a2b4a26b02a90d4bdb9` |
| Snapshot hash, nasha-brewery / count-gap | `a5b2d084a33ab4dcb331e88c49f35463379e615d2785c2c027e3cb128b3ff385` |
| Snapshot hash, meridian-fitness / count-gap | `9a9f5e2376aa6bfef02ca4a7dafdcea471d8e5c343b1fef82d070d94f2531449` |
| `accepted_result_sha256`, accepted-answer vector | `9afdfa56a73f1601bd1955e217670d27e700315bef929e6dc8799c11705924b9` |
| canonical of `{"b":1,"a":2,"c":{"z":1,"y":[3,2,1]}}` | `{"a":2,"b":1,"c":{"y":[3,2,1],"z":1}}`, sha256 `cd3cfe8d...` |

**Renderer strings** (shared renderer, decision D7): answer = "In this synthetic snapshot, the expected quantity of {alias} is {E} and the counted quantity is {C}. {relation} These scenario assumptions do not establish a physical root cause." with relation "The counted quantity is {D} below expected." / "... {D} above expected." / "The counted quantity equals the expected quantity."; "1 unit" vs "N units"; the alias is HTML-escaped. Abstention strings, the rejected and failed messages and the `unnecessary_abstention` message are in `rendered.json`.

**Diagnostic mapping:** `diagnostics.json` lists every code with class, status and its M-OPS-1 spelling; the two provenance codes are the only renames; `reserved_for_deferred_claim_kinds` lists the specification's codes for COMPARISON/EXTREMUM/SCOPED_ABSENCE that are not emitted until those kinds ship.

## 5. Remaining schema incompatibilities and open items (documented; the published schemas were NOT changed)

1. **Profile identity is not visible in the data.** The model-input and execution-profile schemas are closed and have no record-hash-profile field, so the profile is pinned in this module and must be pinned in the host's execution profile by convention. Making it explicit would be a schema change (a new input version and a new pin set); stopped here for review.
2. **Provider object has no `finish_reason`.** The host must map truncation before validation (above); recording it in the result would be a schema change.
3. **Trusted-hash map and `now`/`max_age`** are host inputs with no schema home; their keys are `record_id|source_ref`. Codex should confirm that key.
4. **Amara payload is not a drop-in.** Differences: `expected/counted` vs `expected_units/counted_units`; `units` vs `UNITS`; classification and source strings; tenant NAME ids vs an opaque `tenant_scope_id`; her record and snapshot digests vs record-hash.v1 and the contract snapshot hash; no `as_of`, entities, availability, `inventory_item_id`, analysis/workflow/snapshot ids; and **different wording** (decision D7 pending Codex). `amara_adapter.json` holds the mapping rules and expected inputs.
5. The tenant scope ids in the vectors (`...a1`, `...b2`) are **placeholders**; the derivation of real ones is a host decision not yet made.
6. Spec codes for deferred claim kinds are reserved only.

## 6. Concise handoff for Codex

* Package: `lab/contracts/ops_explanation_vectors/v1/` on `career/master-directive-phase0` (identity `14f526e71a5e76eb7f7287e7e313934d9cf32c0c0af6cf0ca8cd21fca2e59e2f`). Read `README.md`, run `python3 verify_vectors.py` (no dependencies), then **verify with your own implementation**: canonical bytes and hashes (`canonical_json.json`), v0 and v1 record hashes and the sensitivity table (`record_hashes.json`), snapshot hashes (`scenarios.json`), rendered strings (`rendered.json`), envelopes incl. `accepted_result_sha256` (`envelopes.json`), the diagnostics table and its classes (`diagnostics.json`), and the 102 verdicts (`verdicts.json`).
* Please report any byte or verdict that differs. **Integration is not considered until you have independently verified the vectors.**
* Decide D7 (whose wording becomes the shared strings) and the open items in section 5; any change is a new vector version, not an edit.
* Nothing in your branches, the shared platform, the default branch or the portfolio was touched.
