# Case study: an operations control plane for a human-supervised AI agent

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** This is a portfolio project on a synthetic enterprise simulation. There is no live system, no users, no real incidents, no SLAs and no spend. All numbers come from running the simulation; the evaluation is same-author.

## The problem

An AI agent that proposes actions for a human to approve is only half a system. The other half is knowing what it did, noticing when it is degrading, stopping a bad change, and having a written procedure when something breaks. I had the agent (a LangGraph workflow with typed tools, permission classes, signed approvals and a frozen evaluation). I built the operating layer around it, and tried hard to break it.

## What I built

* **Telemetry on real runs**: per-run and per-step latency, per-tool success and failure, retrieval hit / abstain / miss, planner type, token counts, approval state, outcome category, and version ids (planner, prompt hash, tool-schema hash, corpus hash). Metric names follow OpenTelemetry conventions; logs are structured JSON.
* **Alert rules as data**: 27 declarative rules over a failure taxonomy of 20 classes, an evaluator, and incident records with timelines. Each class has a runbook (detection, triage, containment, recovery, rollback, escalation).
* **A regression gate and a version registry**: a fixed 56-scenario suite, a frozen reference, and a rollback drill that switches versions, catches a bad candidate and restores the good one.
* **SLOs as design targets** with multi-window burn-rate alerts.
* **A static, accessible dashboard** rendered from the result files (no JavaScript, no CDN, axe-core clean at four viewports and themes).
* **Eleven injected fault types**, 20 seeded trials each, plus a clean control set.

## What I found (the useful part is the misses)

* **Control held.** In 260 clean runs the alert rules raised no alert (95% interval 0 to 1.5%). In 20 of 21 staged faults in a simulated 160-run day, an alert of the right class fired.
* **Most faults were detected, contained and recovered at 20 of 20**: model timeout, tool timeout, malformed tool result, approval expiry, database failure, schema violation. Containment means no unapproved action, no external action, no ungrounded claim, and a conservative or unchanged proposal.
* **Some things were not seen.** An index that lost its authoritative documents is invisible for one event family, where abstaining is normal (detected 13 of 20; all 7 misses were that family). Stale or superseded documents were never cited, but the system gives no sign they were involved, so no alert is possible (detected 7 of 20). A contradictory *canonical* document was cited next to the real decision in every trial, and nothing noticed the conflict. I recorded these as gaps instead of tuning the rules until the table looked better.
* **The gate is blunt.** It catches a regression that touches 40% of events every time, but only 6 of 20 when 5% of events are degraded, and a single failed ordinary scenario passes by design. I fixed that policy before measuring and kept it.
* **A real bug in the stock service.** A run that crashes stays "running", and the event is then ignored as a duplicate. I handled it in the wrapper, tested the stock behaviour, and left the core untouched.
* **Retries are dangerous without idempotency.** When a draft write commits but the response is lost, a naive retry duplicated the draft in 10 of 10 runs; reconciling before retrying duplicated none.

## Decisions I would explain in an interview

* Replay alerts over stored traces rather than claim a live pager: honest about what "time to detect" means.
* Keep the OpenTelemetry SDK out until there is a backend; keep the names compatible.
* Treat the permission and approval layers as the control, and measure containment against them rather than model quality.
* Label every threshold and target as an assumption, and report intervals and misses next to the headline numbers.

## What it is not

Not production reliability. Not a language-model evaluation (model faults use scripted stand-ins). Not load or concurrency testing, and not a real outage: faults are injected at in-process seams. The alert thresholds were checked on one development machine and may not transfer. Everything is reproducible from the repository with the commands in `OPS-CONTROL-CENTER.md`.

Evidence: `OPS-CONTROL-CENTER-EVALUATION.md` (all numbers and limits), `RELIABILITY-MATRIX.md` (every catalogued failure mapped to a test and a result), `lab/results/ops/` (raw data), `lab/ops/runbooks/` (16 runbooks).
