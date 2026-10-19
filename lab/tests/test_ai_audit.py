from nasha_lab.ai_audit import AuditLedger

def test_correlation_reconstructs_ordered_incident_without_payloads():
    ledger=AuditLedger()
    ledger.record(correlation_id="run-1",role="SENTINEL",kind="handoff",
                  payload={"private_supplier_quote":"SENSITIVE-VALUE"},duration_ms=1.2)
    ledger.record(correlation_id="run-2",role="ECHO",kind="handoff",payload={"other":2})
    ledger.record(correlation_id="run-1",role="THE WEIR",kind="policy_decision",
                  payload={"verdict":"APPROVE"})
    ledger.record(correlation_id="run-1",role="HUMAN",kind="approval_pending")
    rows=ledger.reconstruct("run-1")
    assert len(rows)==3
    assert [r.seq for r in rows]==[1,3,4]
    assert ledger.verify("run-1",required=("handoff","policy_decision","approval_pending"))
    assert not ledger.verify("run-1",required=("execution_authorized",))
    assert "SENSITIVE-VALUE" not in repr(rows)
    assert len(rows[0].payload_sha256)==64

def test_missing_audit_identity_rejected():
    import pytest
    with pytest.raises(ValueError):
        AuditLedger().record(correlation_id="",role="SENTINEL",kind="handoff")
