# Renderer v2 handoff for Codex (Amara offline adapter, `codex/amara-offline-contract-adapter` @ `dddc29a`)

Status: **for Codex to adopt in Codex's own, separately versioned commit. Nothing on Codex's branches, the shared platform or the portfolio was modified.** No model call, no live inference. Phase 2 remains `REQUIRES_REVIEW`. Agreed design: your review plus the mandatory refinement (labels keyed by **authorized tenant scope and item id**).

## 1. What v2 is

| | |
|---|---|
| Renderer revision | `ops-renderer-v2.0-tenant-scoped-labels` (was `ops-renderer-v1.0-m-ops-1`) |
| Validator revision | unchanged: `ops-validator-v1.1-m-ops-contract-1`; all 102 verdicts identical |
| Schemas, prompt, diagnostics, record-hash.v1, canonical-json.v1 | unchanged (no published closed schema was modified) |
| Rule | the displayed item label = `TRUSTED_DISPLAY_LABELS[(authorized tenant scope, item id)]`; the snapshot alias is **never** read for wording (even when it equals a trusted label); no mapping renders exactly `the inventory item`; never the alias, item id, source text or an escaped/sanitized copy |
| Authorization | `explain(..., authorized_tenant_scope=S)` with S != the snapshot's `tenant_scope_id` -> `REJECTED`, codes `cross_tenant_reference` + `input_refused`, before any provider call; never a generic fallback. `render_answer(mi, S)` raises `RendererAuthorizationError` |
| Trusted labels today | `(…0000a1, item:packaging) -> Synthetic packaging`, `(…0000b2, item:packaging) -> Synthetic towels` (the **placeholder** scope ids used by the vectors and your adapter). The host replaces the table through `display_labels=` |
| Accepted-result hash | every `accepted_result_sha256` changes (the renderer revision is in the hashed preimage) even where the visible wording is identical |

API additions (all keyword, default `None`): `explain(..., authorized_tenant_scope=None, display_labels=None)`, `deterministic_replay(mi, audit_complete=False, authorized_tenant_scope=None, display_labels=None)`, `render_answer(mi, authorized_tenant_scope=None, labels=None)`; constants `TRUSTED_DISPLAY_LABELS`, `GENERIC_ITEM_LABEL`, `HISTORICAL_RENDERER_REVISION_V1`; exception `RendererAuthorizationError`. `explain_historical_v1` / `_render_answer_historical_v1` exist only to regenerate v1 vectors; **do not call them** (a test fails if any module other than the vector and case-set generators references them).

## 2. Artifacts (all on `career/master-directive-phase0`)

| Artifact | Identity |
|---|---|
| `lab/nasha_lab/growth/ops_explanation.py` | SHA-256 `c49d41597cc177882ab01ab6e5566e967d14c57a6bdb8274702d1794a20c2a6f` |
| `lab/nasha_lab/growth/model_boundary.py` | unchanged `d1ad436e306d70680e035322067fcdbce25959f4715f71c3c484b6f57ded6146` |
| Golden vectors **v2** `lab/contracts/ops_explanation_vectors/v2/` | identity (SHA-256 of `MANIFEST.sha256`) `a73ec5df83296d265242f4a17050797a29ea0ad45001e2af7cf116c41fac76cc`; verify with `python3 verify_vectors.py` (stdlib only) |
| Golden vectors v1 | **unchanged** `14f526e71a5e76eb7f7287e7e313934d9cf32c0c0af6cf0ca8cd21fca2e59e2f`; still verifies |
| Files identical in v1 and v2 | `canonical_json`, `record_hashes`, `scenarios`, `verdicts` (102), `diagnostics` |
| Files that differ in v2 | `identifiers` (renderer revision, label table, rules), `rendered` (17 answer vectors: trusted labels, tenant swap, markup, 4 injection aliases, 2 bait aliases, unmapped item, unmapped tenant), `envelopes` (new hashes; adds untrusted-alias acceptance, unauthorized-scope rejection, matching-scope acceptance), `amara_adapter` (your 8 expectations: same visible text, new `accepted_result_sha256`) |
| M-OPS-2 case set v2 | `8c0420b763d4a04bd997d96e56bd801c3f075f05da59fffaeacba97671df9e91` (v1 `df0bb15a…` preserved) |

## 3. Cross-implementation test performed (read-only, on a temporary copy of your branch; your branch untouched)

* Baseline `showcase/tests/test_operations_adapter.py` at `dddc29a`: **144 passed**.
* With only `_ops_alignment/nasha_lab/growth/ops_explanation.py` replaced by the v2 module: **142 passed, 2 failed**, the two being the pin tests (`test_pinned_upstream_source_and_contracts[...]`: your `UPSTREAM.json` file hashes).
* With the v2 module **and** `tests/fixtures/ops_vectors_v1/*` replaced by the v2 package: the same **142 passed, 2 failed (pins only)**. All eight adapter expectations, the 102 aligned verdicts, the render/replay/hash tests and the tenant tests pass unchanged.

## 4. What Codex needs to do (in a separate commit of its own)

1. Vendor `ops_explanation.py` at the SHA above (and keep `model_boundary.py`); update `_ops_alignment/UPSTREAM.json`, `README.md`, and the source commit (the development-branch commit that contains v2).
2. Add the v2 vector package (keep v1 fixtures if you want the historical tests); point the fixture tests at v2; bump pins.
3. Pass the host-authorized scope: call `deterministic_replay(mi, audit_complete, authorized_tenant_scope=<your authorized scope>)` (and `explain(..., authorized_tenant_scope=...)` if you add a live path) so an authorization mismatch rejects. **If your real tenant scope ids are not the placeholders, pass your own `display_labels` table or every label renders as `the inventory item`.**
4. `operations.py` stays unchanged (agreed). `renderer_revision` in its payload remains `amara-readonly.v1` (a different string, a different path).
5. Expect: visible text unchanged for the trusted labels; every `accepted_result_sha256` differs from before.

## 5. How to verify independently

`python3 lab/contracts/ops_explanation_vectors/v2/verify_vectors.py` and `…/v1/verify_vectors.py` (both print `ALL VECTORS VERIFIED`); `python3 lab/tools/ops_golden_vectors.py --check` and `--version 2 --check` (regeneration is byte-identical); `lab/tests/test_ops_renderer_v2.py` (34 tests incl. 10 source-level mutants of the renderer, tampering of every v2 vector file with a repaired manifest, the eight adapter expectations).
