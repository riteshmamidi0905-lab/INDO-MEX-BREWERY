#!/usr/bin/env python3
"""Parametric glass CONCEPT geometry with optional collar ring (Sprint 15). CONCEPT GEOMETRY - MANUFACTURABILITY UNVERIFIED.
Industrial-form study only: NOT a logo (D-66), NOT a trademark, NOT a production specification, NOT an engineered drawing. Any ring is a plain geometric
band with no text/mark. Dimensions are user inputs in mm; defaults are TEST values, not a NASHA specification.
Computes: external dimensions, brimful capacity (ml), fill-line height for a target pour, glass volume/mass (soda-lime density ASSUMED 2.5 g/cm3),
approximate centre of mass empty and at the fill line (liquid density ASSUMED 1.01 g/ml), and a simple static tip angle.
  python3 tools/glass_params.py studies OUTDIR        build the 4 collar studies from test dimensions and write a comparison table
  python3 tools/glass_params.py selftest
Correction note: Sprint 14 reported '618.5 ml' for a first test shape. That was the SOLID volume of an uncut revolve (cm3), not a drinking capacity."""
import json, os, subprocess, sys, tempfile
import numpy as np, trimesh
GLASS_RHO, LIQ_RHO = 2.5, 1.01   # g/cm3, ASSUMED
def body_profile(rim_d, max_d, base_d, height, max_at=0.62, n=14, belly_exp=1.0):
    """belly_exp=1.0 reproduces the Sprint 15 sine bulge; larger values (e.g. 1.8) give a slimmer lower body that widens late."""
    zs = np.linspace(0, height, n); rb, rm, rr = base_d / 2, max_d / 2, rim_d / 2; zm = max_at * height
    r = np.where(zs <= zm, rb + (rm - rb) * np.sin(np.pi / 2 * zs / zm) ** belly_exp, rm + (rr - rm) * np.clip((zs - zm) / (height - zm), 0, 1) ** 1.2)
    return list(zip(map(float, r), map(float, zs)))
def outer_with_ring(body, ring_z=None, ring_h=0, ring_proj=0):
    if not ring_h or not ring_proj: return body
    zs = [q[1] for q in body]; rs = [q[0] for q in body]; r0 = float(np.interp(ring_z, zs, rs)); r1 = float(np.interp(ring_z + ring_h, zs, rs))
    pre = [q for q in body if q[1] < ring_z]; post = [q for q in body if q[1] > ring_z + ring_h]
    return pre + [(r0, ring_z), (r0 + ring_proj, ring_z), (r0 + ring_proj, ring_z + ring_h), (r1, ring_z + ring_h)] + post
def scad_of(prof): return f"rotate_extrude($fn=96) polygon({[list(p) for p in ([(0, prof[0][1])] + prof + [(0, prof[-1][1])])]});"
def inner_of(body, wall, base_t):
    zs = [q[1] for q in body]; rs = [q[0] for q in body]; zf = base_t
    return [(0.0, zf), (max(float(np.interp(zf, zs, rs)) - wall, 0.01), zf)] + [(max(r - wall, 0.01), z) for r, z in body if z > zf]
def analytic_capacity_ml(rim_d, max_d, base_d, height, wall, base_t, max_at=0.62, belly_exp=1.0, n=400):
    """Independent check of brimful capacity by numeric integration of the inner profile (ml)."""
    body = body_profile(rim_d, max_d, base_d, height, max_at, n=n, belly_exp=belly_exp); inner = inner_of(body, wall, base_t)
    z = np.array([q[1] for q in inner[1:]]); r = np.array([q[0] for q in inner[1:]]); return float(np.trapezoid(np.pi * r ** 2, z) / 1000)
