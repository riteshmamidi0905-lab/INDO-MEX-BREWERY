import asyncio
from types import SimpleNamespace
import pytest
from nasha_lab.weir_adapter import WeirAdapter

class RecordingGateway:
    def __init__(self, outcome=None, error=None):
        self.calls = []
        self.outcome, self.error = outcome, error
    async def call_tool_detailed(self, session, name, arguments):
        self.calls.append((session, name, arguments))
        if self.error:
            raise self.error
        return self.outcome

def outcome(*, forwarded=False, approval_id=None, is_error=False):
    return SimpleNamespace(forwarded=forwarded, approval_id=approval_id, call_id="c1",
                           codes=[], result={"isError": is_error})

def invoke(gateway, tool="nasha__query_inventory", args=None, allowed=None):
    adapter = WeirAdapter(gateway, object(), allowed_tools=frozenset(
        allowed if allowed is not None else {"nasha__query_inventory"}))
    return asyncio.run(adapter.invoke(tool, args if args is not None else {"location_id":"L01","ingredient":"malt"}, correlation_id="test-correlation"))

def test_missing_gateway_is_rejected():
    with pytest.raises(ValueError):
        WeirAdapter(None, object(), allowed_tools=frozenset())

def test_unauthorized_tool_never_reaches_gateway():
    g = RecordingGateway(outcome(forwarded=True))
    result = invoke(g, "nasha__release_draft")
    assert result.status == "DENY" and not result.forwarded
    assert not g.calls

def test_pending_approval_is_not_execution():
    g = RecordingGateway(outcome(approval_id="ap-1"))
    result = invoke(g)
    assert result.status == "APPROVE" and not result.forwarded
    assert result.approval_id == "ap-1"
    assert len(g.calls) == 1

def test_upstream_error_fails_closed():
    g = RecordingGateway(error=RuntimeError("secret token"))
    result = invoke(g)
    assert result.status == "DENY" and not result.forwarded
    assert result.codes == ("GATEWAY_UNAVAILABLE",)
    assert "secret" not in repr(result)

def test_forwarded_error_is_not_authorized_success():
    g = RecordingGateway(outcome(forwarded=True, is_error=True))
    result = invoke(g)
    assert result.status == "DENY" and not result.forwarded

def test_allowed_forwarded_call_reports_success():
    g = RecordingGateway(outcome(forwarded=True))
    result = invoke(g)
    assert result.status == "ALLOW" and result.forwarded
    assert result.correlation_id == "test-correlation"
    assert len(g.calls) == 1
