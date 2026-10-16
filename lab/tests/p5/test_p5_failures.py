"""Failure-injection tests (P5). Each scenario states EXPECTED before acting, then records OBSERVED. See docs/P5-FAILURE-LOG.md for the weaknesses these found."""
from __future__ import annotations

import concurrent.futures as cf
import json
import shutil
import threading
import time
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from conftest import auth, make_settings, new_service
from nasha_lab.service import store as ST
from nasha_lab.service.app import create_hardened_app
from nasha_lab.service.migrations import MIG_DIR, Migrator
from results_recorder import record

pytestmark = pytest.mark.p5_pg


def K(): return {"Idempotency-Key": "t-" + uuid.uuid4().hex}


def n(dsn, sql, *a):
    with psycopg.connect(dsn) as c: return c.execute(sql, a).fetchone()[0]


def dbname(dsn): return psycopg.conninfo.conninfo_to_dict(dsn)["dbname"]


def start(c, keys, ev="EV-A1", key=None, who=("alice", "BUYER")):
    return c.post("/v1/runs", json={"event_id": ev}, headers={**auth(keys, *who), **(key or K())})


def agent_runs(svc): return len(svc.store.con.execute("SELECT * FROM agent_runs").fetchall())


# ------------------------------------------------------------------------------------------------ F01 database unavailable at start
def test_F01_database_unavailable_at_start_then_recovers(migrated_db, proxy, keys, svc, tmp_path):
    exp = ("App starts degraded: /healthz 200; /readyz 503 with failed=[db, schema]; DB-backed routes 503 DB_UNAVAILABLE or DB_POOL_EXHAUSTED with Retry-After; routes that do not need the "
           "database (read tools) still answer 200; after the database returns /readyz becomes 200 without a restart. With require_db_at_start=true the process refuses to start.")
    proxy.set_mode("down"); dsn = proxy.dsn(dbname(migrated_db)); t0 = time.perf_counter(); obs = {}
    s = make_settings(dsn, keys, str(tmp_path), db_pool_timeout_s=0.5, db_breaker_reset_s=1.0)
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        obs["healthz"] = c.get("/healthz").status_code
        rz = c.get("/readyz"); obs["readyz"] = rz.status_code; obs["readyz_failed"] = rz.json()["error"]["details"]["failed"]; obs["readyz_code"] = rz.json()["error"]["code"]
        r = start(c, keys); obs["db_route"] = [r.status_code, r.json()["error"]["code"], bool(r.headers.get("retry-after"))]
        obs["tool_route_without_db"] = c.get("/v1/inventory/goat?location_id=L01", headers=auth(keys)).status_code
        proxy.set_mode("pass"); recovered = None; t1 = time.perf_counter()
        for _ in range(60):
            c.app.state.ctx.ready_cache = None
            if c.get("/readyz").status_code == 200: recovered = time.perf_counter() - t1; break
            time.sleep(0.5)
        obs["recovered_without_restart"] = recovered is not None
        obs["run_after_recovery"] = start(c, keys).status_code if recovered is not None else None
    s2 = make_settings(proxy.dsn(dbname(migrated_db)), keys, str(tmp_path / "x"), require_db_at_start=True, db_pool_timeout_s=0.5); proxy.set_mode("down")
    with pytest.raises(RuntimeError, match="refusing to start"):
        with TestClient(create_hardened_app(s2, service=new_service(svc.rt.kb))): pass
    obs["require_db_at_start_refuses"] = True
    ok = obs["healthz"] == 200 and obs["readyz"] == 503 and set(obs["readyz_failed"]) == {"db", "schema"} and obs["db_route"][0] == 503 and obs["db_route"][1] in ("DB_UNAVAILABLE", "DB_POOL_EXHAUSTED") and obs["db_route"][2] \
        and obs["tool_route_without_db"] == 200 and obs["recovered_without_restart"] and obs["run_after_recovery"] == 201
    record("F01", "database unavailable at start", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F02 database lost mid-request
def test_F02_database_lost_mid_request_leaves_nothing_half_written_and_the_retry_reconciles(migrated_db, proxy, keys, svc, tmp_path, monkeypatch):
    exp = ("The connection dies after the agent started the run but before the row is written: 503 (DB_UNAVAILABLE), no runs row, no idempotency row, one orphan agent run. "
           "The breaker then opens (fast 503 without waiting). After recovery the SAME Idempotency-Key succeeds with reconciled=true and the agent still has exactly one run for the event.")
    dsn = proxy.dsn(dbname(migrated_db)); s = make_settings(dsn, keys, str(tmp_path), db_pool_timeout_s=0.5, db_breaker_threshold=2, db_breaker_reset_s=1.0); obs = {}; t0 = time.perf_counter()
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        assert start(c, keys, "EV-A2").status_code == 201
        orig = ST.insert_run
        def dies(conn, **kw): proxy.set_mode("down"); return orig(conn, **kw)
        monkeypatch.setattr(ST, "insert_run", dies); key = K()
        r = start(c, keys, "EV-A1", key); obs["first"] = [r.status_code, r.json()["error"]["code"]]
        monkeypatch.setattr(ST, "insert_run", orig)
        obs["agent_runs_for_event"] = len(svc.store.con.execute("SELECT * FROM agent_runs WHERE event_id='EV-A1'").fetchall())
        t1 = time.perf_counter(); fast = [start(c, keys, "EV-A1", key).json()["error"]["code"] for _ in range(3)]; obs["while_down"] = fast; obs["while_down_fast"] = (time.perf_counter() - t1) < 3.0
        proxy.set_mode("pass"); time.sleep(1.3)
        for _ in range(30):
            r = start(c, keys, "EV-A1", key)
            if r.status_code == 201: break
            time.sleep(0.5)
        obs["retry"] = [r.status_code, r.json().get("reconciled")]
        obs["runs_rows_for_event"] = n(migrated_db, "SELECT count(*) FROM runs WHERE event_id='EV-A1'"); obs["agent_runs_for_event_after"] = len(svc.store.con.execute("SELECT * FROM agent_runs WHERE event_id='EV-A1'").fetchall())
        obs["idem_rows_for_key"] = n(migrated_db, "SELECT count(*) FROM idempotency_keys WHERE key=%s", key["Idempotency-Key"])
    ok = obs["first"][0] == 503 and obs["first"][1] in ("DB_UNAVAILABLE", "DB_POOL_EXHAUSTED") and obs["agent_runs_for_event"] == 1 and obs["retry"] == [201, True] and obs["runs_rows_for_event"] == 1 and obs["agent_runs_for_event_after"] == 1 and obs["idem_rows_for_key"] == 1 and obs["while_down_fast"]
    record("F02", "database lost mid-request (between agent effect and DB write)", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F03 slow database
def test_F03_slow_database_hits_statement_timeout_and_pool_timeout_without_leaking_connections(migrated_db, keys, svc, tmp_path, monkeypatch):
    exp = ("A statement slower than db_statement_timeout_ms is cancelled by PostgreSQL: 504 DB_TIMEOUT, advised retry only with the same key. When every pooled connection is busy the next request waits at most "
           "db_pool_timeout_s then gets 503 DB_POOL_EXHAUSTED with Retry-After. Afterwards the pool is healthy: the next normal request is 200 and no connection stays in 'idle in transaction'.")
    s = make_settings(migrated_db, keys, str(tmp_path), db_statement_timeout_ms=300, db_pool_max=2, db_pool_min=2, db_pool_timeout_s=0.4); obs = {}; t0 = time.perf_counter()
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        h = auth(keys, "alice", "BUYER")
        orig = ST.list_runs
        monkeypatch.setattr(ST, "list_runs", lambda conn, **kw: conn.execute("SELECT pg_sleep(3)").fetchall())
        t1 = time.perf_counter(); r = c.get("/v1/runs", headers=h); obs["statement_timeout"] = [r.status_code, r.json()["error"]["code"], r.json()["error"]["client_retry"]]; obs["cancelled_quickly"] = (time.perf_counter() - t1) < 1.5
        monkeypatch.setattr(ST, "list_runs", orig)
        ctx = c.app.state.ctx; hold = threading.Event(); started = []
        def occupy():
            with ctx.db.tx(): started.append(1); hold.wait(5)
        ts = [threading.Thread(target=occupy) for _ in range(2)]
        for t in ts: t.start()
        while len(started) < 2: time.sleep(0.02)
        t1 = time.perf_counter(); r = c.get("/v1/runs", headers=h); waited = time.perf_counter() - t1
        obs["pool_exhausted"] = [r.status_code, r.json()["error"]["code"], bool(r.headers.get("retry-after"))]; obs["waited_at_most_pool_timeout"] = waited < 1.5
        hold.set(); [t.join() for t in ts]; time.sleep(0.3)
        obs["after"] = c.get("/v1/runs", headers=h).status_code
        obs["idle_in_tx"] = n(migrated_db, "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND state LIKE 'idle in transaction%%'")
    ok = obs["statement_timeout"][:2] == [504, "DB_TIMEOUT"] and obs["statement_timeout"][2] == "same_idempotency_key" and obs["cancelled_quickly"] and obs["pool_exhausted"] == [503, "DB_POOL_EXHAUSTED", True] and obs["waited_at_most_pool_timeout"] and obs["after"] == 200 and obs["idle_in_tx"] == 0
    record("F03", "slow database: statement timeout and pool timeout", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


def test_F03b_slow_network_to_the_database_returns_a_bounded_error(migrated_db, proxy, keys, svc, tmp_path):
    exp = "With 0.8 s added to every database packet and a 1 s request deadline, a DB-backed request returns 504 DEADLINE_EXCEEDED (or 503) within about 2 s instead of hanging; with the delay removed requests succeed again."
    dsn = proxy.dsn(dbname(migrated_db)); s = make_settings(dsn, keys, str(tmp_path), default_deadline_s=1.0, db_pool_timeout_s=0.5); obs = {}; t0 = time.perf_counter()
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        h = auth(keys, "alice", "BUYER"); assert c.get("/v1/runs", headers=h).status_code == 200
        proxy.set_mode("slow", 0.8); t1 = time.perf_counter(); r = c.get("/v1/runs", headers=h); el = time.perf_counter() - t1
        obs["slow"] = [r.status_code, r.json()["error"]["code"]]; obs["bounded"] = el < 3.0
        proxy.set_mode("pass"); time.sleep(1.0)
        ok2 = False
        for _ in range(20):
            if c.get("/v1/runs", headers=h).status_code == 200: ok2 = True; break
            time.sleep(0.5)
        obs["recovered"] = ok2
    ok = obs["slow"][0] in (503, 504) and obs["bounded"] and obs["recovered"]
    record("F03b", "slow network to the database (added latency)", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F04/F05 authentication
def test_F04_F05_invalid_and_expired_auth(app_env):
    exp = "No/garbage/forged token: 401 AUTH_REQUIRED or AUTH_INVALID_TOKEN; expired token: 401 AUTH_TOKEN_EXPIRED; zero database connections used and zero rows written for all of them."
    from conftest import tok
    c, k = app_env.client, app_env.keys; obs = {}
    before = n(app_env.dsn, "SELECT count(*) FROM audit_log")
    cases = {"none": {}, "garbage": {"Authorization": "Bearer abc"}, "forged": {"Authorization": "Bearer " + tok(k, "a", "FOUNDER")[:-5] + "AAAAA"}, "expired": {"Authorization": "Bearer " + tok(k, "a", "FOUNDER", 60, now=time.time() - 7200)}}
    for name, h in cases.items():
        r = c.post("/v1/runs", json={"event_id": "EV-A1"}, headers={**h, **K()}); obs[name] = [r.status_code, r.json()["error"]["code"]]
    obs["rows_written"] = n(app_env.dsn, "SELECT count(*) FROM audit_log") - before + n(app_env.dsn, "SELECT count(*) FROM runs")
    ok = obs["none"] == [401, "AUTH_REQUIRED"] and obs["garbage"] == [401, "AUTH_INVALID_TOKEN"] and obs["forged"] == [401, "AUTH_INVALID_TOKEN"] and obs["expired"] == [401, "AUTH_TOKEN_EXPIRED"] and obs["rows_written"] == 0
    record("F04", "invalid authentication", exp, {k: v for k, v in obs.items() if k != "expired"}, ok); record("F05", "expired authentication", exp, {"expired": obs["expired"]}, obs["expired"] == [401, "AUTH_TOKEN_EXPIRED"]); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F06 rate limit
def test_F06_rate_limit_exceeded_per_principal_and_per_ip_with_recovery(migrated_db, keys, svc, tmp_path):
    exp = ("Capacity 5 per principal and no refill: of 10 calls by one principal exactly 5 succeed and 5 are 429 RATE_LIMITED with Retry-After; a second principal is unaffected; per-IP capacity 8: of 12 unauthenticated "
           "calls exactly 8 reach auth (401) and 4 are 429; probes /healthz and /readyz are never limited; after the clock advances 10 s the principal can call again.")
    now = [1000.0]; obs = {}
    s = make_settings(migrated_db, keys, str(tmp_path), rate_principal_capacity=5, rate_principal_refill_per_s=0.5, rate_ip_capacity=8, rate_ip_refill_per_s=0.0001)
    with TestClient(create_hardened_app(s, service=svc, clock=lambda: now[0]), raise_server_exceptions=False) as c:
        a = [c.get("/v1/events", headers=auth(keys, "alice", "BUYER")).status_code for _ in range(7)]       # IP bucket: 7 of 8 used
        obs["note"] = "first 7 calls consume the IP bucket; principal calls use their own bucket (5)"
        obs["principal_alice_first7"] = {"200": a.count(200), "429": a.count(429)}
        r = c.get("/v1/events", headers=auth(keys, "alice", "BUYER")); obs["alice_8th"] = [r.status_code, r.json()["error"]["code"] if r.status_code != 200 else None, r.headers.get("retry-after")]
        obs["probes_never_limited"] = all(c.get(p).status_code == 200 for p in ["/healthz"] * 15 + ["/readyz"] * 5)
        r = c.get("/v1/events"); obs["ip_exhausted"] = [r.status_code, r.json()["error"]["code"]]
    s = make_settings(migrated_db, keys, str(tmp_path / "b"), rate_principal_capacity=5, rate_principal_refill_per_s=0.5, rate_ip_capacity=1000, rate_ip_refill_per_s=1000)
    with TestClient(create_hardened_app(s, service=svc, clock=lambda: now[0]), raise_server_exceptions=False) as c:
        out = [c.get("/v1/events", headers=auth(keys, "alice", "BUYER")) for _ in range(10)]; codes = [r.status_code for r in out]
        obs["alice_10_calls"] = {"200": codes.count(200), "429": codes.count(429)}; limited = next(r for r in out if r.status_code == 429)
        obs["limited_envelope"] = [limited.json()["error"]["code"], int(limited.headers["retry-after"]) >= 1]
        obs["bob_unaffected"] = c.get("/v1/events", headers=auth(keys, "bob", "BUYER")).status_code
        now[0] += 10; obs["alice_after_10s"] = c.get("/v1/events", headers=auth(keys, "alice", "BUYER")).status_code
        obs["limiter_metric"] = c.app.state.ctx.metrics.counter_value("nasha_rate_limited_total", scope="principal")
    ok = obs["alice_10_calls"] == {"200": 5, "429": 5} and obs["limited_envelope"] == ["RATE_LIMITED", True] and obs["bob_unaffected"] == 200 and obs["alice_after_10s"] == 200 and obs["probes_never_limited"] \
        and obs["ip_exhausted"] == [429, "RATE_LIMITED"] and obs["limiter_metric"] == 5
    record("F06", "rate limit exceeded", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F07 duplicate request
def test_F07_duplicate_requests(app_env):
    exp = "20 concurrent identical requests with one Idempotency-Key: all 201 with the identical body, 19 marked Idempotent-Replay, exactly 1 runs row, 1 agent run, 1 audit row. Same key + different body: 422 IDEMPOTENCY_KEY_REUSED."
    c, k = app_env.client, app_env.keys; key = K(); obs = {}; t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(10) as ex: out = list(ex.map(lambda _: start(c, k, "EV-B1", key), range(20)))
    obs["statuses"] = sorted({r.status_code for r in out}); obs["distinct_bodies"] = len({json.dumps(r.json(), sort_keys=True) for r in out}); obs["replays"] = sum(r.headers.get("idempotent-replay") == "true" for r in out)
    obs["runs_rows"] = n(app_env.dsn, "SELECT count(*) FROM runs"); obs["agent_runs"] = agent_runs(app_env.service); obs["audit_rows"] = n(app_env.dsn, "SELECT count(*) FROM audit_log WHERE action='run.start'")
    r = start(c, k, "EV-B2", key); obs["different_body"] = [r.status_code, r.json()["error"]["code"]]
    ok = obs == dict(statuses=[201], distinct_bodies=1, replays=19, runs_rows=1, agent_runs=1, audit_rows=1, different_body=[422, "IDEMPOTENCY_KEY_REUSED"])
    record("F07", "duplicate request (idempotency)", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F08/F09 tool timeout and upstream 500
def test_F08_tool_timeout_is_retried_only_under_the_policy_and_surfaces_504(migrated_db, keys, svc, tmp_path):
    exp = ("query_inventory is SAFE_TO_RETRY, so a timing-out tool is attempted 3 times (policy max_attempts) and then returns 504 TOOL_TIMEOUT with attempts=3 and policy_actions [RETRY, RETRY, ...]; "
           "the total stays within the request deadline; a mutating route is never retried by this path.")
    s = make_settings(migrated_db, keys, str(tmp_path), tool_timeout_s=0.3, default_deadline_s=5.0); svc.rt.world.faults["query_inventory"] = "timeout"; obs = {}; t0 = time.perf_counter()
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        r = c.get("/v1/inventory/goat?location_id=L01", headers=auth(keys)); e = r.json()["error"]
        obs = {"status": r.status_code, "code": e["code"], "attempts": e["details"]["attempts"], "actions": e["details"]["policy_actions"], "policy_failure_class": e["details"]["policy_failure_class"], "client_retry": e["client_retry"]}
        obs["within_deadline"] = (time.perf_counter() - t0) < 5.0
    ok = obs["status"] == 504 and obs["code"] == "TOOL_TIMEOUT" and obs["attempts"] == 3 and obs["actions"][:2] == ["RETRY", "RETRY"] and obs["within_deadline"]
    record("F08", "tool timeout", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


def test_F09_upstream_500_retry_then_breaker_then_recovery(migrated_db, keys, svc, tmp_path):
    exp = ("A tool that always raises (upstream 500): 502 UPSTREAM_FAILURE after 3 attempts; consecutive failures open the per-tool circuit breaker, after which calls fail fast with 503 DEPENDENCY_UNAVAILABLE and ZERO attempts; "
           "a transient fault that clears after 2 failures is absorbed (200 with attempts=3); the retry budget is respected.")
    s = make_settings(migrated_db, keys, str(tmp_path)); obs = {}; t0 = time.perf_counter(); calls = []
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        svc.rt.world.faults["query_inventory"] = "error"; h = auth(keys)
        r = c.get("/v1/inventory/goat?location_id=L01", headers=h); e = r.json()["error"]; obs["first"] = [r.status_code, e["code"], e["details"]["attempts"]]
        r = c.get("/v1/inventory/goat?location_id=L01", headers=h); e = r.json()["error"]; obs["second_breaker_open"] = [r.status_code, e["code"], e["details"]["attempts"]]
        svc.rt.world.faults.pop("query_inventory")
        ctx = c.app.state.ctx; ctx.gateway.breaker.opened_at.clear(); ctx.gateway.breaker.fails.clear()
        from nasha_lab import tools as T
        def flaky(w, name, args, cx):
            calls.append(1)
            if len(calls) <= 2: return dict(ok=False, tool=name, permission="READ", error=dict(code="UPSTREAM_FAILURE", message="boom"), data=None, ms=0.1)
            return T.execute(w, name, args, cx)
        ctx.gateway._execute = flaky
        r = c.get("/v1/inventory/goat?location_id=L01", headers=h); obs["transient"] = [r.status_code, r.json().get("attempts")]
        obs["retry_metric"] = ctx.metrics.counter_value("nasha_tool_retries_total", tool="query_inventory")
    ok = obs["first"] == [502, "UPSTREAM_FAILURE", 3] and obs["second_breaker_open"][:2] == [503, "DEPENDENCY_UNAVAILABLE"] and obs["second_breaker_open"][2] == 0 and obs["transient"] == [200, 3]
    record("F09", "upstream 500 (retry, breaker, recovery)", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F10 malformed payloads
def test_F10_malformed_payloads_never_reach_the_database_or_the_agent(app_env):
    exp = "Truncated JSON, invalid UTF-8, wrong types, unknown fields, NUL bytes, wrong media type, oversize body: only 4xx envelopes (400/413/415/422); zero rows written; the agent was never called."
    c, k = app_env.client, app_env.keys; h = {**auth(k, "alice", "BUYER"), **K(), "Content-Type": "application/json"}; obs = {}
    bodies = {"truncated": b'{"event_id": "EV-A', "bad_utf8": b"\xff\xfe", "wrong_type": b'{"event_id": 7}', "unknown_field": b'{"event_id":"EV-A1","x":1}', "nul": b'{"event_id":"EV-A1\\u0000"}', "oversize": b'{"event_id":"' + b"A" * 20000 + b'"}'}
    for name, b in bodies.items():
        r = c.post("/v1/runs", content=b, headers=h); obs[name] = r.status_code
    r = c.post("/v1/runs", content=b"{}", headers={**h, "Content-Type": "text/plain"}); obs["media_type"] = r.status_code
    obs["rows"] = n(app_env.dsn, "SELECT count(*) FROM runs") + n(app_env.dsn, "SELECT count(*) FROM idempotency_keys"); obs["agent_runs"] = agent_runs(app_env.service)
    ok = obs == dict(truncated=400, bad_utf8=400, wrong_type=422, unknown_field=422, nul=422, oversize=413, media_type=415, rows=0, agent_runs=0)
    record("F10", "malformed payloads", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F11 schema drift
def test_F11_schema_older_than_the_app(fresh_db, keys, svc, tmp_path):
    exp = ("Database migrated only to version 1 (app needs 3): /readyz 503 SCHEMA_MISMATCH naming SCHEMA_OLDER; a DB-backed request returns 503 SCHEMA_MISMATCH (never a 500 with SQL details) if the missing objects are hit; "
           "after the migration job runs the app becomes ready without restart.")
    Migrator(fresh_db).up(target=1); s = make_settings(fresh_db, keys, str(tmp_path)); obs = {}; t0 = time.perf_counter()
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        rz = c.get("/readyz"); obs["readyz"] = [rz.status_code, rz.json()["error"]["code"], rz.json()["error"]["details"]["checks"]["schema"]["detail"][:12]]
        with psycopg.connect(fresh_db, autocommit=True) as cn: cn.execute("ALTER TABLE runs RENAME COLUMN owner TO owner_old")        # simulate an incompatible older schema
        r = c.get("/v1/runs", headers=auth(keys, "alice", "READER")); obs["request_on_incompatible_schema"] = [r.status_code, r.json()["error"]["code"]]
        with psycopg.connect(fresh_db, autocommit=True) as cn: cn.execute("ALTER TABLE runs RENAME COLUMN owner_old TO owner")
        Migrator(fresh_db).up(); c.app.state.ctx.ready_cache = None; time.sleep(0.1)
        obs["ready_after_migrate"] = c.get("/readyz").status_code
    ok = obs["readyz"] == [503, "SCHEMA_MISMATCH", "SCHEMA_OLDER"] and obs["request_on_incompatible_schema"] == [503, "SCHEMA_MISMATCH"] and obs["ready_after_migrate"] == 200
    record("F11a", "schema drift: database older than the app", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


def test_F11_schema_newer_than_the_app(fresh_db, keys, svc, tmp_path):
    exp = "Database migrated beyond the build (extra additive migration 4): /readyz 503 SCHEMA_MISMATCH naming SCHEMA_NEWER; with allow_newer_schema=true (explicit rollback-compat switch) the same build is ready and serves requests."
    d = tmp_path / "m"; shutil.copytree(MIG_DIR, d); (d / "0004_extra.up.sql").write_text("ALTER TABLE runs ADD COLUMN extra text;\n"); (d / "0004_extra.down.sql").write_text("ALTER TABLE runs DROP COLUMN extra;\n")
    Migrator(fresh_db, str(d)).up(); obs = {}
    with TestClient(create_hardened_app(make_settings(fresh_db, keys, str(tmp_path / "a")), service=svc), raise_server_exceptions=False) as c:
        rz = c.get("/readyz"); obs["strict"] = [rz.status_code, rz.json()["error"]["code"], rz.json()["error"]["details"]["checks"]["schema"]["detail"][:12]]
    with TestClient(create_hardened_app(make_settings(fresh_db, keys, str(tmp_path / "b"), allow_newer_schema=True), service=new_service(svc.rt.kb)), raise_server_exceptions=False) as c:
        obs["compat_ready"] = c.get("/readyz").status_code; obs["compat_request"] = start(c, keys).status_code
    ok = obs["strict"] == [503, "SCHEMA_MISMATCH", "SCHEMA_NEWER"] and obs["compat_ready"] == 200 and obs["compat_request"] == 201
    record("F11b", "schema drift: database newer than the app", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F12 partial transaction
def test_F12a_crash_between_two_writes_in_one_transaction_is_atomic(app_env, monkeypatch):
    exp = "The audit insert (second write of the start transaction) fails after the runs insert: neither row, nor the idempotency row, exists; the response is a 5xx envelope; a retry with the same key then succeeds once."
    from psycopg import errors as pgerr
    orig = ST.audit; calls = {"n": 0}
    def boom(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 1: raise pgerr.DiskFull("simulated failure between two writes")
        return orig(*a, **kw)
    monkeypatch.setattr(ST, "audit", boom); key = K(); c, k = app_env.client, app_env.keys; obs = {}
    r = start(c, k, "EV-A1", key); obs["first"] = r.status_code
    obs["after_failure_rows"] = {"runs": n(app_env.dsn, "SELECT count(*) FROM runs"), "audit": n(app_env.dsn, "SELECT count(*) FROM audit_log"), "idempotency": n(app_env.dsn, "SELECT count(*) FROM idempotency_keys")}
    r = start(c, k, "EV-A1", key); obs["retry"] = [r.status_code, r.json().get("reconciled")]
    obs["after_retry_rows"] = {"runs": n(app_env.dsn, "SELECT count(*) FROM runs"), "audit": n(app_env.dsn, "SELECT count(*) FROM audit_log")}; obs["agent_runs"] = agent_runs(app_env.service)
    ok = obs["first"] >= 500 and obs["after_failure_rows"] == dict(runs=0, audit=0, idempotency=0) and obs["retry"] == [201, True] and obs["after_retry_rows"] == dict(runs=1, audit=1) and obs["agent_runs"] == 1
    record("F12a", "partial transaction: crash between two writes", exp, obs, ok); assert ok, json.dumps(obs, default=str)


def test_F12b_effect_executed_but_not_recorded_dead_letters_and_reconciles_without_double_execution(app_env):
    exp = ("The approval executes in the agent, then the database write fails: 500 DECISION_AMBIGUOUS (not a silent success), the transaction rolls back (no approvals row, run still awaiting in the DB), a dead letter "
           "(HUMAN_REVIEW_REQUIRED) is stored; retrying with the SAME key returns 409 CONFLICT_STATE 'reconciled', syncs the run row to the agent state and does NOT execute the approval again.")
    c, k = app_env.client, app_env.keys; rid = start(c, k).json()["run_id"]; ctx = app_env.app.state.ctx; obs = {}; key = K(); h = {**auth(k, "carol", "FOUNDER"), **key}
    def hook(): raise psycopg.OperationalError("simulated connection loss after the effect")
    ctx.after_effect_hook = hook
    r = c.post(f"/v1/runs/{rid}/approve", json={"note": "ok"}, headers=h); obs["first"] = [r.status_code, r.json()["error"]["code"], r.json()["error"]["client_retry"]]
    ctx.after_effect_hook = None
    obs["db_after"] = {"approvals": n(app_env.dsn, "SELECT count(*) FROM approvals"), "awaiting_in_db": n(app_env.dsn, "SELECT awaiting_human FROM runs WHERE run_id=%s", rid), "idempotency_rows": n(app_env.dsn, "SELECT count(*) FROM idempotency_keys WHERE key=%s", key["Idempotency-Key"])}
    obs["agent_decided"] = not app_env.service.summary(rid)["awaiting_human"]
    obs["dead_letters"] = n(app_env.dsn, "SELECT count(*) FROM dead_letters WHERE op_class='HUMAN_REVIEW_REQUIRED' AND run_id=%s", rid)
    ev_before = len(app_env.service.store.events(rid))
    r = c.post(f"/v1/runs/{rid}/approve", json={"note": "ok"}, headers=h); obs["retry"] = [r.status_code, r.json()["error"]["code"]]
    obs["after_retry"] = {"awaiting_in_db": n(app_env.dsn, "SELECT awaiting_human FROM runs WHERE run_id=%s", rid), "status": n(app_env.dsn, "SELECT status FROM runs WHERE run_id=%s", rid), "approvals": n(app_env.dsn, "SELECT count(*) FROM approvals"),
                          "reconcile_audit_rows": n(app_env.dsn, "SELECT count(*) FROM audit_log WHERE action='run.reconcile'")}
    obs["not_executed_twice"] = len(app_env.service.store.events(rid)) == ev_before
    ok = obs["first"] == [500, "DECISION_AMBIGUOUS", "after_human_review"] and obs["db_after"] == dict(approvals=0, awaiting_in_db=True, idempotency_rows=0) and obs["agent_decided"] and obs["dead_letters"] == 1 \
        and obs["retry"] == [409, "CONFLICT_STATE"] and obs["after_retry"] == dict(awaiting_in_db=False, status="COMPLETED", approvals=0, reconcile_audit_rows=1) and obs["not_executed_twice"]
    record("F12b", "partial transaction: effect executed, record failed", exp, obs, ok); assert ok, json.dumps(obs, default=str)


def test_F12c_dead_letter_is_spooled_when_the_database_is_the_failure_and_replayed_later(migrated_db, proxy, keys, svc, tmp_path):
    exp = ("If the database is down when the ambiguity is detected, the dead letter goes to the local JSONL spool (never lost, never fabricated as success); once the database is back /readyz replays the spool "
           "into dead_letters (keyed by dl_id, so replay is idempotent) and the spool file is retired.")
    dsn = proxy.dsn(dbname(migrated_db)); s = make_settings(dsn, keys, str(tmp_path), db_pool_timeout_s=0.5, db_breaker_reset_s=1.0); obs = {}
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        rid = start(c, keys).json()["run_id"]; ctx = c.app.state.ctx
        def hook(): proxy.set_mode("down"); raise psycopg.OperationalError("connection lost")
        ctx.after_effect_hook = hook
        r = c.post(f"/v1/runs/{rid}/approve", json={}, headers={**auth(keys, "carol", "FOUNDER"), **K()}); obs["first"] = [r.status_code, r.json()["error"]["code"]]
        ctx.after_effect_hook = None
        import os
        obs["spool_exists"] = os.path.exists(ctx.spool.path); obs["spooled_metric"] = ctx.metrics.counter_value("nasha_dead_letter_spooled_total")
        proxy.set_mode("pass"); time.sleep(1.3); replayed = False
        for _ in range(30):
            ctx.ready_cache = None
            if c.get("/readyz").status_code == 200 and not os.path.exists(ctx.spool.path): replayed = True; break
            time.sleep(0.5)
        obs["spool_replayed"] = replayed; obs["dead_letters_in_db"] = n(migrated_db, "SELECT count(*) FROM dead_letters WHERE run_id=%s", rid)
    ok = obs["first"][1] in ("DECISION_AMBIGUOUS",) and obs["spool_exists"] and obs["spooled_metric"] == 1 and obs["spool_replayed"] and obs["dead_letters_in_db"] == 1
    record("F12c", "dead letter while the database is down (spool and replay)", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F13 migration failure
def test_F13_migration_failure_leaves_the_old_version_serving(fresh_db, keys, svc, tmp_path):
    exp = ("A migration whose 2nd statement fails is rolled back completely (table and version unchanged), the migration CLI exits non-zero with a clear message, and an app already running against the old schema "
           "keeps reporting its real state: the build that needs the new schema is not ready (SCHEMA_OLDER), nothing is half-applied.")
    d = tmp_path / "m"; shutil.copytree(MIG_DIR, d); Migrator(fresh_db).up(); (d / "0004_bad.up.sql").write_text("CREATE TABLE half (id int);\nINSERT INTO nope VALUES (1);\n"); (d / "0004_bad.down.sql").write_text("DROP TABLE half;\n"); obs = {}
    from nasha_lab.service import migrations as M
    import os; os.environ["NASHA_SVC_MIGRATE_DSN"] = fresh_db
    try:
        mig = M.Migrator(fresh_db, str(d))
        with pytest.raises(M.MigrationError) as e: mig.up()
    finally: os.environ.pop("NASHA_SVC_MIGRATE_DSN")
    obs["error_kind"] = e.value.kind; obs["half_table_exists"] = n(fresh_db, "SELECT to_regclass('half') IS NOT NULL"); obs["version"] = mig.status()["current"]
    with TestClient(create_hardened_app(make_settings(fresh_db, keys, str(tmp_path / "a")), service=svc), raise_server_exceptions=False) as c: obs["old_build_ready"] = c.get("/readyz").status_code
    ok = obs == dict(error_kind="MIGRATION_FAILED", half_table_exists=False, version=3, old_build_ready=200)
    record("F13", "migration failure", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F14 configuration error
def test_F14_configuration_errors_fail_fast_with_no_secret_in_the_message(monkeypatch, capsys):
    exp = "Bad values, missing secrets, weak keys, unknown (typo) settings, unreadable secret files: ConfigError / process exit 78 within one call; the message names the setting and reason and never contains a secret."
    import secrets as sec
    from nasha_lab.service.config import ConfigError, load_settings
    from nasha_lab.service import serve
    pw, key = sec.token_hex(8), sec.token_hex(32); base = {"NASHA_SVC_DATABASE_URL": f"postgresql://u:{pw}@h/d", "NASHA_SVC_JWT_KEYS": json.dumps({"k1": key}), "NASHA_SVC_JWT_ACTIVE_KID": "k1"}; obs = {}; msgs = []
    bad = {"pool_zero": {"NASHA_SVC_DB_POOL_MAX": "0"}, "typo": {"NASHA_SVC_JWT_ISUER": "x"}, "kid_missing": {"NASHA_SVC_JWT_ACTIVE_KID": "k9"}, "weak_key": {"NASHA_SVC_JWT_KEYS": json.dumps({"k1": "weak"})}, "dsn_scheme": {"NASHA_SVC_DATABASE_URL": "mysql://x"},
           "staging_dev_issuer": {"NASHA_SVC_ENV": "staging", "NASHA_SVC_DEV_TOKEN_ISSUER": "true"}, "missing_secret_file": {"NASHA_SVC_JWT_KEYS": None, "NASHA_SVC_JWT_KEYS_FILE": "/nonexistent/keys"}}
    for name, over in bad.items():
        e = {k: v for k, v in {**base, **over}.items() if v is not None}
        try: load_settings(e); obs[name] = "ACCEPTED"
        except ConfigError as x: obs[name] = "rejected"; msgs.append(str(x))
    obs["secret_in_any_message"] = any(pw in m or key in m for m in msgs)
    for k2, v2 in {**base, "NASHA_SVC_DB_POOL_MAX": "0"}.items(): monkeypatch.setenv(k2, v2)
    with pytest.raises(SystemExit) as ex: serve.app()
    obs["exit_code"] = ex.value.code; obs["stderr_has_secret"] = pw in capsys.readouterr().err
    ok = all(v == "rejected" for k, v in obs.items() if k in bad) and not obs["secret_in_any_message"] and obs["exit_code"] == 78 and not obs["stderr_has_secret"]
    record("F14", "configuration error", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F15 NUL byte in free text (found by the security suite)
def test_F15_nul_byte_in_free_text_is_rejected_before_any_effect(app_env):
    exp = "A NUL byte in a decision note is rejected at validation (422 INVALID_REQUEST) before the agent is resumed: the run stays awaiting in both the agent and the database, no dead letter is created."
    c, k = app_env.client, app_env.keys; rid = start(c, k).json()["run_id"]
    r = c.post(f"/v1/runs/{rid}/approve", json={"note": "ok\u0000bad"}, headers={**auth(k, "carol", "FOUNDER"), **K()}); obs = {"status": r.status_code, "code": r.json()["error"]["code"]}
    obs["agent_still_awaiting"] = app_env.service.summary(rid)["awaiting_human"]; obs["dead_letters"] = n(app_env.dsn, "SELECT count(*) FROM dead_letters")
    ok = obs == dict(status=422, code="INVALID_REQUEST", agent_still_awaiting=True, dead_letters=0)
    record("F15", "NUL byte in free text", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F16 deadlines and cancellation
def test_F16_deadline_exceeded_does_not_commit_and_the_retry_reconciles(migrated_db, keys, svc, tmp_path, monkeypatch):
    exp = ("The agent step takes 1.2 s but the route deadline is 0.6 s: the client gets 504 DEADLINE_EXCEEDED (advice: retry with the same key); the worker is told to stop, so when it finishes the transaction ROLLS BACK "
           "(no runs row, no idempotency row); the SAME key then succeeds with reconciled=true and the agent has exactly one run for the event.")
    s = make_settings(migrated_db, keys, str(tmp_path), run_deadline_s=0.6, tool_timeout_s=0.3); orig = svc.start; obs = {}; t0 = time.perf_counter()
    def slow(*a, **k): time.sleep(1.2); return orig(*a, **k)
    monkeypatch.setattr(svc, "start", slow); key = K()
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        t1 = time.perf_counter(); r = start(c, keys, "EV-A1", key); obs["first"] = [r.status_code, r.json()["error"]["code"], r.json()["error"]["client_retry"]]; obs["answered_near_deadline"] = (time.perf_counter() - t1) < 1.1
        time.sleep(1.5)           # let the abandoned worker finish
        obs["after_worker_finished"] = {"runs": n(migrated_db, "SELECT count(*) FROM runs"), "idempotency": n(migrated_db, "SELECT count(*) FROM idempotency_keys"), "agent_runs": agent_runs(svc)}
        monkeypatch.setattr(svc, "start", orig)
        r = start(c, keys, "EV-A1", key); obs["retry"] = [r.status_code, r.json().get("reconciled")]; obs["agent_runs_after_retry"] = agent_runs(svc); obs["runs_after_retry"] = n(migrated_db, "SELECT count(*) FROM runs")
    ok = obs["first"] == [504, "DEADLINE_EXCEEDED", "same_idempotency_key"] and obs["answered_near_deadline"] and obs["after_worker_finished"] == dict(runs=0, idempotency=0, agent_runs=1) \
        and obs["retry"] == [201, True] and obs["agent_runs_after_retry"] == 1 and obs["runs_after_retry"] == 1
    record("F16", "request deadline exceeded mid-work (cancellation and rollback)", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


def test_F16b_a_saturated_worker_pool_sheds_queued_work_it_can_no_longer_answer(migrated_db, keys, svc, tmp_path, monkeypatch):
    exp = ("One worker thread, three concurrent starts for different events, each agent step 1.0 s, deadline 1.5 s: one request completes (201); the other two answer 504 within the deadline; the queued one is cancelled before it "
           "starts so it creates NO agent run (agent runs = 2: one recorded, one executed-but-rolled-back), runs rows = 1.")
    s = make_settings(migrated_db, keys, str(tmp_path), worker_threads=1, run_deadline_s=1.5, tool_timeout_s=0.3); orig = svc.start; obs = {}
    def slow(*a, **k): time.sleep(1.0); return orig(*a, **k)
    monkeypatch.setattr(svc, "start", slow)
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        with cf.ThreadPoolExecutor(3) as ex: fs = [ex.submit(start, c, keys, ev) for ev in ("EV-A1", "EV-A2", "EV-B1")]; rs = [f.result() for f in fs]
        obs["statuses"] = sorted(r.status_code for r in rs); obs["error_codes"] = sorted(r.json()["error"]["code"] for r in rs if r.status_code != 201)
        time.sleep(2.5)
        obs["runs_rows"] = n(migrated_db, "SELECT count(*) FROM runs"); obs["agent_runs"] = agent_runs(svc)
    ok = obs == dict(statuses=[201, 504, 504], error_codes=["DEADLINE_EXCEEDED", "DEADLINE_EXCEEDED"], runs_rows=1, agent_runs=2)
    record("F16b", "worker pool saturation (queued work is cancelled, not run late)", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F18 graceful shutdown on a real server socket
def test_F18_graceful_shutdown_finishes_the_inflight_request_and_refuses_new_ones(migrated_db, keys, svc, tmp_path):
    exp = ("With a real uvicorn server: SIGTERM-equivalent (should_exit) while a 1 s request is in flight -> that request still returns 200; the lifespan shutdown drains (readiness 503 SHUTTING_DOWN for probes during the drain), "
           "waits for in-flight=0 and closes the pool; the server thread exits within shutdown_grace_s.")
    import socket, uvicorn, httpx
    s = make_settings(migrated_db, keys, str(tmp_path), shutdown_grace_s=5.0); app = create_hardened_app(s, service=svc); ctx = app.state.ctx; orig = ctx.gateway.call; obs = {}
    def slow(*a, **k): time.sleep(1.0); return orig(*a, **k)
    ctx.gateway.call = slow
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on", timeout_graceful_shutdown=8))
    th = threading.Thread(target=srv.run, daemon=True); th.start()
    for _ in range(100):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=1).status_code == 200: break
        except Exception: time.sleep(0.1)
    res = {}
    def inflight(): res["r"] = httpx.get(f"http://127.0.0.1:{port}/v1/inventory/goat?location_id=L01", headers=auth(keys), timeout=10)
    t = threading.Thread(target=inflight); t.start(); time.sleep(0.3)
    t0 = time.perf_counter(); srv.should_exit = True; t.join(); th.join(timeout=10)
    obs["inflight_status"] = res["r"].status_code; obs["server_stopped"] = not th.is_alive(); obs["drained_flag_set"] = ctx.rt.draining; obs["inflight_at_exit"] = ctx.rt.inflight
    obs["pool_closed"] = ctx.db.pool.closed
    ok = obs == dict(inflight_status=200, server_stopped=True, drained_flag_set=True, inflight_at_exit=0, pool_closed=True)
    record("F18", "graceful shutdown with an in-flight request", exp, obs, ok, (time.perf_counter() - t0) * 1000); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F19 metrics while the database is down
def test_F19_metrics_and_liveness_survive_a_database_outage(migrated_db, proxy, keys, svc, tmp_path):
    exp = "While the database is unreachable /healthz is 200 and /metrics (OPERATOR token) is still 200 with nasha_db_up 0; after recovery nasha_db_up is 1. Operators can see the outage in the metrics that the outage affects."
    dsn = proxy.dsn(dbname(migrated_db)); s = make_settings(dsn, keys, str(tmp_path), db_pool_timeout_s=0.5, db_breaker_reset_s=1.0); obs = {}
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        h = auth(keys, "ops", "OPERATOR"); assert c.get("/metrics", headers=h).status_code == 200
        proxy.set_mode("down"); r = c.get("/metrics", headers=h); obs["down"] = [r.status_code, "nasha_db_up 0" in r.text, c.get("/healthz").status_code]
        proxy.set_mode("pass"); time.sleep(1.3); up = False
        for _ in range(20):
            if "nasha_db_up 1" in c.get("/metrics", headers=h).text: up = True; break
            time.sleep(0.5)
        obs["recovered"] = up
    ok = obs["down"] == [200, True, 200] and obs["recovered"]
    record("F19", "metrics and liveness during a database outage", exp, obs, ok); assert ok, json.dumps(obs, default=str)


# ------------------------------------------------------------------------------------------------ F20..F23: weaknesses found by review, each with a failing-first test
def raw_request(app, method, path, headers=None):
    import asyncio
    sent = []
    async def go():
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "path": path, "raw_path": path.encode(), "query_string": b"", "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
                 "client": ("203.0.113.7", 1), "server": ("t", 80), "scheme": "http", "state": {}}
        async def receive(): return {"type": "http.request", "body": b"", "more_body": False}
        async def send(m): sent.append(m)
        await app(scope, receive, send)
    asyncio.run(go()); st = next(m for m in sent if m["type"] == "http.response.start")
    return st["status"], {k.decode(): v.decode() for k, v in st["headers"]}


def test_F20_expired_idempotency_keys_are_purged(app_env):
    exp = "Expired idempotency rows do not accumulate: after their expiry passes, the maintenance task removes them (count returns to 0) while unexpired rows remain."
    c, k = app_env.client, app_env.keys; assert start(c, k, "EV-A1").status_code == 201 and start(c, k, "EV-A2").status_code == 201
    with psycopg.connect(app_env.dsn, autocommit=True) as cn: cn.execute("UPDATE idempotency_keys SET expires_at = now() - interval '1 hour' WHERE response_body->>'event_id' = 'EV-A1'")
    ctx = app_env.app.state.ctx; purged = ctx.run_maintenance() if hasattr(ctx, "run_maintenance") else -1
    obs = {"purged": purged, "rows_left": n(app_env.dsn, "SELECT count(*) FROM idempotency_keys"), "expired_left": n(app_env.dsn, "SELECT count(*) FROM idempotency_keys WHERE expires_at <= now()")}
    ok = obs == dict(purged=1, rows_left=1, expired_left=0)
    record("F20", "idempotency table grows without bound (expired keys never deleted)", exp, obs, ok); assert ok, json.dumps(obs)


def test_F21_unknown_http_methods_cannot_inflate_metric_label_cardinality(app_env):
    exp = "Requests with arbitrary (attacker-chosen) HTTP method tokens produce at most one extra metric series ('OTHER'), not one series per distinct method."
    before = len(app_env.app.state.ctx.metrics.counters["nasha_http_requests_total"])
    for i in range(40): raw_request(app_env.app, "ZZ" + str(i), "/healthz")
    after = len(app_env.app.state.ctx.metrics.counters["nasha_http_requests_total"])
    obs = {"new_series_after_40_distinct_methods": after - before}
    ok = obs["new_series_after_40_distinct_methods"] <= 1
    record("F21", "metric label cardinality (method)", exp, obs, ok); assert ok, json.dumps(obs)


def test_F22_trailing_slash_does_not_redirect_before_authentication(app_env):
    exp = "GET /v1/events/ (trailing slash) without a token answers the 404 route envelope, never a 307 redirect that skips the error contract."
    r = app_env.client.get("/v1/events/", follow_redirects=False); obs = {"status": r.status_code, "code": (r.json().get("error") or {}).get("code") if r.headers.get("content-type", "").startswith("application/json") else None}
    ok = obs == dict(status=404, code="ROUTE_NOT_FOUND")
    record("F22", "trailing-slash redirect outside the error contract", exp, obs, ok); assert ok, json.dumps(obs)


def test_F23_readiness_does_not_disclose_versions_or_internal_detail_to_anonymous_callers(app_env, pg_admin_dsn, keys, svc, tmp_path):
    exp = "The public /readyz body (healthy and unhealthy) contains no schema version numbers, database codes or exception names: only per-check ok flags and coarse words."
    from conftest import _swap_db
    ok_body = app_env.client.get("/readyz").text; name = "p5_" + uuid.uuid4().hex[:10]
    with psycopg.connect(pg_admin_dsn, autocommit=True) as cn: cn.execute(f'CREATE DATABASE "{name}"')
    try:
        old = _swap_db(pg_admin_dsn, name); Migrator(old).up(target=1)
        with TestClient(create_hardened_app(make_settings(old, keys, str(tmp_path)), service=new_service(svc.rt.kb)), raise_server_exceptions=False) as c: bad_body = c.get("/readyz").text
    finally:
        with psycopg.connect(pg_admin_dsn, autocommit=True) as cn: cn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    import re
    obs = {"healthy_has_digits_version": bool(re.search(r"version\W+\d", ok_body)) or "schema_version" in ok_body, "unhealthy_has_numbers": bool(re.search(r"database \d|needs \d|version \d", bad_body)), "unhealthy_names_direction": "SCHEMA_OLDER" in bad_body}
    ok = obs == dict(healthy_has_digits_version=False, unhealthy_has_numbers=False, unhealthy_names_direction=True)
    record("F23", "readiness information disclosure", exp, obs, ok); assert ok, json.dumps(obs) + bad_body[:500]


def test_F20b_the_background_maintenance_task_purges_without_being_called(migrated_db, keys, svc, tmp_path):
    exp = "With maintenance_interval_s=0.5 an expired idempotency row disappears by itself within a few seconds, and the task stops at shutdown without error."
    s = make_settings(migrated_db, keys, str(tmp_path), maintenance_interval_s=0.5); obs = {}
    with TestClient(create_hardened_app(s, service=svc), raise_server_exceptions=False) as c:
        assert start(c, keys).status_code == 201
        with psycopg.connect(migrated_db, autocommit=True) as cn: cn.execute("UPDATE idempotency_keys SET expires_at = now() - interval '1 minute'")
        gone = False
        for _ in range(20):
            if n(migrated_db, "SELECT count(*) FROM idempotency_keys") == 0: gone = True; break
            time.sleep(0.25)
        obs["purged_by_background_task"] = gone
    ok = gone
    record("F20b", "background maintenance purges expired idempotency keys", exp, obs, ok); assert ok, json.dumps(obs)
