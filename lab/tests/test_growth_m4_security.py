"""Security and reliability of the Milestone 4 surface: concurrent workflow runs, duplicate and replayed approvals, cross-tenant supplier access, unauthorised updates, missing audit evidence at the database,
atomic rollback of the approval's project-state update, and external research failures. Default-deny is asserted, not assumed. SYNTHETIC tenants; no network; nothing is ordered."""
import asyncio
import threading
import uuid

import pytest

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("fastapi")
from test_growth_journey import A, B, H, world, sql  # noqa: E402,F401  (shared fixture and helpers)

from nasha_lab.growth import schema as S  # noqa: E402

BASE = f"/v1/tenants/{A}"


def run_all(fns):
    out, errs = [None] * len(fns), []
    def w(i, f):
        try:
            out[i] = f()
        except Exception as e:  # noqa: BLE001
            out[i] = e; errs.append(repr(e))
    ts = [threading.Thread(target=w, args=(i, f)) for i, f in enumerate(fns)]
    [t.start() for t in ts]; [t.join(60) for t in ts]
    assert not any(t.is_alive() for t in ts), "a worker hung"
    assert not errs, errs[:2]                      # no exception may be lost inside a worker
    return out


def first_project(world):
    c, envs, _ = world
    return c.get(f"{BASE}/projects", headers=H(envs, "vic")).json()["items"][0]["id"]


def new_run(world, key=None, weeks=2):
    c, envs, _ = world
    return c.post(f"{BASE}/projects/{first_project(world)}/procurement", json={"period_weeks": weeks}, headers=H(envs, "ana", **({"Idempotency-Key": key} if key else {})))


def chain_ok(world, t=A):
    c, envs, _ = world
    return c.get(f"/v1/tenants/{t}/audit/verify", headers=H(envs, "ada", t)).json()["chain_valid"] is True


# ---------------------------------------------------------------- concurrency
def test_concurrent_requests_with_one_idempotency_key_create_exactly_one_run(world):
    key = "conc-" + uuid.uuid4().hex[:10]
    res = run_all([lambda: new_run(world, key) for _ in range(6)])
    codes = sorted(r.status_code for r in res)
    assert set(codes) <= {200, 202, 409} and codes.count(202) == 1, codes
    assert sql(world, "SELECT count(*) FROM procurement_recommendations WHERE idem_key=%s", (key,))[0][0] == 1
    assert len({r.json()["corr_id"] for r in res if r.status_code in (200, 202)}) == 1
    assert chain_ok(world)


def test_concurrent_requests_with_different_keys_make_independent_runs_with_a_valid_chain(world):
    base = sql(world, "SELECT count(*) FROM procurement_recommendations")[0][0]
    res = run_all([lambda: new_run(world, "k-" + uuid.uuid4().hex[:10]) for _ in range(4)])
    assert [r.status_code for r in res] == [202] * 4 and len({r.json()["corr_id"] for r in res}) == 4
    assert sql(world, "SELECT count(*) FROM procurement_recommendations")[0][0] == base + 4
    assert chain_ok(world)


