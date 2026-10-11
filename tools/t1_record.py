#!/usr/bin/env python3
"""Summarise real T1 kitchen results (food/t1-results/t1-results.csv). Never invents data: with no rows it reports NOT PERFORMED.
  python3 tools/t1_record.py report     summary per dish/construction/time, a winner ONLY if the pre-set rule below is met, concept-vs-real skeleton
  python3 tools/t1_record.py selftest   exercises the logic on in-memory TEST rows (never saved)"""
import csv, os, re, statistics, sys
P = "food/t1-results/t1-results.csv"
NUM = ["chicken_identity_0_5", "totopo_identity_0_5", "flavor_0_5", "aroma_0_5", "texture_0_5", "fusion_coherence_0_5", "crispness_0_5", "structural_integrity_0_5", "appearance_0_5", "repeatability_0_5", "another_bite_0_5"]  # column names keep the legacy suffix; the scale is 1-5 (Sprint 12)
GATES = {"NOT_65", "NO_CORN", "SOGGY", "IMPRACTICAL", "COLLAPSE", "SAUCE_DOMINATES", "GENERIC_NACHOS", "UNRELATED_CHIPS", "D54", "UNSAFE"}
D54 = re.compile(r"\b(beef|veal|pork|bacon|ham|lard(?!-free)|tallow|suet|gelatin|gelatine|chicharron|chorizo)\b", re.I)
# FROZEN BEFORE COOKING (Sprint 12, 2026-10-11; founder's recommended starting rule, 1-5 scale; edit only BEFORE a test, with a decision-ledger note). Not industry standards.
FROZEN = dict(chicken_identity=4.0, totopo_identity=4.0, fusion=4.0, crisp10=3.5, structure=3.5, another_bite=4.0)
MIN_ITER = 2   # a construction needs this many iterations that pass EVERY gate

def validate(rows):
    errs = []
    for i, r in enumerate(rows, 2):
        if r["data_source"].strip() != "real_cook": errs.append(f"row {i}: data_source must be real_cook")
        if not r["photo_ids"].strip(): errs.append(f"row {i}: photo_ids required (no photographs, no evidence)")
        if r["time_min"] not in ("0", "5", "10"): errs.append(f"row {i}: time_min must be 0, 5 or 10")
        if not r.get("panel_n", "").strip(): errs.append(f"row {i}: panel_n required (n=5 scores are directional only)")
        if r["time_min"] == "10" and not r["failure_modes"].strip(): errs.append(f"row {i}: failure_modes must be filled at T+10 (write 'none observed' if true)")
        if D54.search(" ".join(r.values())): errs.append(f"row {i}: D-54 beef/pork mention")
        for k in NUM:
            if r[k].strip() and not re.fullmatch(r"[1-5](\.\d+)?", r[k].strip()): errs.append(f"row {i}: {k} must be on the 1-5 scale")
        for g in [x.strip() for x in r.get("gate_failures", "").split("|") if x.strip()]:
            if g not in GATES: errs.append(f"row {i}: unknown gate failure code {g} (allowed: {sorted(GATES)})")
    return errs

def mean(rows, k):
    v = [float(r[k]) for r in rows if r[k].strip()]
    return round(statistics.mean(v), 2) if v else None

