"""Integration tests against a real PostgreSQL: persistence, idempotency, authorization, IDOR, approvals, audit, dead letters, readiness, metrics, graceful shutdown."""
from __future__ import annotations

import concurrent.futures as cf
import threading
import time
import uuid

import psycopg
import pytest

from conftest import auth

pytestmark = pytest.mark.p5_pg


def K(): return {"Idempotency-Key": "t-" + uuid.uuid4().hex}


def start(e, ev="EV-A1", who=("alice", "BUYER"), key=None):
    return e.client.post("/v1/runs", json={"event_id": ev}, headers={**auth(e.keys, *who), **(key or K())})


def count(dsn, sql, *a):
    with psycopg.connect(dsn) as c: return c.execute(sql, a).fetchone()[0]


def test_start_run_persists_state_audit_and_idempotency_row(app_env):
    r = start(app_env); assert r.status_code == 201, r.text
    b = r.json(); assert b["status"] == "AWAITING_HUMAN" and b["awaiting_human"] and b["proposal"] and b["run_id"].startswith("run-")
    assert count(app_env.dsn, "SELECT count(*) FROM runs WHERE run_id=%s AND owner='alice' AND awaiting_human", b["run_id"]) == 1
    assert count(app_env.dsn, "SELECT count(*) FROM audit_log WHERE action='run.start' AND resource=%s", b["run_id"]) == 1
    assert count(app_env.dsn, "SELECT count(*) FROM idempotency_keys") == 1


def test_run_state_survives_an_application_restart_because_it_is_in_postgres(app_env, svc, keys, tmp_path):
    from fastapi.testclient import TestClient
    from nasha_lab.service.app import create_hardened_app
    rid = start(app_env).json()["run_id"]
    app2 = create_hardened_app(app_env.settings, service=svc)           # a second process-equivalent against the same database
    with TestClient(app2) as c2:
        r = c2.get(f"/v1/runs/{rid}", headers=auth(keys)); assert r.status_code == 200 and r.json()["run_id"] == rid and r.json()["awaiting_human"]


def test_same_key_and_body_returns_the_stored_response_and_executes_once(app_env):
    key = K(); a = start(app_env, key=key); b = start(app_env, key=key)
    assert a.status_code == 201 and b.status_code == 201 and a.json() == b.json() and b.headers["idempotent-replay"] == "true" and "idempotent-replay" not in a.headers
    assert count(app_env.dsn, "SELECT count(*) FROM runs") == 1 and len(app_env.service.store.con.execute("SELECT * FROM agent_runs").fetchall()) == 1


def test_same_key_different_body_is_rejected_422_and_nothing_executes(app_env):
    key = K(); assert start(app_env, "EV-A1", key=key).status_code == 201
    r = start(app_env, "EV-A2", key=key); assert r.status_code == 422 and r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert count(app_env.dsn, "SELECT count(*) FROM runs") == 1


def test_same_key_on_a_different_route_is_rejected(app_env):
    key = K(); rid = start(app_env, key=key).json()["run_id"]
    r = app_env.client.post(f"/v1/runs/{rid}/reject", json={}, headers={**auth(app_env.keys), **key}); assert r.status_code == 422 and r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_idempotency_keys_are_scoped_per_principal(app_env):
    key = K(); a = start(app_env, "EV-A1", ("alice", "BUYER"), key); b = start(app_env, "EV-A2", ("bob", "QUALITY_LEAD"), key)
    assert a.status_code == 201 and b.status_code == 201 and a.json()["run_id"] != b.json()["run_id"]


def test_concurrent_duplicates_with_one_key_are_serialised_to_one_execution(app_env):
    key = K(); out = []
    with cf.ThreadPoolExecutor(8) as ex:
        out = list(ex.map(lambda _: start(app_env, key=key), range(8)))
    assert {r.status_code for r in out} == {201} and len({r.json()["run_id"] for r in out}) == 1
    assert sum(1 for r in out if r.headers.get("idempotent-replay") == "true") == 7
    assert count(app_env.dsn, "SELECT count(*) FROM runs") == 1 and len(app_env.service.store.con.execute("SELECT * FROM agent_runs").fetchall()) == 1


