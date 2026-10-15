import asyncio, json, logging
import pytest
from fastapi.testclient import TestClient
from mcp import Client
from nasha_lab import api, eval_agent as EA, mcp_server, tools as T, trace


@pytest.fixture()
def client():
    svc, w = EA.fresh()
    return TestClient(api.create_app(service=svc))


def test_health_ready_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok", "synthetic": True}
    r = client.get("/ready").json(); assert r["status"] == "ready" and r["orders"] > 3000 and r["knowledge_chunks"] > 500
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/agent/runs", "/agent/runs/{run_id}/approve", "/agent/runs/{run_id}/reject", "/traces/{run_id}", "/knowledge/ask", "/inventory/{ingredient}", "/quality/findings/{finding_id}"]: assert p in paths


def test_request_id_is_generated_and_echoed(client):
    assert client.get("/health").headers["x-request-id"].startswith("req-")
    assert client.get("/health", headers={"X-Request-ID": "mine-1"}).headers["x-request-id"] == "mine-1"


def test_error_contract_is_uniform(client):
    for r, code, st in [(client.get("/inventory/goat?location_id=ZZ"), "INVALID_REQUEST", 422), (client.get("/inventory/unobtainium?location_id=L01"), "NOT_FOUND", 404),
                        (client.get("/quality/findings/999999"), "NOT_FOUND", 404), (client.get("/agent/runs/nope"), "NOT_FOUND", 404), (client.post("/agent/runs", json={"event_id": "bad"}), "INVALID_REQUEST", 422),
                        (client.post("/agent/runs", json={"event_id": "EV-Z9"}), "UNKNOWN_EVENT", 404), (client.post("/knowledge/ask", json={"question": "x"}), "INVALID_REQUEST", 422)]:
        assert r.status_code == st and set(r.json()["error"]) == {"code", "message", "request_id"} and r.json()["error"]["code"] == code


def test_inventory_quality_and_knowledge_routes(client):
    inv = client.get("/inventory/goat?location_id=L01").json(); assert inv["days_of_cover"] < 3 and inv["unit"] == "kg"
    f = client.get("/quality/findings?rule=duplicate_order&limit=2").json()["findings"]; assert len(f) == 2 and client.get(f"/quality/findings/{f[0]['finding_id']}").json()["rule"] == "duplicate_order"
    a = client.post("/knowledge/ask", json={"question": "Is goat birria allowed under the dietary policy?"}).json(); assert not a["abstained"] and a["citations"]
    assert client.post("/knowledge/ask", json={"question": "What is the capital of France?"}).json()["abstained"]
    s = client.post("/knowledge/search", json={"query": "dietary policy beef pork", "k": 3}).json()["hits"]; assert s and all(h["effective_status"] not in {"SUPERSEDED", "UNVERIFIED", "VISION"} for h in s)


def test_full_flow_start_inspect_approve_trace(client):
    r = client.post("/agent/runs", json={"event_id": "EV-A1"}, headers={"X-Request-ID": "flow-1"}); assert r.status_code == 201
    run = r.json(); rid = run["run"]["run_id"]; assert run["awaiting_human"] and run["proposal"]["action"] == "DRAFT_PURCHASE_RECOMMENDATION"
    assert client.get(f"/agent/runs/{rid}").json()["awaiting_human"]
    done = client.post(f"/agent/runs/{rid}/approve", json={"reviewer": "founder", "note": "ok"}).json()
    assert done["final"]["outcome"] == "APPROVED_AND_EXECUTED_IN_SIMULATION"
    tr = client.get(f"/traces/{rid}").json()["events"]; assert tr[0]["request_id"] == "flow-1" and tr[-1]["kind"] == "final"
    assert client.post(f"/agent/runs/{rid}/approve", json={"reviewer": "founder"}).status_code == 409


