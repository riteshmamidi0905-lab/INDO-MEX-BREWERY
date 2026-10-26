# Amara offline adapter — renderer v2 adoption

This update starts from offline adapter `dddc29a03bf30273828d6099874d081c6ddc5b23` and is isolated on `codex/amara-offline-renderer-v2`. Original Amara `cb71397`, its operations.py, UI and authorization/workforce code remain unchanged. This is still offline integration only: provider_calls=0, live_model=false, every result AUDIT_PENDING with audit_complete=false. Phase 2 remains REQUIRES_REVIEW.

## Pins and policy

- Pure component source: `0f9149ad13c7e870ff309814345c338e797c345e`.
- Vendored ops_explanation.py SHA-256: `c49d41597cc177882ab01ab6e5566e967d14c57a6bdb8274702d1794a20c2a6f`.
- Renderer: `ops-renderer-v2.0-tenant-scoped-labels`.
- Validator: unchanged, `ops-validator-v1.1-m-ops-contract-1`.
- Hash profile/output schema: unchanged, `record-hash.v1` / `ops-explanation-output.v1`.
- v2 vector manifest identity: `a73ec5df83296d265242f4a17050797a29ea0ad45001e2af7cf116c41fac76cc`.
- Historical v1 identity retained: `14f526e71a5e76eb7f7287e7e313934d9cf32c0c0af6cf0ca8cd21fca2e59e2f`.
- Independently reviewed frozen case-set v2 SHA: `8c0420b763d4a04bd997d96e56bd801c3f075f05da59fffaeacba97671df9e91` (review artifact, not an inference dispatch).

UPSTREAM.json explicitly pins the component files, revision and v2 identity. All published contract bytes remain unchanged. The two source files remain byte-for-byte copies of the approved upstream pin. v1 fixtures are untouched; v2 fixtures are added beside them, never placed in the v1 directory. Neither published vector verifier is invoked as independent evidence.

OfflineConfig.display_labels builds a read-only `(configured tenant scope UUID, item:packaging) -> reviewed constant` mapping from the existing trusted tenant registry and the two existing server constants. The model input alias, source text and model output are not consulted. The adapter **always passes** its authorized scope and this explicit mapping to render_answer. It does not use the component's default placeholder label table or optional missing-context defaults. Those pure-library defaults do not provide authorization and must not be used by an execution host.

Missing mappings yield exactly `the inventory item`; scope mismatch raises/refuses instead. No alias, item ID, source text or sanitized fragment is used as fallback. Client-supplied mappings/scopes/renderer versions are not accepted by replay. Only the configured tenant parameter, validated against the retained immutable source and existing owned run, determines scope. No production UUID or identity is created.

The adapter pins the renderer revision both during configuration creation and before input admission; mismatch/downgrade fails with FAILED mode_mismatch. No old renderer or generic candidate pipeline is called. Trusted configuration SHA now binds renderer, vector identity and the canonical label policy/table. Therefore old SourceSnapshots bound to the v1 config digest cannot be silently reused: re-retain authoritative source under the new approved configuration. Record/snapshot hashes themselves remain unchanged for the same source facts and timestamps.

## Independent conformance and hashes

Independent review calculations live outside Git at `/workspace/.nasha-hq/renderer-v2-adoption-review/`. They use the reviewer's separate serializer/semantic implementation and the standard jsonschema package, not Claude's verifier or production validator. Both packages pass:

- v1: 7 answer strings, 15 envelopes, original result hashes and 102 exact verdicts.
- v2: **18** answer strings, 18 envelopes/result hashes and 102 exact verdicts. The upstream handoff's “17” answer-vector count is a nonfunctional documentation count discrepancy; the actual package has 18.
- Both: 8 positive/14 negative canonical vectors, 24 v1 record hashes, 3 historical-v0 hashes, 13 sensitivity checks, 9 snapshot hashes and all eight Amara mappings.
- Frozen case-set comparison: all 60 ModelInputs, snapshot hashes, oracle hashes and prompt unchanged; only c43–c50/c51/c53/c54/c56 answer strings change. All twelve renderer-originated exposures are absent in independently calculated v2 output. No model was invoked.

All eight adapter ModelInputs and trusted answer strings remain unchanged. Each computed accepted-result SHA changes because renderer_revision is in the existing preimage, even when text is unchanged. The preimage still uses ops-explanation-output.v1. Tests compare the adapter's new hashes directly to all eight v2 expectations, including null hashes for abstention. Historical v1 expected hashes remain reproducible independently without exposing a production downgrade path.

The trusted label rule repairs a renderer exposure, not the model's behavior. Do not combine raw-model injection results with renderer-originated exposure counts or call a scripted replay model evidence.

## Tests and packaging

Run from this worktree:

```bash
PYTHONPATH=showcase:lab /workspace/.brewery-venv/bin/python -m pytest -q showcase/tests/test_operations_adapter.py showcase/tests/test_renderer_v2_adapter.py
PYTHONPATH=showcase:lab /workspace/.brewery-venv/bin/python -m pytest -q showcase/tests
```

Results: **198 targeted passed; 282 full-suite passed**, zero failures. One non-failing platformdirs runtime-directory warning appeared. Full suite includes PostgreSQL RLS/reconciliation, original HQ/workforce authorization, unchanged proposal/action hashes, owned-run access and audit/trace/WEIR behavior. New tests independently check both manifests, historical/current result hashes, 18 v2 renderings, the eight adapter expectations, all twelve attack/bait aliases, swapped tenant labels, missing mappings, non-placeholder host scopes, explicit trusted context, historical-path prohibition and renderer downgrade refusal. The 102 verdict fixtures are byte-identical between v1 and v2 and all remain green. Wheel resource/pin loading and offline replay are checked separately; no shared platform is installed or changed.

## Remaining readiness limits

The adapter is ready as an offline contract component for a future controlled demonstration. It is not a live path or model approval. Remaining work still requires acceptable exact-configuration M-OPS-2 evidence and authorized runtime safeguards, identity/capability bindings, durable explanation sidecar/audit/idempotency and authenticated WEIR/endpoint/UI integration. The existing no-provider adapter creates no workflows, approvals, purchases, communications or financial records. Do not convert AUDIT_PENDING to ACCEPTED without actual durable auditing. No schema or validator revision was needed for this correction.