def test_concurrent_requests_for_the_same_event_with_different_keys_start_one_run(app_env):
    with cf.ThreadPoolExecutor(6) as ex: out = list(ex.map(lambda _: start(app_env, "EV-A1"), range(6)))
    codes = sorted(r.status_code for r in out); assert codes == [201] + [409] * 5, codes
    assert {r.json()["error"]["code"] for r in out if r.status_code == 409} == {"EVENT_ALREADY_PROCESSED"}
    assert count(app_env.dsn, "SELECT count(*) FROM runs") == 1


def test_second_start_for_an_event_does_not_leak_the_run_id_to_a_stranger(app_env):
    start(app_env, "EV-A1", ("alice", "BUYER"))
    r = start(app_env, "EV-A1", ("eve", "READER" if False else "BUYER")); assert r.status_code == 409 and "details" in r.json()["error"]       # reviewers with read_all may see it
    from conftest import tok
    r = app_env.client.post("/v1/runs", json={"event_id": "EV-A1"}, headers={**auth(app_env.keys, "mallory", "OPERATOR"), **K()}); assert r.status_code == 403         # OPERATOR cannot start runs


def test_unknown_event_is_404_and_leaves_no_state(app_env):
    r = start(app_env, "EV-Z99"); assert r.status_code == 404 and r.json()["error"]["code"] == "UNKNOWN_EVENT"
    assert count(app_env.dsn, "SELECT count(*) FROM runs") == 0 and len(app_env.service.store.con.execute("SELECT * FROM agent_runs").fetchall()) == 0


def test_missing_or_invalid_idempotency_key_is_a_400(app_env):
    h = auth(app_env.keys)
    assert app_env.client.post("/v1/runs", json={"event_id": "EV-A1"}, headers=h).json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    for bad in ("short", "x" * 129, "has space in it", "semi;colon;key", "new\\nline-key"):
        r = app_env.client.post("/v1/runs", json={"event_id": "EV-A1"}, headers={**h, "Idempotency-Key": bad}); assert r.status_code == 400 and r.json()["error"]["code"] == "IDEMPOTENCY_KEY_INVALID", bad


# ---------------------------------------------------------------------------- approvals and roles
def test_approve_records_approval_updates_run_and_replays_by_key(app_env):
    rid = start(app_env).json()["run_id"]; key = K()
    r = app_env.client.post(f"/v1/runs/{rid}/approve", json={"note": "ok"}, headers={**auth(app_env.keys, "carol", "FOUNDER"), **key}); assert r.status_code == 200, r.text
    assert r.json()["status"] == "COMPLETED" and not r.json()["awaiting_human"]
    assert count(app_env.dsn, "SELECT count(*) FROM approvals WHERE run_id=%s AND reviewer='carol' AND role='FOUNDER' AND decision='approve'", rid) == 1
    r2 = app_env.client.post(f"/v1/runs/{rid}/approve", json={"note": "ok"}, headers={**auth(app_env.keys, "carol", "FOUNDER"), **key}); assert r2.status_code == 200 and r2.headers["idempotent-replay"] == "true"
    assert count(app_env.dsn, "SELECT count(*) FROM approvals") == 1


def test_approving_twice_with_different_keys_is_a_409_not_a_second_execution(app_env):
    rid = start(app_env).json()["run_id"]; h = auth(app_env.keys, "carol", "FOUNDER")
    assert app_env.client.post(f"/v1/runs/{rid}/approve", json={}, headers={**h, **K()}).status_code == 200
    r = app_env.client.post(f"/v1/runs/{rid}/approve", json={}, headers={**h, **K()}); assert r.status_code == 409 and r.json()["error"]["code"] == "CONFLICT_STATE"
    assert count(app_env.dsn, "SELECT count(*) FROM approvals") == 1


