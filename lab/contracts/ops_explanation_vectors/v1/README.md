# NASHA Operations explanation: golden vectors v1

A deterministic, versioned package for checking that two implementations of the Operations explanation contract agree **bit for bit**. Produced by this repository's reference implementation (`lab/tools/ops_golden_vectors.py`, `--check` verifies the committed files are exactly what it generates). **Nothing here is model output.**

| File | What it fixes |
|---|---|
| `identifiers.json` | every version identifier: `canonical-json.v1`, `record-hash.v1` (live) and `record-hash.v0` (historical only), diagnostics `ops-diagnostics.v1`, validator and renderer revisions, the Codex contract pin set (`codex-phase5-spec@b064414…`), limits |
| `canonical_json.json` | canonical bytes, hex and SHA-256 for positive inputs; strict-parse refusals with their lower-case diagnostic for negative inputs |
| `record_hashes.json` | v0 preimages that reproduce the published example hashes; v1 tenant-scoped preimages and hashes for 2 tenants x 4 scenarios; a sensitivity table (changing any preimage field changes the hash) |
| `scenarios.json` | full model inputs for the 4 published scenarios x 2 tenants, their snapshot hashes and required abstention reasons; the published example's snapshot hash |
| `rendered.json` | the shared renderer's strings (shortfall, surplus, equal, singular unit, escaping, every abstention, rejected, failed) and the template rules |
| `envelopes.json` | one full `ops-explanation-result.v1` envelope per case, including `accepted_result_sha256`, REJECTED vs FAILED cases, truncation, profile pins |
| `diagnostics.json` | the complete lower-case diagnostic table with class and REJECTED/FAILED status, the M-OPS-1 spellings, the provenance disambiguation, reserved codes |
| `verdicts.json` | 100+ cases: input, candidate output, options, expected status, lower-case codes and flags |
| `amara_adapter.json` | Amara's current payload (transcribed from `codex/amara-readonly-operations@cb71397`), the expected contract ModelInput per scenario and tenant, field/unit/classification maps, and where the wording differs (decision D7 pending) |
| `verify_vectors.py` | **standard-library-only verifier that imports nothing from the repository** |
| `MANIFEST.sha256` | hashes of every file in the package |

Verify: `python3 verify_vectors.py` (prints `ALL VECTORS VERIFIED`). A second implementation should reproduce every canonical byte string, hash, rendered string, envelope hash, diagnostic and verdict **independently**, then report any difference. Tenant scope ids and the analysis/workflow ids in the vectors are fixed placeholders (the host assigns real ones). Do not edit these files: a change is a new version directory.
