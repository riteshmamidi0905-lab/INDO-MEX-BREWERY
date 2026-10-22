# P5 failure log

**SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.** Every row is a weakness a test or review of the hardened service actually exposed, with the behaviour first observed, the root cause, the fix and the regression test. Scenario results (expected stated before the run, observed, pass/fail) are in `results/p5/failure_scenarios.json`; statuses, codes and counts there are deterministic, fields named `wall_clock_ms_NOT_DETERMINISTIC` are one run on one machine. The scenarios' final state is all-pass; the first-observed column is what happened before the fix.

## A. Weaknesses found and fixed

| ID | Scenario | First-observed behaviour | Root cause | Fix | Regression test |
|---|---|---|---|---|---|
| P5-W1 | F01 database unavailable at start | The app started (liveness 200, readiness 503, DB routes 503, as designed) but never recovered: 30 s after the database came back `/readyz` was still 503 and the circuit breaker stayed OPEN | `psycopg_pool.ConnectionPool.wait()`, used in start-up, **closes the pool when it times out**; every later request got `PoolClosed` | `Database.wait_ready` polls pool statistics instead of calling `wait()` | `test_F01_database_unavailable_at_start_then_recovers` (recovery without restart) |
| P5-W2 | F11a schema older than the app | `/v1/runs` against an incompatible schema (renamed column) returned `500 INTERNAL_ERROR` | `UndefinedColumn`/`UndefinedTable` fell through to the generic mapping | mapped to `503 SCHEMA_MISMATCH` (never retried) | `test_F11_schema_older_than_the_app` |
| P5-W3 | F15 NUL byte in free text | `POST /runs/{id}/approve` with `"note": "ok\u0000bad"` returned `500 DECISION_AMBIGUOUS`: the agent had already executed the approval, then PostgreSQL refused the text (`NUL (0x00) bytes`); a dead letter was created for a request that should have been a 422 | request models accepted any string; the database error came after the in-process effect | all request strings reject control characters at validation (before any effect) | `test_F15_nul_byte...`, `test_free_text_with_a_nul_byte...`, property test `test_no_request_model_accepts_control_characters` |
| P5-W4 | F20 idempotency table growth | expired keys stayed in `idempotency_keys` forever (2 rows, 1 expired, nothing deleted; `purged: -1`, no purge existed) | the TTL only filtered reads | `Ctx.run_maintenance` plus a background task every `MAINTENANCE_INTERVAL_S` | `test_F20_...`, `test_F20b_...` |
| P5-W5 | F21 metric label cardinality | 40 requests with distinct HTTP method tokens created 40 new `nasha_http_requests_total` series | raw method used as a label | unknown methods count as `OTHER` | `test_F21_...` |
| P5-W6 | F22 trailing slash | `GET /v1/events/` answered `307` before authentication, outside the error contract | framework `redirect_slashes` | disabled; the route envelope `ROUTE_NOT_FOUND` is returned | `test_F22_...` |
| P5-W7 | F23 readiness disclosure | anonymous `/readyz` body contained `schema_version: 3`, "version 3", and (unhealthy path, from code review and the first F11 run) "database 1, build needs 3" | helpful detail strings | coarse per-check words only (`ok`, `unavailable`, `SCHEMA_OLDER`, `SCHEMA_NEWER`); versions only in `nasha_schema_version` (OPERATOR) | `test_F23_...` |
| P5-W8 | F14 configuration (secret files) | a key ring supplied as `NASHA_SVC_JWT_KEYS_FILE` failed with "Input should be a valid dictionary" (a misleading, but value-free, message) | file content was passed as a string, not parsed as JSON | the loader parses file content for JSON settings | `test_secrets_can_be_read_from_files` |
| P5-W9 | contract | read of a run by an AUDITOR was refused `403` on `GET /v1/runs/{id}` although the role holds `runs:read_all` | AUDITOR lacked `runs:read_own`, which the route requires | permission table corrected | `test_privileged_roles_can_see_all_runs` |
| P5-W10 | F10 malformed payloads | invalid UTF-8 body answered `422 INVALID_REQUEST "request rejected"`; a JSON array was reported as malformed JSON (400) | status mapping defaults | 400 maps to `MALFORMED_BODY`; only `json_invalid` is malformed, shape errors are 422 | `test_malformed_bodies_and_media_types` |

