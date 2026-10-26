"""M-OPS-1: the Operations explanation module must leave the governed procurement workflow exactly as it was. Using the real workflow (THE WEIR gateway, per-tenant ledger, real approvals): running explanations - accepted, abstained, rejected, failed - never changes a
proposal hash, never creates an audit row or side effect, never approves or executes anything, and the approval path (requester role denied, a different owner executes, replay refused) behaves as before. No model is called."""
import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
from nasha_lab.growth import ops_explanation as O, ops_explanation_eval as E  # noqa: E402
from test_growth_launch import dsn, make, project, q, tok, world  # noqa: E402,F401


def counts(world):  # noqa: F811
    return {t: q(world, f"SELECT count(*) FROM {t}")[0][0] for t in ("audit_log",)}


def explanations_of_every_kind():
    gap, miss = E.IN["gap"], E.IN["miss"]
    bad = E.edit(lambda o: E.claim(o, "c3").update(claimed_difference=1))(gap)
    yield O.explain(gap, lambda m: O.reference_output(m), audit_complete=True)
    yield O.explain(miss, lambda m: O.reference_output(m), audit_complete=True)
    yield O.explain(gap, lambda m: bad)
    yield O.explain(gap, lambda m: (_ for _ in ()).throw(TimeoutError()))
    yield O.explain(E.IN["poisoned"], lambda m: O.reference_output(m))
    yield O.deterministic_replay(gap, True)


def test_explanations_never_change_a_proposal_hash_never_write_and_never_approve(world):  # noqa: F811
    wf = make(world)
    r = wf.run(tok(wf, "ana"), project(world), 4)
    before = wf.status(r["corr_id"]); rows = counts(world)
    assert r["status"] == "AWAITING_APPROVAL" and r["side_effects"] == dict(orders_placed=0, suppliers_contacted=0, emails_sent=0)
    envelopes = [x["envelope"] for x in explanations_of_every_kind()]
    assert {e["status"] for e in envelopes} >= {"ACCEPTED", "ABSTAINED", "REJECTED", "FAILED"}
    after = wf.status(r["corr_id"])
    assert after["proposal_hash"] == before["proposal_hash"] and after["state"] == before["state"] == "AWAITING_APPROVAL" and after["agent_mode"] == before["agent_mode"]
    assert counts(world) == rows, "no audit row was written"
    assert not q(world, "SELECT 1 FROM audit_log WHERE action='procurement.record' AND entity_id=%s", (r["corr_id"],)), "nothing recorded: no explanation is an approval"
    # the approval path is exactly as before
    assert wf.decide(r["corr_id"], tok(wf, "ana"), True).get("failure") == "ROLE_DENIED"
    assert wf.decide(r["corr_id"], tok(wf, "ada"), True)["status"] == "EXECUTED"
    assert wf.decide(r["corr_id"], tok(wf, "omar"), True).get("failure") == "APPROVAL_REPLAY"
    wf.close()


def test_two_workflow_runs_have_identical_proposal_hashes_with_and_without_explanations_in_between(world):  # noqa: F811
    wf = make(world)
    h1 = wf.status(wf.run(tok(wf, "ana"), project(world), 4)["corr_id"])["proposal_hash"]
    list(explanations_of_every_kind())
    h2 = wf.status(wf.run(tok(wf, "ana"), project(world), 4)["corr_id"])["proposal_hash"]
    assert h1 == h2
    wf.close()


def test_a_model_explanation_cannot_alter_the_deterministic_fallback_of_a_workflow_run(world):  # noqa: F811
    wf = make(world)
    r = wf.run(tok(wf, "ana"), project(world), 4)
    st = wf.status(r["corr_id"])
    assert st["agent_mode"] == "deterministic_fallback"
    list(explanations_of_every_kind())
    assert wf.status(r["corr_id"])["agent_mode"] == "deterministic_fallback" and wf.status(r["corr_id"])["proposal_hash"] == st["proposal_hash"]
    wf.close()
