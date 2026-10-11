#!/usr/bin/env python3
"""Core 5 beer glass FAMILY (concept geometry) built with tools/glass_params.py (Sprint 16). CONCEPT GEOMETRY - MANUFACTURABILITY UNVERIFIED.
Dimensions are concept TARGETS (mm) proposed by the glassware-designer agent review and the project's GLASSWARE-V2 roles; they are not specifications and no
vendor or brewer has reviewed them. No logo, text or mark appears on any glass (D-66). Four volumes are kept distinct: solid glass volume (cm3, material only),
internal brimful capacity, serving volume (fill_ml) and the fill-line height. Validation fails if serving volume >= brimful or if the model is not watertight.
  python3 tools/core5_glasses.py build            writes visuals/glass-studies/core5/* and core5-summary.csv
  python3 tools/core5_glasses.py selftest"""
import csv, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glass_params as gp
OUT = "visuals/glass-studies/core5"
SPECS = [  # name, rim_d, max_d, base_d, height, wall, base_t, ring_h, ring_proj, ring_z, fill_ml, ring2 (z,h,proj) or None, max_at
    ("hefeweizen", 72, 88, 54, 235, 2.0, 10, 9, 1.8, 59, 500, None, 0.6),
    ("mexican-lager", 76, 77, 56, 165, 2.2, 8, 5, 1.0, 41, 400, None, 0.7),
    ("vienna-amber", 76, 78, 58, 140, 2.2, 8, 4, 1.0, 35, 350, (44, 4, 0.8), 0.65),
    ("pilsner", 66, 69, 46, 200, 2.0, 7, 3, 1.5, 50, 330, None, 0.7),
    ("witbier", 80, 88, 58, 125, 2.4, 8, 7, 1.5, 28, 330, None, 0.55),
]
BRIMFUL_TARGET = {"hefeweizen": 680, "mexican-lager": 470, "vienna-amber": 415, "pilsner": 430, "witbier": 400}   # ml, concept targets from the glassware review (hand estimates)
BELLY_EXP = 1.8
def calibrate(spec):
    """Scale rim and belly diameters by one factor k (base diameter stays at its spec value so stability is not traded for the capacity target) until analytic brimful capacity hits the concept target (a HAND ESTIMATE, UNVERIFIED). Returns k."""
    n, rim, mx, base, h, wall, bt, *_ , mat = spec; tgt = BRIMFUL_TARGET[n]; lo, hi = 0.3, 1.6
    f = lambda k: gp.analytic_capacity_ml(rim * k, mx * k, base, h, wall, bt, mat, BELLY_EXP) - tgt
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) > 0: hi = mid
        else: lo = mid
    return (lo + hi) / 2
def build_all(out):
    rows = []
    for spec in SPECS:
        n, rim, mx, base, h, wall, bt, rh, rp, rz, fill, r2, mat = spec; k = calibrate(spec)
        rim, mx = round(rim * k, 1), round(mx * k, 1)
        r = gp.build(n, out, rim_d=rim, max_d=mx, base_d=base, height=h, wall=wall, base_t=bt, ring_h=rh, ring_proj=rp, ring_z=rz, fill_ml=fill, max_at=mat, ring2=r2, belly_exp=BELLY_EXP)
        r["calibration_scale"] = round(k, 3)
        r["analytic_check_ml"] = round(gp.analytic_capacity_ml(rim, mx, base, h, wall, bt, mat, BELLY_EXP), 1); r["headspace_above_fill_mm"] = round(h - r["fill_line_height_mm"], 1) if r.get("fill_line_height_mm") else None
        if abs(r["analytic_check_ml"] - r["brimful_ml"]) / r["brimful_ml"] > 0.03: r.setdefault("checks_extra", []).append("ANALYTIC vs MESH capacity differ >3%")
        r["serving_ml_target"] = fill; r["checks"] = list(r.pop("checks_extra", []))
        if not r["watertight"]: r["checks"].append("NOT WATERTIGHT")
        if fill >= r["brimful_ml"]: r["checks"].append("SERVING >= BRIMFUL")
        if r.get("fill_line_height_mm") is None: r["checks"].append("FILL LINE NOT FOUND")
        r["checks"] = "; ".join(r["checks"]) or "geometry checks pass (not a manufacturability check)"
        rows.append(r)
    return rows
def selftest():
    r = build_all(tempfile.mkdtemp()); assert len(r) == 5 and all(x["brimful_ml"] > x["serving_ml_target"] and x["watertight"] for x in r), r
    print("selftest ok: five watertight glasses, serving volume below brimful capacity for each")
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest()
    elif sys.argv[1:] == ["build"]:
        rows = build_all(OUT); keys = ["name", "height_mm", "rim_dia_mm", "max_body_dia_mm", "base_dia_mm", "wall_mm", "base_thickness_mm", "ring_height_mm", "ring_projection_mm", "serving_ml_target", "brimful_ml", "analytic_check_ml", "calibration_scale", "headspace_above_fill_mm", "ring_outer_dia_mm", "wall_at_ring_mm", "fill_line_datum", "fill_line_height_mm", "glass_volume_cm3", "glass_mass_g_assumed", "com_filled_height_mm", "tip_angle_deg_static", "watertight", "status", "checks"]
        with open(f"{OUT}/core5-summary.csv", "w", newline="") as f:
            w = csv.DictWriter(f, keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
        for r in rows: print({k: r.get(k) for k in ("name", "rim_dia_mm", "max_body_dia_mm", "base_dia_mm", "brimful_ml", "analytic_check_ml", "serving_ml_target", "fill_line_height_mm", "glass_volume_cm3", "tip_angle_deg_static", "checks")})
    else: print(__doc__)
