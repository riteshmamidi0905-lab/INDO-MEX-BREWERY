# Amara offline Operations contract adapter

This milestone is **offline only**. It starts at preserved Amara commit `cb71397260ba269f6907af46ff5621fb1cd94f18` on isolated branch `codex/amara-offline-contract-adapter`. It adds a server-side Python adapter, not an HTTP endpoint, new UI, agent framework, provider or deployment. Headquarters and its original deterministic payload remain unchanged.

## Inputs and outputs

`showcase.operations_adapter` exposes:

1. `OfflineConfig(tenant_scopes, source_as_of, max_age_seconds=86400)`: explicit trusted host configuration. The only admitted hash profile is `record-hash.v1`; an unknown/v0 pin is FAILED `record_hash_profile_unsupported`. Configuration mappings are copied/frozen. No tenant UUID defaults, production identity creation or configuration persistence are provided. Deterministic UUID mappings from the published vectors are used **only in offline tests**.
2. `retain_scenario(config, tenant, scenario_id) -> SourceSnapshot`: reads Amara's existing expected/count records and Phase 4's supplementary target assumption, selecting one of four existing scenarios for one of the two existing tenant names. It retains immutable canonical snapshot bytes, full v1 record hashes, source revision/as_of, tenant scope and a copied/frozen trusted-hash map. Both businesses still represent synthetic assumptions, not measured inventory. No financial records are read or changed.
3. `model_input(config, source, tenant=..., analysis_id=..., workflow_id=..., now=...) -> ModelInput`: produces the exact published `ops-explanation-input.v1` object. It checks tenant/config binding, canonical bytes, profile, source/snapshot hashes, source map and freshness. It does not create a workflow or generate IDs. Test fixtures supply their published dummy bindings; an execution host must supply a genuinely owned existing run.
4. `replay(...) -> offline artifact`: returns ModelInput, an `ops-explanation-result.v1` envelope containing `ops-explanation-output.v1`, semantic verification status, shared rendered explanation, source/profile/config pins, `live_model=false`, `provider_calls=0`, and an explicit deterministic label. It computes the exact four claims or justified abstention with the pinned pure component. There is no candidate callback, provider argument, mode selector, retry or automatic fallback. Every envelope remains **AUDIT_PENDING, audit_complete=false**: this milestone does not claim durable explanation auditing or approval. The explanation is an offline verified artifact, not a newly authorized business action.
5. `replay_owned_run(engine, reviewer, run_id, config, analysis_id=..., now=...)`: optional thin server-only resolver for existing Phase 4 runs. Under the existing engine lock it uses `owned`, verifies existing ledger/WEIR integrity, reads the retained context, compares its count assumptions to the retained scenario source, and performs the pure replay. It never calls start, decide, write_gateway or any execution path. Existing access-denied audit behavior is retained. No new endpoint exposes this resolver or lets clients supply its trusted configuration.

ModelInput has one inventory entity (`item:packaging` as required by the golden vectors, with tenant-specific packaging/towels alias), sorted expected_units/counted_units/target_units facts, empty comparison_groups/completeness, the existing fixed prohibited_effects, supplied bindings and immutable source timestamp. Target is evidence only and cannot become a fifth claim or replenishment order. Budget-risk yields an inventory explanation, not a financial assessment. Missing count yields ABSTAIN with MISSING_REQUIRED_EVIDENCE.

The returned model-input dictionary is detached from retained bytes/maps. Downstream mutation cannot alter the authoritative source. Rejected input raises `AdapterRefused` with stable lowercase `codes` and REJECTED status; configuration failures carry FAILED. A stale/future source is refused. Replaying historical assumptions requires an explicit trusted offline review clock; this cannot be used to fake current source freshness for a later live run.

## Provenance and contract pins

The adapter independently constructs the agreed preimage:

`{profile:"record-hash.v1", tenant_scope_id, source_kind, source_ref, record_id, source_revision, subject_id, inventory_item_id, field, availability, value, unit, as_of}`.

Canonical JSON is sorted-key compact UTF-8 (`ensure_ascii=false`, no BOM/newline, no floats/nonfinite values/unpaired surrogates); record_sha256 is lowercase SHA-256 of those bytes. Snapshot hash covers exactly `{as_of,entities,facts,comparison_groups,completeness}`. The accepted-result hash uses **`ops-explanation-output.v1`** in its schema_version preimage, matching the independently verified vectors. Original Amara fingerprints remain unchanged and are not relabeled contract hashes.

Each trusted map belongs to a single immutable SourceSnapshot, scoped by tenant UUID, configuration/profile pin and **snapshot SHA-256**. The human-readable snapshot ID is reused across golden cases and is not a globally unique cache key. Current schema components exclude `|`, so `record_id|source_ref` is unambiguous; duplicate keys are refused during source retention. Do not flatten maps across tenants, revisions or snapshots, or URL-decode/normalize their keys. Map values are retained from the authoritative server source before a candidate could ever exist; no request/model input supplies the trusted map.

