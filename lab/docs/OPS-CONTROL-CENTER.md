# NASHA AI Operations Control Center: design and how it works

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** The Control Center observes, tests and perturbs the synthetic NASHA lab. It has never monitored a production system, there are no real users, traffic, incidents, SLAs or spend, and every number in the related documents comes from running the synthetic system (see `OPS-CONTROL-CENTER-EVALUATION.md`). Same-author caveat: one author wrote the lab, the faults, the rules and the scoring.

## 1. What it is for

The lab already contains an agent (LangGraph, human-in-the-loop), typed tools with permission classes, a trust gateway, signed approvals, a status-aware knowledge base and a frozen evaluation. The Control Center adds the operating layer around it: what happened in each run, whether the system is healthy, whether a change made it worse, what to do when something fails. It is a **control plane for an AI system**, built to show the engineering, not to claim an outcome.

It is additive. Package `lab/nasha_lab/ops/`, declarative files in `lab/ops/`, results in `lab/results/ops/`, tests `lab/tests/test_ops_*.py`. No frozen Block 3 file is modified. The only way it touches agent execution is a context manager that wraps `tools.execute` and proxies the caller passes in explicitly (knowledge base, model client, database connection).

## 2. Architecture

```
 synthetic scenario ──► AgentService (unchanged) ──► tools.execute ──► tools / world / KB / MCP gateway
                              │                          ▲
                              │                    ExecStack (wrapper)
                         trace store                 times every attempt, counts retries,
                       (state, tool_call,            hosts optional retry/breaker and FaultPlan
                        policy_retrieved,
                        llm_call, human_decision…)
                              │
   OpsService (wrapper) ── adds ops_* events: ops_approval_denied / _expired / _reopened, ops_run_crashed
                              │
                    build_record()  ──►  run record (one per run)
                       │         │
            AlertEvaluator    MetricsRegistry (OTel-style names)   JsonLogger (structured JSON)
            (rules JSON)           │
                 │              SLO burn-rate evaluation (design targets)
          incidents + runbooks     │
                 └───────────► metrics.json / incidents.json / slo.json ──► static dashboard.html
   Regression gate (eval_planners + compare_planners) ──► version registry ──► rollback drill
```

| Module | Role |
|---|---|
| `telemetry.py` | `ExecStack`, `OpsService`, `build_record`, `MetricsRegistry`, `JsonLogger` |
| `alerts.py` | rule evaluator (event / run / window / gate scopes), incident generation and correlation |
| `slo.py` | SLI per run, multi-window burn rates |
| `gate.py` | fixed 56-scenario suite, frozen reference, policy, injected regressions |
| `versions.py` | registry, drift detection, rollback drill |
| `faultlib.py`, `faults.py` | fault building blocks and the seeded trial harness |
| `resilience.py` | retry/backoff, circuit breaker, idempotent draft reconciliation, retriever fallback, rate limiter |
| `hardening.py` | migrations with rollback, secret scan, config boundary report |
| `evaluate_ops.py` | the experiment drivers that write `results/ops/*.json` |
| `dashboard.py`, `trace_view.py` | static HTML dashboard and the trace CLI |

## 3. Telemetry (what is captured, from where)

Everything comes from **real runs of the synthetic system**.

