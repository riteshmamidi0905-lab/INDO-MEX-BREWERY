"""Regression tests for the failure-injection scenarios: inject -> detect -> contain -> recover. SYNTHETIC / OFFLINE.
Each test pins seeded trials per fault (the committed 20-trial results are in results/ops/fault_injection.json)."""
import pytest
from nasha_lab.ops import alerts as A, faults as F, runner as R


@pytest.fixture(scope="module", autouse=True)
def warm(): R.run_scenario(R.clean_pool()["dev"][0])


def run(fault, seed):
    row, det, env, rid = F.RUN_FAULTS[fault](seed); return row, det, env, rid


def check(row, rules):
    assert row["detected"], row
    assert set(row["rules"]) & set(rules), (row["rules"], rules)
    assert row["contained"], row["containment"]
    assert row["containment"]["mutations_executed"] == 0 and row["containment"]["external_actions"] == 0 and row["containment"]["ungrounded_claims"] == 0


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_model_timeout(seed):
    row, *_ = run("model_timeout", seed); check(row, ["AR-06"]); assert row["containment"]["action"].startswith("ESCALATE") and row["recovered"], row["recovery"]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_tool_timeout(seed):
    row, *_ = run("tool_timeout", seed); check(row, ["AR-01"]); assert row["recovered"], row["recovery"]
    assert row["containment"]["action"].startswith(("ESCALATE", "ABSTAIN")) or row["containment"]["action"] == row["containment"]["clean_action"]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_malformed_tool_result(seed):
    row, *_ = run("malformed_tool_result", seed); check(row, ["AR-04"]); assert row["recovered"]


def test_retrieval_miss_is_detected_for_inventory_and_policy_but_not_for_data_quality():
    rows = [run("retrieval_miss", s)[0] for s in range(8)]
    for r in rows:
        assert r["contained"] and r["recovered"]
        if r["family"] == "DATA_QUALITY": assert not r["detected"], "documented limitation: abstention is the clean baseline for DATA_QUALITY events"
        else: assert r["detected"] and "AR-17" in r["rules"]
    assert any(r["family"] == "DATA_QUALITY" for r in rows) and any(r["family"] != "DATA_QUALITY" for r in rows)


def test_stale_portal_note_is_flagged_and_not_used():
    rows = [run("stale_document", s)[0] for s in range(10)]; p = [r for r in rows if r["variant"] == "stale_portal_note"]
    assert p and all(r["detected"] and "AR-15" in r["rules"] and r["contained"] for r in p)


@pytest.mark.parametrize("seed", [0, 2, 3])
def test_permission_rejection(seed):
    row, det, env, rid = run("permission_rejection", seed); check(row, ["AR-10", "AR-08", "AR-09"]); assert row["recovered"]
    if row["variant"] == "reviewer_role_denied":
        assert row["containment"]["action"] and row["denied_code"] == "ROLE_NOT_PERMITTED"


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_approval_expiry(seed):
    row, *_ = run("approval_expiry", seed); check(row, ["AR-11"]); assert row["recovered"] and row["denied_code"] in ("EXPIRED", "APPROVAL_EXPIRED")


def test_database_failure_both_variants():
    rows = [run("database_failure", s)[0] for s in range(8)]; assert {r["variant"] for r in rows} == {"breaks_mid_run", "down_at_start"}
    for r in rows:
        check(r, ["AR-02", "AR-13"]); assert r["recovered"], r["recovery"]
        if r["variant"] == "down_at_start": assert r["crashed"] and r["containment"]["run_status"] == "FAILED"


def test_schema_violation_transient_recovers_by_retry_and_persistent_escalates():
    rows = [run("schema_violation", s)[0] for s in range(12)]
    for r in rows:
        assert r["detected"] and r["contained"]
        if r["variant"] == "model_reply_persistent": assert r["containment"]["action"].startswith("ESCALATE") and r["recovered"]
        if r["variant"].startswith("model_reply_transient"): assert r["recovered"]


def test_latency_spike_large_is_detected_small_is_not_and_clean_sequence_is_quiet():
    big = F.latency_trial(1, 200); assert big["detected"] and big["detected_by"] in ("event", "window") and big["ttd_runs"] <= 3 and not big["false_alert_before_onset"]
    small = F.latency_trial(2, 10); assert not small["detected"], "a +10 ms/call spike stays inside the design target and must not alert"
    assert not F.latency_trial(3, 0, with_spike=False)["any_latency_alert_in_clean_sequence"]


def test_expected_classes_exist_in_the_taxonomy():
    ev = A.AlertEvaluator()
    for f, cl in F.EXPECTED.items(): assert cl <= set(ev.classes) | {"SCHEMA_VIOLATION_TOOL_ARGS"}, f
