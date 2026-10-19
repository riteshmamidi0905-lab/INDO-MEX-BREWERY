from nasha_lab.ai_execution import investigate_inventory
from nasha_lab import knowledge

class Events:
    def __init__(self): self.rows = []
    def event(self, kind, **data): self.rows.append((kind, data))

def test_real_typed_inventory_handoffs(world):
    trace = Events()
    result = investigate_inventory(world, knowledge.default_kb(), "L01", "malt", trace=trace,
                                   correlation_id="scenario-001")
    assert result.correlation_id == "scenario-001"
    assert result.external_actions == 0
    assert result.steps
    assert result.steps[0].tool == "query_inventory"
    assert all(s.role in {"SENTINEL", "MERIDIAN"} for s in result.steps)
    assert all(s.elapsed_ms >= 0 for s in result.steps)
    assert trace.rows[-1][0] == "ai.final"
    assert all(e["correlation_id"] == "scenario-001" for _, e in trace.rows)

def test_invalid_location_fails_closed_and_does_not_continue(world):
    trace = Events()
    result = investigate_inventory(world, knowledge.default_kb(), "INVALID", "malt", trace=trace)
    assert result.status == "FAILED_CLOSED"
    assert len(result.steps) == 1
    assert result.steps[0].error_code == "INVALID_ARGUMENTS"
    assert result.external_actions == 0
    assert len([x for x in trace.rows if x[0] == "ai.handoff"]) == 1