`showcase/_ops_alignment/` contains byte-for-byte copies of only the aligned pure checker/renderer and its pure text-boundary dependency from `e549725b1f0ad111d8f009785a411e13bbb1194b`, plus the eight unchanged Codex contract artifacts it pins. `UPSTREAM.json` lists all hashes. This isolated package avoids changing Claude's lab, the shared platform, global import paths or the older lab code on Amara's base. Its generic provider-callback pipeline is **not used**: the adapter directly invokes pure admission, reference-output, validation and renderer functions. No provider SDK/network is imported by the copied component. Source revision constants are provenance identifiers, not approval of the candidate model named in its metadata.

`tests/fixtures/ops_vectors_v1/` is an exact copy of Claude's published package, manifest identity `14f526e71a5e76eb7f7287e7e313934d9cf32c0c0af6cf0ca8cd21fca2e59e2f`; no golden files or published schemas were edited. The copied verifier is not invoked. The handoff's prose literal `ops-record-hash.v1` remains an upstream documentation typo; all functioning code and vectors pin `record-hash.v1`. No schema change is required for this adapter.

## Renderer and labels

Contract artifacts use the published renderer verbatim, for example:

> In this synthetic snapshot, the expected quantity of Synthetic packaging is 100 units and the counted quantity is 40 units. The counted quantity is 60 units below expected. These scenario assumptions do not establish a physical root cause.

Equality, signed surplus, singular units, escaping and abstention come from the pinned renderer. There is no competing template implementation. The offline artifact label is “Deterministic contract replay — no model call.” Original Amara screens retain their original revision; UI projection is intentionally deferred. A future UI must preserve escaping boundaries and withhold AUDIT_PENDING content as an accepted live explanation. Renderer error wording that mentions AI must never be used to imply that this offline milestone called a model.

## Validation

From this worktree with the existing environment:

```bash
PYTHONPATH=showcase:lab /workspace/.brewery-venv/bin/python -m pytest -q showcase/tests/test_operations_adapter.py
PYTHONPATH=showcase:lab /workspace/.brewery-venv/bin/python -m pytest -q showcase/tests
```

Targeted tests independently compute canonical bytes, v1 preimages, snapshot/result hashes and compare complete ModelInputs/rendered strings against all eight previously independently verified fixtures. Standard JSON Schema validation is separate from the pinned component's interpreter. All 102 aligned verdict vectors are also replayed as conformance/regression checks (not new independent model evaluations). Tests cover immutable copies, unknown/v0/mixed profiles, cross-tenant hash copying, missing maps/counts, stale/future sources, malformed/profile-smuggling input, detached outputs, no provider callback path, existing run ownership, proposal/action hashes and unchanged ledger/trace/WEIR records. Separate existing-run tests show wrong reviewers remain denied and the original authorized rejection still works without adapter-issued approval.

Golden hashes and copied source/contract pins are checked byte-for-byte. **Results:** 144 targeted tests passed; the full relevant suite passed 228 tests with zero failures (one non-failing platformdirs runtime-directory warning). The full suite includes PostgreSQL reconciliation/RLS/constraints and original Headquarters/workforce authorization tests. Frontend build and JavaScript syntax checks run without UI changes. Wheel packaging is checked to ensure the immutable contract resources ship alongside the adapter. All databases used for new test setup are temporary; adapter calls do not create runs, drafts or approvals. Original protected fixture hashes are checked separately. Review logs/XML and wheel/build artifacts remain outside Git under `/workspace/.nasha-hq/amara-adapter-review/`.

## Readiness and remaining blockers

The contract adapter is ready as an **offline component** for a future controlled M-OPS-2 demonstration. It is **not** an activated live-model path. GitHub CI/model approval is not inferred from local conformance. No inference or model-live evaluation was dispatched.

Remaining host work requires separate authorization: acceptable exact-configuration M-OPS-2 evidence; trusted runtime/model/finish-reason attestation and bounded cancellation/truncation handling; durable explanation sidecar/audit and idempotency; reviewed tenant/reviewer capability bindings; a minimal authenticated WEIR read-tool/endpoint/UI projection. Existing run ownership must be preserved; the current pure Amara view must not fabricate a run or start procurement to obtain a contract field. Production tenant IDs and durable identity infrastructure were not created or modified here. Historical assumptions cannot be passed off as live stock. Do not call AUDIT_PENDING ACCEPTED merely to make a demonstration appear complete.

No merge, deployment, default/Claude/shared-platform/portfolio change or live activation is authorized by this milestone.