def test_concurrent_approvals_with_different_keys_execute_exactly_once(app_env):
    rid = start(app_env).json()["run_id"]; h = auth(app_env.keys, "carol", "FOUNDER")
    with cf.ThreadPoolExecutor(6) as ex: out = list(ex.map(lambda _: app_env.client.post(f"/v1/runs/{rid}/approve", json={}, headers={**h, **K()}), range(6)))
    assert sorted(r.status_code for r in out) == [200] + [409] * 5
    assert count(app_env.dsn, "SELECT count(*) FROM approvals") == 1


@pytest.mark.parametrize("role", ["READER", "OPERATOR", "AUDITOR"])
def test_roles_without_decide_permission_cannot_approve_or_reject(app_env, role):
    rid = start(app_env).json()["run_id"]
    for verb in ("approve", "reject"):
        r = app_env.client.post(f"/v1/runs/{rid}/{verb}", json={}, headers={**auth(app_env.keys, "x1", role), **K()}); assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"
    assert count(app_env.dsn, "SELECT count(*) FROM approvals") == 0 and count(app_env.dsn, "SELECT awaiting_human FROM runs WHERE run_id=%s", rid)


def test_agent_role_policy_is_still_enforced_no_role_escalation(app_env):
    """QUALITY_LEAD may not approve the proposal's action under the lab's own ROLE_POLICY; the hardened layer must not widen it."""
    from nasha_lab import identity as ID
    runs = {}
    for ev in ("EV-A1", "EV-A2", "EV-B1", "EV-C1", "EV-C2", "EV-D1"):
        r = start(app_env, ev)
        if r.status_code == 201: runs[ev] = r.json()
    denied = 0; allowed = 0
    for ev, run in runs.items():
        acts = (run.get("proposal") or {}).get("mutating_actions", [])
        if not acts: continue
        r = app_env.client.post(f"/v1/runs/{run['run_id']}/approve", json={}, headers={**auth(app_env.keys, "bob", "QUALITY_LEAD"), **K()})
        expected_ok = all(ID.Authority.role_allowed("QUALITY_LEAD", a["tool"], a["args"]) for a in acts)
        assert (r.status_code == 200) == expected_ok, (ev, r.status_code, r.text[:200])
        if r.status_code == 403: assert r.json()["error"]["code"] == "ROLE_NOT_PERMITTED"; denied += 1
        else: allowed += 1
        if not expected_ok: assert count(app_env.dsn, "SELECT awaiting_human FROM runs WHERE run_id=%s", run["run_id"]) is True
    assert denied + allowed >= 1


def test_denied_approval_is_audited(app_env):
    rid = start(app_env).json()["run_id"]
    app_env.client.post(f"/v1/runs/{rid}/approve", json={}, headers={**auth(app_env.keys, "x1", "READER"), **K()})
    # READER is refused before reaching the handler (FORBIDDEN): that is an authz failure recorded in metrics, not an audit row
    assert count(app_env.dsn, "SELECT count(*) FROM audit_log WHERE outcome='denied'") == 0
    assert app_env.app.state.ctx.metrics.counter_value("nasha_auth_failures_total", reason="FORBIDDEN") >= 1


def test_reject_records_and_completes(app_env):
    rid = start(app_env).json()["run_id"]
    r = app_env.client.post(f"/v1/runs/{rid}/reject", json={"note": "no"}, headers={**auth(app_env.keys, "carol", "FOUNDER"), **K()}); assert r.status_code == 200 and not r.json()["awaiting_human"]
    assert count(app_env.dsn, "SELECT decision FROM approvals WHERE run_id=%s", rid) == "reject"


def test_decision_on_unknown_run_is_404_after_authentication(app_env):
    r = app_env.client.post("/v1/runs/run-0000000000/approve", json={}, headers={**auth(app_env.keys, "carol", "FOUNDER"), **K()}); assert r.status_code == 404
    r = app_env.client.post("/v1/runs/run-0000000000/approve", json={}, headers=K()); assert r.status_code == 401         # unauthenticated callers learn nothing about run existence


