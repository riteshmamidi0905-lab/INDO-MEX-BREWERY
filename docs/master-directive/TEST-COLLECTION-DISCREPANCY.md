# Six-test collection discrepancy (local 708 vs CI 702) — resolved

Commit examined: `306b29d` (career/integration-review), fresh clean worktree. CI run: lab-ci #133 → `686 passed, 16 skipped` (702).

## Findings (reproduced locally)
- Fresh checkout, Python 3.13: `pytest --collect-only tests` → **708** collected; full run → **585 passed, 123 skipped** (no Postgres, no private keys, no model runtime locally).
- `tests/test_ops_otel_export.py` has **7** tests (7 passed locally with the OTel packages installed).
- That module starts with `pytest.importorskip("opentelemetry.sdk.trace")`. `requirements-otel.txt` is **not** installed by `lab-ci` (`requirements-dev.txt` only pulls in `opentelemetry-api` through fastapi; the CI install log shows `opentelemetry-api` and no SDK).
- A module-level `importorskip` turns the whole module into **1** skip. 708 − 7 + 1 = **702**. The arithmetic matches CI exactly.

## Consequence (real finding)
The 7 OpenTelemetry export tests have been **silently skipped in CI**; they only run where the OTel SDK is installed. Not a failure, but CI never exercised them.

## What is NOT verified
- The exact composition of CI's 16 skips: CI ran without `-rs`, so the log has no per-test skip reasons, and the log blob could not be downloaded from this sandbox. Expected: 12 private-key + 1 model-runtime + 1 OTel module = 14; the other 2 are unattributed.
- Python 3.12 (CI) vs 3.13 (local) was not shown to change collection.

## Recommended fix (not applied, needs approval to touch CI)
Add `pip install -r lab/requirements-otel.txt` to lab-ci, and run pytest with `-rs` so skip reasons are in the log.
