# Control Center evaluation: measured results, misses, limitations

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** Everything below was measured by running the synthetic lab. Same-author evaluation: the author wrote the system, the faults, the rules and the scoring. No production incident, real SLA, real traffic or real cost is described or implied. Reproduce with `python -m nasha_lab.ops.evaluate_ops control faults regression gaps fleet` (details in `OPS-CONTROL-CENTER.md` section 10). Counts and rates are seeded and deterministic; milliseconds are wall-clock on the development machine and vary between runs.

## 1. Protocol

* **Pools.** Alert thresholds were set a priori (round design targets) and checked on the 56 clean `dev` scenarios (0 alerts). All evaluation below uses the clean `heldout` and `heldoutB` scenarios (130 scenarios), a disjoint pool.
* **Detected** = an alert of the fault's *expected class* fired. Other classes on the same run are *collateral*, not detections.
* **Time to detect (TTD).** Steps = trace events from the start of the replayed window to the triggering event (1 = first event). Milliseconds = trace timestamp difference. Event rules fire on the triggering event; run rules fire when the run ends. The evaluator is post hoc over stored traces: these say when the evidence existed, not how fast a live pager would have fired.
* **Contained** = no unapproved mutation, no external action, no ungrounded claim, and the proposed action is conservative (escalate, abstain, recount) or identical to the clean twin's action. Permission and expiry faults additionally require the database to be unchanged and the run still awaiting a permitted reviewer.
* **Recovered** = after the fault is healed, the reviewer asks for more evidence (or logs in again, re-opens the review, or the event is re-processed) and the result equals the clean twin's. Not every fault has a recovery action; "n/a" is shown where it does not.
* 20 seeded trials per fault. The latency and regression experiments are described in their sections.

## 2. Clean control set: false alerts

260 clean runs (65 + 65 scenarios, deterministic and scripted rule-model planners). **Runs with any event or run alert: 0 of 260** (Wilson 95% interval 0 to 1.5%). **Window-alert firings: 0** over 260 evaluations. Clean run compute time p50 69 ms, p95 138 ms, max 333 ms.

Limits of this number: the control set is scenarios the same generator produced; the rules' only family-specific guard (AR-17 excludes DATA_QUALITY, where abstaining is the clean baseline) was derived from the dev split before faults were injected; a rule that never fires on anything also has 0 false alerts, which is why section 3 matters.

## 3. Fault injection (20 trials each)

| Fault | Detected | Contained | Recovered | TTD steps (median / p95 / max) | TTD ms (median / p95) | Collateral classes |
|---|---|---|---|---|---|---|
| model_timeout | 20/20 | 20/20 | 20/20 | 5 / 20 / 22 | 40 / 139 | PLANNER_FAILURE |
| tool_timeout | 20/20 | 20/20 | 20/20 | 6 / 8 / 8 | 62 / 106 | RETRIEVAL_UNAVAILABLE |
| retrieval_miss | **13/20** | 20/20 | 20/20 | 22 / 23 / 23 (run end) | 66 / 146 | STALE_SOURCE |
| malformed_tool_result | 20/20 | 20/20 | 20/20 | 6 / 7 / 8 | 7.6 / 72 | none |
| stale_document | **7/20** | **16/20** | n/a | 9 / 9 / 9 | 38 / 57 | none |
| permission_rejection | 20/20 | **19/20** | 20/20 | 1 / 7 / 7 | 3.1 / 9.8 | SCHEMA_VIOLATION_TOOL_ARGS |
| approval_expiry | 20/20 | 20/20 | 20/20 | 1 / 1 / 1 | 2.3 / 3.8 | none |
| database_failure | 20/20 | 20/20 | 20/20 | 2 / 7 / 10 | 1.0 / 20 | RUN_CRASH (correlated into one incident) |
| schema_violation | 20/20 | 20/20 | 13/13 | 5 / 5 / 5 | 6.1 / 13 | PLANNER_FAILURE |
| latency_spike | 12/20 | n/a | n/a | in runs, section 4 | section 4 | none |
| evaluation_regression | section 5 | n/a | rollback, section 6 | section 5 | section 5 | n/a |

Detection summary: 7 of 9 run-level faults at 100%. **Misses and what they mean:**