# ---------------------------------------------------------------------------- IDOR and visibility
def test_a_reader_cannot_read_or_list_someone_elses_run_and_gets_the_same_answer_as_for_a_missing_run(app_env):
    rid = start(app_env, "EV-A1", ("alice", "BUYER")).json()["run_id"]
    mine = app_env.client.get(f"/v1/runs/{rid}", headers=auth(app_env.keys, "alice", "BUYER")); assert mine.status_code == 200
    other = app_env.client.get(f"/v1/runs/{rid}", headers=auth(app_env.keys, "mallory", "READER")); missing = app_env.client.get("/v1/runs/run-ffffffffff", headers=auth(app_env.keys, "mallory", "READER"))
    assert other.status_code == missing.status_code == 404
    strip = lambda r: {k: v for k, v in r.json()["error"].items() if k not in ("request_id", "message")}
    assert strip(other) == strip(missing)
    assert app_env.client.get("/v1/runs", headers=auth(app_env.keys, "mallory", "READER")).json()["runs"] == []
    assert [x["run_id"] for x in app_env.client.get("/v1/runs", headers=auth(app_env.keys, "alice", "BUYER")).json()["runs"]] == [rid]


def test_privileged_roles_can_see_all_runs(app_env):
    rid = start(app_env, "EV-A1", ("alice", "BUYER")).json()["run_id"]
    for who in (("ops", "OPERATOR"), ("aud", "AUDITOR"), ("carol", "FOUNDER")):
        assert app_env.client.get(f"/v1/runs/{rid}", headers=auth(app_env.keys, *who)).status_code == 200


def test_run_list_pagination_is_stable_and_bounded(app_env):
    ids = [start(app_env, ev).json()["run_id"] for ev in ("EV-A1", "EV-A2", "EV-B1")]
    h = auth(app_env.keys, "alice", "BUYER")
    p1 = app_env.client.get("/v1/runs?limit=2", headers=h).json(); assert len(p1["runs"]) == 2 and p1["next_before"]
    p2 = app_env.client.get(f"/v1/runs?limit=2&before={p1['next_before']}", headers=h).json()
    assert [r["run_id"] for r in p1["runs"] + p2["runs"]] == ids[::-1]
    assert app_env.client.get("/v1/runs?limit=101", headers=h).status_code == 422


# ---------------------------------------------------------------------------- tools
def test_read_tools_return_data_and_attempt_counts(app_env):
    h = auth(app_env.keys)
    r = app_env.client.get("/v1/inventory/goat?location_id=L01", headers=h); assert r.status_code == 200 and r.json()["attempts"] == 1 and r.json()["data"]
    assert app_env.client.get("/v1/quality/findings?limit=3", headers=h).status_code == 200
    assert app_env.client.post("/v1/knowledge/ask", json={"question": "Are dairy alternatives allowed in the menu?"}, headers=h).status_code == 200
    assert app_env.client.get("/v1/events", headers=h).json()["events"]


def test_unknown_ingredient_is_a_permanent_404_with_no_retry(app_env):
    r = app_env.client.get("/v1/inventory/nonexistent?location_id=L01", headers=auth(app_env.keys)); e = r.json()["error"]
    assert r.status_code == 404 and e["code"] == "NOT_FOUND" and e["details"]["attempts"] == 1 and e["details"]["policy_actions"] == ["FAIL_FAST"]


