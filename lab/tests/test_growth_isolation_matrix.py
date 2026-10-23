"""Tenant-isolation matrix beyond the service layer: HTTP API, database (RLS on every tenant table), agent tools, workflow state, approvals, audit records and evidence exports, with cross-tenant
identifiers and manipulated requests. Two synthetic tenants with coherent data (the demo scenarios). SYNTHETIC data only."""
import json
import re
from pathlib import Path

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, demo as DM, schema as S, service as SV

A, B = "tenant-nasha", "tenant-fit"
LAB = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import pixeltable_pgserver as pg
    root = tmp_path_factory.mktemp("giso")
    try:
        srv = pg.get_server(str(root / "pg"), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    dsn = srv.get_uri()
    envs = DM.build(root / "d", dsn, schema="growth_iso", with_warehouse=False)
    yield TestClient(GA.create_growth_app(envs)), envs, dsn
    srv.cleanup()


def H(envs, tenant, user="ada", **x):
    return {"Authorization": "Bearer " + envs[tenant].authority.login(user, f"{tenant}-{user}-dev-passcode"), **x}


def get(c, envs, tenant, path, user="ada"):
    return c.get(f"/v1/tenants/{tenant}{path}", headers=H(envs, tenant, user))


def ids_of(c, envs, tenant, path, key="id"):
    return [i[key] for i in get(c, envs, tenant, path).json()["items"]]


# ---------------------------------------------------------------- HTTP API
def test_every_by_id_read_and_write_endpoint_treats_the_other_tenants_identifiers_as_not_found(world):
    c, envs, _ = world
    other = dict(lead=ids_of(c, envs, B, "/leads?limit=50", "lead_id")[0], account=ids_of(c, envs, B, "/accounts?limit=50")[0], opp=ids_of(c, envs, B, "/opportunities?limit=50")[0],
                 contact=ids_of(c, envs, B, "/contacts?limit=50")[0], run=ids_of(c, envs, B, "/workflows/runs?limit=50")[0])
    h = H(envs, A, "ada")
    base = f"/v1/tenants/{A}"
    reqs = [("GET", f"/leads/{other['lead']}", None), ("GET", f"/accounts/{other['account']}", None), ("GET", f"/workflows/runs/{other['run']}", None),
            ("POST", f"/leads/{other['lead']}/convert", {"opportunity_name": "x", "amount_cents": 1}), ("POST", f"/opportunities/{other['opp']}/stage", {"to_stage": "qualified"}),
            ("PUT", f"/contacts/{other['contact']}/consent", {"status": "opt_in"}), ("POST", f"/workflows/runs/{other['run']}/decision", {"approve": True}),
            ("POST", "/workflows/lead-qualification", {"lead_id": other["lead"]}), ("POST", "/contacts", {"account_id": other["account"], "full_name": "x", "email": "x@example.invalid"}),
            ("POST", "/leads", {"contact_id": other["contact"], "source": "synthetic-x"}), ("POST", "/activities", {"kind": "note", "body": "x", "opportunity_id": other["opp"]})]
    for m, p, body in reqs:
        r = c.request(m, base + p, json=body, headers={**h, "Idempotency-Key": "iso-" + re.sub(r"\W", "", p)[:50].ljust(12, "x")}) if body is not None else c.request(m, base + p, headers=h)
        assert r.status_code in (404, 409, 422), (m, p, r.status_code, r.text[:120])
        assert not any(v in r.text for v in other.values()), (m, p, "the other tenant's identifier must not be echoed back")
    assert get(c, envs, B, f"/leads/{other['lead']}").json()["status"] in ("new", "qualified", "disqualified", "converted")


def test_list_endpoints_return_only_own_tenant_rows_and_cursors_cannot_cross(world):
    c, envs, _ = world
    own = {p: set(ids_of(c, envs, A, p)) for p in ("/accounts?limit=50", "/contacts?limit=50", "/opportunities?limit=50", "/activities?limit=50", "/products?limit=50")}
    oth = {p: set(ids_of(c, envs, B, p)) for p in own}
    for p in own:
        assert own[p].isdisjoint(oth[p]), p
    assert set(ids_of(c, envs, A, "/leads?limit=50", "lead_id")).isdisjoint(ids_of(c, envs, B, "/leads?limit=50", "lead_id"))
    assert {r["id"] for r in get(c, envs, A, "/workflows/runs?limit=50").json()["items"]}.isdisjoint({r["id"] for r in get(c, envs, B, "/workflows/runs?limit=50").json()["items"]})
    assert get(c, envs, A, "/accounts?limit=2&cursor=999999").json()["items"] == []
    assert get(c, envs, A, "/accounts?cursor=abc").status_code == 422


def test_manipulated_requests_cannot_change_the_tenant(world):
    c, envs, _ = world
    tokA = H(envs, A)
    assert c.get(f"/v1/tenants/{B}/accounts", headers=tokA).status_code == 401, "a token from tenant A is not valid for tenant B"
    assert c.get(f"/v1/tenants/{A}/accounts", headers={**tokA, "X-Tenant-Id": B, "X-Tenant": B, "X-Forwarded-Tenant": B}).json()["items"][0]["id"] in ids_of(c, envs, A, "/accounts?limit=50")
    assert c.get(f"/v1/tenants/{A}/accounts?tenant={B}&tenant_id={B}&app.tenant_id={B}", headers=tokA).status_code == 200
    r = c.post(f"/v1/tenants/{A}/accounts", json={"name": "Smuggled", "tenant_id": B}, headers={**tokA, "Idempotency-Key": "smuggle-key-1"})
    assert r.status_code == 422
    assert c.get(f"/v1/tenants/{A}/accounts/%27%3B%20SET%20app.tenant_id%3D%27{B}", headers=tokA).status_code in (404, 422)
    assert c.get(f"/v1/tenants/{B}/me", headers=tokA).status_code == 401 and c.get(f"/v1/tenants/unknown-tenant/me", headers=tokA).status_code == 401


def test_the_same_idempotency_key_in_two_tenants_never_returns_the_other_tenants_response(world):
    c, envs, _ = world
    key = "shared-key-123456"
    r1 = c.post(f"/v1/tenants/{A}/accounts", json={"name": "Iso Alpha Org"}, headers={**H(envs, A, "sam"), "Idempotency-Key": key})
    r2 = c.post(f"/v1/tenants/{B}/accounts", json={"name": "Iso Beta Org"}, headers={**H(envs, B, "sam"), "Idempotency-Key": key})
    assert r1.status_code == r2.status_code == 201 and r1.json()["id"] != r2.json()["id"]
    assert "Iso Beta Org" not in {a["name"] for a in get(c, envs, A, "/accounts?limit=50").json()["items"]}


# ---------------------------------------------------------------- database
def test_row_level_security_is_forced_on_every_tenant_table_and_an_unset_tenant_sees_nothing(world):
    c, envs, dsn = world
    with psycopg.connect(SV.app_dsn(dsn), autocommit=True) as con:
        con.execute('SET search_path TO "growth_iso", pg_catalog, public')
        for t in S.ALL_TENANT_TABLES:
            assert con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] == 0, f"{t}: a session with no tenant set must see no rows"
        con.execute("SELECT set_config('app.tenant_id', %s, false)", (A,))
        for t in S.ALL_TENANT_TABLES:
            assert con.execute(f"SELECT count(*) FROM {t} WHERE tenant_id<>%s", (A,)).fetchone()[0] == 0, t
    with psycopg.connect(dsn, autocommit=True) as adm:
        adm.execute('SET search_path TO "growth_iso", pg_catalog, public')
        rows = adm.execute("SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='growth_iso' AND c.relname = ANY(%s)", (list(S.ALL_TENANT_TABLES),)).fetchall()
        assert len(rows) == len(S.ALL_TENANT_TABLES) and all(r[1] and r[2] for r in rows)


