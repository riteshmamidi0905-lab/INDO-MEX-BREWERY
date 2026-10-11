#!/usr/bin/env python3
"""Brewing arithmetic for NASHA PLANNING (Sprint 9). AI planning support only: NOT operating instructions, NOT professionally validated, and it does NOT
decide the unresolved brewery scale (G-6). A licensed brewer owns real production decisions. Every input here is an ASSUMPTION unless you supply evidence.
  python3 tools/brew_calc.py abv --og 1.050 --fg 1.012
  python3 tools/brew_calc.py srm --lb 10 --lovibond 3 --gal 5          (Morey estimate; SRM -> approximate colour)
  python3 tools/brew_calc.py capacity --tank-bbl 15 --tanks 6 --days 14 [--utilization 0.85]
  python3 tools/brew_calc.py scenarios                                   (the D-51 mismatch, arithmetic only)
  python3 tools/brew_calc.py selftest"""
import argparse, sys
L_PER_BBL = 117.348; GAL_PER_BBL = 31.0   # US beer barrel

def abv(og, fg): return (og - fg) * 131.25                      # common approximation; real ABV needs measurement
def srm_morey(lb, lov, gal): mcu = lb * lov / gal; return 1.4922 * mcu ** 0.6859
def capacity(tank_bbl, tanks, days, util=0.85):
    turns = 365 / days; return tank_bbl * tanks * turns * util, turns

def selftest():
    assert abs(abv(1.050, 1.012) - 4.9875) < 1e-6
    assert abs(srm_morey(10, 3, 5) - 1.4922 * 6 ** 0.6859) < 1e-9
    cap, turns = capacity(15, 6, 14, 1.0); assert abs(turns - 26.0714) < 1e-3 and abs(cap - 15 * 6 * turns) < 1e-6
    print("brew_calc selftest OK")

def main():
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest="c")
    a = s.add_parser("abv"); a.add_argument("--og", type=float, required=True); a.add_argument("--fg", type=float, required=True)
    b = s.add_parser("srm"); b.add_argument("--lb", type=float, required=True); b.add_argument("--lovibond", type=float, required=True); b.add_argument("--gal", type=float, required=True)
    c = s.add_parser("capacity"); c.add_argument("--tank-bbl", type=float, required=True); c.add_argument("--tanks", type=int, required=True); c.add_argument("--days", type=float, required=True); c.add_argument("--utilization", type=float, default=.85)
    s.add_parser("scenarios"); s.add_parser("selftest")
    n = p.parse_args()
    if n.c == "abv": print(f"approx ABV {abv(n.og, n.fg):.2f}% (estimate from gravities; measure, do not assume)")
    elif n.c == "srm": print(f"approx SRM {srm_morey(n.lb, n.lovibond, n.gal):.1f} (Morey estimate; style windows are in the reference library)")
    elif n.c == "capacity":
        cap, turns = capacity(n.tank_bbl, n.tanks, n.days, n.utilization)
        print(f"ASSUMPTION-BASED: {n.tanks} x {n.tank_bbl:g} bbl, {n.days:g}-day tank cycle ({turns:.1f} turns/yr), utilization {n.utilization:.0%}: about {cap:,.0f} bbl/yr ({cap*L_PER_BBL/100:,.0f} hL). Not a recommendation; G-6 is open.")
    elif n.c == "scenarios":
        print("D-51 arithmetic (canon tanks about 50 bbl working vs about 780 bbl/yr demand benchmark, both assumptions/T3):")
        print(f"  780 bbl/yr / 50 bbl = {780/50:.1f} full tank fills per year, one every {365/(780/50):.0f} days for one tank")
        for tb, t, d in ((50, 1, 14), (15, 4, 14), (7, 4, 14)):
            cap, _ = capacity(tb, t, d); print(f"  {t} x {tb} bbl at {d}-day cycle, 85% utilization: ~{cap:,.0f} bbl/yr")
        print("  No scenario is recommended here: it needs a brewer, demand evidence and costs (G-6).")
    elif n.c == "selftest": selftest()
    else: p.print_help()
main()
