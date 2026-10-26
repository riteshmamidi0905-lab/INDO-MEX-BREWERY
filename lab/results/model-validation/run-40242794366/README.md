# model-live run #4 (GitHub Actions run 40242794366), preserved evidence

**Provenance, stated plainly.** These files were extracted from the *job log* of the run (the last 5,000 lines, which contain every result block). They are **not** the uploaded artifact `model-live-evidence` (ID 12618274256, zip SHA-256 `c128aed54cea59ed94cd9b94c1c7b7324e1291be7248b25022ad2f38a6cd5226` as printed by the upload step): the artifact is served from `productionresultssa18.blob.core.windows.net`, which this session's network policy refuses, so it could not be downloaded or its hash verified. The artifact's `live-battery.json` is the same file the job printed between `MODEL_LIVE_RESULT_BEGIN/END`, so `result.json` here should be byte-equivalent in content; that has NOT been checked against the artifact.

| File | Content |
|---|---|
| `job-log-tail-5000-lines.txt` | the job log, timestamps kept, first lines cut (the model-pull progress); everything from the digest step on is present |
| `result.json` | the battery result (`MODEL_LIVE_RESULT_BEGIN/END`) |
| `cases.jsonl` | the 19 `MODEL_LIVE_CASE` lines, one per case, unmodified |
| `comparison.json` | the comparison with run 1 and run 3 |
| `acceptance.json` | the independent evaluator's output (criteria 1.0-proposed) |
| `SHA256SUMS` | hashes of the above, computed when they were written |

Integrity checks run when writing: 19 case lines = `cases_total`; passed cases (14) = `cases_passed`; the verdict line in the log equals `acceptance.json`; the model digest is identical in identity, model, expected and evaluator records and `digest_verified` is true; governed workflow `model_output_accepted` = 0; the artifact-upload line is present. Historical records (`baseline-run-40109758918.json`, `run-40141457239.json`, `rescore-run-40141457239-v2.json`) are untouched.

**Recording limitations of run #4 (format 1).** The rejected claim is preserved only to 120 characters (audit event) and 200 characters (comparison); the report, query and retrieved evidence of the governed runs were not recorded. A search of every preserved record and the Ollama request lines found no longer copy; the original claim is not recoverable. See `docs/growth-os/PHASE2-RECORDING-REQUIREMENTS.md`.