def test_reject_and_review_edit_routes(client):
    rid = client.post("/agent/runs", json={"event_id": "EV-A1"}).json()["run"]["run_id"]
    r = client.post(f"/agent/runs/{rid}/review", json={"decision": "edit", "reviewer": "founder", "edits": {"qty_kg": 30}}).json(); assert r["awaiting_human"] and not r["proposal"].get("edit_error")
    assert client.post(f"/agent/runs/{rid}/reject", json={"reviewer": "founder"}).json()["final"]["outcome"] == "REJECTED_BY_HUMAN_NO_ACTION"
    assert client.post(f"/agent/runs/{rid}/review", json={"decision": "approve_all", "reviewer": "x"}).status_code == 422


def test_duplicate_event_is_idempotent_over_http(client):
    a = client.post("/agent/runs", json={"event_id": "EV-B1"}); b = client.post("/agent/runs", json={"event_id": "EV-B1"})
    assert a.status_code == 201 and b.status_code == 200 and b.json()["status"] == "DUPLICATE_IGNORED"


def test_requests_are_logged_as_structured_json(client, caplog):
    with caplog.at_level(logging.INFO, logger="nasha.api"):
        client.get("/health", headers={"X-Request-ID": "log-1"})
    rec = [json.loads(r.message) for r in caplog.records if r.name == "nasha.api"]
    assert rec and rec[0]["request_id"] == "log-1" and rec[0]["path"] == "/health" and rec[0]["status"] == 200 and "ms" in rec[0]


# ------------------------------------------------------------------ MCP
def mcp(fn):
    svc, w = EA.fresh()
    async def go():
        async with Client(mcp_server.build_server(w, svc.rt.kb, trace.Store())) as c: return await fn(c, w)
    return asyncio.run(go())


def test_mcp_lists_exactly_the_allowlisted_tools_with_schemas_and_no_mutations():
    async def f(c, w): return await c.list_tools()
    tools = mcp(f).tools
    assert [t.name for t in tools] == list(mcp_server.MCP_TOOLS)
    assert all(t.description.startswith("[") and "SYNTHETIC" in t.description and t.input_schema for t in tools)
    names = {t.name for t in tools}
    assert not names & {"adjust_inventory_record", "flag_record_for_review", "release_draft", "contact_supplier", "place_purchase_order"}


def test_mcp_call_returns_structured_results_and_structured_errors():
    async def f(c, w):
        ok = await c.call_tool("query_inventory", {"location_id": "L01", "ingredient": "goat"})
        bad = await c.call_tool("query_inventory", {"location_id": "L01", "ingredient": "unobtainium"})
        pol = await c.call_tool("get_current_policy", {"question": "Is beef allowed under the dietary policy?"})
        return ok.structured_content, bad.structured_content, pol.structured_content
    ok, bad, pol = mcp(f)
    assert ok["ok"] and ok["permission"] == T.READ and ok["data"]["days_of_cover"] < 3
    assert not bad["ok"] and bad["error"]["code"] == "NOT_FOUND"
    assert pol["ok"] and any(c["document_id"] == "D-54" for c in pol["data"]["citations"])


def test_mcp_draft_tool_enforces_validation_and_creates_no_order():
    async def f(c, w):
        r = await c.call_tool("draft_purchase_recommendation", dict(location_id="L01", ingredient="goat", qty_kg=1, supplier_id="S02", rationale="too small a quantity", evidence_ids=["E1"]))
        g = await c.call_tool("draft_purchase_recommendation", dict(location_id="L01", ingredient="goat", qty_kg=15, supplier_id="S02", rationale="cover below lead time", evidence_ids=["E1"]))
        return r.structured_content, g.structured_content, w.q("SELECT COUNT(*) n FROM purchase_orders")[0]["n"]
    bad, good, npo = mcp(f)
    assert bad["error"]["code"] == "REJECTED" and good["data"]["status"] == "DRAFT_NOT_SUBMITTED" and npo == 3


def test_mcp_calls_are_traced():
    svc, w = EA.fresh(); store = trace.Store()
    async def go():
        async with Client(mcp_server.build_server(w, svc.rt.kb, store)) as c: await c.call_tool("get_supplier_status", {"supplier_id": "S02"})
    asyncio.run(go())
    runs = store.con.execute("SELECT DISTINCT run_id FROM trace_events").fetchall()
    assert len(runs) == 1 and store.events(runs[0][0])[0]["tool"] == "get_supplier_status"