def test_a_tenant_cannot_write_or_audit_into_another_tenant_even_with_raw_sql(world):
    c, envs, dsn = world
    s = SV.GrowthService(dsn, "growth_iso", A, "ada")
    for sql in ("INSERT INTO accounts (tenant_id,id,name,kind) VALUES ('tenant-fit','acc-x','forged','business')", "INSERT INTO audit_log (tenant_id,seq,actor,role,action,decision,detail,prev_hash,hash) VALUES ('tenant-fit',99999,'ada','OWNER','x','allow','{}','a','b')",
                "INSERT INTO workflow_runs (tenant_id,id,workflow,requester,role,lead_id,state) VALUES ('tenant-fit','wf-x','w','ada','OWNER','l','STARTED')"):
        with pytest.raises((psycopg.errors.InsufficientPrivilege, psycopg.errors.ForeignKeyViolation, psycopg.errors.IntegrityConstraintViolation)):
            s.con.execute(sql)
    s.close()


# ---------------------------------------------------------------- agent tools
def test_agent_tools_are_bound_to_one_tenant_and_cannot_read_the_others_lead_or_pipeline(world):
    ap = pytest.importorskip("agentplatform", reason="INTEGRATION UNAVAILABLE: Production AI Agent Platform not installed")
    from nasha_lab.growth import agent_tools as AT
    c, envs, dsn = world
    lead_b = ids_of(c, envs, B, "/leads?limit=50", "lead_id")[0]
    rt = AT.GrowthToolRuntime(SV.GrowthService(dsn, "growth_iso", A, "sam"))
    from agentplatform.orchestrator.executor import ToolFailure
    with pytest.raises(ToolFailure, match="no such lead in this tenant"):
        rt.call("get_lead_context", {"lead_id": lead_b})
    own = rt.call("pipeline_summary", {})
    dash = get(c, envs, A, "/dashboard").json()
    assert json.dumps(own, default=str).count(B) == 0
    assert sum(p["count"] for p in dash["pipeline"]) == sum(x[1] for x in SV.GrowthService(dsn, "growth_iso", A, "ada").read("SELECT stage, count(*) FROM opportunities WHERE tenant_id=%s GROUP BY stage", (A,)))


