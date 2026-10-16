# Failure and retry policy

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** Declarative source: `ops/failure-policy.json`. Code: `nasha_lab/ops/failure_policy.py`. Trials: `nasha_lab/ops/policy_trials.py` -> `results/ops/failure_policy_trials.json`. Tests: `tests/test_ops_failure_policy.py`.

## Decision (owner)

"Make retry and fallback the default" is **rejected** as a universal rule. A retry is correct only when repeating the call cannot change state, or when the target can recognise the repeat. Every operation therefore carries exactly one explicit class; an operation that has no entry is treated as `DO_NOT_RETRY` and dead-lettered on ambiguity (fail closed).

## Motivating evidence (GAP-01, `results/ops/reliability_gaps.json`)

A draft whose first attempt commits and then reports a timeout is an *ambiguous* failure. Measured over 10 seeded runs: no retry left an orphan committed draft and an escalation in 10/10; **naive retry duplicated the draft in 10/10**; reconcile-then-retry duplicated it in 0/10 and still reached the draft proposal. The committed GAP-01 file is kept as that pre-policy baseline and is not regenerated.

## Operation classes

| Class | Meaning | Examples here |
|---|---|---|
| `SAFE_TO_RETRY` | no side effects | every READ and ANALYZE tool, the LLM planner call, knowledge retrieval, HTTP GET |
| `SAFE_WITH_IDEMPOTENCY_KEY` | side effects, target deduplicates on a key; retry only with the same key | run start (key = event id), ops-store writes, keyed HTTP POST |
| `RECONCILE_BEFORE_RETRY` | side effects, no key; read whether the effect happened first | both DRAFT tools (by run, kind, exact payload), `release_draft` (by draft status) |
| `DO_NOT_RETRY` | side effects that state alone cannot disambiguate, or must never run | `adjust_inventory_record`, `flag_record_for_review`, both EXTERNAL_ACTION tools, unkeyed DB writes, unkeyed HTTP POST |
| `HUMAN_REVIEW_REQUIRED` | a person decides every failure | the approval -> execute step |

Per-tool rationale is in the JSON. A test fails if a registered tool is unclassified, if the JSON disagrees with the registry's permission class, or if a MUTATE/EXTERNAL tool is `SAFE_TO_RETRY` or `SAFE_WITH_IDEMPOTENCY_KEY`.

## Failure classes

`TRANSIENT`, `TIMEOUT_AMBIGUOUS` (a timeout of an operation with side effects; a timeout of a pure read is just `TRANSIENT`), `RATE_LIMIT`, `DEPENDENCY_DOWN` (breaker open, model unavailable), `VALIDATION`, `AUTH` (approval, taint, forbidden), `PERMANENT`, `MALFORMED_RESULT`. Unknown error codes are `TIMEOUT_AMBIGUOUS` when the operation has side effects and `PERMANENT` otherwise.

## Decision table (operation class x failure class -> action)

Actions: **R** retry with exponential backoff + seeded jitter within a retry limit; **C** reconcile then retry; **F** fail fast; **D** dead-letter + human queue.

| | TRANSIENT | TIMEOUT_AMBIG. | RATE_LIMIT | DEP_DOWN | VALIDATION | AUTH | PERMANENT | MALFORMED |
|---|---|---|---|---|---|---|---|---|
| SAFE_TO_RETRY | R | R | R (waits >= Retry-After) | F | F | F | F | F (R for the LLM planner) |
| SAFE_WITH_IDEMPOTENCY_KEY | R | R | R | F | F | F | F | R |
| RECONCILE_BEFORE_RETRY | C | C | C | F | F | F | F | C |
| DO_NOT_RETRY | D | D | F | F | F | F | F | D |
| HUMAN_REVIEW_REQUIRED | D | D | D | D | D | D | D | D |

Guards: a keyed class without a key becomes D; C without a reconciler becomes D; R past the retry limit or an exhausted retry budget becomes D for an operation with side effects and F otherwise; a reconcile that is inconclusive is D; a reconcile that finds the effect returns it as the success.

## Machinery

* Backoff reuses `resilience.RetryPolicy` (base 20 ms, factor 2, cap 200 ms, +-25 % seeded jitter); the circuit breaker is `resilience.CircuitBreaker`, fed only by failures that speak to dependency health.
* `RetryBudget`: retries may add at most 20 % over first attempts plus a floor of 3, so a degraded dependency is not turned into a retry storm.
* Dead-letter record (`OpsStore`, SQLite, file-persisted, own versioned migrations): id (keyed, so a replayed failure converges to one record), created, correlation id, run id, operation, tool, class, failure code and class, attempt count, reason, args hash and redacted args, status (`OPEN`, `ALREADY_APPLIED`, `REPLAYED`, `DISCARDED`) and **replay instructions** specific to the class. `OpsStore.list()` is the human queue.
* `OpsStore.run_once(key, ...)` is the idempotency ledger: the first completed result for a key is returned for every later call and the side effect is not repeated.
* `PolicyStack` is a drop-in for `ExecStack` that applies the policy to the real tool executor; `PolicyRunner` applies it to any callable (LLM, retrieval, HTTP). The stock service still does not use either unless the caller wires them in (opt-in, like the other resilience wrappers).

## Measured (seeded trials, `results/ops/failure_policy_trials.json`)

| Trial | Result |
|---|---|
| Ambiguous draft (commit then timeout), 10 runs | no retry: 0 reach the proposal; naive retry: **10/10 duplicated drafts**; ExecStack reconcile: 0/10 duplicated, 10/10 reach the proposal; **failure policy: 0/10 duplicated, 10/10 reach the proposal**, 0 dead letters (reconciliation resolved it) |
| Ambiguous approved mutation (`flag_record_for_review`, commit then timeout), 10 runs | policy: 1 attempt per run, 10/10 dead-lettered with replay instructions, 0 duplicates. "Retry everything": 2 attempts per run, **0 duplicates**, because the single-use approval grant refused the second attempt (`REPLAYED`) in 10/10 runs |
| Transient timeout on the first attempt, 20 runs | action equals the clean action: no retry 2/20; policy 20/20; retry-everything 20/20 |
| Malformed tool result, 20 runs | policy: 20 attempts (fail fast); retry-everything: 60 attempts; same conservative end state (16/20) in both |
| Persistent tool timeout, 20 runs | policy and retry-everything both 60 attempts (3 per call): **the policy does not save work here**; a persistent timeout of a pure read is retried to the limit. The breaker is what bounds repeated runs |
| Persistent upstream error, one stack across 6 runs | 3 attempts in the first run, then the breaker is open and the next 5 runs make 0 attempts (`CIRCUIT_OPEN`) |

Honest reading: the duplicate-draft result is the policy's real contribution. For approved mutations the identity layer's single-use grants already prevented a duplicate; what the policy adds is that the ambiguity is *recorded* for a human instead of surfacing as a confusing `APPROVAL_REQUIRED: REPLAYED` on a retry. It also means a retried `release_draft` cannot succeed after a transient failure (the grant was consumed): only the reconcile-found path helps; otherwise a re-approval is needed.

## Limits

* The LLM planner (`llm_planner.py`, frozen-adjacent) keeps its own bounded retry; its limit is asserted equal to the policy's. It is not routed through `PolicyRunner`.
* Reconciliation of a draft treats two drafts with identical run, kind and payload as the same draft.
* No alert class or runbook exists for a dead letter yet; the human queue is read from the store.
* Sequential runs on synthetic data; no concurrency, no real upstream.
