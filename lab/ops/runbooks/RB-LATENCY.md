# RB-LATENCY: Latency degradation

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: LATENCY_DEGRADATION. Alert rules: AR-16, AR-23.

## Detection
AR-16: a single successful tool call took 250 ms or more (design target). AR-23: p95 run compute time above 600 ms over the last 5 runs (design target; SLO-3).

## Triage
- All tools slow (platform) or one tool (dependency)? Dashboard: per-tool p95.
- Cold start: the first run after process start builds the knowledge base (about 2 s) and is excluded from calibration; do not page on it.

## Containment
Timeouts bound every call, so slow-but-working dependencies degrade latency but not correctness.

## Recovery
Remove the cause; the window alert clears after about 5 healthy runs (measured).

## Rollback
Not version-related unless a version added tool calls.

## Escalation
SEV3; SEV2 if SLO-3 burns on both windows.
