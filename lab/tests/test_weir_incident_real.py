"""Incident reconstruction acceptance against actual THE WEIR audit store."""
import asyncio
import sqlite3
import pytest

from nasha_lab.ai_audit import AuditLedger
from nasha_lab.specialist_workflows import execute
from nasha_lab.weir_incident import reconstruct
from test_weir_real_integration import make, TOOL, ARGS

def run(coro):
    return asyncio.run(coro)

def test_joined_handoffs_approval_execution_and_evaluation(tmp_path):
    now, store, world, gateway, session, adapter = make(tmp_path)
    ledger = AuditLedger()
    flow = execute("inventory_procurement", correlation_id=session.id, audit=ledger)
    assert flow.status == "REQUIRES_HUMAN_APPROVAL"
    pending = run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert pending.status == "APPROVE" and not world.effects
    assert store.resolve_approval(pending.approval_id, True) == "approved"
    executed = run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert executed.forwarded and len(world.effects) == 1
    events = [dict(correlation_id=e.correlation_id, kind=e.kind, role=e.role,
                   seq=e.seq, payload_sha256=e.payload_sha256)
              for e in ledger.reconstruct(session.id)]
    incident = reconstruct(session.id, weir_store=store, nasha_events=events, require_complete=True)
    assert incident.complete and incident.missing == ()
    assert incident.approvals_consumed == 1 and incident.protected_executions == 1
    assert [e["role"] for e in incident.events if e["system"] == "NASHA" and e["kind"] == "handoff"] == [
        h.role for h in flow.handoffs
    ]
    assert any(e["kind"] == "approval.consumed" for e in incident.events)
    assert any(e["kind"] == "call.result" for e in incident.events)
    assert any(e["kind"] == "final_outcome" for e in incident.events)

def test_missing_or_wrong_correlation_fails_strict_reconstruction(tmp_path):
    now, store, world, gateway, session, adapter = make(tmp_path)
    with pytest.raises(RuntimeError, match="incomplete"):
        reconstruct(session.id, weir_store=store, require_complete=True)
    with pytest.raises(ValueError, match="inconsistent"):
        reconstruct(session.id, weir_store=store,
                    nasha_events=[{"correlation_id": "other", "kind": "handoff"}],
                    require_complete=True)

def test_tampered_audit_chain_refused(tmp_path):
    now, store, world, gateway, session, adapter = make(tmp_path)
    run(adapter.invoke(TOOL, ARGS, correlation_id=session.id))
    assert store.verify_chain()[0]
    store._db.execute("UPDATE events SET payload=? WHERE seq=(SELECT MIN(seq) FROM events)",
                      ('{"tampered":true}',))
    assert not store.verify_chain()[0]
    with pytest.raises(RuntimeError, match="audit chain"):
        reconstruct(session.id, weir_store=store)