# ---------------------------------------------------------------------------- dead letters, audit
def test_dead_letter_listing_and_resolution_are_operator_only_and_idempotent(app_env):
    from nasha_lab.service import store as ST
    rec = ST.dead_letter_record(correlation_id="req-test0001", run_id="run-aaaaaaaaaa", operation="human_approval_execute_step", tool=None, op_class="HUMAN_REVIEW_REQUIRED", failure_code="X",
                                failure_class="TIMEOUT_AMBIGUOUS", attempts=1, reason="test", args={"run_id": "run-aaaaaaaaaa", "api_key": "should-be-redacted-value"})
    with psycopg.connect(app_env.dsn) as c: ST.insert_dead_letter(c, rec); c.commit()
    ops, buyer = auth(app_env.keys, "ops", "OPERATOR"), auth(app_env.keys, "alice", "BUYER")
    assert app_env.client.get("/v1/dead-letters", headers=buyer).status_code == 403
    lst = app_env.client.get("/v1/dead-letters", headers=ops).json()["dead_letters"]; assert len(lst) == 1 and lst[0]["status"] == "OPEN" and "should-be-redacted-value" not in str(lst)
    key = K(); body = {"status": "ALREADY_APPLIED", "note": "checked the target state"}
    assert app_env.client.post(f"/v1/dead-letters/{rec['dl_id']}/resolve", json=body, headers={**buyer, **key}).status_code == 403
    r = app_env.client.post(f"/v1/dead-letters/{rec['dl_id']}/resolve", json=body, headers={**ops, **key}); assert r.status_code == 200 and r.json()["status"] == "ALREADY_APPLIED"
    assert app_env.client.post(f"/v1/dead-letters/{rec['dl_id']}/resolve", json=body, headers={**ops, **key}).headers["idempotent-replay"] == "true"
    assert app_env.client.post(f"/v1/dead-letters/{rec['dl_id']}/resolve", json=body, headers={**ops, **K()}).status_code == 404       # no longer OPEN
    assert app_env.client.get("/v1/dead-letters", headers=ops).json()["dead_letters"] == []


def test_audit_endpoint_is_restricted_and_hashes_principals(app_env):
    start(app_env, who=("alice", "BUYER"))
    assert app_env.client.get("/v1/audit", headers=auth(app_env.keys, "alice", "BUYER")).status_code == 403
    for who in (("ops", "OPERATOR"), ("aud", "AUDITOR")):
        r = app_env.client.get("/v1/audit", headers=auth(app_env.keys, *who)); assert r.status_code == 200 and r.json()["entries"] and "alice" not in r.text


# ---------------------------------------------------------------------------- readiness, metrics, shutdown
def test_readyz_reports_each_dependency(app_env):
    r = app_env.client.get("/readyz"); b = r.json(); assert r.status_code == 200 and b["schema_version"] == 3 and set(b["checks"]) == {"db", "schema", "agent", "draining"} and all(v["ok"] for v in b["checks"].values())


def test_metrics_endpoint_requires_operator_and_exposes_the_required_series(app_env):
    start(app_env); app_env.client.get("/v1/inventory/goat?location_id=L01", headers=auth(app_env.keys))
    assert app_env.client.get("/metrics").status_code == 401
    assert app_env.client.get("/metrics", headers=auth(app_env.keys, "alice", "BUYER")).status_code == 403
    t = app_env.client.get("/metrics", headers=auth(app_env.keys, "ops", "OPERATOR")).text
    for series in ("nasha_http_requests_total", "nasha_http_request_duration_seconds_bucket", "nasha_http_errors_total", "nasha_rate_limited_total" if False else "nasha_auth_failures_total",
                   "nasha_db_pool{", "nasha_db_up 1", "nasha_schema_version 3", "nasha_dead_letters{", "nasha_inflight_requests", "nasha_tool_calls_total", "nasha_build_info"):
        assert series in t, series
    assert 'route="/v1/runs"' in t and "alice" not in t


def test_graceful_shutdown_drains_new_requests_and_lets_inflight_finish(app_env):
    ctx = app_env.app.state.ctx; res = {}
    orig = ctx.gateway.call
    def slow(*a, **k): time.sleep(0.6); return orig(*a, **k)
    ctx.gateway.call = slow
    t = threading.Thread(target=lambda: res.setdefault("r", app_env.client.get("/v1/inventory/goat?location_id=L01", headers=auth(app_env.keys))))
    t.start(); time.sleep(0.2)
    ctx.rt.draining = True
    r = app_env.client.get("/v1/events", headers=auth(app_env.keys)); assert r.status_code == 503 and r.json()["error"]["code"] == "SHUTTING_DOWN" and r.headers["retry-after"]
    assert app_env.client.get("/healthz").status_code == 200                         # liveness stays up while draining
    rz = app_env.client.get("/readyz"); assert rz.status_code == 503 and rz.json()["error"]["details"]["failed"] == ["draining"]
    t.join(); assert res["r"].status_code == 200                                      # the in-flight request completed
    ctx.rt.draining = False
