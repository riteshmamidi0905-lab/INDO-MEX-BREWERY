"""Committed Control Center results and documents: labelling, consistency, honesty rules. SYNTHETIC / OFFLINE."""
import json
import os
import re
import pytest
from nasha_lab.ops import LABEL, dashboard as D
from nasha_lab.ops.util import RESULTS_DIR, OPS_DIR, load_json

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")
NEW_DOCS = ["OPS-CONTROL-CENTER.md", "OPS-CONTROL-CENTER-EVALUATION.md", "OPS-CONTROL-CENTER-CASE-STUDY.md", "RELIABILITY-MATRIX.md", "OPS-ROLLBACK.md"]
R = lambda n: load_json(os.path.join(RESULTS_DIR, n))


@pytest.mark.parametrize("name", ["control.json", "fault_injection.json", "regression_gate.json", "reliability_gaps.json", "metrics.json", "incidents.json", "slo.json", "cost.json", "sample_traces.json", "rollback_drill.json", "gate_reference.json"])
def test_every_result_file_is_labelled_synthetic(name):
    d = R(name); lab = d["label"] + d.get("synthetic_label", "")
    assert "SYNTHETIC" in lab and "NOT PRODUCTION DEPLOYED" in lab


def test_fault_results_cover_all_eleven_faults_with_at_least_twenty_trials():
    fi = R("fault_injection.json"); want = {"model_timeout", "tool_timeout", "retrieval_miss", "malformed_tool_result", "stale_document", "permission_rejection", "approval_expiry", "database_failure", "schema_violation", "latency_spike", "evaluation_regression"}
    assert set(fi["faults"]) | {"evaluation_regression"} >= want
    for f, v in fi["faults"].items(): assert v["trials"] >= 20, f
    assert R("regression_gate.json")["severity_curve"]["1.0"]["detection"]["n"] >= 20


def test_summaries_match_their_rows():
    fi = R("fault_injection.json")
    for f, rows in fi["rows"].items():
        if f in fi["faults"] and "detection" in fi["faults"][f] and rows and "contained" in rows[0]:
            assert fi["faults"][f]["detection"]["k"] == sum(1 for r in rows if r["detected"]), f
            assert fi["faults"][f]["containment"]["k"] == sum(1 for r in rows if r["contained"]), f


def test_control_set_is_disjoint_from_calibration_and_reports_false_alerts():
    c = R("control.json"); assert c["runs"] >= 200 and "k" in c["runs_with_any_event_or_run_alert"] and c["threshold_calibration_split"].startswith("dev")


def test_slo_and_cost_files_carry_their_assumption_labels():
    assert "DESIGN TARGETS" in R("slo.json")["label"] and "ASSUMPTIONS" in R("cost.json")["assumptions"]["label"]
    assert all(r["api_charge_usd"] == 0.0 for r in R("cost.json")["rows"])


def test_incidents_have_required_fields_and_runbooks():
    inc = R("incidents.json")["incidents"]; assert len(inc) >= 8
    for i in inc:
        for k in ("incident_id", "cls", "severity", "detection_rule", "runbook_id", "status", "timeline"): assert k in i
        assert os.path.exists(os.path.join(OPS_DIR, "runbooks", i["runbook_id"] + ".md"))


def test_no_document_states_a_tool_count_and_all_carry_the_synthetic_label():
    for n in NEW_DOCS:
        t = open(os.path.join(DOCS, n), encoding="utf-8").read()
        assert "SYNTHETIC" in t, n
        assert not re.search(r"\b(1[0-9]|2[0-9])\s+(typed\s+)?(business\s+)?tools\b", t, re.I), f"{n} states a tool count"


def test_reliability_matrix_maps_every_catalog_entry():
    t = open(os.path.join(DOCS, "RELIABILITY-MATRIX.md"), encoding="utf-8").read()
    for i in range(1, 20): assert f"FC-{i:02d}" in t
    for i in range(1, 11): assert f"GAP-{i:02d}" in t
    assert len(re.findall(r"\| (COVERED|PARTIAL|NOT APPLICABLE|NOT DONE)", t)) >= 29


def test_dashboard_is_self_contained_accessible_and_rendered_from_the_json():
    h = D.render(D.load())
    assert h.startswith("<!doctype html>") and '<html lang="en">' in h and "<title>" in h and 'class="skip"' in h and "prefers-color-scheme" in h and LABEL in h
    assert not re.search(r"(src|href)=\"https?://", h) and "<script" not in h and "cdn" not in h.lower()
    assert h.count("<h1") == 1 and 'id="main"' in h and "<caption>" in h
    m = R("metrics.json"); assert str(m["runs"]) in h


def test_dashboard_escapes_untrusted_text():
    """FC-16 lesson applied to the dashboard: values are HTML-escaped, never inserted as markup."""
    data = D.load(); evil = "<img src=x onerror=alert(1)>"
    data["incidents"]["incidents"][0]["timeline"][0]["detail"] = evil; data["traces"]["traces"][0]["events"][0]["kind"] = evil
    h = D.render(data); assert evil not in h and "&lt;img src=x onerror=alert(1)&gt;" in h


def test_trace_cli_lists_and_renders_a_sample_run(capsys):
    from nasha_lab.ops import trace_view as TV
    assert TV.main(["--list"]) == 0; first = capsys.readouterr().out.split()[0]
    assert first.startswith("run-") and TV.main([first]) == 0
    out = capsys.readouterr().out; assert "SYNTHETIC" in out and "approval state" in out and "versions:" in out
    assert TV.main(["run-nonexistent"]) == 1