def report(rows):
    if not rows: print("NOT PERFORMED: no real T1 results recorded. Evidence readiness cannot move."); return 0
    errs = validate(rows)
    for e in errs: print("FAIL", e)
    if errs: return 1
    groups = {}
    for r in rows: groups.setdefault((r["dish_id"], r["construction"]), []).append(r)
    scores = {}
    for (dish, con), rs in sorted(groups.items()):
        iters = len({r["iteration"] for r in rs}); print(f"\n{dish} / {con}: {iters} iteration(s), {len(rs)} rows")
        for t in ("0", "5", "10"):
            sub = [r for r in rs if r["time_min"] == t]
            if sub: print(f"  T+{t}: crispness {mean(sub,'crispness_0_5')}, flavour {mean(sub,'flavor_0_5')}, structure {mean(sub,'structural_integrity_0_5')}, sauce migration {sorted({r['sauce_migration'] for r in sub})}")
        t10 = [r for r in rs if r["time_min"] == "10"]
        passing = 0
        for it in {r["iteration"] for r in rs}:
            sub = [r for r in rs if r["iteration"] == it]; t10i = [r for r in sub if r["time_min"] == "10"]
            m = dict(crisp10=mean(t10i, "crispness_0_5"), structure=mean(t10i, "structural_integrity_0_5"), chicken_identity=mean(sub, "chicken_identity_0_5"), totopo_identity=mean(sub, "totopo_identity_0_5"), fusion=mean(sub, "fusion_coherence_0_5"), another_bite=mean(sub, "another_bite_0_5"))
            gate_fail = any(r.get("gate_failures", "").strip() for r in sub)
            if all(v is not None for v in m.values()) and all(m[k] >= FROZEN[k] for k in FROZEN) and not gate_fail: passing += 1
        scores[(dish, con)] = dict(iters=iters, passing=passing)
    for dish in sorted({d for d, _ in scores}):
        ok = [(c, s) for (d, c), s in scores.items() if d == dish and s["passing"] >= MIN_ITER]
        if len(ok) > 1: print(f"\n{dish}: SEVERAL constructions qualify ({', '.join(c for c, _ in ok)}): NO SINGLE WINNER; rank by margin and rework")
        elif len(ok) == 1: print(f"\n{dish}: candidate winner {ok[0][0]} (passed every FROZEN gate in 2 iterations with no failure-gate codes; with one cook and one panel this is directional, a PROMISING PROTOTYPE at best, not a validated dish)")
        else: print(f"\n{dish}: NO WINNER DECLARED ({len(ok)} construction(s) meet the rule with >= {MIN_ITER} iterations)")
    print("\nConcept vs real: complete food/t1-test-sheets/09-concept-vs-real-comparison.md; advance visual_stage to PROTOTYPE at most, with stage_evidence_ref set.")
    return 0

def selftest():
    base = {k: "" for k in open(P, encoding="utf-8").readline().strip().split(",")}
    good = dict(base, dish_id="TEST", construction="A", iteration="1", time_min="10", data_source="real_cook", photo_ids="TEST-1", crispness_0_5="4", panel_n="5", failure_modes="none observed", gate_failures="")
    assert not validate([good]); assert validate([dict(good, data_source="ai")]); assert validate([dict(good, photo_ids="")]); assert validate([dict(good, time_min="7")])
    import io, contextlib
    def rows_for(con, it, ok=True, gate=""):
        out = []
        for tm in ("0", "5", "10"):
            out.append(dict(good, construction=con, iteration=it, time_min=tm, chicken_identity_0_5="4.5" if ok else "3", totopo_identity_0_5="4.5", fusion_coherence_0_5="4.5", crispness_0_5="4", structural_integrity_0_5="4", another_bite_0_5="4.5", gate_failures=gate if tm == "10" else ""))
        return out
    def winner(rows):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): report(rows)
        return buf.getvalue()
    assert "candidate winner A" in winner(rows_for("A", "1") + rows_for("A", "2"))          # two passing iterations
    assert "NO WINNER" in winner(rows_for("A", "1") + rows_for("A", "2", ok=False))          # one failing iteration
    assert "NO WINNER" in winner(rows_for("A", "1") + rows_for("A", "2", gate="SOGGY"))      # failure gate
    assert "NO WINNER" in winner(rows_for("A", "1"))                                         # one iteration is never enough
    print("t1_record selftest OK (TEST data, not saved)")

if len(sys.argv) > 1 and sys.argv[1] == "selftest": selftest(); sys.exit(0)
rows = list(csv.DictReader(open(P, encoding="utf-8"))) if os.path.exists(P) else []
sys.exit(report(rows))
