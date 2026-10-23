"""Lead qualification: validate the recorded evidence, score it with the transparent rules in scoring.py, and produce an evidence-backed recommendation whose every reason cites an evidence id.
The validation gate re-derives the score from the cited evidence with its OWN arithmetic (not by calling scoring.py), so a recommendation that disagrees with its evidence is rejected.
This is a rule set over synthetic signals, not a validated model; the recommendation says so."""
from . import scoring

ALLOWED_SOURCE_PREFIX = "synthetic"
BOOLS = ("budget_confirmed", "decision_maker")


class InvalidEvidence(Exception):
    def __init__(self, problems):
        super().__init__("; ".join(problems)); self.problems = problems


def validate_signals(sig):
    """Raises InvalidEvidence unless the recorded signals are complete and in range."""
    bad = []
    if not isinstance(sig, dict):
        raise InvalidEvidence(["signals missing"])
    for k in BOOLS:
        if not isinstance(sig.get(k), bool):
            bad.append(f"{k} must be true or false")
    t = sig.get("timeline_days")
    if t is not None and (isinstance(t, bool) or not isinstance(t, int) or t < 0 or t > 3650):
        bad.append("timeline_days must be an integer 0..3650 or null")
    for k in ("fit", "engagement"):
        v = sig.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1:
            bad.append(f"{k} must be a number 0..1")
    extra = set(sig) - set(BOOLS) - {"timeline_days", "fit", "engagement"}
    if extra:
        bad.append(f"unknown signals: {sorted(extra)}")
    if bad:
        raise InvalidEvidence(bad)


def recommend(ctx):
    """ctx = get_lead_context() result. Returns a recommendation dict; raises InvalidEvidence for bad signals."""
    sig = ctx["signals"]
    validate_signals(sig)
    score, status = scoring.score_lead(sig)
    evidence = {"E1:lead.source": ctx["source"], "E2:contact.consent_status": ctx["consent_status"], "E3:contact.suppressed": ctx["suppressed"], "E4:lead.signals": sig, "E5:lead.version": ctx["lead_version"]}
    w = scoring.WEIGHTS
    t = sig.get("timeline_days")
    reasons = [dict(text=f"budget confirmed: {sig['budget_confirmed']}", evidence="E4:lead.signals", points=w["budget_confirmed"] if sig["budget_confirmed"] else 0),
               dict(text=f"decision maker: {sig['decision_maker']}", evidence="E4:lead.signals", points=w["decision_maker"] if sig["decision_maker"] else 0),
               dict(text=f"timeline {t} days", evidence="E4:lead.signals", points=w["timeline"] if t is not None and t <= 30 else (w["timeline"] // 2 if t is not None and t <= 90 else 0)),
               dict(text=f"fit {sig['fit']}", evidence="E4:lead.signals", points=round(w["fit"] * sig["fit"])), dict(text=f"engagement {sig['engagement']}", evidence="E4:lead.signals", points=round(w["engagement"] * sig["engagement"]))]
    return dict(action="APPLY_QUALIFICATION", lead_id=ctx["lead_id"], proposed_status=status, score=score, expected_lead_version=ctx["lead_version"], reasons=reasons, evidence=evidence,
                outreach_allowed=(ctx["consent_status"] == "opt_in" and not ctx["suppressed"]),
                notice="Rule-based score over synthetic signals; not a validated model. Qualifying a lead sends nothing and contacts no one.")


def validate_recommendation(rec, ctx):
    """Independent check: recompute the points from the cited evidence with separate arithmetic and compare; every reason must cite existing evidence; the proposal must match the context."""
    problems = []
    if rec.get("lead_id") != ctx["lead_id"] or rec.get("expected_lead_version") != ctx["lead_version"]:
        problems.append("proposal does not match the lead context")
    ev = rec.get("evidence") or {}
    for r in rec.get("reasons", []):
        if r["evidence"] not in ev:
            problems.append(f"reason cites unknown evidence {r['evidence']}")
    sig = ev.get("E4:lead.signals")
    try:
        validate_signals(sig)
    except InvalidEvidence as e:
        return problems + e.problems
    pts = (25 if sig["budget_confirmed"] else 0) + (20 if sig["decision_maker"] else 0)
    t = sig["timeline_days"]
    pts += 20 if (t is not None and t <= 30) else (10 if (t is not None and t <= 90) else 0)
    pts += round(20 * sig["fit"]) + round(15 * sig["engagement"])
    pts = max(0, min(100, pts))
    if rec.get("score") != pts or sum(r["points"] for r in rec["reasons"]) != pts:
        problems.append(f"score {rec.get('score')} does not follow from the evidence ({pts})")
    if rec.get("proposed_status") != ("qualified" if pts >= 60 else "disqualified"):
        problems.append("status does not follow from the score")
    if ev.get("E4:lead.signals") != ctx["signals"] or ev.get("E3:contact.suppressed") != ctx["suppressed"]:
        problems.append("evidence differs from the recorded context")
    return problems
