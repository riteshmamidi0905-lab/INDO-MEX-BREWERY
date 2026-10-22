# Engineering branch integration review (2026-10-22)

Scope authorized: inspect, compare, test, and integrate only into a NEW isolated branch. No protected branch was touched; nothing was pushed.

## Branches and dependencies (base `claude/nasha-enterprise-ai-lab` @ e4eeb73; all merge-bases 9cb7ca4)
| Branch | Commits over base | Files changed | Notes |
|---|---|---|---|
| `career/reliability-policies` a1bf2a7 | 11 | 90 | contains `career/p1-p2-ai-ops-control-center` (b6bde60) as an ancestor; failure/retry policy, authority v2, gate calibration, optional OTel, dashboard script |
| `career/p4-analytics-mart-clean` 2897e12 | 3 | 104 | SQLite mart, 24 library queries, forecast, experiment, prospective design; no overlap with the other two |
| `career/p5-hardened-service` a40f2ad | 11 | 129 | forked from reliability at e4ff09e, then diverged (5 commits each side); adds `nasha_lab/service/`, migrations, Docker/Compose, CI workflow |
Not in this integration (not requested): `career/p3-product-case` f6d4b9e, `career/stronger-model-prereg` b669b84.

## Overlaps
p5 and reliability both edit `lab/nasha_lab/ops/*`, `lab/ops/*`, several docs and `.gitignore`. Merging reliability, then p4, then p5 produced ONE textual conflict (`.gitignore`, resolved by union); the `ops/` files auto-merged. Files in which p5 and reliability differ are: .gitignore, lab/README.md, OPS-CONTROL-CENTER(-CASE-STUDY).md, RELIABILITY-MATRIX.md, ops/faults.py, ops/runner.py, ops/telemetry.py, ops/alert-rules.json, ops/failure-taxonomy.json, ops/runbooks/RB-STALE-SOURCE.md.

## Security controls
All p5 service, auth, middleware, migration and gateway files are byte-identical to the p5 branch after integration (compared blob by blob; no differences). The integration did not alter JWT/RBAC, rate limiting, idempotency or migration code.

## Result
Isolated local branch `career/integration-review` (worktree `/home/user/worktrees/integ`), merge commits 90275b3 (reliability), 0e0331d (p4), 306b29d (p5), on top of e4eeb73. Full lab suite on that branch: **585 passed, 123 skipped, 0 failed (365 s)**. The skips were not itemised here; earlier P5 notes say the PostgreSQL-dependent tests (109) need a database that this sandbox lacks, so they remain CI-only evidence. The Docker image and compose files were not built here (no Docker daemon).

## Not verified
Whether p5's CI (Postgres service container) still passes on the merged tree; the merged branch has not been run on GitHub. Whether `canonical_claims` numbers still hold after the merge (the claim tests passed in the suite, but public documents were not re-read). Dashboard rendering (Playwright) was not re-run.

## Recommended plan (needs your approval to push)
1. Push `career/integration-review` and let CI run (Postgres, Docker smoke). 2. If green, open a PR into `claude/nasha-enterprise-ai-lab`. 3. Re-run `canonical_claims` and update documented counts (test count changes from 275/1). 4. Then rebase the new enterprise-simulation work on top. Do not merge the old branch `career/p4-analytics-mart` (answer keys).


## Update 2026-10-22: GitHub CI on the pushed branch (`career/integration-review` @ 306b29d; repository is PUBLIC, content identical to branches already public, no deploy workflow reacts to this branch)
- **lab-ci run 133: success.** test job: 686 passed, 16 skipped (5 min 12 s) with PostgreSQL/pgvector service container; Block-1 evaluation, planner experiment and retrieval-v2 reproduction steps passed; docker job passed.
- **p5-service-ci run 4: success (3 jobs).** Static: ruff, mypy, hadolint, secret scan, no committed env/key files. PostgreSQL job: "P5 tests (real PostgreSQL; none may be skipped here)" passed, migration up/status/verify/down/up cycle passed, failure-scenario results reproduced. Docker job: compose config, build, up, /readyz, contract smoke (auth, idempotency, approval, metrics), container hardening facts, graceful SIGTERM stop all passed.
- **Not run anywhere:** the 12 tests that need private answer keys; the one test that needs a local model runtime.

## The 123 skipped tests in the local run (585 passed / 123 skipped, listed with `pytest -rs`)
| Count | Reason | Where it runs |
|---|---|---|
| 108 | PostgreSQL unavailable locally (`NASHA_PG_DSN`): tests/p5 security 32, service 31, failures 26, migrations 12, contract 7 | executed in CI (p5-service-ci Postgres job; lab-ci has a Postgres service) |
| 12 | `NASHA_PRIVATE_KEYS` not set: analytics difficult-case answer keys are deliberately not in the repo | NOT executed anywhere public (owner-only; unverified) |
| 1 | PostgreSQL + pgvector unreachable (`tests/test_retrieval_v2.py`) | executed in CI (lab-ci pgvector service) |
| 1 | hadolint not installed locally | executed in CI (p5-service-ci static job) |
| 1 | no local model runtime (`tests/test_llm_planner.py` integration) | only via the model-eval workflow, not the CI test job |
CI reported 16 skipped (not itemised in the log): the 12 private-key tests, hadolint, the local-model test, and about 2 not identified. CI collected 702 tests against 708 locally: the 6-test difference is unexplained.

## Validation status
Validated on GitHub: Postgres, Docker/Compose, migrations, security scan, contract smoke, regression suite, reproducibility steps. NOT validated: the 12 private-key tests, the local-model integration test, merge into the default or any production branch (not done).
