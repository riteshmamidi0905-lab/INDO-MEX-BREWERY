# Knowledge authority rules v2

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** Code: `nasha_lab/knowledge_authority.py` (a wrapper; `knowledge.py` and `tools.py` are unchanged). Trials: `nasha_lab/ops/authority_trials.py` -> `results/ops/authority_trials.json`. Tests: `tests/test_knowledge_authority.py`.

## Why

The P1/P2 study (GAP-03, `stale_document` fault) found two things. (1) Superseded and unverified sources never reached the match list, because the knowledge layer ranks authoritative chunks first and truncates, so no alert was possible (0/21 alerted). (2) A contradictory CANONICAL document was cited alongside D-54 in 7/7 trials and nothing noticed the conflict (not contained). Owner decision: fix both, without editing frozen files.

## What v2 does

`AuthorityKB(kb, "v1")` is a pass-through (the existing behaviour, byte-identical). `AuthorityKB(kb, "v2")` wraps the same `ask`:

* **(a) Excluded sources surfaced.** A wide candidate scan (200) lists every relevant non-authoritative source (cover >= 0.20) in `non_authoritative_matches` as `kind="excluded_source"`.
* **(b) Status preserved**: document id, path, effective status, verification status, registry class, authority rank, tier (`AUTHORITATIVE` / `CAVEATED` / `EXCLUDED`), `superseded_by`, cover.
* **(c) Conflict detection**, by explicit rules, between sources whose cover of the question is >= 0.35 (>= 0.20 for excluded ones):
  * **R1 polarity**: one sentence PERMITs and the other PROHIBITs, in different documents, sharing >= 2 question terms. Polarity is regular-expression based (`permitted/allowed/approved...` vs `not allowed/prohibited/beef-free/no beef/do not serve...`). A sentence matching both after stripping prohibitions is MIXED and ignored.
  * **R2 numeric (advisory only)**: different quantity sets (currency, percent, number + unit) in sentences sharing >= 3 question terms. Never blocks; high false-positive heuristic.
* **(d) Abstain / escalate.** Resolution is by tier only. Authoritative over caveated over excluded: such a conflict is *resolved by the existing status rule*, the answer is unchanged, and the conflict is recorded (types `SUPERSEDED_CONTRADICTS_CURRENT`, `EXCLUDED_CONTRADICTS_CURRENT`, `LOWER_AUTHORITY_CONTRADICTS_HIGHER`). Two sources of the same usable tier (two authoritative, or two caveated) cannot be resolved by status, so the answer is `INSUFFICIENT VERIFIED EVIDENCE` with reason `AUTHORITY_CONFLICT: A vs B ...`, **no citation**, both sources listed, `authority_escalation=True`. The agent then proposes the abstain/escalate action. Nothing is silently picked.
* **(e) Telemetry.** Conflicts ride in `non_authoritative_matches` (the one list that survives `PolicyOut`). The ops layer counts `retrieval.authority_conflicts` (blocking) and `retrieval.excluded_contradictions`. New alert **AR-26** (class `AUTHORITY_CONFLICT`, SEV3, runbook `RB-AUTHORITY-CONFLICT`) and **AR-27** (class `STALE_SOURCE`, SEV4, an excluded source contradicts the current answer). AR-18 is unchanged.

## Measured (seeded; `results/ops/authority_trials.json`)

stale_document fault trials (same 20 seeds as the committed fault study, plus 7 per variant for the GAP-03 set):

| | v1 | v2 |
|---|---|---|
| 20 trials: detected | 7 | 20 |
| 20 trials: contained (no stale/contradicting source cited, safe action) | 16 | 20 |
| 20 trials: stale or contradictory source cited | 4 | 0 |
| contradictory CANONICAL, GAP-03 set (7): cited alongside D-54 / contained | 7 / 0 | 0 / 7 (7/7 abstain, AR-26 7/7) |
| superseded doc (7): detected by the discriminating rule (AR-27) | 0 | 7 |
| unverified note (7): detected by AR-27 | 0 | 7 |

Both v1 detected counts for the portal variant (7/7) come from the trust gateway, not from the knowledge layer, and are unchanged.

**Costs and failures, not tuned away**

* **First run (v2.0) failed on clean data.** On the 130 clean control runs AR-26 fired 58 times and policy abstentions rose from 30 to 88; on the 55 golden questions 12 had a blocking conflict (11 from R2 numeric, 1 from R1). Causes: R2 compared list enumerators and sprint numbers between D-81 and D-82, and R1 read "Plain statement allowed ... We do not serve beef or pork" as a permission. Revision v2.1: R2 became advisory and quantity-only; "do not serve/use/..." became a prohibition. Later a regex bug ("not allowed" counted as permit and prohibit, hence ignored) was fixed. The revision used the same fixed questions that the control uses, so the clean-control numbers below are **no longer held out**; the golden questions are split dev/test (38/17) and both are 0.
* **v2.1 on clean data**: 0 AR-26, 0 AR-27, 0 action changes, abstentions unchanged (30 and 30) over 130 control runs; 0 blocking conflicts on 55 golden questions (dev 0/38, test 0/17).
* **AR-18 became noise.** Surfacing relevant excluded sources means AR-18 ("a non-authoritative source matched") now fires in 100 of 130 clean runs (it fired in 0 under v1, because the list was truncated). It is kept unchanged, and the discriminating signals are AR-26/AR-27 (0 false alerts on the control).
* **Latency**: `get_current_policy` p50 11.6 ms -> 20.1 ms, p95 23.6 -> 42.8 ms (warm, this machine; wall clock). Sentence analysis is cached per chunk.

## Limits

* Polarity is regex over English sentences; it will miss contradictions phrased without these markers and misread some sentences (those it cannot parse are MIXED/None and ignored). Recall was measured only on three injected documents of one kind (policy contradictions about beef/pork/derivatives), not on a general contradiction benchmark.
* A conflict needs >= 2 shared question terms, so a contradiction on a different subject than the question is not examined.
* Two authoritative documents that disagree because one is simply newer are escalated, not resolved: only explicit supersession metadata resolves, by design.
* v2 is opt-in (`AuthorityKB`, `make_env(authority_rules="v2")`); the stock service still runs v1.
* Metamorphic tests cover the three injected documents plus a few phrasings, not all possible documents.
