# P5 threat model (STRIDE over the real components)

**SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.** Scope: the hardened service in `nasha_lab/service/`, PostgreSQL, the in-process agent, the container and compose design. It extends `THREAT-MODEL.md` (agent, tools, trust gateway), which still applies to everything behind the API. No asset here is real; the analysis is of the design and of what the tests prove.

Assets: run state and approvals (integrity), the audit log (integrity, non-repudiation), signing keys and database credentials (confidentiality), availability of the API, the synthetic data. Actors: anonymous network caller, authenticated low-privilege caller (READER), reviewer, operator, a compromised container, a hostile document or tool output (see the base threat model).

| Component | STRIDE | Threat | Control (implemented) | Evidence | Residual risk |
|---|---|---|---|---|---|
| API entry | S | forged, replayed or downgraded token | HS256 pinned, `kid` required and known, issuer/audience/exp/iat/jti required, lifetime cap | `test_forged_or_malformed_tokens...` (16 cases incl. `none`, algorithm switch) | no revocation before `exp`; shared secret means anyone who can verify can mint |
| API entry | S | spoofed client address to dodge limits | forwarded headers ignored unless `TRUSTED_PROXY_HOPS` set | `test_forwarded_headers_cannot_be_used...` | behind a proxy the setting must be right |
| Routes | E | role escalation, extra claims | only `role` maps to permissions; token cannot carry permissions; deny by default, start-up refuses an unprotected route; lab `ROLE_POLICY` still decides mutation approvals | permission matrix test, `test_a_token_cannot_carry_a_permission_claim...`, `test_agent_role_policy_is_still_enforced...` | coarse roles, no per-object ACL beyond run ownership |
| Run endpoints | I | IDOR: reading another user's run | non-owners without `runs:read_all` get 404 identical to "missing" | `test_a_reader_cannot_read_or_list_someone_elses_run...` | reviewers can see all runs by design |
| Run endpoints | E / R | caller names another reviewer in the body | body has `extra=forbid`; reviewer is the token subject | `test_the_reviewer_identity_comes_from_the_token...` | |
| Approvals | T | double execution via retry or race | idempotency key + advisory lock, `FOR UPDATE` on the run row, agent state check, reconciliation | F07, F12b, concurrent approval test | executed-but-unrecorded window is dead-lettered and reconciled, not impossible |
| Inputs | T | SQL injection, path/param injection, NUL, oversize, wrong media type, header injection | bound parameters only; regex-constrained params; control characters rejected; 16 KiB body cap (header and streaming); JSON only; request id and idempotency key validated | `test_injection_strings...`, oversize and header tests, F10 | the lab's own tools receive only validated, typed arguments |
| Inputs | D | request flood, big bodies, slow work | IP and principal token buckets, body cap, bounded worker pool, deadlines, DB statement/lock/pool timeouts, breaker | F03, F06, F16b | in-memory limits, no slow-client (slowloris) protection beyond uvicorn defaults, no WAF |
| Metrics | D | label-cardinality memory growth | route templates, method clamp, bounded span ring and limiter tables | F21, bounded-memory tests | |
| Logs / errors | I | secrets, tokens, DSN or PII in logs and responses | `SecretStr`, scrubber, whitelisted fields, principal hashed with a keyed hash, exception type only, one envelope with no SQL or stack | `test_no_secret_or_token_appears...`, `test_logs_identify_principals_only_by_keyed_hash` | free text from callers is scrubbed by pattern, not by classification |
| `/readyz` | I | topology and version disclosure | coarse words only | F23 | `/readyz` is unauthenticated: keep it off the public listener |
| `/metrics`, `/v1/audit`, dead letters | I / E | unauthorised access | OPERATOR/AUDITOR permission | role matrix | scraper needs a token |
| PostgreSQL | T / R | tampering with or deleting audit rows | append-only trigger; `approvals`/`runs` written in the same transaction as the audit row | `test_audit_log_is_append_only` | superuser can drop the trigger; no external log sink or hash chain |
| PostgreSQL | T | edited or skipped migrations | checksums, contiguity check, advisory lock, transactional apply | migration tests | whoever can run DDL can bypass the tool |
| PostgreSQL | D | outage, slowness, schema drift | pool/timeouts, breaker, readiness, `SCHEMA_MISMATCH`, spool for dead letters | F01, F02, F03, F11 | no replica/failover |
| Config / secrets | I / S | secret in repo, image, env dump or logs | secret files, `.gitignore`, build-context ignore, CI secret scan and no-env-file check, placeholder-only tests | `test_p5_deploy_static.py`, CI `static` job | secrets mounted with mode 644 in CI only because the runner is throw-away; real hosts need 0400 and a secret manager |
| Config | T | typo disables a security setting | unknown `NASHA_SVC_*` rejected; `*`-CORS and weak keys rejected; staging forbids dev issuer and docs | config tests, F14 | |
| Container | E | breakout or write to the image | non-root uid 10001, read-only root, `cap_drop ALL`, `no-new-privileges`, tmpfs, resource limits, loopback-only publish, no DB port | static tests; **CI-verified only** | no seccomp/AppArmor profile, no image signing or scan |
| Agent / tools | T / E | prompt injection, tainted arguments, forbidden actions | unchanged lab controls (permission classes, signed grants bound to run+tool+args, taint tracking, trust gateway) | existing suites | see `THREAT-MODEL.md` |
| Supply chain | T | compromised dependency or base image | base images pinned by tag; lower-bound requirements | | **no lock file, no digest pin, no SBOM or vulnerability scan** |

## Top residual risks, in order
1. Symmetric tokens with no revocation, and no real identity provider.
2. In-memory rate limits and process-local agent checkpoints: not safe to scale out as is.
3. Agent effects outliving a cancelled request until reconciled.
4. Supply chain controls absent.
5. Everything container-related is proven only by CI, not by running on a host.
