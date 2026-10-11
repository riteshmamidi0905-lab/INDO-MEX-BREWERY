#!/usr/bin/env python3
"""Recipe scaling, yield and unit conversion with explicit assumptions (Sprint 14). Never invents a yield: pass --yield only from a weighed result,
otherwise the output says ASSUMED. Planning arithmetic, not a tested recipe.
  python3 tools/recipe_scale.py scale --base-kg 1 --target-kg 1.3 --item "ginger-garlic paste=40" --item "salt=10"
  python3 tools/recipe_scale.py need --cooked-g 460 --yield 0.75 [--yield-basis ASSUMED|MEASURED]
  python3 tools/recipe_scale.py bakers --flour "rice flour=40" --flour "cornflour=40" --item "water=90"
  python3 tools/recipe_scale.py selftest"""
import argparse, sys
from pint import UnitRegistry
U = UnitRegistry()
def conv(v, a, b): return U.Quantity(v, a).to(b).magnitude
def scale(base, target, items):
    f = target / base; return {k: round(v * f, 2) for k, v in items.items()}, f
def need(cooked_g, y, basis="ASSUMED"): return dict(raw_g=round(cooked_g / y, 1), cooked_g=cooked_g, yield_factor=y, yield_basis=basis)
def bakers(flours, items):
    tot = sum(flours.values()); return {k: round(v / tot * 100, 1) for k, v in {**flours, **items}.items()}
def parse(pairs): return {k.strip(): float(v) for k, v in (p.rsplit("=", 1) for p in pairs or [])}
def selftest():
    out, f = scale(1, 1.3, {"salt": 10}); assert out == {"salt": 13.0} and f == 1.3
    assert need(460, 0.75)["raw_g"] == 613.3 and need(460, .75)["yield_basis"] == "ASSUMED"
    assert abs(conv(1, "lb", "kg") - 0.45359237) < 1e-9 and abs(conv(350, "degF", "degC") - 176.667) < 0.01
    assert bakers({"rice": 40, "corn": 40}, {"water": 90})["water"] == 112.5
    print("selftest ok: scaling, yield, unit conversion, baker's %")
if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("cmd", choices=["scale","need","bakers","selftest"])
    p.add_argument("--base-kg", type=float); p.add_argument("--target-kg", type=float); p.add_argument("--item", action="append"); p.add_argument("--flour", action="append")
    p.add_argument("--cooked-g", type=float); p.add_argument("--yield", dest="y", type=float); p.add_argument("--yield-basis", default="ASSUMED")
    a = p.parse_args()
    if a.cmd == "selftest": selftest()
    elif a.cmd == "scale": o, f = scale(a.base_kg, a.target_kg, parse(a.item)); print(f"factor {f:.4f}", o)
    elif a.cmd == "need": print(need(a.cooked_g, a.y, a.yield_basis))
    else: print(bakers(parse(a.flour), parse(a.item)))