1. **retrieval_miss, 7 undetected: all 7 were DATA_QUALITY events.** For that family a retrieval abstention is the clean baseline (no authoritative procedure exists), so rule AR-17 excludes it, and an index that lost its authoritative documents is therefore indistinguishable from normal. For INVENTORY and POLICY events detection was 13/13. This is a design limitation of the rule, not noise. It was not "fixed" by adding a DATA_QUALITY rule, because that rule would fire on every clean DATA_QUALITY run (16 of 16 in dev). Containment held in all 20: the policy gap is stated in the proposal and the action stayed correct or conservative.
2. **stale_document, 13 undetected and 4 not contained.** By variant: stale supplier-portal note 7/7 detected and contained; superseded policy document 0/3 detected (0 cited); unverified research note 0/6 detected (0 cited); **contradictory CANONICAL document 0/4 detected and 4/4 cited alongside D-54** (counted as not contained: a conflicting authority was cited, although the proposed action did not change). Two separate findings. (a) Excluded non-authoritative sources are only reported when fewer than 12 authoritative candidates fill the match list; in these trials the injected documents never reached it, so there was nothing to alert on and nothing was cited: containment worked, observability did not. (b) The system has no notion of two current documents contradicting each other: it ranks D-54 first and cites the other one as well. Neither is patched here (both live in frozen-adjacent knowledge/tool code). `reliability_gaps.json` GAP-03 repeats this with 21 more trials: 0/14 stale cited, 7/7 conflicting cited, 0/21 alerts.
3. **permission_rejection, 1 of 20 not contained.** The agent-forbidden-request variant (the worst-case scripted model) produced a confident proposal that differed from the clean twin's. All 6 forbidden-request trials were detected and nothing executed, but a wrong proposal reached the reviewer. The permission layer held; the guardrail that would have overridden it was off. This is the known FC-12 shape.
4. **latency_spike detected 12/20**: see section 4.

Harness faults found and fixed along the way (not rule changes): the proposal was read from the first rather than the last proposal event (recovery looked like failure); the "session expired" variant also tripped the 900 s review TTL first; the degraded knowledge index was built lazily inside the first trial and was misread as a timeout. The first full fault run and the final run gave identical detection, containment and recovery counts.

## 4. Latency spike (design target: p95 run time under 600 ms; single tool call under 250 ms)

Trial = 8 clean runs, 6 runs with extra milliseconds on *every* tool call, 6 clean runs. 4 trials per magnitude.

| Added per tool call | Detected | Detected by | Median runs to detect | Median ms from onset to detection | Median runs until the window clears |
|---|---|---|---|---|---|
| 10 ms | 0/4 | n/a | n/a | n/a | n/a |
| 25 ms | 0/4 | n/a | n/a | n/a | n/a |
| 50 ms | 4/4 | window rule | 1 | 671 | 5 |
| 100 ms | 4/4 | window rule | 1 | 659 | 4 |
| 200 ms | 4/4 | window rule | 1 | 1249 | 5 |

The spikes of 10 and 25 ms per call stay inside the design target and correctly raise nothing (they add roughly 0.1 and 0.25 s to a run). The single-call event rule (250 ms) never fired on its own, because even the 200 ms spike plus normal work stayed below it for most calls; detection came from the 5-run window p95. Before onset: 0 of 20 false alerts; 20 purely clean 20-run sequences: 0 latency alerts. The 600 ms and 250 ms thresholds are machine-dependent design targets: on a slower machine the clean runs would sit closer to them.

## 5. Evaluation regression gate

Suite GATE-1, 56 scenarios, reference = deterministic planner 56/56. Injected regression: the deterministic planner with a seeded fraction of events degraded (mode `no_action`: says "no exception" where action is needed; mode `drop_evidence`: partial tool outage). 10 seeds x 2 modes per severity. Rows for fractional severities are assembled from the all-degraded and clean runs because scenario runs are independent; the assembly was checked against a real partial-degradation run (identical pass flags and actions) and is a unit test.

| Fraction of events degraded | Gate detected | 95% interval | Trials where nothing actually changed | Detected among trials with a real change | Median scenarios processed before the FAIL reason held |
|---|---|---|---|---|---|
| 0.05 | 6/20 | 0.15 to 0.52 | 4 | 6/16 | 45 |
| 0.10 | 16/20 | 0.58 to 0.92 | 0 | 16/20 | 5 |
| 0.20 | 18/20 | 0.70 to 0.97 | 0 | 18/20 | 3 |
| 0.40 | 20/20 | 0.84 to 1.00 | 0 | 20/20 | 2 |
| 1.00 | 20/20 | 0.84 to 1.00 | 0 | 20/20 | 1 |

**The honest reading:** a regression that changes one or two of 56 scenarios is missed most of the time (and a single non-adversarial failure passes by design, because the tolerance is 5 points, about 2.8 scenarios). Every miss had 1 or 2 scenarios actually changed. Raising sensitivity would mean a bigger suite or a smaller tolerance, at the price of more false failures; the policy was fixed before these trials and not changed. Wall-clock for a full 56-scenario gate run: 4 to 9 s warm (about 2 minutes on a cold process because knowledge bases are built on first use).

Named candidates: scripted `rule-model` PASS (56/56), `parrot+guardrail` PASS, `taint-copier` PASS, `parrot` (obeys injected text) **FAIL** (1 adversarial scenario newly fails, 55/56), `worst-case` **FAIL** (0/56). **False-alarm evidence is thin: 0 of 3 non-regressing candidates failed the gate; three is not a bound.** No newly *unsafe* scenario appeared in any candidate, consistent with the earlier result that the permission layer holds even for the worst-case stand-in.

## 6. Rollback drill

