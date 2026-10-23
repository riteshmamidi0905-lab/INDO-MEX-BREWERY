"""Launch-workspace HTTP API: projects, assumptions, research, suppliers, financial scenarios and the governed procurement recommendation, over real PostgreSQL and THE WEIR, two synthetic tenants. SYNTHETIC data only."""
import re
import uuid
from datetime import date

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, demo as DM

A, B = "tenant-nasha", "tenant-fit"
RAW_ID = re.compile(r"\b(pr-[0-9a-f]{6,}|proj-[0-9a-f]{6,}|sup-[0-9a-f]{6,}|ap_[0-9a-f]{6,}|P\d\d|R-[A-Z]+)\b")


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import pixeltable_pgserver as pg
    root = tmp_path_factory.mktemp("glapi")
    try:
        srv = pg.get_server(str(root / "pg"), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    dsn = srv.get_uri()
    envs = DM.build(root / "d", dsn, schema="growth_lapi", with_warehouse=False)
    yield TestClient(GA.create_growth_app(envs)), envs, dsn
    srv.cleanup()


def H(envs, t, u, **x):
    return {"Authorization": "Bearer " + envs[t].authority.login(u, f"{t}-{u}-dev-passcode"), **x}


def pid(world, t=A):
    c, envs, _ = world
    return c.get(f"/v1/tenants/{t}/projects", headers=H(envs, t, "ada")).json()["items"][0]["id"]


def test_projects_are_listed_per_tenant_and_the_overview_carries_the_whole_story(world):
    c, envs, _ = world
    for t, name in ((A, "NASHA — The Courtyard"), (B, "Second studio location")):
        items = c.get(f"/v1/tenants/{t}/projects", headers=H(envs, t, "vic")).json()["items"]
        assert [p["name"] for p in items] == [name]
        ov = c.get(f"/v1/tenants/{t}/projects/{items[0]['id']}", headers=H(envs, t, "vic")).json()
        assert ov["assumptions"] and ov["milestones"] and ov["findings"] and ov["shortlist"] and ov["scenarios"] == []
    assert "fusion" not in c.get(f"/v1/tenants/{A}/projects", headers=H(envs, A, "vic")).text.lower()
    assert c.get(f"/v1/tenants/{B}/projects/{pid(world)}", headers=H(envs, B, "ada")).status_code == 404, "another tenant's project id is not found"


def test_project_creation_validation_roles_and_idempotency(world):
    c, envs, _ = world
    body = dict(name="Pop-up concept", industry="Retail", location="Austin, TX", concept="A short-run pop-up shop to test demand before committing to a lease.", budget_cents=2_500_000)
    assert c.post(f"/v1/tenants/{A}/projects", json=body, headers=H(envs, A, "sam")).status_code == 403
    h = H(envs, A, "ada", **{"Idempotency-Key": "proj-key-" + uuid.uuid4().hex[:8]})
    r1 = c.post(f"/v1/tenants/{A}/projects", json=body, headers=h); r2 = c.post(f"/v1/tenants/{A}/projects", json=body, headers=h)
    assert r1.status_code == 201 and r2.status_code == 201 and r1.json() == r2.json()
    assert c.post(f"/v1/tenants/{A}/projects", json={**body, "name": "Another"}, headers=H(envs, A, "ada", **{"Idempotency-Key": h["Idempotency-Key"]})).status_code == 409
    assert c.post(f"/v1/tenants/{A}/projects", json={**body, "name": "X2", "tenant_id": B}, headers=H(envs, A, "ada")).status_code == 422
    assert c.post(f"/v1/tenants/{A}/projects", json={**body, "name": "X3", "budget_cents": -5}, headers=H(envs, A, "ada")).status_code == 422
    assert c.post(f"/v1/tenants/{A}/projects", json=body, headers=H(envs, A, "ada")).status_code == 409                      # unique name per tenant
    assert c.post(f"/v1/tenants/{B}/projects", json=body, headers=H(envs, B, "ada")).status_code == 201                       # but the other tenant may use it


def test_assumptions_drive_the_financial_plan_and_only_owner_and_analyst_may_change_them(world):
    c, envs, _ = world
    p = pid(world); base = f"/v1/tenants/{A}/projects/{p}"
    before = c.post(f"{base}/scenarios/preview", json={}, headers=H(envs, A, "vic")).json()
    asm = dict(label="Guest orders per week", value=900, unit="orders", basis="founder", note="founder revision")
    assert c.put(f"{base}/assumptions/weekly_orders", json=asm, headers=H(envs, A, "sam")).status_code == 403
    assert c.put(f"{base}/assumptions/weekly_orders", json=asm, headers=H(envs, A, "ana")).status_code == 200
    after = c.post(f"{base}/scenarios/preview", json={}, headers=H(envs, A, "vic")).json()
    assert after["results"]["revenue_cents"] > before["results"]["revenue_cents"] and after["inputs_hash"] != before["inputs_hash"] and after["results"]["kind"] == "simulated"
    c.put(f"{base}/assumptions/weekly_orders", json=dict(asm, value=650, basis="synthetic_assumption", note=None), headers=H(envs, A, "ana"))
    assert c.put(f"{base}/assumptions/weekly_orders", json=dict(asm, basis="guess"), headers=H(envs, A, "ana")).status_code == 422
    assert c.post(f"{base}/scenarios/preview", json={"price_change_pct": 50}, headers=H(envs, A, "vic")).status_code == 422
    assert c.post(f"{base}/scenarios/preview", json={"weekly_orders": 1, "bogus": 1}, headers=H(envs, A, "vic")).status_code == 422


def test_scenario_comparison_saving_and_reproducibility_over_http(world):
    c, envs, _ = world
    p = pid(world); base = f"/v1/tenants/{A}/projects/{p}"
    cmp = c.post(f"{base}/scenarios/compare", json={"scenarios": [{"name": "Base"}, {"name": "Price +5%", "overrides": {"price_change_pct": 0.05}}, {"name": "Costs +20%", "overrides": {"cost_change_pct": 0.2}}]}, headers=H(envs, A, "ana")).json()
    assert [r["name"] for r in cmp["rows"]] == ["Base", "Price +5%", "Costs +20%"] and cmp["rows"][0]["profit_vs_base_cents"] == 0 and cmp["rows"][2]["profit_vs_base_cents"] < 0 and "not actual business performance" in cmp["note"]
    r = c.post(f"{base}/scenarios", json={"name": "Price +5%", "overrides": {"price_change_pct": 0.05}}, headers=H(envs, A, "ana", **{"Idempotency-Key": "scn-key-" + uuid.uuid4().hex[:8]}))
    assert r.status_code == 201
    sc = c.get(f"{base}/scenarios/{r.json()['id']}", headers=H(envs, A, "vic")).json()
    prev = c.post(f"{base}/scenarios/preview", json={"price_change_pct": 0.05}, headers=H(envs, A, "vic")).json()
    assert sc["results"]["results"] == prev["results"] and sc["inputs_hash"] == prev["inputs_hash"]
    assert c.post(f"{base}/scenarios", json={"name": "Price +5%"}, headers=H(envs, A, "sam")).status_code == 403
    assert c.get(f"/v1/tenants/{B}/projects/{pid(world, B)}/scenarios/{r.json()['id']}", headers=H(envs, B, "ada")).status_code == 404


def test_supplier_api_refuses_invented_contacts_unverified_claims_and_fake_prices_and_shows_provenance(world):
    c, envs, _ = world
    h = H(envs, A, "ana")
    sup = dict(name="Candidate Coffee Roasters", category="Coffee", service_area="Texas (per source)", verification_status="lead_unverified", source_kind="search_result", source_url="https://example.org/listing", notes="Seen in a directory.")
    assert c.post(f"/v1/tenants/{A}/suppliers", json={**sup, "contact_channel": "owner@candidate.example"}, headers=h).status_code == 422
    assert c.post(f"/v1/tenants/{A}/suppliers", json={**sup, "name": "No source", "source_url": None}, headers=h).status_code == 422
    assert c.post(f"/v1/tenants/{A}/suppliers", json={**sup, "name": "Claims verified", "verification_status": "verified_public"}, headers=h).status_code == 422
    assert c.post(f"/v1/tenants/{A}/suppliers", json={**sup, "source_url": "http://insecure.example"}, headers=h).status_code == 422
    assert c.post(f"/v1/tenants/{A}/suppliers", json=sup, headers=H(envs, A, "sam")).status_code == 403
    sid = c.post(f"/v1/tenants/{A}/suppliers", json=sup, headers=h).json()["id"]
    bad = dict(name="Invented price", unit="kg", price_class="NONE_PUBLISHED", limitation="none published", unit_price_cents=99)
    assert c.post(f"/v1/tenants/{A}/suppliers/{sid}/products", json=bad, headers=h).status_code == 422
    assert c.post(f"/v1/tenants/{A}/suppliers/{sid}/products", json={**bad, "unit_price_cents": None}, headers=h).status_code == 201
    d = {s["name"]: s for s in c.get(f"/v1/tenants/{A}/suppliers", headers=H(envs, A, "vic")).json()["items"]}
    assert d["Candidate Coffee Roasters"]["freshness"] == "unverified" and d["Farm to Table LLC"]["verification_status"] == "lead_unverified" and d["Farm to Table LLC"]["source_url"].startswith("https://")
    assert not any(s["name"] == "Candidate Coffee Roasters" for s in c.get(f"/v1/tenants/{B}/suppliers", headers=H(envs, B, "vic")).json()["items"]), "supplier records are tenant-scoped"
    assert c.put(f"/v1/tenants/{A}/projects/{pid(world)}/suppliers/{sid}", json={"status": "shortlisted", "note": "ask for a quote later"}, headers=h).status_code == 200
    assert c.put(f"/v1/tenants/{B}/projects/{pid(world, B)}/suppliers/{sid}", json={"status": "shortlisted"}, headers=H(envs, B, "ana")).status_code in (404, 422), "a supplier id from another tenant cannot be shortlisted"


def test_procurement_over_http_denied_held_approved_recorded_replay_refused_and_audited(world):
    c, envs, dsn = world
    p = pid(world); base = f"/v1/tenants/{A}"
    assert c.post(f"{base}/projects/{p}/procurement", json={}, headers=H(envs, A, "vic")).status_code == 403
    assert c.post(f"{base}/projects/{p}/procurement", json={}, headers=H(envs, A, "sam")).status_code == 403
    assert c.post(f"{base}/projects/{p}/procurement", json={"period_weeks": 99}, headers=H(envs, A, "ana")).status_code == 422
    assert c.post(f"{base}/projects/proj-nonexistent1/procurement", json={}, headers=H(envs, A, "ana")).status_code == 404
    assert c.post(f"/v1/tenants/{B}/projects/{p}/procurement", json={}, headers=H(envs, B, "ana")).status_code == 404
    k = "proc-key-" + uuid.uuid4().hex[:8]
    r = c.post(f"{base}/projects/{p}/procurement", json={"period_weeks": 3}, headers=H(envs, A, "ana", **{"Idempotency-Key": k}))
    assert r.status_code == 202 and r.json()["status"] == "AWAITING_APPROVAL" and r.json()["side_effects"] == dict(orders_placed=0, suppliers_contacted=0, emails_sent=0)
    assert c.post(f"{base}/projects/{p}/procurement", json={"period_weeks": 3}, headers=H(envs, A, "ana", **{"Idempotency-Key": k})).status_code == 200
    run = r.json()["corr_id"]
    d = c.get(f"{base}/procurement/runs/{run}", headers=H(envs, A, "ana")).json()
    assert d["business"]["approval"]["can_decide"] is True and d["business"]["recommendation"]["total_cost_cents"] > 0 and d["business"]["research"]["mode_label"]
    biz = " ".join([d["business"]["summary"]["outcome"], d["business"]["summary"]["objective"]] + [t["title"] + " " + (t["detail"] or "") for t in d["business"]["timeline"]])
    assert not RAW_ID.search(biz), RAW_ID.search(biz)
    assert c.post(f"{base}/procurement/runs/{run}/decision", json={"approve": True}, headers=H(envs, A, "ana")).status_code == 403          # analyst cannot approve
    assert c.post(f"/v1/tenants/{B}/procurement/runs/{run}/decision", json={"approve": True}, headers=H(envs, B, "ada")).status_code == 404
    ok = c.post(f"{base}/procurement/runs/{run}/decision", json={"approve": True, "comment": "ok"}, headers=H(envs, A, "ada"))
    assert ok.status_code == 200 and ok.json()["status"] == "EXECUTED"
    assert c.post(f"{base}/procurement/runs/{run}/decision", json={"approve": True}, headers=H(envs, A, "omar")).status_code == 409
    aud = c.get(f"{base}/audit?limit=50", headers=H(envs, A, "ada")).json()["items"]
    rec = [a for a in aud if a["action"] == "procurement.record" and a["entity_id"] == run]
    assert len(rec) == 1 and rec[0]["detail"]["approved_by"] == "ada" and "procurement recommendation" in rec[0]["summary"] and "after approval by" in rec[0]["summary"]
    runs = c.get(f"{base}/procurement/runs", headers=H(envs, A, "vic")).json()["items"]
    assert any(x["id"] == run and x["status_label"] == "Completed" for x in runs) and all(x["project"] and x["requested_by"] for x in runs)
    assert not [x for x in c.get(f"/v1/tenants/{B}/procurement/runs", headers=H(envs, B, "vic")).json()["items"] if x["id"] == run]
    assert c.get(f"/v1/tenants/{A}/audit/verify", headers=H(envs, A, "ada")).json()["chain_valid"] is True


def test_offer_economics_equal_the_pricing_engine_over_stored_prices_and_costs_and_nothing_is_published(world):
    c, envs, _ = world
    from nasha_lab.growth import pricing as GP
    j = c.get(f"/v1/tenants/{A}/marketing/offers", headers=H(envs, A, "mia")).json()
    assert j["offers"] and j["campaigns"] and all(x["status"] in ("draft", "approved", "expired") for x in j["campaigns"] + j["offers"]) and "nothing is published" in j["note"].lower()
    for o in j["offers"]:
        a = GP.discount_analysis(o["price_cents"], o["unit_cost_cents"], o["discount_pct"])
        assert o["margin_before"] == round(a["margin_before"], 4) and o["margin_after"] == round(a["margin_after"], 4) and o["breakeven_volume_uplift"] == round(a["breakeven_volume_uplift"], 4)
        assert o["margin_after"] < o["margin_before"]
    assert c.get(f"/v1/tenants/{B}/marketing/offers", headers=H(envs, B, "mia")).json()["offers"] == []


def test_inventory_planning_in_the_recommendation_is_derived_from_the_plan(world):
    c, envs, _ = world
    runs = c.get(f"/v1/tenants/{A}/procurement/runs", headers=H(envs, A, "vic")).json()["items"]
    run = next(r for r in runs if r["state"] == "EXECUTED")
    d = c.get(f"/v1/tenants/{A}/procurement/runs/{run['id']}", headers=H(envs, A, "vic")).json()
    rep, plan = d["business"]["recommendation"]["replenishment"], d["plan"]
    assert rep and len(rep) == len([i for i in plan["items"] if i["chosen"]])
    it = {i["ingredient"]: i for i in plan["items"] if i["chosen"]}
    for r in rep[:10]:
        src = it[r["ingredient"]]
        assert abs(r["weekly_usage"] - src["need_qty"] / plan["period_weeks"]) < 0.002 and r["order_qty"] == src["chosen"]["buy_qty"] and r["lead_days"] == src["chosen"]["lead_days"]
        assert abs(r["reorder_point"] - r["weekly_usage"] * r["lead_days"] / 7 * 1.2) < 0.002
    assert d["business"]["recommendation"]["replenishment_assumption"].endswith("(assumed)")
