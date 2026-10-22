# RB-MODEL-UNAVAILABLE: Model unavailable or planner failure

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: MODEL_UNAVAILABLE, PLANNER_FAILURE. Alert rules: AR-06, AR-19.

## Detection
Alert AR-06 (an `llm_call` trace event with error MODEL_UNAVAILABLE) or AR-19 (proposal carries planner_failure=true). Confirm in the trace: `python -m nasha_lab.ops trace RUN_ID` shows `llm_call error=MODEL_UNAVAILABLE` and a proposal of ESCALATE_INSUFFICIENT_EVIDENCE.

## Triage
- Is it one run or all runs? Count AR-06 over the last 20 runs (dashboard: incidents, SLO-6).
- Which planner/model/version? Read `run_meta` in the trace and the version id in the run record.
- Is the local model runtime reachable at NASHA_LLM_ENDPOINT? (Ollama `/api/show`.) Timeouts and refused connections both surface as MODEL_UNAVAILABLE.

## Containment
None needed for safety: the planner returns ESCALATE_INSUFFICIENT_EVIDENCE with no mutating action, so nothing can execute. A reviewer must NOT approve an escalation proposal as if it were a recommendation. If the outage is wide, pause intake of new events.

## Recovery
Restore the model runtime, then for each affected pending run use the reviewer decision `request_more_evidence`; the planner is called again and the proposal should equal what a healthy run produces. Verified in fault injection (model_timeout).

## Rollback
If the outage persists, switch the active planner version to the deterministic control planner (version registry `v1`) with `Registry.activate`; re-run the regression gate afterwards.

## Escalation
SEV2. Page the owner of the model runtime. If more than 1% of LLM-planner runs fail over the burn-rate window, SLO-6 burn alerts escalate automatically.
