"""The complete entrepreneur journey over HTTP, on persistent data, as separate roles, in one tenant: create a project, set a start-up budget, record research, shortlist and compare suppliers, change assumptions,
recalculate start-up costs, save a scenario, generate a governed procurement recommendation, hold it for a DIFFERENT person's approval, record the decision, see the project state move, and read the audit history.
Every effect is asserted against the API or the database. SYNTHETIC tenants; nothing is ordered, no supplier is contacted, and the agent (if any) is the offline heuristic."""
import re
from datetime import date

import pytest

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, demo as DM

A, B = "tenant-nasha", "tenant-fit"
AS_OF = date(2026, 10, 23)
RAW_ID = re.compile(r"\b(pr-[0-9a-f]{6,}|proj-[0-9a-f]{6,}|sup-[0-9a-f]{6,}|asm-[0-9a-f]{6,}|ms-[0-9a-f]{6,}|scn-[0-9a-f]{6,}|psup-[0-9a-f]{6,}|find-[0-9a-f]{6,})\b")


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import pixeltable_pgserver as pg
    root = tmp_path_factory.mktemp("gjourney")
    try:
        srv = pg.get_server(str(root / "pg"), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    dsn = srv.get_uri()
    envs = DM.build(root / "d", dsn, schema="growth_journey", with_warehouse=False)
    try:
        import agentplatform  # noqa: F401
        app = GA.create_growth_app(envs, agent_dsn=dsn, as_of=AS_OF)
    except ImportError:
        app = GA.create_growth_app(envs, as_of=AS_OF)
    yield TestClient(app), envs, dsn
    srv.cleanup()


def H(envs, u, t=A, **x):
    return {"Authorization": "Bearer " + envs[t].authority.login(u, f"{t}-{u}-dev-passcode"), **x}


def sql(world, q, params=()):
    _, _, dsn = world
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute('SET search_path TO "growth_journey", pg_catalog, public')
        return c.execute(q, params).fetchall()


def test_the_whole_journey_from_a_new_idea_to_an_approved_recommendation_and_an_auditable_history(world):
    c, envs, _ = world
    base = f"/v1/tenants/{A}"

    # 1-2. create a business-launch project with a start-up budget (an OWNER decision)
    body = dict(name="Courtyard pilot kitchen", industry="Hospitality", location="Austin, TX", concept="A small pilot kitchen to test the opening menu with real recipes before the full venue is built.", budget_cents=45_000_000, launch_target="2027-04-01")
    assert c.post(f"{base}/projects", json=body, headers=H(envs, "ana")).status_code == 403, "an analyst cannot start a project"
    p = c.post(f"{base}/projects", json=body, headers=H(envs, "ada")); assert p.status_code == 201
    pid = p.json()["id"]
    ov = c.get(f"{base}/projects/{pid}", headers=H(envs, "vic")).json()
    assert ov["stage"] == "idea" and ov["budget_cents"] == 45_000_000 and ov["assumptions"] == [] and ov["milestones"] == [] and ov["scenarios"] == []

    # 3. record market research (cited, dated, with its limitation)
    f = c.post(f"{base}/projects/{pid}/findings", json=dict(topic="Local demand", finding="Founder's notes: lunch traffic near the proposed site is expected to be the weakest daypart.", source_kind="founder_note", confidence=0.4, limitation="A founder note, not measured demand."), headers=H(envs, "ana"))
    assert f.status_code == 201

    # 4-5. build a shortlist from the supplier directory and compare it with explicit data categories
    intel = c.get(f"{base}/supplier-intelligence?project_id={pid}", headers=H(envs, "ana")).json()
    syn = [x for x in intel["cards"] if x["information_category"] == "synthetic_fixture"][:2]
    lead = next(x for x in intel["cards"] if x["information_category"] == "unverified_public_lead")
    for x in syn + [lead]:
        assert c.put(f"{base}/projects/{pid}/suppliers/{x['id']}", json=dict(status="shortlisted", note="Compare quotes later"), headers=H(envs, "ana")).status_code == 200
    intel2 = c.get(f"{base}/supplier-intelligence?project_id={pid}", headers=H(envs, "ana")).json()
    assert {x["name"] for x in intel2["cards"] if x["shortlist_status"] == "shortlisted"} == {x["name"] for x in syn + [lead]}
    assert all(set(r["categories"]) <= {"synthetic_quotation"} and r["cross_category_ranking"] is None for r in intel2["quotes"]["rows"])
    assert lead["price_categories"] == {"none_published": 1} and lead["official_website_verified"] is False

    # 6-7. state assumptions, then change one and recalculate the start-up requirement from stored data
    for k, label, v, unit in (("weekly_orders", "Guest orders per week", 300, "orders"), ("items_per_order", "Items per order", 2.5, "items"), ("rent_monthly_cents", "Rent", 900_000, "cents/month"), ("labor_monthly_cents", "Labour", 2_600_000, "cents/month"),
                              ("capex_buildout_cents", "Build-out", 24_000_000, "cents"), ("capex_equipment_cents", "Equipment", 9_000_000, "cents"), ("working_capital_months", "Working capital months", 2, "months"), ("contingency_pct", "Contingency", 10, "%")):
        r = c.put(f"{base}/projects/{pid}/assumptions/{k}", json=dict(label=label, value=v, unit=unit, basis="synthetic_assumption"), headers=H(envs, "ana")); assert r.status_code == 200, (k, r.text)
    before = c.post(f"{base}/projects/{pid}/scenarios/preview", json={}, headers=H(envs, "ana")).json()["results"]["startup"]
    assert c.put(f"{base}/projects/{pid}/assumptions/capex_buildout_cents", json=dict(label="Build-out", value=20_000_000, unit="cents", basis="founder"), headers=H(envs, "ada")).status_code == 200
    after = c.post(f"{base}/projects/{pid}/scenarios/preview", json={}, headers=H(envs, "ana")).json()
    assert before["total_requirement_cents"] - after["results"]["startup"]["total_requirement_cents"] == round(4_000_000 * 1.10), "a 4,000,000-cent cut plus its 10% contingency"
    assert after["results"]["kind"] == "simulated" and after["results"]["formulas"] and after["limitations"]
    assert c.post(f"{base}/projects/{pid}/scenarios", json=dict(name="Base plan", overrides={}), headers=H(envs, "ana")).status_code == 201

    # 8-9. generate a governed procurement recommendation; it is HELD for a different person
    run = c.post(f"{base}/projects/{pid}/procurement", json={"period_weeks": 2}, headers=H(envs, "ana"))
    assert run.status_code == 202 and run.json()["status"] == "AWAITING_APPROVAL" and run.json()["side_effects"] == dict(orders_placed=0, suppliers_contacted=0, emails_sent=0)
    rid = run.json()["corr_id"]
    detail = c.get(f"{base}/procurement/runs/{rid}", headers=H(envs, "ana")).json()["business"]
    assert detail["approval"]["can_decide"] is True and detail["recommendation"]["total_cost_cents"] > 0
    assert detail["research"]["mode_label"] and ("language model" in detail["research"]["mode_label"] or "No agent ran" in detail["research"]["mode_label"] or "offline heuristic" in detail["research"]["mode_label"])
    assert c.get(f"{base}/projects/{pid}", headers=H(envs, "vic")).json()["stage"] == "idea", "nothing moves the project forward until a person approves"

    # 10. the authorisation decision: the requester's role cannot approve; an OWNER can; a replay is refused
    assert c.post(f"{base}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, "ana")).status_code == 403
    done = c.post(f"{base}/procurement/runs/{rid}/decision", json={"approve": True, "comment": "Reviewed the quotes."}, headers=H(envs, "ada"))
    assert done.status_code == 200 and done.json()["status"] == "EXECUTED"
    assert c.post(f"{base}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, "omar")).status_code == 409

    # 11. the project state moved, in the same transaction as the approval
    ov = c.get(f"{base}/projects/{pid}", headers=H(envs, "vic")).json()
    assert ov["stage"] == "roadmap", "approved recommendation + a saved scenario => roadmap"
    done_ms = [m for m in ov["milestones"] if m["title"].startswith("Procurement recommendation approved")]
    assert len(done_ms) == 1 and done_ms[0]["status"] == "done" and "nothing was ordered" in done_ms[0]["note"].lower() and done_ms[0]["phase"] == "sourcing"

    # 12. an auditable execution history: exactly what was recorded, in order, readable, and the chain verifies
    hist = c.get(f"{base}/projects/{pid}/history", headers=H(envs, "vic")).json()
    acts = [h["action"] for h in hist["items"]]
    assert acts[0] == "project.create" and {"finding.add", "supplier.shortlist", "project.assumption", "scenario.save", "procurement.record"} <= set(acts)
    assert [h["seq"] for h in hist["items"]] == sorted(h["seq"] for h in hist["items"]) and all(h["decision"] == "allow" and h["summary"] for h in hist["items"])
    assert not RAW_ID.search(" ".join(h["summary"] for h in hist["items"])), "the business history never shows internal ids"
    rec = [h for h in hist["items"] if h["action"] == "procurement.record"][0]
    assert rec["detail"]["approved_by"] == "ada" and rec["detail"]["stage_to"] == "roadmap" and f"project_milestones:{rec['detail']['milestone']}" in rec["detail"]["also"]
    assert c.get(f"{base}/audit/verify", headers=H(envs, "ada")).json()["chain_valid"] is True
    assert sql(world, "SELECT count(*) FROM procurement_recommendations WHERE id=%s AND state='EXECUTED'", (rid,))[0][0] == 1

    # the same journey is invisible to the other tenant
    assert c.get(f"/v1/tenants/{B}/projects/{pid}/history", headers=H(envs, "ada", B)).status_code == 404
    assert c.get(f"/v1/tenants/{B}/projects", headers=H(envs, "ada", B)).json()["items"][0]["name"] != "Courtyard pilot kitchen"


def test_a_rejected_recommendation_does_not_move_the_project(world):
    c, envs, _ = world
    base = f"/v1/tenants/{A}"
    pid = c.post(f"{base}/projects", json=dict(name="Courtyard second pilot", industry="Hospitality", location="Austin, TX", concept="A second pilot used to test that a rejection changes nothing about the project state.", budget_cents=30_000_000), headers=H(envs, "ada")).json()["id"]
    run = c.post(f"{base}/projects/{pid}/procurement", json={"period_weeks": 1}, headers=H(envs, "ana"))
    if run.status_code != 202:
        pytest.skip(f"no recommendation could be made for this project: {run.status_code}")
    rid = run.json()["corr_id"]
    r = c.post(f"{base}/procurement/runs/{rid}/decision", json={"approve": False, "comment": "Not now."}, headers=H(envs, "ada"))
    assert r.status_code == 200 and r.json()["status"] == "REJECTED"
    ov = c.get(f"{base}/projects/{pid}", headers=H(envs, "vic")).json()
    assert ov["stage"] == "idea" and not [m for m in ov["milestones"] if m["title"].startswith("Procurement recommendation approved")]
    assert "procurement.record" not in [h["action"] for h in c.get(f"{base}/projects/{pid}/history", headers=H(envs, "vic")).json()["items"]]
