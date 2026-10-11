#!/usr/bin/env python3
"""Summarise real T1 kitchen results (food/t1-results/t1-results.csv). Never invents data: with no rows it reports NOT PERFORMED.
  python3 tools/t1_record.py report     summary per dish/construction/time, a winner ONLY if the pre-set rule below is met, concept-vs-real skeleton
  python3 tools/t1_record.py selftest   exercises the logic on in-memory TEST rows (never saved)"""
import csv, os, re, statistics, sys
P = "food/t1-results/t1-results.csv"
NUM = ["chicken_identity_0_5", "totopo_identity_0_5", "flavor_0_5", "aroma_0_5", "texture_0_5", "fusion_coherence_0_5", "crispness_0_5", "structural_integrity_0_5", "appearance_0_5", "repeatability_0_5"]
D54 = re.compile(r"\b(beef|pork|bacon|lard)\b", re.I)
MIN_ITER, MIN_CRISP10, MIN_ID, MIN_FUSION = 2, 3.0, 3.0, 3.0   # PROVISIONAL defaults; the founder must pre-set the real rule on sheet 07 BEFORE cooking and edit these

def validate(rows):
    errs = []
    for i, r in enumerate(rows, 2):
        if r["data_source"].strip() != "real_cook": errs.append(f"row {i}: data_source must be real_cook")
        if not r["photo_ids"].strip(): errs.append(f"row {i}: photo_ids required (no photographs, no evidence)")
        if r["time_min"] not in ("0", "5", "10"): errs.append(f"row {i}: time_min must be 0, 5 or 10")
        if D54.search(" ".join(r.values())): errs.append(f"row {i}: D-54 beef/pork mention")
        for k in NUM:
            if r[k].strip() and not re.fullmatch(r"[0-5](\.\d+)?", r[k].strip()): errs.append(f"row {i}: {k} must be 0-5")
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
        scores[(dish, con)] = dict(iters=iters, crisp10=mean(t10, "crispness_0_5"), idc=mean(rs, "chicken_identity_0_5"), idt=mean(rs, "totopo_identity_0_5"), fus=mean(rs, "fusion_coherence_0_5"))
    for dish in sorted({d for d, _ in scores}):
        ok = [(c, s) for (d, c), s in scores.items() if d == dish and s["iters"] >= MIN_ITER and (s["crisp10"] or 0) >= MIN_CRISP10 and min(s["idc"] or 0, s["idt"] or 0) >= MIN_ID and (s["fus"] or 0) >= MIN_FUSION]
        if len(ok) == 1: print(f"\n{dish}: candidate winner {ok[0][0]} (meets the provisional rule; confirm against the rule pre-set on the sheet)")
        else: print(f"\n{dish}: NO WINNER DECLARED ({len(ok)} construction(s) meet the rule with >= {MIN_ITER} iterations)")
    print("\nConcept vs real: complete food/t1-test-sheets/09-concept-vs-real-comparison.md; advance visual_stage to PROTOTYPE at most, with stage_evidence_ref set.")
    return 0

def selftest():
    base = {k: "" for k in "run_id,date,dish_id,construction,iteration,time_min,data_source,cook,chicken_identity_0_5,totopo_identity_0_5,flavor_0_5,aroma_0_5,texture_0_5,fusion_coherence_0_5,crispness_0_5,sauce_migration,structural_integrity_0_5,temp_c,portion_g,appearance_0_5,complexity_1_5,repeatability_0_5,failure_modes,photo_ids,notes".split(",")}
    good = dict(base, dish_id="TEST", construction="A", iteration="1", time_min="10", data_source="real_cook", photo_ids="TEST-1", crispness_0_5="4")
    assert not validate([good]); assert validate([dict(good, data_source="ai")]); assert validate([dict(good, photo_ids="")]); assert validate([dict(good, time_min="7")])
    print("t1_record selftest OK (TEST data, not saved)")

if len(sys.argv) > 1 and sys.argv[1] == "selftest": selftest(); sys.exit(0)
rows = list(csv.DictReader(open(P, encoding="utf-8"))) if os.path.exists(P) else []
sys.exit(report(rows))
