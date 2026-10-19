import pytest
from nasha_lab.specialist_workflows import execute

@pytest.mark.parametrize("workflow,roles",[
    ("seasonal_beer",["ATLAS","SCRIBE","BREWMASTER","SENTINEL","MERIDIAN","PULSE","FORGE","GUARDIAN","LUMEN","NEXUS"]),
    ("inventory_procurement",["SENTINEL","PULSE","MERIDIAN","GUARDIAN","LUMEN"]),
    ("customer_marketing",["ECHO","PULSE","ATLAS","SPARK","GUARDIAN","LUMEN","NEXUS"]),
])
def test_all_workflows_execute_real_specialists_with_dependencies(workflow,roles):
    result=execute(workflow,correlation_id="synthetic-e2e")
    assert result.status=="REQUIRES_HUMAN_APPROVAL"
    assert result.correlation_id=="synthetic-e2e"
    assert result.external_actions==0 and result.approval_required
    assert [s.role for s in result.handoffs]==roles
    assert all(s.status=="OK" and s.evaluation["valid"] for s in result.handoffs)
    again=execute(workflow,correlation_id="synthetic-e2e")
    assert result.handoffs==again.handoffs

def test_unknown_workflow_rejected():
    with pytest.raises(ValueError):
        execute("real_external_procurement")


def test_workflow_incident_can_be_reconstructed_from_audit():
    from nasha_lab.ai_audit import AuditLedger
    ledger=AuditLedger()
    result=execute("customer_marketing",correlation_id="incident-123",audit=ledger)
    events=ledger.reconstruct("incident-123")
    assert len(events)==len(result.handoffs)+1
    assert [e.role for e in events[:-1]]==[r.role for r in result.handoffs]
    assert events[-1].kind=="final_outcome"
    assert ledger.verify("incident-123",required=("handoff","final_outcome"))
    assert not ledger.verify("incident-123",required=("policy_decision","execution_authorized"))
