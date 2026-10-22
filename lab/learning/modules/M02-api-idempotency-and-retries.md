# Module M02: APIs, idempotency and retries (hardened service)

Status for you: NOT ASSESSED.

**A. Theory.** HTTP semantics, status codes (401 vs 403), idempotency keys, bounded retries with backoff, dead letters, rate limits, readiness vs liveness.
**B. Small implementation (do alone).** Write a tiny FastAPI service with POST /orders that accepts an `Idempotency-Key` header and, for a repeated key, returns the first response without creating a second order. Write three tests: first call creates, repeat returns the same body and creates nothing, a different body with the same key is rejected.
**C. Where it appears.** `lab/nasha_lab/service/` and `lab/docs/P5-HARDENED-SERVICE.md` on `career/p5-hardened-service`; `lab/nasha_lab/ops/failure_policy.py` on `career/reliability-policies`; trial result in `lab/docs/FAILURE-POLICY.md`: an ambiguous draft (commit, then timeout) was duplicated by naive retry in 10/10 seeded runs and in 0/10 by reconcile-then-retry (re-verify from the result file before quoting).
**D. Debugging.** Make your handler store the key AFTER the side effect. Show a crash window that still produces a duplicate, then fix it with a transaction or a unique constraint.
**E. Design tradeoffs.** Where the key lives (DB vs cache), key expiry, what to do with in-flight duplicates, per-client scope.
**F. Interview defence.** Why is PUT idempotent but POST not by default? What must never be retried?
**G. Evidence.** Date / task / link / unaided or not.
