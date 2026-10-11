#!/usr/bin/env python3
"""Parametric glass CONCEPT model (Sprint 14). Draws a revolved profile with OpenSCAD, measures volume with trimesh and computes the fill line.
Outputs an STL for review. MANUFACTURABILITY UNVERIFIED. Not an engineered or vendor-approved drawing. NOT a logo: no mark, text or icon is generated (D-66).
Dimensions are user inputs (mm) - the defaults are a TEST object, not a NASHA specification.
  python3 tools/glass_model.py build --name test --out /tmp/glass --profile "0,0;36,0;36,4;32,60;40,150;41,175" --wall 2.2 [--fill-ml 400]
  python3 tools/glass_model.py selftest"""
import argparse, os, subprocess, tempfile, sys
import numpy as np, trimesh
def pts(s): return [tuple(map(float, p.split(","))) for p in s.split(";")]
def solid_scad(prof):  # outer profile (r,z) closed on the axis
    p = ([(0, prof[0][1])] if prof[0][0] else []) + prof + [(0, prof[-1][1])]
    return f"rotate_extrude($fn=96) polygon({[list(x) for x in p]});"
def build(prof, wall, out, name, fill_ml=None):
    os.makedirs(out, exist_ok=True)
    outer = solid_scad(prof)
    zf = prof[0][1] + wall; zs_o, rs_o = [q[1] for q in prof], [q[0] for q in prof]
    inner_prof = [(0, zf), (max(float(np.interp(zf, zs_o, rs_o)) - wall, 0.01), zf)] + [(max(r - wall, 0.01), z) for r, z in prof if z > zf]
    scad = f"difference(){{ {outer} \n translate([0,0,0]) {solid_scad(inner_prof)} }}"
    sf, stl = f"{out}/{name}.scad", f"{out}/{name}.stl"; open(sf, "w").write(scad)
    r = subprocess.run(["openscad", "-o", stl, sf], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    m = trimesh.load(stl); inner = trimesh.creation.revolve(np.array(inner_prof + [(0, inner_prof[-1][1])]), sections=96)
    cap_ml = inner.volume / 1000
    res = dict(name=name, glass_volume_cm3=round(float(m.volume) / 1000, 1), brimful_ml=round(float(cap_ml), 1), height_mm=prof[-1][1], rim_dia_mm=prof[-1][0] * 2, base_dia_mm=prof[0][0] * 2 if prof[0][0] else prof[1][0] * 2,
               wall_mm=wall, watertight=bool(m.is_watertight), status="MANUFACTURABILITY UNVERIFIED")
    if fill_ml:  # find z where inner volume = fill_ml
        zs = np.linspace(inner_prof[0][1], inner_prof[-1][1], 400); best = None
        for z in zs:
            sub = [q for q in inner_prof if q[1] < z]; r_at = np.interp(z, [q[1] for q in inner_prof[1:]], [q[0] for q in inner_prof[1:]])
            sec = trimesh.creation.revolve(np.array(sub + [(r_at, z), (0, z)]), sections=96) if len(sub) > 1 else None
            if sec is not None and sec.volume / 1000 >= fill_ml: best = z; break
        res["fill_line_height_mm"] = None if best is None else round(float(best), 1)
    return res
def selftest():
    # cylinder-like beaker: r=30, h=100, wall 2 -> inner r=28: volume pi*28^2*98 = 241.4 ml
    r = build([(30, 0), (30, 100)], 2.0, tempfile.mkdtemp(), "t", fill_ml=100)
    assert abs(r["brimful_ml"] - 241.4) < 5, r; assert r["watertight"] and "UNVERIFIED" in r["status"]; assert 38 < r["fill_line_height_mm"] < 60, r
    print("selftest ok:", r)
if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("cmd", choices=["build","selftest"]); p.add_argument("--name", default="test"); p.add_argument("--out", default="glass-out")
    p.add_argument("--profile"); p.add_argument("--wall", type=float, default=2.2); p.add_argument("--fill-ml", type=float)
    a = p.parse_args()
    if a.cmd == "selftest": selftest()
    else: print(build(pts(a.profile), a.wall, a.out, a.name, a.fill_ml))
