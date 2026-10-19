import asyncio
from nasha_lab import knowledge
from nasha_lab.ai_execution import governed_inventory_action
from nasha_lab.weir_adapter import WeirAdapter
from types import SimpleNamespace

class Gateway:
    def __init__(self, approval=True):
        self.calls = []
        self.approval = approval
    async def call_tool_detailed(self, session, tool, args):
        self.calls.append((tool, args))
        return SimpleNamespace(forwarded=False, approval_id="approval-1" if self.approval else None,
                               call_id="c1", codes=["R-GATE-WRITE"], result={"isError":True})

def test_unconfigured_gateway_blocks_protected_action(world):
    r = asyncio.run(governed_inventory_action(world, knowledge.default_kb(), "L01", "malt",
                    adapter=None, action_tool="nasha__release_draft", action_args={"draft_id":"DR-example"}))
    assert r["status"] == "DENY"
    assert r["external_actions"] == 0

def test_unknown_protected_tool_does_not_reach_gateway(world):
    gateway = Gateway()
    adapter = WeirAdapter(gateway, object(), allowed_tools=frozenset())
    r = asyncio.run(governed_inventory_action(world, knowledge.default_kb(), "L01", "malt",
                    adapter=adapter, action_tool="nasha__release_draft", action_args={"draft_id":"DR-example"}))
    assert r["status"] == "DENY"
    assert r["external_actions"] == 0
    assert gateway.calls == []

def test_invalid_inventory_input_blocks_before_gateway(world):
    gateway = Gateway()
    adapter = WeirAdapter(gateway, object(), allowed_tools=frozenset({"nasha__release_draft"}))
    r = asyncio.run(governed_inventory_action(world, knowledge.default_kb(), "INVALID", "malt",
                    adapter=adapter, action_tool="nasha__release_draft", action_args={"draft_id":"DR-example"}))
    assert r["status"] == "DENY"
    assert r["reason"] == "INVESTIGATION_INCOMPLETE"
    assert gateway.calls == []
