#!/usr/bin/env python3
"""Restaurant/brewery scenario model skeleton (Sprint 14). Reads ops/finance/assumptions.csv (header only today) and REFUSES to compute when any required
input is missing: it never invents revenue, costs, rent, labor or prices. Output is arithmetic on stated assumptions, not a forecast.
  python3 tools/fin_model.py            check required inputs
  python3 tools/fin_model.py selftest   monthly P&L, break-even and sensitivity on in-memory TEST numbers (never saved)
Required assumption_ids: covers, avg_check, food_cogs_pct, bev_cogs_pct, bev_mix_pct, labor_monthly, occupancy_monthly, other_fixed_monthly, days_open"""
import csv, os, sys
F = "ops/finance/assumptions.csv"; REQ = ["covers","avg_check","food_cogs_pct","bev_cogs_pct","bev_mix_pct","labor_monthly","occupancy_monthly","other_fixed_monthly","days_open"]
def pnl(a):
    rev = a["covers"] * a["avg_check"] * a["days_open"]; cogs = rev * ((1 - a["bev_mix_pct"]) * a["food_cogs_pct"] + a["bev_mix_pct"] * a["bev_cogs_pct"])
    fixed = a["labor_monthly"] + a["occupancy_monthly"] + a["other_fixed_monthly"]
    cm = rev - cogs; be_rev = fixed / (cm / rev) if cm > 0 else float("inf")
    return dict(revenue=rev, cogs=cogs, gross_profit=cm, fixed=fixed, ebitda=cm - fixed, breakeven_revenue=be_rev)
def sensitivity(a, key, deltas=(-.1, 0, .1)): return {d: round(pnl({**a, key: a[key] * (1 + d)})["ebitda"], 2) for d in deltas}
SCENARIOS = ("mobile_mvp", "popup", "brewery_residency", "small_permanent", "flagship")
def load(scenario=None):
    """Assumptions for one scenario (rows whose 'scenario' column equals it); rows with an empty scenario apply to every scenario. No defaults."""
    if not os.path.exists(F): return {}
    out = {}
    for r in csv.DictReader(open(F, encoding="utf-8")):
        sc = (r.get("scenario") or "").strip()
        if sc and scenario and sc != scenario: continue
        if (r.get("provenance_class") or "").strip().upper() == "UNKNOWN": continue   # UNKNOWN is the default and never feeds a model; only QUOTE/ACTUAL rows may feed investor-facing output, FOUNDER ASSUMPTION / INDUSTRY or PUBLIC REFERENCE rows only sensitivity ranges and must be labelled
        try: out[r["assumption_id"]] = float(r["value"])
        except (ValueError, KeyError): pass
    return out
def run_all(rows=None):
    rows = rows if rows is not None else list(csv.DictReader(open(F, encoding="utf-8"))) if os.path.exists(F) else []
    res = {}
    for sc in SCENARIOS:
        a = {}
        for r in rows:
            scn = (r.get("scenario") or "").strip()
            if scn and scn != sc: continue
            try: a[r["assumption_id"]] = float(r["value"])
            except (ValueError, KeyError): pass
        miss = [k for k in REQ if k not in a]
        res[sc] = {"status": "NOT RUN", "missing": miss} if miss else {"status": "RUN", **pnl(a)}
    return res
def selftest():
    a = dict(covers=10, avg_check=10, food_cogs_pct=.3, bev_cogs_pct=.2, bev_mix_pct=.5, labor_monthly=1000, occupancy_monthly=500, other_fixed_monthly=500, days_open=30)
    r = pnl(a); assert r["revenue"] == 3000 and abs(r["cogs"] - 750) < 1e-9 and abs(r["ebitda"] - 250) < 1e-9
    assert sensitivity(a, "covers")[0.1] > sensitivity(a, "covers")[-0.1]
    rows = [dict(assumption_id=k, value=str(v), scenario="popup") for k, v in a.items()]
    out = run_all(rows); assert out["popup"]["status"] == "RUN" and out["flagship"]["status"] == "NOT RUN" and out["mobile_mvp"]["status"] == "NOT RUN"
    print("selftest ok (TEST numbers only, not a NASHA result):", {k: round(v, 1) for k, v in r.items()})
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest(); sys.exit()
    res = run_all(); ran = {k: v for k, v in res.items() if v["status"] == "RUN"}
    for k, v in res.items(): print(k, "RUN" if v["status"] == "RUN" else "NOT RUN (missing: " + ", ".join(v["missing"][:3]) + ("..." if len(v["missing"]) > 3 else "") + ")")
    if not ran: print("NO MODEL RUN: nothing is invented; enter real or clearly marked scenario assumptions (assumption_id, value, scenario, source, tier)."); sys.exit(2)
    for k, v in ran.items(): print(k, {a: round(b, 1) for a, b in v.items() if a != "status"})
