#!/usr/bin/env python3
"""Recorder for Core 5 physical sessions 2-5 (Sprint 17). Reads the FROZEN gates in food/sessions/sessions.json (D-76) and real results in
food/sessions/results.csv (header only until a real cook). Same discipline as tools/t1_record.py: only real_cook rows, every score row needs photo_ids and panel_n,
1-5 scale, 'NOT MEASURED' is allowed for measures but never invented, thresholds are never changed after tasting. n<8 = small directional R&D panel, raw values only.
  python3 tools/session_record.py report            evaluate every session (NOT PERFORMED when there are no rows)
  python3 tools/session_record.py hash              print the SHA-256 of the canonical gates JSON (recorded in D-76)
  python3 tools/session_record.py selftest
Row columns: run_id,date,dish_id,construction,iteration,time_min,kind(score|measure),gate_or_measure,value,failure_codes,photo_ids,panel_n,panel_roles,blinded,data_source,notes"""
import csv, hashlib, json, os, sys
SPEC, RES = "food/sessions/sessions.json", "food/sessions/results.csv"
COLS = ["run_id", "date", "dish_id", "construction", "iteration", "time_min", "kind", "gate_or_measure", "value", "failure_codes", "photo_ids", "panel_n", "panel_roles", "blinded", "data_source", "notes"]
MIN_ITER = 2
def spec(p=SPEC): return json.load(open(p, encoding="utf-8"))
def canonical(s):
    keep = ("constructions", "test_variable", "gates", "failure_gates", "times")   # protocol details (shopping, quantities, day plans, safety lines) may be corrected before tasting
    return json.dumps({"sessions": {k: {f: v[f] for f in keep} for k, v in s["sessions"].items()}, "scale": s["_meta"]["scale"]}, sort_keys=True, separators=(",", ":"))
def gates_hash(s): return hashlib.sha256(canonical(s).encode()).hexdigest()
def rows(p=RES): return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []
def problems(rs, s):
    errs = []
    for i, r in enumerate(rs, 2):
        d = r["dish_id"]
        if r["data_source"] != "real_cook": errs.append(f"row {i}: data_source must be real_cook"); continue
        if d not in s["sessions"]: errs.append(f"row {i}: unknown dish {d}"); continue
        ss = s["sessions"][d]
        if r["construction"] not in ss["constructions"] and not r["construction"].startswith("control"): errs.append(f"row {i}: unknown construction {r['construction']}")
        if r["kind"] == "score":
            if r["gate_or_measure"] not in ss["gates"]: errs.append(f"row {i}: unknown gate {r['gate_or_measure']}")
            try:
                v = float(r["value"]); assert 1 <= v <= 5
            except Exception: errs.append(f"row {i}: score must be 1-5 (never estimate or fill from memory)")
            if not r["photo_ids"].strip() or not r["panel_n"].strip(): errs.append(f"row {i}: score rows need photo_ids and panel_n")
        for c in filter(None, r["failure_codes"].replace(";", "|").split("|")):
            if c.strip() not in ss["failure_gates"]: errs.append(f"row {i}: unknown failure code {c}")
    return errs
def evaluate(rs, s):
    out = {}
    for d, ss in s["sessions"].items():
        mine = [r for r in rs if r["dish_id"] == d and r["data_source"] == "real_cook"]
        if not mine: out[d] = dict(status="NOT PERFORMED", detail={}); continue
        det = {}
        for c in sorted({r["construction"] for r in mine}):
            iters = {}
            for it in sorted({r["iteration"] for r in mine if r["construction"] == c}):
                cr = [r for r in mine if r["construction"] == c and r["iteration"] == it]
                fails = sorted({x.strip() for r in cr for x in r["failure_codes"].replace(";", "|").split("|") if x.strip()})
                miss, bad = [], []
                for g, spec_g in ss["gates"].items():
                    if spec_g.get("control_exempt") and c.startswith(("control", "A")) and d == "goat-birria" and c == "A": continue
                    vals = [float(r["value"]) for r in cr if r["kind"] == "score" and r["gate_or_measure"] == g and r["time_min"] == str(spec_g["at"])]
                    if not vals: miss.append(g)
                    elif sum(vals) / len(vals) < spec_g["min"]: bad.append(f"{g} {sum(vals)/len(vals):.2f}<{spec_g['min']}")
                iters[it] = dict(pass_=not miss and not bad and not fails, missing=miss, below=bad, failure_gates=fails)
            n_pass = sum(v["pass_"] for v in iters.values())
            det[c] = dict(iterations=iters, passing=n_pass, status=("PASSES (2+ iterations)" if n_pass >= MIN_ITER else "INCOMPLETE/REWORK: " + (f"{n_pass} passing iteration(s); need {MIN_ITER}" )))
        winners = [c for c, v in det.items() if v["passing"] >= MIN_ITER and not (d == "goat-birria" and c == "A")]
        status = "NO WINNER YET" if not winners else (f"WINNER CANDIDATE {winners[0]}" if len(winners) == 1 else "NO SINGLE WINNER (several qualify)")
        out[d] = dict(status=status, detail=det)
    return out
def selftest():
    s = spec()
    assert evaluate([], s)["paneer-tikka-taco"]["status"] == "NOT PERFORMED"
    g = s["sessions"]["paneer-tikka-taco"]["gates"]
    def mk(it, val, fail=""):
        rs = []
        for k, v in g.items(): rs.append(dict(run_id="T", date="x", dish_id="paneer-tikka-taco", construction="A", iteration=str(it), time_min=str(v["at"]), kind="score", gate_or_measure=k, value=str(val), failure_codes="", photo_ids="P1", panel_n="5", panel_roles="", blinded="no", data_source="real_cook", notes=""))
        if fail: rs[0]["failure_codes"] = fail
        return rs
    assert evaluate(mk(1, 4.5) + mk(2, 4.5), s)["paneer-tikka-taco"]["status"].startswith("WINNER")
    assert evaluate(mk(1, 4.5) + mk(2, 3.0), s)["paneer-tikka-taco"]["status"] == "NO WINNER YET"
    assert evaluate(mk(1, 4.5) + mk(2, 4.5, "RUBBERY"), s)["paneer-tikka-taco"]["status"] == "NO WINNER YET"
    bad = mk(1, 4.5); bad[0]["value"] = "9"; assert problems(bad, s)
    sim = mk(1, 4.5); sim[0]["data_source"] = "simulated"; assert problems(sim, s)
    print("selftest ok: NOT PERFORMED with no rows; 2 passing iterations win; a failing iteration or failure gate blocks; invalid and simulated rows rejected")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["selftest"]: selftest(); sys.exit()
    s = spec()
    if a[:1] == ["hash"]: print(gates_hash(s)); sys.exit()
    rs = rows(); errs = problems(rs, s)
    for e in errs: print("PROBLEM", e)
    for d, v in evaluate(rs, s).items():
        print(f"Session {s['sessions'][d]['session']} {s['sessions'][d]['dish']}: {v['status']}")
        for c, cv in v["detail"].items():
            print(f"   {c}: {cv['status']}")
            for it, iv in cv["iterations"].items(): print(f"      iteration {it}: {'PASS' if iv['pass_'] else 'NOT PASSING'} missing={iv['missing']} below={iv['below']} failure_gates={iv['failure_gates']}")
    sys.exit(1 if errs else 0)
