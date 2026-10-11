#!/usr/bin/env python3
"""Glass family V2 geometry system (Sprint 17). CONCEPT GEOMETRY - MANUFACTURABILITY UNVERIFIED; no logo/text/mark (D-66). Fixes the Sprint 16 weaknesses:
style-shaped profiles from control points (monotone PCHIP, not a barrel), a smooth radiused collar band, a rounded lip (fire-polish radius), rounded base corner and floor fillet,
true wall offset (shapely buffer), exact metrics by Pappus' theorem and polygon moments (an INDEPENDENT check of the revolved mesh volume), and honest separate volumes:
solid glass volume, internal brimful capacity, serving volume, fill-line height (measured from the outside bottom, liquid only), headspace. Capacities and dimensions are
DESIGN ASSUMPTIONS from visuals/glass-studies/v2/specs.json (ledger V-73). Static tip angle = atan(contact radius / centre-of-mass height): a ranking, not a safety figure.
  python3 tools/glass_v2.py build [--out DIR]     writes summary CSV, JSON, silhouette comparison PNG (and STL meshes, git-ignored: regenerate with this command)
  python3 tools/glass_v2.py selftest"""
import csv, json, math, os, sys, tempfile
import numpy as np
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
SPEC = "visuals/glass-studies/v2/specs.json"
def spec(p=SPEC): return json.load(open(p, encoding="utf-8"))
def ring_bump(z, z0, h, proj):
    t = (z - z0) / h
    return np.where((t > 0) & (t < 1), proj * np.sin(np.pi * t) ** 2, 0.0)      # smooth cosine-squared band, no corners
def outer_profile(g, common, ring=None, scale=1.0, n=240):
    pts = np.array(g["points"], float); sc = np.where(np.arange(len(pts)) == 0, 1.0, scale)      # the base radius is NOT scaled (stability is not traded for the capacity target)
    z = np.linspace(pts[0][0], g["height_mm"], n); r = PchipInterpolator(pts[:, 0], pts[:, 1] * sc)(z)
    if ring: r = r + ring_bump(z, ring["z0"], ring["h"], ring["proj"])
    rb, cr = pts[0][1], common["base_corner_radius_mm"]
    th = np.linspace(-math.pi / 2, 0, 12); arc = [(rb - cr + cr * math.cos(t), cr + cr * math.sin(t)) for t in th]      # rounded base corner, ends at (rb, cr)
    return [(0.0, 0.0)] + arc + [(float(a), float(b)) for a, b in zip(r, z) if b > cr + 1e-6]
def half(poly): return poly.intersection(box(0, -1, 1e4, 1e4))
def build_polys(g, common, ring=None, scale=1.0):
    prof = outer_profile(g, common, ring, scale); H = g["height_mm"]
    right = prof + [(prof[-1][0], H), (0.0, H)]
    sym = lambda pts: Polygon([(-x, y) for x, y in pts[::-1]] + pts)
    S = sym(right).buffer(0)
    ext = sym(prof + [(prof[-1][0], H + 25), (0.0, H + 25)]).buffer(0)
    cav_full = ext.buffer(-common["wall_mm"], join_style=1).intersection(box(-1e4, common["base_thickness_mm"], 1e4, H))
    cav_full = cav_full.buffer(-common["floor_fillet_mm"], join_style=1).buffer(common["floor_fillet_mm"], join_style=1)
    glass_full = S.difference(cav_full)
    lr = common["lip_radius_mm"]; glass_full = glass_full.buffer(-lr, join_style=1).buffer(lr, join_style=1)      # round the lip (fire-polish concept)
    return half(glass_full), half(cav_full), half(S)
def moments(poly):
    """area, centroid_x, centroid_y, and integral of x*y dA for a polygon (exact, by vertex formulas)."""
    a = ixy = 0.0; cx = cy = 0.0
    polys = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    A = Ix = Iy = Ixy = 0.0
    for p in polys:
        for ring, sign in [(p.exterior, 1)] + [(i, -1) for i in p.interiors]:
            c = list(ring.coords)
            if Polygon(c).exterior.is_ccw is False: c = c[::-1]
            for (x0, y0), (x1, y1) in zip(c[:-1], c[1:]):
                cr = x0 * y1 - x1 * y0
                A += sign * cr / 2; Ix += sign * cr * (x0 + x1) / 6; Iy += sign * cr * (y0 + y1) / 6
                Ixy += sign * cr * (x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0) / 24
    return A, Ix, Iy, Ixy
