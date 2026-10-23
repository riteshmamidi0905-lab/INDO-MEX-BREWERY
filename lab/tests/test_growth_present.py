"""Business view vs Engineering view of Growth OS: both are derived from the SAME stored records. These tests check that the business language is complete, contains no raw identifiers,
never invents a stage that did not occur, and agrees with the engineering records. Also: realistic scenario seed data is internally consistent and its pipeline values are real calculations.
SYNTHETIC data only."""
import re
import socket
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, demo as DM, present as PR, scenarios as SC

RAW_ID = re.compile(r"\b(wf-[0-9a-f]{6,}|lead-[0-9a-f]{6,}|con-[0-9a-f]{6,}|acc-[0-9a-f]{6,}|ap_[0-9a-f]{6,}|E\d:[a-z_.]+|R-[A-Z]+|G\d\d)\b")


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import pixeltable_pgserver as pg
    root = tmp_path_factory.mktemp("gpres")
    try:
        srv = pg.get_server(str(root / "pg"), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    dsn = srv.get_uri()
    envs = DM.build(root / "data", dsn, schema="growth_present", with_warehouse=False)
    yield TestClient(GA.create_growth_app(envs)), envs, dsn
    srv.cleanup()


def hdr(envs, tenant, user):
    return {"Authorization": "Bearer " + envs[tenant].authority.login(user, f"{tenant}-{user}-dev-passcode")}


def runs(c, envs, tenant="tenant-nasha", user="ada"):
    return c.get(f"/v1/tenants/{tenant}/workflows/runs?limit=50", headers=hdr(envs, tenant, user)).json()["items"]


def detail(c, envs, run_id, tenant="tenant-nasha", user="ada"):
    return c.get(f"/v1/tenants/{tenant}/workflows/runs/{run_id}", headers=hdr(envs, tenant, user)).json()


def by_state(c, envs, state, tenant="tenant-nasha"):
    return [r for r in runs(c, envs, tenant) if r["state"] == state]


def business_text(b):
    parts = [b["summary"]["workflow"], b["summary"]["objective"], b["summary"]["outcome"], b["summary"]["next_action"] or "", b["summary"]["inquiry"] or ""]
    for t in b["timeline"] + b["authorization"]:
        parts += [t["title"], t["detail"] or ""]
    if b["qualification"]:
        q = b["qualification"]
        parts += [q["why"], q["recommended_action"], *q["limitations"], *(f["label"] + " " + f["explanation"] for f in q["factors"])]
    return "\n".join(parts)


def test_every_run_has_a_complete_business_view_with_names_and_no_raw_identifiers(world):
    c, envs, _ = world
    for tenant in ("tenant-nasha", "tenant-fit"):
        items = runs(c, envs, tenant)
        assert len(items) >= 5
        for r in items:
            d = detail(c, envs, r["id"], tenant)
            b, s = d["business"], d["business"]["summary"]
            assert s["prospect"] and s["organization"] and s["inquiry"] and s["owner"] and s["scenario"] and s["status_label"] and s["outcome"], r
            assert not RAW_ID.search(business_text(b)), (r["state"], RAW_ID.search(business_text(b)))
            assert r["prospect"] == s["prospect"] and r["organization"] == s["organization"], "list and detail agree"


def test_business_numbers_equal_the_engineering_records(world):
    c, envs, _ = world
    for r in by_state(c, envs, "EXECUTED") + by_state(c, envs, "AWAITING_APPROVAL"):
        d = detail(c, envs, r["id"])
        q, p = d["business"]["qualification"], d["proposal"]
        assert q["score"] == p["score"] == sum(f["points"] for f in q["factors"]) and q["verdict"] == p["proposed_status"]
        assert [f["points"] for f in q["factors"]] == [x["points"] for x in sorted(p["reasons"], key=lambda x: PR.FACTOR_ORDER.index(x["factor"]))]
        assert all(f["explanation"] and f["max_points"] for f in q["factors"])
        assert (q["score"] >= PR.THRESHOLD) == (q["verdict"] == "qualified")


def test_every_timeline_entry_resolves_to_a_recorded_event_and_nothing_is_invented(world):
    c, envs, _ = world
    for r in runs(c, envs):
        d = detail(c, envs, r["id"])
        raw = {e["seq"]: e for e in d["events"]}
        for t in d["business"]["timeline"]:
            assert t["seq"] in raw and t["technical"] == raw[t["seq"]] and t["ts"] == raw[t["seq"]]["ts"]
        titles = " ".join(t["title"] for t in d["business"]["timeline"])
        recorded = {e.get("name") for e in d["events"]}
        assert ("CRM updated" in titles) == ("crm_updated" in recorded), "a completed stage is shown only if it was recorded"
        assert ("No email or message was sent" in titles) == ("no_external_contact" in recorded)
        assert ("Waiting for a human decision" in titles) == ("held_for_approval" in recorded)
        assert [t["seq"] for t in d["business"]["timeline"]] == sorted(t["seq"] for t in d["business"]["timeline"])


def test_a_blocked_run_exposes_no_approval_action_and_says_nothing_changed(world):
    c, envs, _ = world
    blocked = by_state(c, envs, "BLOCKED")
    assert len(blocked) >= 2
    for r in blocked:
        b = detail(c, envs, r["id"])["business"]
        assert b["approval"]["can_decide"] is False and b["approval"]["label"] == "Blocked"
        assert "No CRM changes were made" in b["summary"]["outcome"]
        assert not any("CRM updated" in t["title"] for t in b["timeline"])
    denied = [r for r in blocked if (r["failure"] or "").startswith("TOOL_DENIED")]
    assert denied
    b = detail(c, envs, denied[0]["id"])["business"]
    assert "does not have permission" in b["summary"]["outcome"] and any(a["tone"] == "no" for a in b["authorization"])


def test_approval_states_are_distinct_and_only_an_awaiting_run_can_be_decided(world):
    c, envs, _ = world
    want = {"AWAITING_APPROVAL": "Awaiting approval", "EXECUTED": "Completed", "REJECTED": "Rejected", "BLOCKED": "Blocked", "ABSTAINED": "Needs more information"}
    for st, label in want.items():
        for r in by_state(c, envs, st):
            ap = detail(c, envs, r["id"])["business"]["approval"]
            assert ap["label"] == label and ap["can_decide"] == (st == "AWAITING_APPROVAL")
    ex = detail(c, envs, by_state(c, envs, "EXECUTED")[0]["id"])["business"]
    assert ex["approval"]["decided_by"] and "approval" in ex["summary"]["outcome"]
    # the UI flag is only a presentation hint: the backend still refuses a decision on a finished run
    rid = by_state(c, envs, "EXECUTED")[0]["id"]
    assert c.post(f"/v1/tenants/tenant-nasha/workflows/runs/{rid}/decision", json={"approve": True}, headers=hdr(envs, "tenant-nasha", "ada")).status_code == 409


def test_audit_events_have_human_readable_summaries_and_keep_the_raw_record(world):
    c, envs, _ = world
    items = c.get("/v1/tenants/tenant-nasha/audit?limit=50", headers=hdr(envs, "tenant-nasha", "ada")).json()["items"]
    assert items and all(i["summary"] and i["action"] and i["seq"] for i in items)
    assert not any(RAW_ID.search(i["summary"]) for i in items), [i["summary"] for i in items if RAW_ID.search(i["summary"])][:2]
    q = [i for i in items if i["action"] == "lead.qualification_applied"]
    assert q and all("after approval by" in i["summary"] for i in q)


def test_the_two_tenants_have_distinct_people_products_prices_and_pipelines(world):
    c, envs, dsn = world
    n = {r["prospect"] for r in runs(c, envs, "tenant-nasha")}
    f = {r["prospect"] for r in runs(c, envs, "tenant-fit")}
    assert n and f and not (n & f)
    dn = c.get("/v1/tenants/tenant-nasha/dashboard", headers=hdr(envs, "tenant-nasha", "ada")).json()
    df = c.get("/v1/tenants/tenant-fit/dashboard", headers=hdr(envs, "tenant-fit", "ada")).json()
    assert dn["open_value_cents"] != df["open_value_cents"] and dn["lead_total"] != df["lead_total"] or dn["pipeline"] != df["pipeline"]
    for t, env in envs.items():
        other = [r for r in runs(c, envs, "tenant-fit" if t == "tenant-nasha" else "tenant-nasha")]
        for r in other:                                  # a run id from the other tenant is not visible here
            assert c.get(f"/v1/tenants/{t}/workflows/runs/{r['id']}", headers=hdr(envs, t, "ada")).status_code == 404


def test_pipeline_values_are_computed_from_stored_prices_not_typed_in(world):
    c, envs, dsn = world
    with psycopg.connect(dsn, autocommit=True) as con:
        con.execute('SET search_path TO "growth_present", pg_catalog, public')
        for tenant, plan in (("tenant-nasha", SC.NASHA), ("tenant-fit", SC.MERIDIAN)):
            prices = {n: int(a) for n, a in con.execute("SELECT p.name, pr.amount_cents FROM products p JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id WHERE p.tenant_id=%s AND pr.status='current'", (tenant,))}
            for sc in plan:
                if sc["opp"] and sc["basket"]:
                    expected = sum(prices[nm] * q for nm, q in sc["basket"])
                    got = con.execute("SELECT amount_cents FROM opportunities WHERE tenant_id=%s AND name=%s", (tenant, sc["opp"])).fetchone()
                    if got:
                        assert int(got[0]) == expected, (sc["opp"], got[0], expected)
        # the NASHA concept prices are the founder-approved ones ($18.50 mains, $13.50 appetizers)
        assert {int(a) for a, in con.execute("SELECT pr.amount_cents FROM prices pr JOIN products p ON p.tenant_id=pr.tenant_id AND p.id=pr.product_id WHERE pr.tenant_id='tenant-nasha' AND pr.status='current'")} <= {1850, 1350}


def test_scenarios_are_fictional_labelled_and_self_consistent():
    for plan in (SC.NASHA, SC.MERIDIAN):
        keys = [s["key"] for s in plan]
        assert len(keys) == len(set(keys))
        for s in plan:
            assert s["inquiry"] and s["scenario"] and s["person"] and s["org"] and s["slug"]
            assert re.fullmatch(r"[a-z.]+", s["slug"])
            if s["signals"]:
                assert 0 <= s["signals"]["fit"] <= 1 and 0 <= s["signals"]["engagement"] <= 1
            if s["disposition"] == "suppressed":
                assert s["suppress_reason"]
    assert {s["disposition"] for s in SC.NASHA} >= {"executed", "rejected", "awaiting", "denied", "suppressed", "abstain"}
