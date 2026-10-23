"""Transparent, rule-based lead scoring (NOT a learned model, NOT validated against real conversions). Weights are documented assumptions; a person reviews every score.
signals: dict with keys budget_confirmed(bool), decision_maker(bool), timeline_days(int|None), fit(0..1), engagement(0..1)."""
WEIGHTS = {"budget_confirmed": 25, "decision_maker": 20, "timeline": 20, "fit": 20, "engagement": 15}
QUALIFY_AT = 60


def score_lead(sig):
    s = 0
    s += WEIGHTS["budget_confirmed"] if sig.get("budget_confirmed") else 0
    s += WEIGHTS["decision_maker"] if sig.get("decision_maker") else 0
    t = sig.get("timeline_days")
    s += WEIGHTS["timeline"] if t is not None and t <= 30 else (WEIGHTS["timeline"] // 2 if t is not None and t <= 90 else 0)
    s += round(WEIGHTS["fit"] * max(0.0, min(1.0, sig.get("fit", 0.0))))
    s += round(WEIGHTS["engagement"] * max(0.0, min(1.0, sig.get("engagement", 0.0))))
    s = max(0, min(100, s))
    return s, ("qualified" if s >= QUALIFY_AT else "disqualified")