def revolve_props(poly):
    """volume (mm3) and centre-of-mass height (mm) of the solid of revolution of a half-profile polygon about x=0 (Pappus + moments)."""
    A, Ix, Iy, Ixy = moments(poly); V = 2 * math.pi * Ix; zc = Ixy / Ix if Ix else 0.0
    return V, zc
def fill_height(cav, serving_ml):
    lo, hi = 0.0, cav.bounds[3]
    for _ in range(60):
        mid = (lo + hi) / 2
        if revolve_props(cav.intersection(box(0, -1, 1e4, mid)))[0] / 1000 > serving_ml: hi = mid
        else: lo = mid
    return (lo + hi) / 2
def analyse(name, g, common, ring_cfg, with_ring=True, scale=None):
    H = g["height_mm"]; ring = dict(z0=ring_cfg["height_fraction_of_total"] * H, h=ring_cfg["band_height_mm"], proj=ring_cfg["projection_mm"]) if with_ring else None
    if scale is None:       # calibrate radial scale so brimful hits the DESIGN-ASSUMPTION target
        lo, hi = 0.4, 1.8
        for _ in range(50):
            mid = (lo + hi) / 2; cav = build_polys(g, common, ring, mid)[1]
            if revolve_props(cav)[0] / 1000 > g["brimful_target_ml"]: hi = mid
            else: lo = mid
        scale = (lo + hi) / 2
    glass, cav, S = build_polys(g, common, ring, scale)
    Vg, zg = revolve_props(glass); Vc, _ = revolve_props(cav); zf = fill_height(cav, g["serving_ml"])
    liq = cav.intersection(box(0, -1, 1e4, zf)); Vl, zl = revolve_props(liq)
    mg, ml = Vg / 1000 * common["glass_density_g_cm3_ASSUMED"], Vl / 1000 * common["liquid_density_g_ml_ASSUMED"]
    com_f = (mg * zg + ml * zl) / (mg + ml)
    pts = np.array(g["points"], float); rb = pts[0][1] - common["base_corner_radius_mm"]
    rim_outer = max(x for x, y in S.exterior.coords if y > H - 1.0) * 2; belly = float(np.max(PchipInterpolator(pts[:, 0], pts[:, 1] * np.where(np.arange(len(pts)) == 0, 1.0, scale))(np.linspace(pts[0][0], H, 400)))) * 2
    max_incl = S.bounds[2] * 2
    inner_rim = (max(x for x, y in cav.exterior.coords if y > H - 1.0)) * 2
    return dict(name=name, ring=bool(with_ring), height_mm=H, rim_outer_dia_mm=round(rim_outer, 1), belly_dia_mm=round(belly, 1), max_dia_incl_ring_mm=round(max_incl, 1), base_contact_dia_mm=round(2 * rb, 1), wall_mm=common["wall_mm"], base_thickness_mm=common["base_thickness_mm"],
                solid_glass_volume_cm3=round(Vg / 1000, 1), glass_mass_g_assumed=round(mg, 0), internal_brimful_ml=round(Vc / 1000, 1), serving_ml=g["serving_ml"], fill_line_height_mm=round(zf, 1), headspace_above_fill_mm=round(H - zf, 1),
                com_empty_mm=round(zg, 1), com_filled_mm=round(com_f, 1), tip_angle_deg_empty=round(math.degrees(math.atan(rb / zg)), 1), tip_angle_deg_filled=round(math.degrees(math.atan(rb / com_f)), 1),
                rim_inner_over_base_contact_NOT_nesting_depth=round(inner_rim / (2 * rb), 2), scale=round(scale, 4), brimful_target_ml_ASSUMPTION=g["brimful_target_ml"], status="CONCEPT GEOMETRY - MANUFACTURABILITY UNVERIFIED"), (glass, cav, scale)
