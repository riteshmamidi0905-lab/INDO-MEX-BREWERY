"""Ops AI warehouse tools behind the REAL THE WEIR gateway (mcp_weir.gateway.Gateway, Store, parse_policy). SYNTHETIC. Skips with a reason if THE WEIR is not installed."""
import asyncio
import json
import sqlite3

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("weir_testbed", reason="INTEGRATION UNAVAILABLE: weir_testbed not installed")
from mcp_weir.gateway import Gateway
from mcp_weir.policy import parse_policy
from mcp_weir.store import Store
from weir_testbed.servers import in_process_upstreams
from weir_testbed.world import World

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import ops_ai_weir as W, pipeline
from nasha_lab.warehouse.ops_ai import OpsAI, Principal

CFG = es.SimConfig(name="weir-test", months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_000, employees=60, open_at_start=3)
run = asyncio.run


@pytest.fixture(scope="module")
def wh(tmp_path_factory):
    d = tmp_path_factory.mktemp("w"); es.generate(CFG, d / "src"); pipeline.run(d / "src", d / "w.db"); return d / "w.db"


def make(wh, tmp_path, who):
    ops = OpsAI(wh, tmp_path / "ops.audit.db")
    world = World.from_fixture({})
    store = Store(str(tmp_path / "weir.db"))
    gw = Gateway(parse_policy(W.policy()), store, {"warehouse": W.OpsAIUpstream(ops, who), "notes": in_process_upstreams(world)["notes"]})
    run(gw.start())
    return ops, store, world, gw, gw.open_session("ops-session-1")


def month(wh):
    c = sqlite3.connect(wh); m = c.execute("SELECT month FROM mart_company_month ORDER BY month").fetchall()[1][0]; c.close(); return m


def test_allowed_read_flows_through_both_layers_and_audits_join(wh, tmp_path):
    ops, store, world, gw, s = make(wh, tmp_path, Principal("e", "exec"))
    m = month(wh)
    out = run(gw.call_tool_detailed(s, "warehouse__company_month", {"month": m}))
    assert out.forwarded and not out.result["isError"]
    rows = json.loads(out.result["content"][0]["text"])["rows"]
    assert rows == ops.call(Principal("e", "exec"), "company_month", {"month": m})["rows"]       # same answer as the direct call
    assert store.verify_chain()[0]
    j = W.joined_audit(store, s.id, ops)
    assert len(j) == 1 and j[0]["verdict"] == "ALLOW" and j[0]["ops_call_id"]


def test_weir_blocks_unknown_and_egress_before_the_upstream_runs(wh, tmp_path):
    ops, store, world, gw, s = make(wh, tmp_path, Principal("e", "exec"))
    unknown = run(gw.call_tool_detailed(s, "warehouse__drop_tables", {}))
    assert not unknown.forwarded
    before = ops.audit.execute("SELECT count(*) FROM ops_ai_audit").fetchone()[0]
    assert before == 0                                                    # nothing reached the Ops AI layer
    m = month(wh)
    run(gw.call_tool_detailed(s, "warehouse__company_month", {"month": m}))     # session now holds `internal` data
    pub = run(gw.call_tool_detailed(s, "notes__publish_note", {"title": "totals", "body": "net sales ..."}))
    assert not pub.forwarded and "R-GATE" in pub.codes and world.effects == []


def test_ops_layer_still_enforces_role_and_site_behind_an_allowing_gateway(wh, tmp_path):
    c = sqlite3.connect(wh); ids = [r[0] for r in c.execute("SELECT location_id FROM dim_location ORDER BY 1")]; c.close()
    ops, store, world, gw, s = make(wh, tmp_path, Principal("sm", "site_manager", ids[0]))
    m = month(wh)
    ok = run(gw.call_tool_detailed(s, "warehouse__location_month", {"month": m, "location_id": ids[0]}))
    other = run(gw.call_tool_detailed(s, "warehouse__location_month", {"month": m, "location_id": ids[1]}))
    ranking = run(gw.call_tool_detailed(s, "warehouse__rank_locations", {"month": m, "metric": "net_cents"}))
    assert ok.forwarded and not ok.result["isError"]
    assert other.forwarded and other.result["isError"] and "site_scope" in other.result["content"][0]["text"]   # WEIR allowed it; Ops AI denied it
    assert ranking.result["isError"] and "role_denied" in ranking.result["content"][0]["text"]
    assert dict(ops.audit.execute("SELECT code, count(*) FROM ops_ai_audit GROUP BY 1")) == {"ok": 1, "site_scope": 1, "role_denied": 1}


def test_write_tools_need_approval_and_nothing_executes_while_pending(wh, tmp_path):
    ops, store, world, gw, s = make(wh, tmp_path, Principal("e", "exec"))
    out = run(gw.call_tool_detailed(s, "notes__save_note", {"title": "weekly review", "body": "draft"}))
    assert not out.forwarded and out.approval_id and world.effects == []
    assert store.resolve_approval(out.approval_id, True) == "approved"
    again = run(gw.call_tool_detailed(s, "notes__save_note", {"title": "weekly review", "body": "draft"}))
    assert again.forwarded and len(world.effects) == 1
    assert store.verify_chain()[0]
