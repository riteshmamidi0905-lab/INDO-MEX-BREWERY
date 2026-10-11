#!/usr/bin/env python3
"""Trade-area screening on FOUNDER-SUPPLIED public points (Sprint 15). Straight-line (geodesic-projected) radius counts ONLY: this is NOT drive-time analysis
(no routing data is available here) and the output says so. No data is fetched; no site, competitor or demographic is invented.
  python3 tools/trade_area.py POINTS.csv --lat 30.26 --lon -97.74 --radii-km 1,3,5      points CSV needs columns: name,type,lat,lon,source_url,access_date
  python3 tools/trade_area.py selftest"""
import argparse, csv, sys, tempfile, os
import geopandas as gpd
from shapely.geometry import Point
def analyse(rows, lat, lon, radii_km):
    g = gpd.GeoDataFrame(rows, geometry=[Point(float(r["lon"]), float(r["lat"])) for r in rows], crs="EPSG:4326").to_crs(32614)   # UTM 14N (Austin area)
    c = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(32614).iloc[0]
    g["km"] = g.geometry.distance(c) / 1000
    return {r: g[g.km <= r].groupby("type").size().to_dict() | {"TOTAL": int((g.km <= r).sum())} for r in radii_km}, g
def selftest():
    rows = [dict(name="a", type="brewery", lat=30.2672, lon=-97.7431), dict(name="b", type="brewery", lat=30.30, lon=-97.74), dict(name="c", type="indian", lat=30.2680, lon=-97.7440)]
    res, _ = analyse(rows, 30.2672, -97.7431, [1, 5]); assert res[1]["TOTAL"] == 2 and res[5]["TOTAL"] == 3 and res[1]["brewery"] == 1, res
    print("selftest ok (synthetic TEST points, straight-line radius only):", res)
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest(); sys.exit()
    p = argparse.ArgumentParser(); p.add_argument("csv"); p.add_argument("--lat", type=float, required=True); p.add_argument("--lon", type=float, required=True); p.add_argument("--radii-km", default="1,3,5")
    a = p.parse_args(); rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    res, _ = analyse(rows, a.lat, a.lon, [float(x) for x in a.radii_km.split(",")])
    print("STRAIGHT-LINE RADIUS (not drive time); counts of the supplied points only, not a market census")
    for r, v in res.items(): print(f"{r} km:", v)
