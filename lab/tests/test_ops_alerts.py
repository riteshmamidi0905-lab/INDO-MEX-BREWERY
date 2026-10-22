"""Alert rules, taxonomy, runbooks, incidents, SLO burn rates. SYNTHETIC / OFFLINE."""
import os
import pytest
from nasha_lab.ops import alerts as A, slo as SLO
from nasha_lab.ops.util import OPS_DIR

REQUIRED_SECTIONS = ["Detection", "Triage", "Containment", "Recovery", "Rollback", "Escalation"]


def test_every_rule_class_exists_and_every_class_has_a_runbook_with_all_sections():
    ev = A.AlertEvaluator(); tax = A.load_taxonomy()
    assert {r["class"] for r in ev.cfg["rules"]} <= set(ev.classes)
    for c in tax["classes"]:
        p = os.path.join(OPS_DIR, "runbooks", c["runbook"] + ".md"); assert os.path.exists(p), c["runbook"]
        txt = open(p).read()
        for s in REQUIRED_SECTIONS: assert f"## {s}" in txt, (c["runbook"], s)
        assert "SYNTHETIC" in txt


def test_every_class_is_reachable_by_some_rule_or_burn_alert():
    ev = A.AlertEvaluator(); covered = {r["class"] for r in ev.cfg["rules"]} | {"SLO_BURN"}
    assert set(ev.classes) <= covered, set(ev.classes) - covered


def evt(ts, kind, **kw): return dict(seq=1, ts=ts, kind=kind, **kw)


def test_event_rules_fire_with_step_and_elapsed_time_and_dedupe():
    ev = A.AlertEvaluator()
    events = [evt(10.0, "state", node="X"), evt(10.01, "tool_error", tool="query_inventory", code="TIMEOUT", message="x"), evt(10.03, "tool_error", tool="get_lineage", code="TIMEOUT", message="y")]
    al = ev.scan_events(events, "r1")
    assert [a["rule_id"] for a in al] == ["AR-01"] and al[0]["step"] == 2 and al[0]["count"] == 2 and 9 < al[0]["elapsed_ms"] < 11


def test_db_error_is_distinguished_from_generic_upstream_failure():
    ev = A.AlertEvaluator()
    db = ev.scan_events([evt(1, "tool_error", tool="t", code="UPSTREAM_FAILURE", message="OperationalError: database is locked")], "r")
    gen = ev.scan_events([evt(1, "tool_error", tool="t", code="UPSTREAM_FAILURE", message="RuntimeError: injected upstream failure")], "r")
    assert [a["cls"] for a in db] == ["DATABASE_UNAVAILABLE"] and [a["cls"] for a in gen] == ["TOOL_UPSTREAM_FAILURE"]


def test_window_rule_needs_min_runs_and_threshold():
    ev = A.AlertEvaluator()
    mk = lambda ms: dict(timing=dict(run_ms=ms), tool_calls=10, tool_failures=0)
    recs = [mk(100)] * 4 + [mk(900)]
    assert ev.scan_window(recs[:4], 3) == []
    assert ev.scan_window(recs, 4)[0]["cls"] == "LATENCY_DEGRADATION"
    assert ev.scan_window([mk(100)] * 5, 4) == []


def test_incident_record_has_required_fields_and_correlates_children():
    ev = A.AlertEvaluator()
    events = [evt(1, "ops_run_crashed", error="OperationalError", detail="d"), evt(1.001, "tool_error", tool="t", code="UPSTREAM_FAILURE", message="x")]
    incs = A.make_incidents(ev.scan_events(events, "run-1"))
    assert len(incs) == 1, "RUN_CRASH is a child of DATABASE_UNAVAILABLE and must not open its own incident"
    i = incs[0]
    for k in ("incident_id", "cls", "severity", "detection_rule", "runbook_id", "status", "timeline"): assert k in i
    assert i["cls"] == "DATABASE_UNAVAILABLE" and i["status"] == "OPEN" and i["timeline"][0]["event"] == "DETECTED"
    A.advance(i, "RESOLVED", "x"); assert i["status"] == "RESOLVED"


def test_unknown_operator_is_an_error_not_a_silent_pass():
    with pytest.raises(ValueError): A._match(1, {"between": [0, 2]})


def mkrec(**kw):
    base = dict(outcome_category="COMPLETED_ACTION", tool_calls=10, tools={}, timing=dict(run_ms=100), retrieval=dict(hit=2, abstain=0, miss=0), safety=dict(approval_boundary_ok=True, external_actions=0), planner=dict(llm_calls=0, llm_errors=0, planner_failure=False))
    base.update(kw); return base


def test_burn_rate_math_and_multiwindow_behaviour():
    assert SLO.burn(99, 100, 0.99) == pytest.approx(1.0) and SLO.burn(90, 100, 0.99) == pytest.approx(10.0) and SLO.burn(100, 100, 1.0) == 0.0 and SLO.burn(99, 100, 1.0) == float("inf")
    good = [mkrec() for _ in range(70)]
    assert SLO.evaluate(good)["burn_alerts"] == []
    burst = good[:60] + [mkrec(outcome_category="CRASHED") for _ in range(10)]          # 10 crashes at the end: both the 60-run and the 10-run window burn fast
    res = SLO.evaluate(burst); assert any(b["slo"] == "SLO-1" and b["burn_alert"] == "BR-1" for b in res["burn_alerts"])
    blip = good[:69] + [mkrec(outcome_category="CRASHED")]                                # one crash is not enough to page
    assert not [b for b in SLO.evaluate(blip)["burn_alerts"] if b["slo"] == "SLO-1" and b["severity"] == "SEV2"]


def test_zero_budget_safety_slo_breaches_on_one_violation():
    recs = [mkrec() for _ in range(30)] + [mkrec(safety=dict(approval_boundary_ok=False, external_actions=0))]
    s = next(x for x in SLO.evaluate(recs)["slos"] if x["id"] == "SLO-5"); assert s["status"] == "BREACHED"


def test_slo_file_is_labelled_as_design_targets():
    cfg = SLO.load_slos(); assert "DESIGN TARGETS" in cfg["label"] and "NOT contractual SLAs" in cfg["label"]
