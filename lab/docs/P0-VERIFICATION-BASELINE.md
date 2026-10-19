# P0 Verification Evidence — baseline and open gates

**Status: VERIFIED CI BASELINE, NOT P0 COMPLETE.** This file records the verified state of the isolated development branch at `f4950e88aba16fe3a380ec26e53550debee9ef6c`. The baseline is synthetic and offline; no production use is implied.

## Reproducible CI baseline

- GitHub Actions `lab-ci` workflow **#85**, run ID `39165523799`: **success**.
- Python software tests: **296 passed, 1 skipped** (150.87 seconds).
- Docker Compose smoke: **success**; API readiness, review console, and human-approval boundary tested.
- Historical DQ artifact `lab/results/eval_v1.json` retained. The historical shifted-duplicate result was 0 TP / 40 FN.
- Candidate DQ evaluation executed twice in CI with byte-identical output. Across synthetic seeds 1–5, shifted duplicates: 40 TP, 0 FP, 0 FN, precision 1.0, recall 1.0, F1 1.0. Original near-duplicates: 40 TP, 0 FP, 0 FN. Candidate clean dataset: 0 findings. The evaluator did not report a TN count; a false-positive *rate* cannot be calculated without the negative population denominator. Results apply only to the author-generated injected scenarios, not real-world legitimate same-basket transactions.
- Planner reproduction: success in #85.
- RAG v2 reproduction: success in #85.
- Standalone release gate: success in #85; its reported aggregate decision was PASS on the existing committed evidence.
- Software tests include security/trust-boundary and release-gate tests; this does not constitute a production security audit.

## Remaining P0 acceptance blockers

1. **DQ ambiguity:** a same-location, same-basket transaction within one second may be legitimate. The existing shifted-duplicate rule reports ERROR without independent transaction identity evidence. Add explicit legitimate-transaction negatives, multiple-candidate tests, order permutations, and a qualified review classification before production use. Do not interpret synthetic 0 FP as a measured real-world false-positive rate.
2. **Exporter determinism:** CI #85 proves a fresh artifact on one run, not three-run hash stability.
3. **Release gate:** the standalone PASS and current tests do not alone prove exhaustive PASS / FAIL / REQUIRES_REVIEW behavior for every malformed, missing, or unsupported input.
4. **THE WEIR integration:** NASHA's `lab/nasha_lab/trust.py` is a local trust-boundary implementation. Separate repository `riteshmamidi0905-lab/mcp-weir` is an experimental MCP gateway with deterministic policy engine. No actual NASHA-to-Weir call-path integration or end-to-end approval-enforcement test has been verified. Do not claim integration.
5. **Observability:** existing trace and security-evidence components exist, but unified correlation, approval provenance, safe telemetry, and reconstructable cross-system incidents have not been verified.
6. **Final P0 acceptance:** integration security, false-positive controls, complete observability, and end-to-end incident reconstruction remain unverified.

## Reproduction

Use Python 3.12 and `lab/requirements-dev.txt`, with PostgreSQL/pgvector and Playwright as configured in `.github/workflows/lab-ci.yml`.

- `cd lab && python -m pytest -q -p no:cacheprovider tests`
- `cd lab && python -m nasha_lab.export_portfolio --check`
- `cd lab && python -m nasha_lab.evaluate v1 > /tmp/dq-candidate-1.json`
- Repeat into `/tmp/dq-candidate-2.json` and run `diff -u /tmp/dq-candidate-1.json /tmp/dq-candidate-2.json`.
- `cd lab && python -m nasha_lab.eval_planners deterministic /tmp/planner.json`
- `cd lab && python -m nasha_lab.repro_check planner /tmp/planner.json results/planner_deterministic.json`
- `cd lab && python -m nasha_lab.release_gate --out /tmp/release-gate.json`
- `cd lab && python -m nasha_lab.eval_rag2 /tmp/rag2.json`
- `cd lab && python -m nasha_lab.repro_check rag2 /tmp/rag2.json results/rag2_retrieval.json`

Do not alter historical evaluation artifacts or promote this baseline to a claim of completed P0.
