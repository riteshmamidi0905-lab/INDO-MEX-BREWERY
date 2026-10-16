"""P3 product case: NEW tests that back user stories the existing suite did not cover (SYNTHETIC; the deterministic agent only; no model).

US-06 / US-07 are about the non-AI baseline's behaviour at its weak spot (D-54 lexicon gap): the system must never turn "no signal" into a clearance,
and must say plainly that "no signal" is not "allowed". The first part is TRUE today and is tested; the second part is NOT met today and is pinned as a gap.
"""
import pytest

from nasha_lab import eval_agent as EA, scenarios as S


def _policy_run(text, source="animal source unspecified", spec="MISSING"):
    svc, w = EA.fresh()
    pid = S.add_proposal(w, text, source, spec)
    eid = S.add_event(w, "POLICY_REVIEW", dict(proposal_id=pid)); w.con.commit()
    s = svc.start(eid, "p3-story")
    return svc, w, s


@pytest.mark.parametrize("term", ["suet", "pepperoni", "pancetta", "gelatine", "oxtail"])
def test_us06_out_of_lexicon_derivative_is_never_cleared_by_the_system(term):
    svc, w, s = _policy_run(term)
    prop = s["proposal"]
    assert prop["action"] == "ABSTAIN_REQUIRE_REVIEW" and prop["abstain"] is True        # the system does not infer allowed, and does not recommend confirming
    assert s["awaiting_human"]
    assert "do not infer that it is allowed or prohibited" in prop["headline"]
    assert w.q("SELECT COUNT(*) n FROM drafts WHERE status<>'DRAFT_NOT_SUBMITTED'")[0]["n"] == 0


def test_us06_even_with_a_supplier_statement_naming_a_permitted_source_the_outcome_is_human_confirmation_not_approval():
    svc, w, s = _policy_run("vegetable shortening for frying", "vegetable oil (supplier statement on file)", "ON_FILE")
    assert s["proposal"]["action"] == "RECOMMEND_HUMAN_CONFIRM_SPEC" and s["awaiting_human"]


def test_us07_GAP_the_screening_claim_for_an_unknown_term_still_reads_like_a_clean_result():
    """NOT MET TODAY (pinned, not hidden): the headline already says 'do not infer that it is allowed or prohibited', but the evidence claim line says
    'Screening verdict NO_POLICY_SIGNAL: no D-54 term and no hidden-derivative term', which reads clean although the lexicon has 14 tokens.
    Requirement FR-13 asks for explicit 'lexicon found nothing; not a clearance' wording on that line.
    When the wording is fixed this test must fail and be replaced by the positive assertion."""
    svc, w, s = _policy_run("suet")
    texts = " ".join(c["text"] for c in s["proposal"]["claims"]).lower()
    assert "no_policy_signal" in texts
    assert "not a clearance" not in texts and "does not mean allowed" not in texts
