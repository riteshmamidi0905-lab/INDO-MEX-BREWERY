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