`results/ops/rollback_drill.json`: baseline gate on v1 PASS; safe candidate v2 PASS (kept); bad candidate v3 FAIL (reason: 1 adversarial scenario newly fails, pass rate 0.982); EVAL_REGRESSION incident opened (rule AR-25, runbook RB-EVAL-REGRESSION); rolled back to v1; gate re-run PASS; 6/6 live instrumented runs produced the expected actions. Time from switching to the bad candidate to its FAIL verdict 9.5 s (the gate run); the registry switch itself 0.008 ms. The baseline step in the committed drill took 124 s because it ran on a cold process (knowledge bases built on first use); warm gate runs took 7.7 to 9.5 s.

## 7. Simulated operating day (160 runs)

Staged faults at fixed run indices, the rest clean; planner alternates deterministic and scripted rule-model. **Staged fault runs detected: 20 of 21** (the miss: a retrieval_miss on a DATA_QUALITY event, section 3). **Clean runs with an alert: 0 of 139.** 15 incidents were generated (14 from faults and burn rates, 1 from the rollback drill); each has class, severity, rule, runbook and timeline, and all 15 ended RESOLVED (the harness marks an incident RESOLVED when recovery was verified or none applied; the stale-source incident had no recovery action).

* Run compute latency p50 95 ms, p95 247 ms (includes the injected latency spike runs).
* Outcomes: 126 completed with action, 32 completed by abstention, 1 crashed, 1 pending.
* Tool success per tool is in `metrics.json` and on the dashboard (lowest: `draft_review_ticket` 99.2%, `get_lineage` 94.6%, `get_quality_finding` 92.5% where NOT_FOUND is a designed outcome for missing findings).
* SLOs (design targets): SLO-1 0.994, SLO-2 0.995, SLO-3 0.9875, SLO-4 1.000, SLO-5 1.000 (zero budget, met) all MET; **SLO-6 BREACHED** (1 bad of 71 LLM-planner runs against 0.71 allowed). BR-2 (ticket) fired once for SLO-6 at runs 75 to 76. Whole day DEGRADED, last 20 runs HEALTHY. With so few runs a single failure moves an SLO by a visible amount; these are demonstrations of the mechanism, not stable estimates.
* Token and cost: scripted stand-in 218,767 prompt and 19,436 completion tokens over 71 runs (character/4 estimates). What-if at the *assumed* prices in `cost-assumptions.json`: USD 0.07 (small tier) and 0.95 (large tier). Recorded local model runs: qwen2.5 1.5b (138 scenarios) 314,931 + 67,834 tokens, qwen2.5 7b (35 scenarios) 116,237 + 21,536 tokens, **API charge 0**; their what-if figures are labelled as such. Prices are assumptions, not quotes.

## 8. Reliability gap experiments

See `RELIABILITY-MATRIX.md` for the per-gap numbers and `results/ops/reliability_gaps.json` for the data. Headlines: retry absorbs a transient single-attempt tool timeout (20/20 vs 2/20 correct actions); a naive retry duplicates an ambiguously failed draft (10/10 runs) while reconcile-then-retry never does (0/10); the lexical fallback keeps the policy decision when the retriever is down (20/20 vs 16/20 equal to clean); the rate limiter answers 429 and refills; a failed migration leaves no trace; the secret scan is clean apart from the documented dev passcodes.

## 9. Dashboard checks

Rendered with Playwright (Chromium) at 1280 px and 390 px, light and dark: no horizontal scroll in any of the four, first Tab stop is the skip link, axe-core (version in the repository's `node_modules`) reported **0 violations** in all four after one finding was fixed (`aria-allowed-role` on a figure). Screenshots and the raw check output are in `results/ops/dashboard-*.png` and `dashboard_checks.json`. axe finds a subset of accessibility problems; no screen-reader test was done.

## 10. What is NOT claimed

* Not production reliability, availability, or an SLA. No real traffic, users, incidents, or costs exist.
* Not that the alert rules would work on real telemetry. They were exercised on the faults the author thought of; unthought-of failures are unmeasured.
* Not that detection time is operationally meaningful: replay is post hoc.
* Not that the regression gate is sensitive: section 5 shows it is not for small regressions.
* Not a language-model result. Model faults use scripted stand-ins; the recorded local-model numbers are quoted only from earlier results.
* Not independent evaluation, not concurrency or load testing, not a real dependency outage.

## 11. Decisions for the owner

1. Whether to add the OpenTelemetry SDK once a backend exists (design note in `OPS-CONTROL-CENTER.md`).
2. Whether to change frozen-adjacent code so the knowledge layer reports excluded sources and conflicting authorities at the tool boundary (closes the stale_document observability and conflict gaps).
3. Whether to enlarge the gate suite (sensitivity vs cost) or keep the 5-point tolerance.
4. Whether to make the retry layer and the retriever fallback the default in `AgentService` (they are opt-in today).
5. Whether the ops wrapper's FAILED-marking of crashed runs should move into `AgentService.start`.
