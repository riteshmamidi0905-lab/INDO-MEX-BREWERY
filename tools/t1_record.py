#!/usr/bin/env python3
"""Summarise real T1 kitchen results (food/t1-results/t1-results.csv). Never invents data: with no rows it reports NOT PERFORMED.
  python3 tools/t1_record.py report     summary per dish/construction/time, a winner ONLY if the pre-set rule below is met, concept-vs-real skeleton
  python3 tools/t1_record.py selftest   exercises the logic on in-memory TEST rows (never saved)"""
import csv, os, re, statistics, sys
P = "food/t1-results/t1-results.csv"
NUM = ["chicken_identity_0_5", "totopo_identity_0_5", "flavor_0_5", "aroma_0_5", "texture_0_5", "fusion_coherence_0_5", "crispness_0_5", "structural_integrity_0_5", "appearance_0_5", "repeatability_0_5"]
D54 = re.compile(r"\b(beef|veal|pork|bacon|ham|lard|tallow|suet|gelatin|gelatine|chicharron|chorizo)\b", re.I)
MIN_ITER, MIN_CRISP10, MIN_ID, MIN_FUSION = 2, 3.5, 3.5, 3.5   # PROVISIONAL defaults (chef review); the real rule must be pre-set on sheet 07 BEFORE cooking and edited here. An iteration passes only if EVERY gate is met; a construction needs 2 passing iterations.

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
        passing = 0
        for it in {r["iteration"] for r in rs}:
            sub = [r for r in rs if r["iteration"] == it]; t10i = [r for r in sub if r["time_min"] == "10"]
            vals = [mean(t10i, "crispness_0_5"), mean(sub, "chicken_identity_0_5"), mean(sub, "totopo_identity_0_5"), mean(sub, "fusion_coherence_0_5")]
            bad = any(r["failure_modes"].strip().lower() not in ("", "none observed", "none") for r in t10i)
            if all(v is not None for v in vals) and vals[0] >= MIN_CRISP10 and min(vals[1:3]) >= MIN_ID and vals[3] >= MIN_FUSION and not bad: passing += 1
        scores[(dish, con)] = dict(iters=iters, passing=passing)
    for dish in sorted({d for d, _ in scores}):
        ok = [(c, s) for (d, c), s in scores.items() if d == dish and s["passing"] >= MIN_ITER]
        if len(ok) == 1: print(f"\n{dish}: candidate winner {ok[0][0]} (passed every gate in 2 iterations; with one cook and one panel this is directional, PROTOTYPE at best)")
        else: print(f"\n{dish}: NO WINNER DECLARED ({len(ok)} construction(s) meet the rule with >= {MIN_ITER} iterations)")
    print("\nConcept vs real: complete food/t1-test-sheets/09-concept-vs-real-comparison.md; advance visual_stage to PROTOTYPE at most, with stage_evidence_ref set.")
    return 0

def selftest():
    base = {k: "" for k in "run_id,date,dish_id,construction,iteration,time_min,data_source,cook,chicken_identity_0_5,totopo_identity_0_5,flavor_0_5,aroma_0_5,texture_0_5,fusion_coherence_0_5,crispness_0_5,sauce_migration,structural_integrity_0_5,temp_c,portion_g,appearance_0_5,complexity_1_5,repeatability_0_5,failure_modes,photo_ids,notes".split(",")}
    good = dict(base, dish_id="TEST", construction="A", iteration="1", time_min="10", data_source="real_cook", photo_ids="TEST-1", crispness_0_5="4", panel_n="5", failure_modes="none observed")
    assert not validate([good]); assert validate([dict(good, data_source="ai")]); assert validate([dict(good, photo_ids="")]); assert validate([dict(good, time_min="7")])
    print("t1_record selftest OK (TEST data, not saved)")

if len(sys.argv) > 1 and sys.argv[1] == "selftest": selftest(); sys.exit(0)
rows = list(csv.DictReader(open(P, encoding="utf-8"))) if os.path.exists(P) else []
sys.exit(report(rows))
