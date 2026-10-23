"""HTTP contract tests for the governed procurement API: auth, tenant boundary, idempotency, pagination, error envelope, OpenAPI contract. SYNTHETIC data."""
import dataclasses
import json
import shutil
import sqlite3

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
from fastapi.testclient import TestClient

from nasha_lab.governed import tenants as T, workflow as W
from nasha_lab.governed.api import create_governed_app


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    return T.default_pair(tmp_path_factory.mktemp("apit"))


def fresh(env, tmp):
    tmp.mkdir(parents=True, exist_ok=True)
    return dataclasses.replace(env, root=tmp, ledger_path=tmp / "ledger.db", weir_db=tmp / "weir.db", trace_db=tmp / "trace.db", memory_db=tmp / "memory.db", authority=T.make_authority(env.tenant_id, env.people))


@pytest.fixture()
def api(pair, tmp_path):
    a, b = fresh(pair[0], tmp_path / "a"), fresh(pair[1], tmp_path / "b")
    sa, sb = W.GovernedProcurement(a), W.GovernedProcurement(b)
    app = create_governed_app({"tenant-a": sa, "tenant-b": sb})
    yield TestClient(app), sa, sb, a, b
    sa.close(); sb.close()


def H(tok, **k):
    return {"Authorization": f"Bearer {tok}", **k}


def target(env):
    c = sqlite3.connect(env.warehouse)
    r = c.execute("SELECT f.location_id, f.ingredient_id FROM scn_variance_flag f JOIN scn_procurement_reco r ON r.location_id=f.location_id AND r.ingredient_id=f.ingredient_id ORDER BY f.excess_pct DESC LIMIT 1").fetchone()
    c.close()
    return dict(location_id=r[0], ingredient_id=r[1])


def test_health_ready_and_request_id_propagation(api):
    c, *_ = api
    assert c.get("/v1/health").json() == {"status": "ok"}
    r = c.get("/v1/ready", headers={"X-Request-Id": "trace-me-123"})
    assert r.status_code == 200 and r.json()["tenants"] == 2 and r.headers["X-Request-Id"] == "trace-me-123"
    assert c.get("/v1/health", headers={"X-Request-Id": "bad id with spaces"}).headers["X-Request-Id"].startswith("req-")


def test_full_flow_over_http_ends_in_a_draft_po_and_no_transmission(api):
    c, sa, sb, a, b = api
    buyer, founder = sa.login("tenant-a-buyer", "tenant-a-buyer-dev-passcode"), sa.login("tenant-a-founder", "tenant-a-founder-dev-passcode")
    r = c.post("/v1/tenants/tenant-a/procurement/runs", json=target(a), headers=H(buyer, **{"Idempotency-Key": "http-run-0001"}))
    assert r.status_code == 202 and r.json()["status"] == "AWAITING_APPROVAL" and r.json()["side_effects"]["purchase_orders_created"] == 0
    corr = r.json()["corr_id"]
    again = c.post("/v1/tenants/tenant-a/procurement/runs", json=target(a), headers=H(buyer, **{"Idempotency-Key": "http-run-0001"}))
    assert again.status_code == 200 and again.json()["status"] == "DUPLICATE" and again.json()["duplicate_of"] == corr
    d = c.post(f"/v1/tenants/tenant-a/procurement/runs/{corr}/decision", json={"approve": True, "comment": "reviewed"}, headers=H(founder))
    assert d.status_code == 200 and d.json()["status"] == "EXECUTED" and d.json()["po_state"] == "DRAFT_NOT_SENT" and d.json()["side_effects"] == {"purchase_orders_created": 1, "external_transmissions": 0}
    replay = c.post(f"/v1/tenants/tenant-a/procurement/runs/{corr}/decision", json={"approve": True}, headers=H(founder))
    assert replay.status_code == 409 and replay.json()["error"]["code"] == "conflict"
    assert c.get(f"/v1/tenants/tenant-a/procurement/runs/{corr}", headers=H(buyer)).json()["state"] == "EXECUTED"


