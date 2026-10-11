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
def load():
    if not os.path.exists(F): return {}
    out = {}
    for r in csv.DictReader(open(F, encoding="utf-8")):
        try: out[r["assumption_id"]] = float(r["value"])
        except (ValueError, KeyError): pass
    return out
def selftest():
    a = dict(covers=10, avg_check=10, food_cogs_pct=.3, bev_cogs_pct=.2, bev_mix_pct=.5, labor_monthly=1000, occupancy_monthly=500, other_fixed_monthly=500, days_open=30)
    r = pnl(a); assert r["revenue"] == 3000 and abs(r["cogs"] - 750) < 1e-9 and abs(r["ebitda"] - 250) < 1e-9
    assert sensitivity(a, "covers")[0.1] > sensitivity(a, "covers")[-0.1]
    print("selftest ok (TEST numbers only, not a NASHA result):", {k: round(v, 1) for k, v in r.items()})
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest(); sys.exit()
    a = load(); miss = [k for k in REQ if k not in a]
    if miss: print("NO MODEL RUN: missing required assumptions -> " + ", ".join(miss) + "\nNothing is invented; enter real or clearly marked scenario assumptions with a source and evidence tier."); sys.exit(2)
    print(pnl(a))