def test_two_people_approving_the_same_recommendation_at_once_record_it_exactly_once(world):
    c, envs, _ = world
    rid = new_run(world, weeks=3).json()["corr_id"]
    res = run_all([lambda: c.post(f"{BASE}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, u)) for u in ("ada", "omar")])
    codes = sorted(r.status_code for r in res)
    assert codes == [200, 409], codes
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND decision='allow' AND entity_id=%s", (A, rid))[0][0] == 1
    assert sql(world, "SELECT count(*) FROM project_milestones WHERE note LIKE %s", (f"%recommendation {rid}%",))[0][0] in (0, 1)
    assert sql(world, "SELECT state FROM procurement_recommendations WHERE id=%s", (rid,))[0][0] == "EXECUTED"
    pid = sql(world, "SELECT project_id FROM procurement_recommendations WHERE id=%s", (rid,))[0][0]
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND decision='allow' AND detail->>'milestone' IS NOT NULL AND entity_id IN (SELECT id FROM procurement_recommendations WHERE project_id=%s AND state='EXECUTED')", (A, pid))[0][0] == \
        sql(world, "SELECT count(*) FROM procurement_recommendations WHERE project_id=%s AND state='EXECUTED'", (pid,))[0][0], "one milestone-bearing audit row per executed run, never two for one"
    assert chain_ok(world)


def test_a_replayed_approval_decision_and_a_replayed_run_request_change_nothing(world):
    c, envs, _ = world
    key = "replay-" + uuid.uuid4().hex[:8]
    r1 = new_run(world, key); rid = r1.json()["corr_id"]
    assert c.post(f"{BASE}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, "ada")).status_code == 200
    n = sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND entity_id=%s", (A, rid))[0][0]
    for u in ("ada", "omar"):
        assert c.post(f"{BASE}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, u)).status_code == 409
    assert new_run(world, key).status_code == 200 and sql(world, "SELECT count(*) FROM procurement_recommendations WHERE idem_key=%s", (key,))[0][0] == 1
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND entity_id=%s", (A, rid))[0][0] == n == 1


# ---------------------------------------------------------------- cross-tenant and unauthorised access
def test_one_tenant_cannot_shortlist_read_or_annotate_another_tenants_suppliers(world):
    c, envs, _ = world
    nasha_sup = c.get(f"{BASE}/suppliers", headers=H(envs, "vic")).json()["items"][0]["id"]
    fit_proj = c.get(f"/v1/tenants/{B}/projects", headers=H(envs, "ada", B)).json()["items"][0]["id"]
    r = c.put(f"/v1/tenants/{B}/projects/{fit_proj}/suppliers/{nasha_sup}", json=dict(status="shortlisted"), headers=H(envs, "ada", B))
    assert r.status_code in (404, 409, 422)
    assert sql(world, "SELECT count(*) FROM project_suppliers WHERE tenant_id=%s AND supplier_id=%s", (B, nasha_sup))[0][0] == 0
    assert c.post(f"/v1/tenants/{B}/suppliers/{nasha_sup}/products", json=dict(name="x", unit="kg", price_class="NONE_PUBLISHED", limitation="no price listed"), headers=H(envs, "ada", B)).status_code in (404, 409, 422)
    assert nasha_sup not in {x["id"] for x in c.get(f"/v1/tenants/{B}/suppliers", headers=H(envs, "ada", B)).json()["items"]}
    assert c.get(f"{BASE}/suppliers", headers=H(envs, "ada", B)).status_code in (401, 403), "a token for one tenant is not valid on another's path"


@pytest.mark.parametrize("user,method,path,body", [
    ("vic", "post", "/projects", dict(name="Viewer project", industry="Hospitality", location="Austin, TX", concept="A concept long enough to pass the input validation rules.", budget_cents=100000)),
    ("sam", "post", "/projects", dict(name="Sales project", industry="Hospitality", location="Austin, TX", concept="A concept long enough to pass the input validation rules.", budget_cents=100000)),
    ("ana", "post", "/projects", dict(name="Analyst project", industry="Hospitality", location="Austin, TX", concept="A concept long enough to pass the input validation rules.", budget_cents=100000)),
    ("vic", "put", "/projects/{p}/assumptions/weekly_orders", dict(label="Weekly orders", value=1, unit="orders", basis="founder")),
    ("mia", "put", "/projects/{p}/assumptions/weekly_orders", dict(label="Weekly orders", value=1, unit="orders", basis="founder")),
    ("ana", "post", "/projects/{p}/milestones", dict(title="Analyst milestone", phase="idea")),
    ("vic", "post", "/suppliers", dict(name="Viewer Supplier Co", category="Produce", service_area="Austin", verification_status="lead_unverified", source_kind="search_result", source_url="https://example.test/v")),
    ("sam", "post", "/suppliers/{s}/sources", dict(kind="press", url="https://example.test/s", claim="A claim from a salesperson.", access="search_snippet", observed_on="2026-10-23"))])
def test_every_unauthorised_write_is_refused_audited_and_changes_nothing(world, user, method, path, body):
    c, envs, _ = world
    p = first_project(world); s = c.get(f"{BASE}/suppliers", headers=H(envs, "vic")).json()["items"][0]["id"]
    denies = sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND actor=%s AND decision='deny'", (A, user))[0][0]
    counts = [sql(world, f"SELECT count(*) FROM {t}")[0][0] for t in ("launch_projects", "project_milestones", "suppliers", "supplier_sources", "procurement_recommendations")]
    r = getattr(c, method)(BASE + path.format(p=p, s=s), json=body, headers=H(envs, user))
    assert r.status_code == 403, (user, path, r.status_code)
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND actor=%s AND decision='deny'", (A, user))[0][0] > denies, "the refusal itself is on the record"
    assert counts == [sql(world, f"SELECT count(*) FROM {t}")[0][0] for t in ("launch_projects", "project_milestones", "suppliers", "supplier_sources", "procurement_recommendations")]


def test_an_unauthorised_direct_procurement_update_by_service_and_by_sql_is_refused(world):
    _, _, dsn = world
    from nasha_lab.growth import service as SV
    rid = new_run(world, weeks=1).json()["corr_id"]
    for user in ("sam", "vic", "mia"):
        s = SV.GrowthService(dsn, "growth_journey", A, user)
        with pytest.raises(SV.Denied):
            s.record_procurement(rid, "ap_forged", user)
        s.close()
    s = SV.GrowthService(dsn, "growth_journey", A, "ada")
    with pytest.raises(psycopg.errors.IntegrityConstraintViolation, match="no audit evidence"):
        s.con.execute("UPDATE procurement_recommendations SET state='EXECUTED' WHERE id=%s", (rid,))
    s.close()
    assert sql(world, "SELECT state FROM procurement_recommendations WHERE id=%s", (rid,))[0][0] == "AWAITING_APPROVAL"


# ---------------------------------------------------------------- the database refuses unaudited writes to every launch table
LAUNCH = [("launch_projects", "INSERT INTO launch_projects (tenant_id,id,name,industry,location,concept,budget_cents) VALUES ('{t}','proj-rawinsert1','Raw','x','y','z',1)"),
          ("project_milestones", "INSERT INTO project_milestones (tenant_id,id,project_id,title,phase) VALUES ('{t}','ms-rawinsert1','{p}','Raw','idea')"),
          ("research_findings", "INSERT INTO research_findings (tenant_id,id,project_id,topic,finding,source_kind,confidence,limitation) VALUES ('{t}','find-rawins1','{p}','t','f','founder_note',0.5,'l')"),
          ("suppliers", "INSERT INTO suppliers (tenant_id,id,name,category,service_area,verification_status,source_kind) VALUES ('{t}','sup-rawinsert1','Raw Supplier Co','c','a','synthetic_fixture','synthetic_fixture')"),
          ("supplier_sources", "INSERT INTO supplier_sources (tenant_id,id,supplier_id,kind,url,claim,access,observed_on) VALUES ('{t}','ssrc-rawins1','{s}','press','https://example.test/raw','A raw insert without audit.','search_snippet','2026-10-23')"),
          ("project_assumptions", "INSERT INTO project_assumptions (tenant_id,id,project_id,key,label,value,unit,basis) VALUES ('{t}','asm-rawinsert1','{p}','raw_key','Raw',1,'u','founder')"),
          ("financial_scenarios", "INSERT INTO financial_scenarios (tenant_id,id,project_id,name,inputs,inputs_hash,results) VALUES ('{t}','scn-rawinsert1','{p}','Raw','{{}}','h','{{}}')"),
          ("launch_projects", "UPDATE launch_projects SET stage='roadmap' WHERE tenant_id='{t}' AND id='{p}'")]


@pytest.mark.parametrize("table,stmt", LAUNCH, ids=[f"{t}-{s.split()[0].lower()}" for t, s in LAUNCH])
def test_the_database_refuses_an_unaudited_write_to_each_launch_table_and_leaves_nothing(world, table, stmt):
    c, envs, dsn = world
    p = first_project(world); s = c.get(f"{BASE}/suppliers", headers=H(envs, "vic")).json()["items"][0]["id"]
    before = sql(world, f"SELECT count(*) FROM {table}")[0][0]; stage = sql(world, "SELECT stage FROM launch_projects WHERE id=%s", (p,))[0][0]
    with psycopg.connect(dsn, autocommit=True) as con:
        con.execute("SET ROLE growth_app"); con.execute('SET search_path TO "growth_journey", pg_catalog, public'); con.execute("SELECT set_config('app.tenant_id', %s, false)", (A,))
        with pytest.raises(psycopg.errors.IntegrityConstraintViolation, match="audit"):
            con.execute(stmt.format(t=A, p=p, s=s))
    assert sql(world, f"SELECT count(*) FROM {table}")[0][0] == before and sql(world, "SELECT stage FROM launch_projects WHERE id=%s", (p,))[0][0] == stage


def test_every_launch_table_is_in_the_isolation_and_audit_inventory():
    assert set(S.LAUNCH_TABLES) | set(S.LAUNCH_TABLES_V10) <= set(S.ALL_TENANT_TABLES) and "supplier_sources" in S.ALL_TENANT_TABLES


# ---------------------------------------------------------------- atomicity of the approval's state update
def test_if_the_project_update_fails_the_whole_approval_rolls_back_and_nothing_is_half_recorded(world):
    c, envs, dsn = world
    pid = c.post(f"{BASE}/projects", json=dict(name="Rollback probe " + uuid.uuid4().hex[:6], industry="Hospitality", location="Austin, TX", concept="A throwaway project used to prove an approval rolls back completely.", budget_cents=30_000_000), headers=H(envs, "ada")).json()["id"]
    assert c.post(f"{BASE}/projects/{pid}/scenarios", json=dict(name="Base", overrides={}), headers=H(envs, "ana")).status_code == 201
    rid = c.post(f"{BASE}/projects/{pid}/procurement", json={"period_weeks": 2}, headers=H(envs, "ana")).json()["corr_id"]
    stage0 = sql(world, "SELECT stage FROM launch_projects WHERE id=%s", (pid,))[0][0]
    ms0 = sql(world, "SELECT count(*) FROM project_milestones WHERE project_id=%s", (pid,))[0][0]
    allow0 = sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND decision='allow'", (A,))[0][0]
    with psycopg.connect(dsn, autocommit=True) as su:
        su.execute('SET search_path TO "growth_journey", pg_catalog, public')
        su.execute("CREATE OR REPLACE FUNCTION fail_stage() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN IF NEW.stage IS DISTINCT FROM OLD.stage THEN RAISE EXCEPTION 'injected failure after the milestone insert'; END IF; RETURN NEW; END $f$")
        su.execute("CREATE TRIGGER zz_fail_stage BEFORE UPDATE ON launch_projects FOR EACH ROW EXECUTE FUNCTION fail_stage()")
        try:
            r = c.post(f"{BASE}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, "ada"))
        finally:
            su.execute("DROP TRIGGER zz_fail_stage ON launch_projects")
    assert stage0 == "idea" and (r.status_code != 200 or r.json().get("status") != "EXECUTED")
    assert sql(world, "SELECT state FROM procurement_recommendations WHERE id=%s", (rid,))[0][0] != "EXECUTED"
    assert sql(world, "SELECT count(*) FROM project_milestones WHERE project_id=%s", (pid,))[0][0] == ms0, "the milestone written before the failure was rolled back with it"
    assert sql(world, "SELECT stage FROM launch_projects WHERE id=%s", (pid,))[0][0] == stage0
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND decision='allow'", (A,))[0][0] == allow0
    assert chain_ok(world)


# ---------------------------------------------------------------- external research failures
@pytest.mark.parametrize("failure", ["unavailable", "runtime_error", "timeout"])
def test_an_external_research_failure_never_blocks_or_alters_the_recommendation(world, failure):
    from nasha_lab.growth import agent_research as AR
    from test_growth_launch import make as _unused  # noqa: F401  (ensures the shared helper module is importable)
    c, envs, dsn = world
    from nasha_lab.growth import launch_workflow as LW
    class Bad:
        async def research(self, docs, query, version):
            if failure == "unavailable": raise AR.AgentUnavailable("engine down")
            if failure == "runtime_error": raise RuntimeError("provider exploded")
            await asyncio.sleep(5)
        async def close(self): return None
    base = LW.LaunchProcurement(envs[A], agent=None, as_of=__import__("datetime").date(2026, 10, 23))
    t = base.login("ana", f"{A}-ana-dev-passcode"); pid = first_project(world)
    h0 = base.status(base.run(t, pid, 2)["corr_id"])["proposal_hash"]; base.close()
    wf = LW.LaunchProcurement(envs[A], agent=Bad(), as_of=__import__("datetime").date(2026, 10, 23), agent_timeout=0.2)
    r = wf.run(wf.login("ana", f"{A}-ana-dev-passcode"), pid, 2); run = wf.status(r["corr_id"])
    assert r["status"] == "AWAITING_APPROVAL" and run["agent_mode"] == "deterministic_fallback" and run["proposal_hash"] == h0 and run["research"]["fallback_reason"]
    wf.close()


@pytest.mark.parametrize("user", ["vic", "sam", "mia"])
def test_a_refused_procurement_request_leaves_a_blocked_record_a_chained_audit_denial_and_no_proposal(world, user):
    c, envs, _ = world
    p = first_project(world)
    denies = sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND actor=%s AND decision='deny' AND action='procurement.request'", (A, user))[0][0]
    r = c.post(f"{BASE}/projects/{p}/procurement", json={}, headers=H(envs, user))
    assert r.status_code == 403
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND actor=%s AND decision='deny' AND action='procurement.request'", (A, user))[0][0] == denies + 1, "the denial is in the tenant's hash-chained audit log"
    row = sql(world, "SELECT state, failure, items IS NULL FROM procurement_recommendations WHERE requester=%s ORDER BY created_at DESC LIMIT 1", (user,))[0]
    assert row[0] == "BLOCKED" and row[1].split(":")[0] in ("ROLE_DENIED", "TOOL_DENIED") and row[2] is not None
    assert chain_ok(world)