def test_authentication_authorisation_and_tenant_boundaries(api):
    c, sa, sb, a, b = api
    buyer_a, viewer_a, founder_b = sa.login("tenant-a-buyer", "tenant-a-buyer-dev-passcode"), sa.login("tenant-a-viewer", "tenant-a-viewer-dev-passcode"), sb.login("tenant-b-founder", "tenant-b-founder-dev-passcode")
    body = target(a)
    assert c.post("/v1/tenants/tenant-a/procurement/runs", json=body).status_code == 401
    assert c.post("/v1/tenants/tenant-a/procurement/runs", json=body, headers=H("not.valid")).status_code == 401
    assert c.post("/v1/tenants/tenant-a/procurement/runs", json=body, headers=H(founder_b)).status_code == 401           # another tenant's session
    r = c.post("/v1/tenants/tenant-a/procurement/runs", json=body, headers=H(viewer_a))
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    unknown = c.post("/v1/tenants/tenant-z/procurement/runs", json=body, headers=H(buyer_a))
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "not_found"
    run = c.post("/v1/tenants/tenant-a/procurement/runs", json=body, headers=H(buyer_a)).json()
    cross = c.get(f"/v1/tenants/tenant-b/procurement/runs/{run['corr_id']}", headers=H(founder_b))                          # A's run id inside B
    assert cross.status_code == 404
    assert c.post(f"/v1/tenants/tenant-b/procurement/runs/{run['corr_id']}/decision", json={"approve": True}, headers=H(founder_b)).status_code == 404
    assert sa.ledger.con.execute("SELECT count(*) FROM po_drafts").fetchone()[0] == 0


def test_validation_errors_use_the_single_error_envelope_and_never_leak(api):
    c, sa, sb, a, b = api
    t = sa.login("tenant-a-buyer", "tenant-a-buyer-dev-passcode")
    for bad in ({"location_id": "L01'; DROP TABLE x;--"}, {"location_id": "L01", "ingredient_id": "../etc/passwd"}, {"location_id": "L01", "extra": 1}, {}):
        r = c.post("/v1/tenants/tenant-a/procurement/runs", json=bad, headers=H(t))
        assert r.status_code == 422 and set(r.json()) == {"error"} and set(r.json()["error"]) == {"code", "message", "request_id"}
        assert "Traceback" not in r.text and "/home/" not in r.text and t not in r.text
    assert c.post("/v1/tenants/tenant-a/procurement/runs", json=target(a), headers=H(t, **{"Idempotency-Key": "short"})).status_code == 422


def test_pagination_has_a_hard_maximum_and_an_opaque_cursor(api):
    c, sa, sb, a, b = api
    t = sa.login("tenant-a-buyer", "tenant-a-buyer-dev-passcode")
    for i in range(3):
        c.post("/v1/tenants/tenant-a/procurement/runs", json=target(a), headers=H(t, **{"Idempotency-Key": f"page-key-{i:04d}"}))
    p1 = c.get("/v1/tenants/tenant-a/procurement/runs?limit=2", headers=H(t)).json()
    assert len(p1["items"]) == 2 and p1["next_cursor"] == "2"
    p2 = c.get(f"/v1/tenants/tenant-a/procurement/runs?limit=2&cursor={p1['next_cursor']}", headers=H(t)).json()
    assert len(p2["items"]) == 1 and p2["next_cursor"] is None and not {x["corr_id"] for x in p1["items"]} & {x["corr_id"] for x in p2["items"]}
    assert c.get("/v1/tenants/tenant-a/procurement/runs?limit=500", headers=H(t)).status_code == 422
    assert c.get("/v1/tenants/tenant-a/procurement/runs?cursor=abc", headers=H(t)).status_code == 422


def test_openapi_contract_is_stable_and_has_no_transmit_operation(api):
    c, *_ = api
    spec = c.get("/openapi.json").json()
    ops = sorted(f"{m.upper()} {p}" for p, v in spec["paths"].items() for m in v)
    assert ops == ["GET /v1/health", "GET /v1/ready", "GET /v1/tenants/{tenant}/procurement/runs", "GET /v1/tenants/{tenant}/procurement/runs/{corr_id}", "POST /v1/tenants/{tenant}/procurement/runs",
                   "POST /v1/tenants/{tenant}/procurement/runs/{corr_id}/decision"]
    assert not any(w in " ".join(spec["paths"]).lower() + " ".join(o.get("operationId", "") for v in spec["paths"].values() for o in v.values()).lower() for w in ("transmit", "send", "place_order", "submit"))
    assert set(spec["components"]["schemas"]["RunIn"]["required"]) == {"location_id"} and spec["components"]["schemas"]["RunIn"]["additionalProperties"] is False