## A2. Found by the first CI run (head f32e62b), the only place these could appear

| ID | Where | First-observed behaviour | Root cause | Fix | Regression |
|---|---|---|---|---|---|
| P5-C1 | lab-ci `test` (full suite, requirements-dev) | `test_openapi_document_matches_the_committed_snapshot` failed: the generated OpenAPI differed from the snapshot | the snapshot recorded generator-specific spelling (constants, nullable types); the full suite installs a different pydantic than my sandbox, and the same test had passed in p5-service-ci | the contract test compares a normalised form (routes, methods, parameters, schema and status-code references, security, property names, required sets); it passes locally under pydantic 2.10.6 and 2.13.5 | `test_openapi_document_matches_the_committed_snapshot` |
| P5-C2 | lab-ci `test` | `test_no_secret_or_token_appears_in_logs_responses_or_errors` failed: 'nasha' found in logs | the CI database password is the throw-away word `nasha`, which is also the logger name `nasha.service`; the test searched for the bare password. Not a leak (the service logs no DSN) but a test that could not tell | the test now looks for the password in the forms in which it could leak (`password=<pw>`, `:<pw>@`), and still searches keys and tokens by value | same test |
| P5-C3 | p5-service-ci `compose-smoke` | build, `compose up`, health, the whole contract smoke and the hardening checks passed; the graceful-stop step failed on exit code | my expectation (exit 0) was wrong: uvicorn re-raises SIGTERM after a clean shutdown, so the container exits 143; the log showed "Application shutdown complete" | the step accepts 0 or 143 (137 would mean a kill) and requires the shutdown log lines | workflow step |
| P5-C4 | earlier lab-ci run (head 13adf4a) | `ModuleNotFoundError: pydantic_settings` collecting tests/p5 | requirements-dev.txt had not yet been updated in that commit | fixed in f32e62b (dev requirements include requirements-service.txt) | CI |

W8, W9 and W10 were found by the development tests on first run (not by an injected fault); W1 to W7 by failure injection or review.

## B. Scenarios that behaved as expected on the first run

F02 (database lost between the agent effect and the write: 503, nothing persisted, same-key retry adopts the agent's run, `reconciled: true`, exactly one agent run), F03 (statement timeout 504 `DB_TIMEOUT`; pool exhaustion 503 with `Retry-After`; no `idle in transaction`), F03b (0.8 s added network latency: bounded 5xx, recovers), F04/F05 (invalid and expired tokens: 401, zero rows), F06 (rate limit: of 10 calls exactly 5 pass; probes never limited; recovery after the clock advances), F07 (20 concurrent duplicates: one run, 19 replays), F08 (tool timeout: 3 attempts under the policy, 504 `TOOL_TIMEOUT`), F09 (upstream error: 502 after 3 attempts, then breaker open: 503 with 0 attempts; a transient fault is absorbed), F10, F11b (newer schema), F12a/b/c (atomicity, effect-without-record dead letter and reconciliation, dead-letter spool and replay), F13 (migration failure), F16/F16b (deadline cancellation and shedding of queued work), F18 (graceful shutdown on a real server socket), F19 (metrics during an outage). That they passed first time is a statement about these tests, not proof the code is free of the same class of bug elsewhere.

## C. Residual weaknesses (found, not fixed)

* An agent step cannot be cancelled once running. After a deadline the client gets 504 and the database transaction rolls back, but the in-process agent effect stays until the same-key retry reconciles it (F16). Eliminating this needs an agent that can be interrupted or a durable outbox.
* The per-process rate limiter does not coordinate across replicas, and its bounded table lets many distinct keys evict one victim's bucket.
* Tokens cannot be revoked before `exp` (rotate the signing key to invalidate all).
* Agent checkpoints are process-local; a replica without them answers `RUN_NOT_RESUMABLE`.
* `ConnectionPool` reconnect was exercised through a TCP proxy against a local server, not through a real network partition.

## D. Not tested

Real TLS, a real reverse proxy, multi-replica behaviour, load beyond tens of concurrent requests, slow-client attacks (uvicorn keep-alive/timeouts left at defaults), disk-full on the database, PostgreSQL failover, clock skew between hosts, container-level behaviour (CI only).
