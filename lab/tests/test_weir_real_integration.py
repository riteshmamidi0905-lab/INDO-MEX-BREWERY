"""Real NASHA -> THE WEIR integration acceptance: genuine Gateway, Store, policy and upstream.

Uses THE WEIR's *actual* in-process synthetic notes service (not a mocked
gateway). All effects are in-memory notes, never purchases or publications.
Dependency pinned in lab CI to a specific upstream commit.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mcp_weir.gateway import Gateway
from mcp_weir.policy import parse_policy
from mcp_weir.store import Store
from weir_testbed.servers import in_process_upstreams
from weir_testbed.world import World
from nasha_lab.weir_adapter import WeirAdapter
from nasha_lab.specialist_workflows import execute
from nasha_lab.weir_incident import reconstruct

TOOL = "notes__save_note"
ARGS = {"title": "synthetic procurement review", "body": "wheat malt reorder proposal only"}
POLICY = {
    "policy": {"name": "nasha-synthetic-approval", "internal_domains": ["corp.example"],
               "approval_ttl_seconds": 3},
    "rules": {"gate_write": "approve", "gate_egress": "deny",
              "flow_conf_secret": "deny", "untrusted_read": "approve"},
    "upstreams": {"notes": {"command": ["python", "-m", "weir_testbed.servers", "notes"]}},
    "tools": {
        "notes__save_note": {"effect": "write", "target": {"title": "other"}, "content": ["body"]},
        "notes__publish_note": {"effect": "egress", "content": ["title", "body"]},
    },
}


def run(coro):
    return asyncio.run(coro)


def make(tmp_path, *, clock=None):
    now = [100.0] if clock is None else clock
    store = Store(str(tmp_path / "weir.db"), clock=lambda: now[0])
    world = World.from_fixture({})
    policy = parse_policy(POLICY)
    gateway = Gateway(policy, store, {"notes": in_process_upstreams(world)["notes"]}, clock=lambda: now[0])
    run(gateway.start())
    session = gateway.open_session("nasha-correlation-001")
    adapter = WeirAdapter(gateway, session, allowed_tools=frozenset({TOOL}))
    return now, store, world, gateway, session, adapter


def test_real_gateway_scoped_approval_consumption_replay_and_audit(tmp_path):
    now, store, world, gateway, session, adapter = make(tmp_path)
    workflow = execute("inventory_procurement", correlation_id=session.id)
    assert workflow.status == "REQUIRES_HUMAN_APPROVAL"
    assert [h.role for h in workflow.handoffs] == [
        "SENTINEL", "PULSE", "MERIDIAN", "GUARDIAN", "LUMEN"
    ]
    first = run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert first.status == "APPROVE" and not first.forwarded and first.approval_id
    assert world.effects == []  # pending approval MUST NOT execute
    ap = store.get_approval(first.approval_id)
    assert ap.state == "pending" and ap.session_id == session.id and ap.tool == TOOL
    changed = run(adapter.invoke(TOOL, {**ARGS, "body": "changed"}, correlation_id=session.id))
    assert changed.status == "APPROVE" and not changed.forwarded
    assert changed.approval_id != first.approval_id and not world.effects
    other = gateway.open_session("another-caller")
    other_result = run(gateway.call_tool_detailed(other, TOOL, ARGS))
    assert not other_result.forwarded and other_result.approval_id != first.approval_id
    assert store.resolve_approval(first.approval_id, True)
    success = run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert success.status == "ALLOW" and success.forwarded
    assert len(world.effects) == 1 and world.effects[0]["op"] == "save"
    replay = run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert replay.status == "APPROVE" and not replay.forwarded
    assert replay.approval_id != first.approval_id and len(world.effects) == 1
    assert store.get_approval(first.approval_id).state == "consumed"
    assert store.verify_chain()[0]  # tamper-evident audit chain
    incident = reconstruct(session.id, weir_store=store)
    assert incident.chain_valid and incident.approvals_consumed == 1
    assert any(e["kind"] == "call.decision" for e in incident.events)
    assert any(e["kind"] == "call.result" for e in incident.events)
    assert store.get_approval(first.approval_id).session_id == workflow.correlation_id


def test_real_gateway_allow_deny_and_missing_permission(tmp_path):
    now, store, world, gateway, session, adapter = make(tmp_path)
    gateway.policy = gateway.policy.with_rules(gate_write="off")
    allowed = run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert allowed.status == "ALLOW" and allowed.forwarded
    assert len(world.effects) == 1
    denied = run(adapter.invoke("notes__publish_note", ARGS, correlation_id=session.id))
    assert denied.status == "DENY" and not denied.forwarded
    assert len(world.effects) == 1
    raw = run(gateway.call_tool_detailed(session, "notes__publish_note", ARGS))
    assert not raw.forwarded and "DENY" in raw.decision.verdict.name
    unknown = run(gateway.call_tool_detailed(session, "notes__nonexistent", {}))
    assert not unknown.forwarded and "R-UNKNOWN" in unknown.codes


def test_expired_approval_fails_closed(tmp_path):
    now, store, world, gateway, session, adapter = make(tmp_path)
    pending = run(adapter.invoke(TOOL, ARGS))
    assert pending.approval_id
    now[0] += 10
    # An expired approval must not permit execution, even if an operator attempts resolution.
    store.resolve_approval(pending.approval_id, True)
    expired = run(adapter.invoke(TOOL, ARGS))
    assert not expired.forwarded and not world.effects


def test_gateway_outage_and_direct_bypass_blocked(tmp_path):
    now, store, world, gateway, session, adapter = make(tmp_path)
    denied = run(adapter.invoke("notes__publish_note", ARGS))
    assert denied.status == "DENY" and not world.effects
    gateway.call_tool_detailed = None
    failed = run(adapter.invoke(TOOL, ARGS))
    assert failed.status == "DENY" and failed.codes == ("GATEWAY_UNAVAILABLE",)
    assert not world.effects
