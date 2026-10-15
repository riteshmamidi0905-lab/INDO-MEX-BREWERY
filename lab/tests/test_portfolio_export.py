"""The public portfolio vendors portfolio-evidence.json; it must be fresh and carry only what the committed results say."""
import json

from nasha_lab import export_portfolio as XP


def test_portfolio_evidence_is_fresh_and_consistent():
    assert XP.main(["--check"]) == 0
    e = json.loads(XP.OUT.read_text()); p = {x["id"]: x for x in e["planners"]}
    assert p["det"]["pass_"] == dict(k=259, n=259) and p["q15r2"]["pass_"] == dict(k=5, n=140) and p["q7"]["pass_"] == dict(k=10, n=35)
    assert all(x["external_actions"] == 0 for x in e["planners"])
    assert [r["id"] for r in e["retrieval"]["table"]][:3] == ["bm25", "lsa", "hybrid"]                     # identified by position, not by the mislabelled text (results/ERRATA.md)
    assert e["trace_sample"]["untrusted_note_shown_as_untrusted"] and e["trace_sample"]["proposal_action"] == "ESCALATE_SUPPLIER_UNAVAILABLE"
    assert e["mutation"]["killed"] == e["mutation"]["valid"] == 22 and e["mutation"]["first_run_killed"] == 19


def test_ledger_prohibits_the_overclaims_the_portfolio_must_not_make():
    e = json.loads(XP.OUT.read_text()); text = " ".join(e["prohibited_claims"]).lower()
    for k in ("customers", "employment", "independent", "frontier", "trademark"): assert k in text