def mesh(glass, path):
    import trimesh
    c = list(glass.exterior.coords) if glass.geom_type == "Polygon" else list(max(glass.geoms, key=lambda p: p.area).exterior.coords)
    from shapely.geometry.polygon import orient
    c = list(orient(Polygon(c), 1.0).exterior.coords)
    m = trimesh.creation.revolve(np.array(c), sections=120)
    if m.volume < 0: m.invert()
    m.export(path, file_type="stl"); return float(m.volume) / 1000, bool(m.is_watertight)
def build(out):
    S = spec(); os.makedirs(out, exist_ok=True); rows, geo = [], {}
    for n, g in S["glasses"].items():
        base_ring = bool(S["ring"].get("default_enabled", False))
        r, (glass, cav, sc) = analyse(n, g, S["common"], S["ring"], base_ring); r1, (gl1, _, _) = analyse(n, g, S["common"], S["ring"], not base_ring, scale=sc); r0 = r1 if base_ring else r
        r_ringvar = r1 if not base_ring else r
        mesh(gl1, f"{out}/{n}-{'ring' if not base_ring else 'noring'}.stl")
        mv, wt = mesh(glass, f"{out}/{n}.stl"); r["mesh_solid_volume_cm3"] = round(mv, 1); r["mesh_watertight"] = wt; r["pappus_vs_mesh_pct"] = round(abs(mv - r["solid_glass_volume_cm3"]) / r["solid_glass_volume_cm3"] * 100, 2)
        r["ring_variant_adds_glass_cm3"] = round(abs(r_ringvar["solid_glass_volume_cm3"] - r["solid_glass_volume_cm3"]), 1); r["ring_variant_max_dia_mm"] = r_ringvar["max_dia_incl_ring_mm"]; r["checks"] = []
        if r["headspace_above_fill_mm"] < S["common"]["min_headspace_mm_design_rule"]: r["checks"].append("HEADSPACE BELOW DESIGN RULE")
        if abs(r["internal_brimful_ml"] - g["brimful_target_ml"]) > 8: r["checks"].append("BRIMFUL MISSES TARGET")
        if r["pappus_vs_mesh_pct"] > 1.0 or not wt: r["checks"].append("MESH vs PAPPUS DISAGREE or not watertight")
        if r["tip_angle_deg_filled"] < 15: r["checks"].append("LOW STATIC TIP ANGLE for its height: stability question (15 deg is a screening marker, NOT a standard or safety figure)")
        r["checks"] = "; ".join(r["checks"]) or "geometry checks pass (not a manufacturability check)"; rows.append(r); geo[n] = (glass, cav, g)
    keys = list(rows[0].keys())
    with open(f"{out}/glass-v2-summary.csv", "w", newline="") as f: w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
    plot(geo, rows, f"{out}/glass-v2-silhouettes.png"); return rows
def plot(geo, rows, path):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(15, 6)); x0 = 0.0; amber = "#d9a441"
    for (n, (glass, cav, g)), r in zip(geo.items(), rows):
        for p, colr, a in ((glass, "#9aa5ad", 0.9),):
            ps = [p] if p.geom_type == "Polygon" else list(p.geoms)
            for q in ps:
                xs, ys = q.exterior.xy; xs = np.array(xs); ax.fill(np.r_[x0 - xs[::-1], x0 + xs], np.r_[np.array(ys)[::-1], ys], color=colr, alpha=a, lw=0)
        zf = r["fill_line_height_mm"]; liq = cav.intersection(box(0, -1, 1e4, zf)); qs = [liq] if liq.geom_type == "Polygon" else list(liq.geoms)
        for q in qs:
            xs, ys = q.exterior.xy; xs = np.array(xs); ax.fill(np.r_[x0 - xs[::-1], x0 + xs], np.r_[np.array(ys)[::-1], ys], color=amber, alpha=0.75, lw=0)
        ax.plot([x0 - 45, x0 + 45], [zf, zf], color="#333", lw=0.8, ls="--")
        ax.text(x0, -16, f"{n}\nbrimful {r['internal_brimful_ml']:.0f} ml | serve {r['serving_ml']} ml\nheight {r['height_mm']} mm | rim {r['rim_outer_dia_mm']} mm\nbase {r['base_contact_dia_mm']} mm | tip {r['tip_angle_deg_filled']} deg", ha="center", va="top", fontsize=7)
        x0 += 125
    ax.set_aspect("equal"); ax.set_xlim(-60, x0 - 55); ax.set_ylim(-70, 250); ax.axis("off")
    ax.set_title("NASHA glass family V2 - CONCEPT GEOMETRY, MANUFACTURABILITY UNVERIFIED (dashed = fill line, amber = serving volume)", fontsize=9)
    fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)
