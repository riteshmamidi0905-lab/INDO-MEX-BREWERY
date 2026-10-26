# NASHA Operations explanation: golden vectors v2 (renderer `ops-renderer-v2.0-tenant-scoped-labels`)

Supersedes nothing: **v1 (`../v1`, identity `14f526e7…2e59e2f`, renderer `ops-renderer-v1.0-m-ops-1`) stays immutable and verifiable.** v2 changes ONE thing: how the item label is displayed.

* The displayed label comes **only** from a server-owned table keyed by `(authorized tenant scope, inventory item id)` (`identifiers.json` -> `display_labels`). The snapshot alias is never read for wording.
* No mapping: exactly `the inventory item` (`generic_item_label`). Never the alias, the item id, source text, or an escaped/sanitized copy.
* The host's authorized scope differing from the snapshot's `tenant_scope_id` is `REJECTED` (`input_refused` + `cross_tenant_reference`) before any provider call; it is never a generic-label fallback.
* For the two trusted labels the visible wording equals v1; every `accepted_result_sha256` changes because the renderer revision is part of the hashed preimage.
* Unchanged and byte-identical to v1: `canonical_json.json`, `record_hashes.json`, `scenarios.json`, `verdicts.json` (the 102 validator verdicts), `diagnostics.json`. Schemas and the validator revision are unchanged.

| File | What it fixes |
|---|---|
| `identifiers.json` | identifiers, `display_labels`, `generic_item_label`, label and authorization rules |
| `rendered.json` | 17 answer vectors (trusted labels, tenant swap, markup, 4 injection aliases, 2 bait aliases, unmapped item, unmapped tenant), abstentions, fixed messages, template |
| `envelopes.json` | one envelope per status incl. the untrusted-alias accepted answer, the unauthorized-scope rejection and the matching-scope acceptance |
| `amara_adapter.json` | the 8 adapter expectations under renderer v2 (same visible text as v1, new accepted hashes) |
| `canonical_json.json`, `record_hashes.json`, `scenarios.json`, `verdicts.json`, `diagnostics.json` | identical to v1 |
| `verify_vectors.py` | standard-library-only verifier that imports nothing from the repository |
| `MANIFEST.sha256` | hashes of every file; its SHA-256 is the package identity |

Verify: `python3 verify_vectors.py` prints `ALL VECTORS VERIFIED`.
