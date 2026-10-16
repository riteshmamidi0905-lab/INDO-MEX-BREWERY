# P5 runbook

**SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.** Commands assume the compose stack in `lab/docker-compose.service.yml` (never run locally by the author; exercised by CI) or the same settings on any host. `C="docker compose -f lab/docker-compose.service.yml --env-file lab/.env"`.

## 1. First start
1. Create the secret files (`lab/secrets/README.md`): `db_password`, `database_url`, `jwt_keys.json`. Never commit them; never paste them into tickets.
2. `cp lab/.env.example lab/.env`; set `P5_ENV=staging`.
3. `$C config -q` (validates interpolation), then `$C up -d --build`. Order is enforced: db healthy, then the `migrate` job must complete, then `api`.
4. `curl -fsS localhost:8000/readyz` returns 200 with all checks `ok`. `docker inspect` health of `api` becomes healthy after the knowledge base is built (about a minute).

## 2. Stop and restart
`$C stop api` sends SIGTERM: the service drains (new requests 503 `SHUTTING_DOWN`, `/readyz` 503), waits up to `SHUTDOWN_GRACE_S`, closes the pool and exits 0. The compose `stop_grace_period` (25 s) is longer than the drain plus uvicorn's 15 s graceful timeout. `$C down` keeps volumes; `$C down -v` deletes the database and agent data.

## 3. Configuration error (container exits at once, code 78)
`$C logs api | head`: the message `CONFIG ERROR: invalid configuration: NASHA_SVC_X: reason` names the setting, never the value. Fix the setting and recreate. Check without starting: `$C run --rm api python -m nasha_lab.service check-config` (secrets are masked). Common causes: key shorter than 32 characters or placeholder-like, `JWT_ACTIVE_KID` not in the key ring, unknown (misspelled) `NASHA_SVC_*` name, `DEV_TOKEN_ISSUER` or `DOCS_ENABLED` with `ENV=staging`, secret file unreadable by uid 10001.

## 4. Database down
Symptoms: `/readyz` 503 (`failed: [db, schema]`), `/v1` DB routes 503 `DB_UNAVAILABLE` or `DB_POOL_EXHAUSTED` with `Retry-After`, `nasha_db_up 0`, `/healthz` still 200, read-only tool routes still answer.
1. `$C ps db`, `$C logs db | tail`. Disk full and a crashed container are the usual causes.
2. Restore the database. The API needs no restart: the pool reconnects and the breaker half-opens within `DB_BREAKER_RESET_S` (verified, F01).
3. If a decision was executed while the database was down, a dead letter is in `data/dead-letter-spool.jsonl` (volume `api_data`); the next healthy `/readyz` replays it into the table. Then triage dead letters (section 9).
Do not restart the API "to fix" an outage: it hides the ambiguity window; check dead letters first.

## 5. Migration failure and ROLLBACK PROCEDURE
Migrations: `python -m nasha_lab.service.migrations {up|down --target N|status|verify}` (inside the `migrate` image; DSN from the same secrets).

**Failure during `up`.** Each migration is one transaction: a failing migration leaves schema and version unchanged and the job exits non-zero (`MIGRATION_FAILED ... version stays N`). The API container does not start (`service_completed_successfully`); an API already running against version N keeps serving if it is compatible. Steps: read `$C logs migrate`; fix the SQL as a NEW migration or correct the unapplied file; run `up` again. Never edit a migration that has been applied (`CHECKSUM_MISMATCH` blocks all migration until reverted).

**Rolling back a bad release (step by step).**
1. Decide whether data written by the new schema may be lost. `down` scripts drop what `up` created.
2. Take a backup first: `$C exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql` (store it outside the repo).
3. Stop traffic to the new API: `$C stop api`.
4. `python -m nasha_lab.service.migrations status` and note `current`.
5. If the new code only ADDED columns/indexes (additive) you can usually keep the schema: deploy the previous image with `NASHA_SVC_ALLOW_NEWER_SCHEMA=true` and stop here.
6. Otherwise roll the schema back: `... migrations down --target <previous version>` (newest first, each in its own transaction; a failing down is rolled back and reported `ROLLBACK_FAILED`).
7. `... migrations verify` must exit 0 (no checksum mismatch, no gap, no newer version).
8. Start the previous image; `/readyz` must be 200; run the smoke calls in section 10.
9. Record the incident and the data decision. If anything is unclear, restore from the dump rather than guessing.
(The older SQLite rollback design for the ops store is in `OPS-ROLLBACK.md`.)

## 6. Key rotation (signing keys)
1. Generate a new key: `openssl rand -hex 32`. Edit `lab/secrets/jwt_keys.json` to hold BOTH keys: `{"k1":"<old>","k2":"<new>"}`.
2. Set `NASHA_SVC_JWT_ACTIVE_KID=k2`, recreate `api` (and `migrate`). New tokens are signed with k2; unexpired k1 tokens still verify.
3. Wait at least `TOKEN_MAX_TTL_S` (default 3600 s).
4. Remove k1 from the file and recreate `api`. Any remaining k1 token now fails `AUTH_INVALID_TOKEN`.
Emergency (suspected leak): skip step 3 and remove the compromised key immediately; all its tokens die at once and callers re-authenticate. There is no per-token revocation.
Database password: change it in PostgreSQL and in `db_password`/`database_url` together, then recreate `db`-dependent services.

## 7. Rate-limit tuning
Symptom: legitimate 429s (`nasha_rate_limited_total{scope}` rising, `RATE_LIMITED` with `retry_after_s`). Per-principal limits protect one user, per-IP limits protect the service (many users behind one proxy share an IP: set `TRUSTED_PROXY_HOPS` correctly or raise `RATE_IP_CAPACITY`). Change `RATE_*_CAPACITY` (burst) and `RATE_*_REFILL_PER_S` (sustained), recreate `api`. Limits are per replica and reset on restart. Do not exempt probes by raising limits; they are already exempt.

## 8. Incident triage (order of questions)
1. `curl /healthz` (process alive?) then `/readyz` (which check failed?).
2. `nasha_db_up`, `nasha_db_pool{state="waiting"}`, `nasha_http_errors_total` by status, `nasha_errors_total` by code (OPERATOR token).
3. Logs: JSON lines; find a failing `request_id`, then all lines with the same `trace_id`. Principals appear only as hashes.
4. 5xx pattern: 503 `DB_*` means the database; 502/504 `UPSTREAM_*`/`TOOL_TIMEOUT` means tools (breaker state is in `nasha_tool_calls_total` outcomes); 500 `DECISION_AMBIGUOUS` means a dead letter exists.
5. 401 spike: expired tokens or a rotated key. 403 spike: role mapping. 429 spike: section 7.
6. Mutating calls that timed out: do NOT assume failure; retry with the SAME `Idempotency-Key`.

## 9. Dead letters
`GET /v1/dead-letters` (OPERATOR). Each record has `replay_instructions` written by the failure policy (inspect the target state first, then decide). After a person has checked, `POST /v1/dead-letters/{id}/resolve` with status `ALREADY_APPLIED`, `REPLAYED` or `DISCARDED` and a note. Nothing is replayed automatically.

## 10. Smoke checks after any change
`/healthz` 200; `/readyz` 200; unauthenticated `/v1/events` 401; a READER cannot approve (403); `POST /v1/runs` twice with one key returns one run (`Idempotent-Replay: true`); `/metrics` with an OPERATOR token shows `nasha_db_up 1`. CI runs exactly these (job `compose-smoke`).