# ---------------------------------------------------------------- workflow state, approvals, audit
def test_workflow_state_approvals_and_audit_are_per_tenant(world):
    c, envs, _ = world
    run_a = ids_of(c, envs, A, "/workflows/runs?limit=50")
    run_b = ids_of(c, envs, B, "/workflows/runs?limit=50")
    assert run_a and run_b and set(run_a).isdisjoint(run_b)
    pend_a = {p["run_id"] for p in get(c, envs, A, "/approvals?state=pending").json()["items"]}; pend_b = {p["run_id"] for p in get(c, envs, B, "/approvals?state=pending").json()["items"]}
    hist_a = {p["run_id"] for p in get(c, envs, A, "/approvals?state=history").json()["items"]}
    assert pend_a.isdisjoint(pend_b) and hist_a.isdisjoint(run_b)
    aud_a = get(c, envs, A, "/audit?limit=50").json()["items"]; aud_b = get(c, envs, B, "/audit?limit=50").json()["items"]
    ent_b = {a["entity_id"] for a in aud_b if a["entity_id"]}
    assert not ({a["entity_id"] for a in aud_a if a["entity_id"]} & ent_b)
    assert get(c, envs, A, "/audit/verify").json()["chain_valid"] is True and get(c, envs, B, "/audit/verify").json()["chain_valid"] is True
    assert all(a["summary"] for a in aud_a) and not any("Meridian" in a["summary"] or "Kestrel" in a["summary"] for a in aud_a)
    # the other tenant's approver cannot decide this tenant's pending run, even with a valid session of their own
    if pend_a:
        r = c.post(f"/v1/tenants/{A}/workflows/runs/{next(iter(pend_a))}/decision", json={"approve": True}, headers=H(envs, B, "ada"))
        assert r.status_code == 401


# ---------------------------------------------------------------- evidence exports
def test_provenance_and_dashboard_are_scoped_and_the_exported_evidence_contains_no_records_or_credentials(world):
    c, envs, _ = world
    pa, pb = get(c, envs, A, "/provenance").json()["categories"], get(c, envs, B, "/provenance").json()["categories"]
    assert pa["founder_approved"]["prices"] and pb["founder_approved"]["prices"] == []
    assert pa["realistic_synthetic"]["accounts"] != 0 and pb["realistic_synthetic"]["accounts"] != 0
    ev = LAB / "portfolio" / "growth-os-evidence.json"
    if ev.exists():
        txt = ev.read_text()
        assert "@example.invalid" not in txt and "dev-passcode" not in txt and not re.search(r"eyJ[A-Za-z0-9_-]{20,}\.", txt), "no e-mail addresses, passcodes or tokens in the exported evidence"
        d = json.loads(txt)
        trace = d["workflow"]["happy_path"]["trace"]
        assert all(e.get("tenant", "tenant-nasha") == "tenant-nasha" for e in trace)