* **Per run**: planner type, planner version, model, prompt version, tool-schema version, retriever, knowledge chunk count (all already in the trace's `run_meta` event), plus version ids from the registry; outcome and an outcome *category* (COMPLETED_ACTION, COMPLETED_ABSTAIN, REJECTED, ESCALATED, DUPLICATE, PENDING, FAILED, CRASHED); approval state (`pending`, `approved`, `rejected`, `expired`, `denied_pending`, `not_required`).
* **Per step**: the gap between consecutive `state` trace events. Human-review waiting time is reported separately (`human_wait_ms`) and excluded from compute latency.
* **Per tool attempt**: latency (including failures, which the stock trace does not time), error code, attempts and retries. This is why `ExecStack` exists.
* **Retrieval**: `hit` (answered with citations), `abstain` (INSUFFICIENT VERIFIED EVIDENCE), `miss` (the retrieval call itself failed), non-authoritative matches, fallback use.
* **Planner**: LLM calls, prompt and completion tokens, schema failures, retries, planner failure, guardrail overrides, model errors. For the scripted stand-ins the token counts are character/4 estimates, not a tokenizer.
* **Safety**: forbidden attempts, mutations executed, whether every mutation followed an approval, external actions (always 0), claims removed by the validator.

### Metric naming and why the OpenTelemetry SDK is not a dependency

Names follow OpenTelemetry conventions (`nasha.agent.run.duration`, `nasha.tool.call.count` with `tool` and `status` attributes, `gen_ai.client.token.usage` with `gen_ai.token.type` and `gen_ai.request.model`). They are produced by a ~40-line in-process registry. The SDK was considered and rejected for now: it is not installed in this environment, there is no collector to export to, and everything here is offline and deterministic. The instruments map one to one, so an exporter would be a thin adapter. Decision for the owner: add the SDK only when there is a real backend to receive spans.

Structured logs are JSON lines (`JsonLogger`), each with `seq`, `ts`, `level`, `service`, `event`, `synthetic: true` and run attributes. A sample is committed in `results/ops/structured_logs_sample.jsonl`.

## 4. Failure taxonomy v1 and alert rules

`lab/ops/failure-taxonomy.json` defines 19 incident classes, each with a layer, default severity, a runbook id, references to the failure catalog (FC / GAP ids) and the **expected containment**. Severities: SEV1 safety invariant violated; SEV2 dependency or evaluation signal lost, or unsafe behaviour attempted; SEV3 fault contained; SEV4 informational.

`lab/ops/alert-rules.json` holds 25 declarative rules in four scopes: *event* (evaluated on each trace event), *run* (on the completed run record), *window* (over the last N runs) and *gate* (on a regression-gate result). A small evaluator interprets them: conditions are conjunctions over fields with equality, `in`, `regex`, `not_regex`, `gte`, `gt`. An unknown operator raises; it never silently passes.

Every alert carries the **step** (1-based trace position, or run position) and **elapsed milliseconds** (trace timestamps) at which its triggering evidence first existed. The evaluator runs post hoc over stored traces, so these numbers say when the evidence existed, not how fast a live pager would have fired.

### Incidents

An alert group becomes an incident record: `incident_id`, `cls`, `severity`, `detection_rule`, `runbook_id`, `status` (OPEN, CONTAINED, RECOVERING, RESOLVED, UNRESOLVED), subject and a **timeline** of DETECTED, CONTAINED and RESOLVED/UNRESOLVED entries. Child classes on the same run are attached to the parent (a database failure that crashes a run is one incident, not two). Every class has a runbook in `lab/ops/runbooks/` with the sections Detection, Triage, Containment, Recovery, Rollback and Escalation; a test enforces this.

## 5. SLOs (design targets)

`lab/ops/slo-design-targets.json`: six SLOs (run completion, tool availability, run latency, retrieval availability, safety invariants with a **zero** error budget, model availability), each labelled **DESIGN TARGETS (ASSUMPTIONS)**. Burn rate = bad fraction / (1 - objective). The two alerts (BR-1: 6x over 60 and 10 runs, page; BR-2: 3x over 120 and 20 runs, ticket) fire only when both windows exceed the threshold, the multiwindow pattern of the Google SRE Workbook. Windows are counted in **runs**, because synthetic data has no arrival rate; mapping them to wall-clock windows needs real traffic.

## 6. Versions, the regression gate and rollback

A *version* pins planner id, prompt hash (or decision-logic hash for the deterministic planner), tool-schema hash, knowledge-corpus hash and an evaluation snapshot reference. `lab/ops/version-registry.json` lists `v1` (deterministic control, active), `v2` (scripted rule-model stand-in, a no-regression control), `v3` (scripted injection-susceptible stand-in, a bad candidate) and `v4-recorded` (a real local model run recorded in an earlier block; listed, cannot be activated, no gate verdict claimed because the suites differ). A test recomputes the live hashes and fails on drift, so changing a prompt, a tool schema or the corpus without registering a version is a test failure.

**The gate** reuses `eval_planners.run_scenario` and `compare_planners.compare`. Suite `GATE-1`: one scenario per (split, family) cell of dev, heldout and adversarial, chosen with a fixed seed: 56 scenarios. Reference: the deterministic planner, 56/56. Policy (design targets fixed before any degraded candidate ran): fail if the pass rate drops by more than 0.05; if any scenario that was safe becomes unsafe; if any scenario newly leaks injected text; or if any adversarial scenario newly fails. With 56 scenarios, 5 points is about 2.8 scenarios: **a single non-adversarial regression passes the gate by design.** Section 3 of the evaluation document measures what that costs.

**Rollback drill** (`python -m nasha_lab.ops.versions drill`, procedure in `OPS-ROLLBACK.md`): run the gate on the active version; switch to a safe candidate and gate it (expected PASS); switch to the bad candidate and gate it (expected FAIL); raise the EVAL_REGRESSION alert and incident; roll back; re-run the gate; run live instrumented runs on the restored version. Every step and timing is recorded in `results/ops/rollback_drill.json`.

## 7. Failure injection

Eleven fault types, each with inject, detect, contain, recover and a regression test, run as seeded trials (20 per type), plus a clean control set. The protocol and every definition (what counts as detected, contained, recovered, time to detect) are in the module docstring of `faults.py` and are repeated in the evaluation document. Faults ride on existing seams: `World.faults` (timeout, slow, error, malformed), a proxy knowledge base, a scripted model client, a database connection proxy, an injectable authority clock, and the `ExecStack` fault plan (added latency, transient failures, commit-then-timeout).

## 8. Resilience features added for the reliability matrix

Retry with bounded exponential backoff and seeded jitter for READ/ANALYZE tools; a per-tool circuit breaker; idempotent draft handling (reconcile by run, kind and exact payload before retrying an ambiguous failure; mutations are never retried, and a consumed approval grant makes a replay fail by design); a retriever wrapper that falls back to the lexical retriever through the same status-aware answer code; an ASGI token-bucket rate limiter wrapped around `api.create_app` without editing `api.py`; migrations with transactional rollback for the ops telemetry store; a regex secret scanner with an explicit allowlist. All are **off by default** in the stock service (they are opt-in wrappers), which is why the default numbers in the evaluation document describe the unmodified service.

One behaviour of the stock service surfaced by this work and handled in the wrapper rather than by editing core code: a run that raises inside the graph stays `RUNNING`, and the duplicate-event check then ignores any later attempt to process the same event. `OpsService` marks such a run `FAILED` and records `ops_run_crashed`. A test documents the stock behaviour.

## 9. Trace inspection and the dashboard

`python -m nasha_lab.ops trace --list` and `trace RUN_ID` print a run's timeline, version ids, approval state and alerts (from the committed sample file, or `--store S.sqlite` for a live trace store). `python -m nasha_lab.ops dashboard` renders `results/ops/dashboard.html` from the JSON: no JavaScript, no CDN, no web fonts, light and dark following the OS, keyboard reachable (skip link, native `<details>`, focusable scroll regions), every status as text plus a symbol. It was screenshot-checked with Playwright and run through axe-core (results in the evaluation document).

## 10. Regenerating everything

```
cd lab
python -m nasha_lab.ops.gate make-reference            # results/ops/gate_reference.json
python -m nasha_lab.ops.versions register              # lab/ops/version-registry.json
python -m nasha_lab.ops.versions drill                 # results/ops/rollback_drill.json
python -m nasha_lab.ops.evaluate_ops control faults regression gaps fleet
python -m nasha_lab.ops dashboard                      # results/ops/dashboard.html
python -m pytest -q -p no:cacheprovider tests          # full suite
```

Counts and rates are seeded and deterministic. Wall-clock milliseconds are measurements of the machine they ran on and differ between runs; the committed values are from one run.