def selftest():
    # a straight-walled cylinder-like glass: analytic capacity check. r=30, wall 2.4, base 9, height 100 -> internal r ~27.6 over about 91 mm (floor fillet makes it slightly smaller)
    g = dict(height_mm=100, base_r_mm=30, points=[[3.5, 30], [100, 30]], brimful_target_ml=200, serving_ml=150)
    common = spec()["common"]; r, (glass, cav, sc) = analyse("t", g, common, spec()["ring"], False, scale=1.0)
    # exact cylinder with no fillets: capacity = pi * (R - wall)^2 * (H - base_t)
    c0 = dict(common, floor_fillet_mm=0.0, base_corner_radius_mm=0.01, lip_radius_mm=0.0001); r0, _ = analyse("c", g, c0, spec()["ring"], False, scale=1.0)
    exact = math.pi * (30 - common["wall_mm"]) ** 2 * (100 - common["base_thickness_mm"]) / 1000; assert abs(r0["internal_brimful_ml"] - exact) / exact < 0.01, (r0["internal_brimful_ml"], exact)
    # exact frustum: radial wall = wall / cos(theta); capacity = pi*h/3*(R1^2+R1R2+R2^2) between base_t and H
    g2 = dict(height_mm=100, base_r_mm=30, points=[[3.5, 30], [100, 40]], brimful_target_ml=200, serving_ml=150); r2, _ = analyse("f", g2, c0, spec()["ring"], False, scale=1.0)
    slope = (40 - 30) / (100 - 3.5); th = math.atan(slope); off = common["wall_mm"] / math.cos(th); rz = lambda z: 30 + slope * (z - 3.5) - off
    z0, z1 = common["base_thickness_mm"], 100.0; R1, R2 = rz(z0), rz(z1); fr = math.pi * (z1 - z0) / 3 * (R1 ** 2 + R1 * R2 + R2 ** 2) / 1000
    assert abs(r2["internal_brimful_ml"] - fr) / fr < 0.02, (r2["internal_brimful_ml"], fr)
    approx = math.pi * 27.6 ** 2 * 91 / 1000; assert abs(r["internal_brimful_ml"] - approx) / approx < 0.06, (r["internal_brimful_ml"], approx)
    d = tempfile.mkdtemp(); mv, wt = mesh(glass, f"{d}/t.stl"); assert wt and abs(mv - r["solid_glass_volume_cm3"]) / mv < 0.01, (mv, r["solid_glass_volume_cm3"])
    assert 0 < r["fill_line_height_mm"] < 100 and r["tip_angle_deg_empty"] > 20
    print("selftest ok: Pappus capacity matches the exact cylinder (1%) and exact frustum (2%) closed forms; mesh volume agrees with Pappus; fill line and tip angle sane")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["selftest"]: selftest()
    elif a[:1] == ["build"]:
        out = a[a.index("--out") + 1] if "--out" in a else "visuals/glass-studies/v2"
        for r in build(out): print({k: r[k] for k in ("name", "height_mm", "belly_dia_mm", "rim_outer_dia_mm", "base_contact_dia_mm", "solid_glass_volume_cm3", "internal_brimful_ml", "serving_ml", "fill_line_height_mm", "headspace_above_fill_mm", "tip_angle_deg_filled", "pappus_vs_mesh_pct", "checks")})
    else: print(__doc__)