def build(name, out, rim_d=80, max_d=84, base_d=60, height=170, wall=2.2, base_t=8, ring_h=0, ring_proj=0, ring_z=None, fill_ml=None, max_at=0.62, ring2=None, belly_exp=1.0):
    os.makedirs(out, exist_ok=True)
    body = body_profile(rim_d, max_d, base_d, height, max_at, belly_exp=belly_exp); outer = outer_with_ring(body, ring_z, ring_h, ring_proj)
    if ring2: outer = outer_with_ring(outer, *ring2)
    inner = inner_of(body, wall, base_t)
    sf, stl = f"{out}/{name}.scad", f"{out}/{name}.stl"
    open(sf, "w").write(f"difference(){{ {scad_of(outer)} {scad_of(inner)} }}")
    r = subprocess.run(["openscad", "-o", stl, sf], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    m = trimesh.load(stl); m.export(stl, file_type="stl")   # re-save as compact BINARY STL (OpenSCAD writes large ASCII)
    cav = trimesh.creation.revolve(np.array(inner + [(0, inner[-1][1])]), sections=96); cap = float(cav.volume) / 1000
    glass_cm3 = float(m.volume) / 1000; gm = glass_cm3 * GLASS_RHO; com_empty = float(m.center_mass[2])
    res = dict(name=name, height_mm=height, rim_dia_mm=rim_d, max_body_dia_mm=max_d, ring_outer_dia_mm=round(max_d * 0 + 2 * float(np.interp(ring_z, [q[1] for q in body], [q[0] for q in body])) + 2 * ring_proj, 1) if ring_proj and ring_z is not None else None, wall_at_ring_mm=round(wall + ring_proj, 2) if ring_proj else wall, fill_line_datum="height above the outside bottom (z=0), liquid only (serving volume excludes foam head)", base_dia_mm=base_d, wall_mm=wall, base_thickness_mm=base_t,
               ring_height_mm=ring_h, ring_projection_mm=ring_proj, brimful_ml=round(cap, 1), glass_volume_cm3=round(glass_cm3, 1), glass_mass_g_assumed=round(gm, 0),
               com_empty_height_mm=round(com_empty, 1), watertight=bool(m.is_watertight), status="CONCEPT GEOMETRY - MANUFACTURABILITY UNVERIFIED")
    if fill_ml:
        fz = None
        for z in np.linspace(base_t, inner[-1][1], 600):
            sub = [q for q in inner if q[1] < z]; rz = float(np.interp(z, [q[1] for q in inner[1:]], [q[0] for q in inner[1:]]))
            if len(sub) > 1 and trimesh.creation.revolve(np.array(sub + [(rz, z), (0, z)]), sections=96).volume / 1000 >= fill_ml: fz = float(z); break
        res["fill_line_height_mm"] = None if fz is None else round(fz, 1)
        if fz:
            liq = trimesh.creation.revolve(np.array([q for q in inner if q[1] < fz] + [(float(np.interp(fz, [q[1] for q in inner[1:]], [q[0] for q in inner[1:]])), fz), (0, fz)]), sections=96)
            lm = float(liq.volume) / 1000 * LIQ_RHO; lz = float(liq.center_mass[2]); com = (gm * com_empty + lm * lz) / (gm + lm)
            res.update(com_filled_height_mm=round(com, 1), tip_angle_deg_static=round(float(np.degrees(np.arctan((base_d / 2) / com))), 1))
    return res
def selftest():
    r = build("t", tempfile.mkdtemp(), rim_d=70, max_d=70, base_d=70, height=100, wall=2.0, base_t=2.0, fill_ml=100)
    # near-cylinder r=35 with interior r=33, floor 2, height 100: pi*33^2*98 ml = ~335 ml
    assert 300 < r["brimful_ml"] < 370 and r["watertight"] and "UNVERIFIED" in r["status"], r
    r2 = build("t2", tempfile.mkdtemp(), rim_d=70, max_d=70, base_d=70, height=100, wall=2.0, base_t=2.0, ring_h=6, ring_proj=1.5, ring_z=50)
    assert r2["glass_volume_cm3"] > r["glass_volume_cm3"] and abs(r2["brimful_ml"] - r["brimful_ml"]) < 1, "ring adds glass, not capacity"
    print("selftest ok: capacity, ring adds glass but not capacity, watertight")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["selftest"]: selftest()
    elif a[:1] == ["studies"]:
        out = a[1]; S = [("S0-none", 0, 0, None), ("S1-subtle-single", 5, 1.0, None), ("S2-soft-wide", 10, 1.8, None), ("S3-narrow", 3, 1.5, None), ("S4-double-step", 4, 1.0, (107, 4, 1.0))]; rows = []
        for n, h, p, r2 in S: rows.append(build(n, out, ring_h=h, ring_proj=p, ring_z=95, fill_ml=400, ring2=r2))
        json.dump(rows, open(f"{out}/studies.json", "w"), indent=1)
        for r in rows: print({k: r[k] for k in ("name", "ring_height_mm", "ring_projection_mm", "brimful_ml", "glass_volume_cm3", "fill_line_height_mm", "com_filled_height_mm", "tip_angle_deg_static")})
    else: print(__doc__)
