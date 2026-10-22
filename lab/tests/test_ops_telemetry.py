"""Telemetry, structured logs, registry and ops-service behaviour. SYNTHETIC / OFFLINE."""
import json
import pytest
from nasha_lab import identity as ID, tools as T
from nasha_lab.ops import runner as R, telemetry as TM, LABEL


@pytest.fixture(scope="module")
def pool(): return R.clean_pool()


def test_exec_stack_restores_tools_execute_and_samples_every_call(pool):
    orig = T.execute
    rec, ev, env = R.run_scenario(pool["heldout"][0])
    assert T.execute is orig
    assert rec["tool_calls"] == len(env.ops.stack.samples) > 3 and rec["tool_failures"] == 0
    assert all(s["ms"] >= 0 and s["attempts"] == 1 for s in env.ops.stack.samples)


def test_record_has_the_required_fields(pool):
    rec, ev, env = R.run_scenario(pool["heldout"][1], "rule-model", versions=dict(version_id="vX", planner_id="p", prompt_hash="h", tool_schema_version="ts1", corpus_version="block3"))
    for k in ("run_id", "family", "versions", "planner", "retriever", "outcome_category", "approval", "timing", "tools", "retrieval", "safety", "label"): assert k in rec
    assert rec["label"] == LABEL and rec["versions"]["version_id"] == "vX"
    p = rec["planner"]; assert p["type"] == "llm" and p["llm_calls"] >= 2 and p["prompt_tokens"] > 0 and p["completion_tokens"] > 0
    assert rec["approval"]["state"] in ("approved", "rejected", "not_required") and rec["timing"]["run_ms"] > 0 and rec["timing"]["steps"]
    assert set(rec["retrieval"]) >= {"hit", "abstain", "miss"} and rec["safety"]["approval_boundary_ok"] is True


def test_approval_states_pending_then_approved_or_rejected(pool):
    sc = pool["heldout"][2]
    env = R.make_env(sc); s = env.ops.start(env.eid, "t"); rid = s["run"]["run_id"]
    assert env.ops.record(rid)["approval"]["state"] == "pending" and env.ops.record(rid)["outcome_category"] == "PENDING"
    env.ops.resume(rid, dict(decision="reject")); r = env.ops.record(rid)
    assert r["approval"]["state"] == "rejected" and r["outcome_category"] == "REJECTED"


def test_crash_marks_run_failed_and_event_can_be_reprocessed(pool):
    sc = pool["heldout"][3]; env = R.make_env(sc, flaky_db=True); env.flaky.broken = True
    s = env.ops.start(env.eid, "t"); assert s["crashed"] and s["status"] == "FAILED"
    rid = s["run"]["run_id"]; assert env.svc.store.run(rid)["status"] == "FAILED"
    assert env.ops.record(rid)["outcome_category"] == "CRASHED"
    env.flaky.broken = False; s2 = env.ops.start(env.eid, "t2")
    assert s2["status"] != "DUPLICATE_IGNORED" and s2["awaiting_human"]


def test_without_the_ops_wrapper_a_crashed_run_blocks_reprocessing(pool):
    """Documents the finding that motivated the wrapper: the stock service leaves a crashed run RUNNING, so the event is then ignored as a duplicate."""
    sc = pool["heldout"][3]; env = R.make_env(sc, flaky_db=True); env.flaky.broken = True
    with pytest.raises(Exception): env.svc.start(env.eid, "t")
    env.flaky.broken = False; s2 = env.svc.start(env.eid, "t2")
    assert s2["status"] == "DUPLICATE_IGNORED"


def test_ops_events_land_in_the_trace_and_do_not_execute_anything(pool):
    sc = next(s for s in pool["heldout"] if s.event_family == "POLICY"); env = R.make_env(sc, session_mode=True)
    rid = env.ops.start(env.eid, "t")["run"]["run_id"]
    with pytest.raises(ID.AuthError): env.ops.resume(rid, dict(decision="approve"), session="garbage")
    kinds = [e["kind"] for e in env.svc.store.events(rid)]
    assert "ops_approval_denied" in kinds and env.ops.summary(rid)["awaiting_human"]


def test_structured_json_logs_and_otel_style_registry(pool):
    reg, log = TM.MetricsRegistry(), TM.JsonLogger()
    rec, ev, env = R.run_scenario(pool["heldout"][4], "rule-model", registry=reg, logger=log)
    TM.observe(reg, rec)
    for line in log.lines: json.dumps(line); assert line["synthetic"] is True and line["event"]
    names = {m["name"] for m in reg.snapshot()}
    assert {"nasha.agent.run.count", "nasha.agent.run.duration", "nasha.tool.call.count", "gen_ai.client.token.usage", "nasha.approval.count", "nasha.retrieval.count"} <= names
    h = next(m for m in reg.snapshot() if m["name"] == "nasha.agent.run.duration"); assert h["type"] == "histogram" and h["p50"] and h["unit"] == "ms"


def test_ops_wrapper_does_not_change_decisions(pool):
    """The wrapper observes only: the proposal equals the one from a plain AgentService run."""
    from nasha_lab import eval_planners as E, planners as PL
    sc = pool["heldout"][5]; rec, ev, env = R.run_scenario(sc)
    r = E.run_scenario(sc, E.FACTORIES["deterministic"])
    assert rec["action"] == r["action"]
