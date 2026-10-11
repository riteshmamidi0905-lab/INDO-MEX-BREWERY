#!/usr/bin/env python3
"""Validate the Core 5 x Core 5 program files (Sprint 16, D-75). Exit 1 on failure. Checks structure and honesty, never taste:
exact five foods and five beers; every physical status NOT PERFORMED / NOT BREWED; pairing matrix complete (25 rows, hypothesis label, no numeric scores) and the first pairing flight covering every dish, beer and mechanism; frozen Session 2-5 gates hash matches D-76; sessions results rows valid;
no prices or quantities without a source; glass family geometry consistent (serving < brimful, watertight, UNVERIFIED label); D-75 recorded; dishes on the website data."""
import csv, json, os, re, sys
FOODS = {"chicken-65-totopos", "paneer-tikka-taco", "goat-birria", "gobi-taco", "butter-chicken-quesadilla"}
BEERS = {"hefeweizen", "mexican-lager", "vienna-amber", "pilsner", "witbier"}
errs = []
def fail(m): errs.append(m)
def rd(p): return list(csv.DictReader(open(p, encoding="utf-8")))
f, b, pm = rd("food/CORE5-FOOD-MATRIX.csv"), rd("beer/CORE5-BEER-MATRIX.csv"), rd("food/CORE5-PAIRING-MATRIX.csv")
if {r["id"] for r in f} != FOODS: fail("food matrix ids differ from D-75 Core 5")
if {r["id"] for r in b} != BEERS: fail("beer matrix ids differ from D-75 Core 5")
for r in f:
    if r["physical_test_status"] != "NOT PERFORMED": fail(f"{r['id']}: physical_test_status must be NOT PERFORMED until real rows exist")
    for c in ("indian_anchor", "mexican_anchor", "cultural_class", "d54_risk", "allergens_proposed", "reference_gaps", "next_experiment", "confidence"):
        if not r[c].strip(): fail(f"{r['id']}: empty {c}")
for r in b:
    if r["physical_status"] != "NOT BREWED": fail(f"{r['id']}: physical_status must be NOT BREWED")
    if not r["brewer_questions"].strip(): fail(f"{r['id']}: empty brewer_questions")
if len(pm) != 25 or {(x["food_id"], x["beer_id"]) for x in pm} != {(a, c) for a in FOODS for c in BEERS}: fail("pairing matrix must have all 25 food x beer rows")
for x in pm:
    if "NOT SENSORY TESTED" not in x["status"]: fail("pairing row missing NOT SENSORY TESTED label")
    if any(k in x for k in ("mean_score", "heat_relief")): fail("numeric pairing scores were removed in v2 (false precision)")
sys.path.insert(0, "tools")
import pairing_matrix as _pm
fe = _pm.check(rd("food/CORE5-PAIRING-FLIGHT-1.csv"), FOODS, BEERS)
for e in fe: fail("pairing flight: " + e)
import session_record as _sr
_sp = _sr.spec(); _rs = _sr.rows()
for e in _sr.problems(_rs, _sp): fail("sessions results: " + e)
_h = _sr.gates_hash(_sp)
if _h not in open("docs/decisions/DECISIONS.md", encoding="utf-8").read(): fail("sessions.json gates hash does not match the hash frozen in D-76 (gates changed after freeze?)")
if set(_sp["sessions"]) != FOODS - {"chicken-65-totopos"}: fail("sessions.json must cover Sessions 2-5 foods")
for r in rd("food/costing/ingredients.csv"):
    if r["price_per_unit"].strip() and not (r["price_source"].strip() and r["price_date"].strip()): fail(f"ingredient {r['ingredient_id']}: price without source/date (never invent prices)")
al = {r["dish_id"] for r in rd("food/ALLERGEN-MATRIX.csv")}
if al != FOODS: fail("allergen matrix must cover exactly the Core 5 foods")
v2 = rd("visuals/glass-studies/v2/glass-v2-summary.csv")
if len(v2) != 5: fail("glass V2 summary must have 5 glasses")
for r in v2:
    if float(r["serving_ml"]) >= float(r["internal_brimful_ml"]) or r["mesh_watertight"] != "True" or "UNVERIFIED" not in r["status"]: fail(f"glass V2 {r['name']}: geometry/label check failed")
    if abs(float(r["pappus_vs_mesh_pct"])) > 1.0: fail(f"glass V2 {r['name']}: exact and mesh volume disagree >1%")
    if float(r["headspace_above_fill_mm"]) < 20: fail(f"glass V2 {r['name']}: headspace below the 20 mm design minimum")
import subprocess
rc = subprocess.run([sys.executable, "tools/food_costing.py"], capture_output=True, text=True)
if rc.returncode: fail("food_costing.py fails (false D-54 trip or real violation): " + rc.stdout[-200:])
if "| D-75 |" not in open("docs/decisions/DECISIONS.md", encoding="utf-8").read(): fail("D-75 not recorded")
ids = {d["id"] for d in json.load(open("website/data/dishes.json", encoding="utf-8"))}
if not FOODS <= ids: fail("website dishes.json is missing a Core 5 dish")
for p in ("beer/pilot-briefs/04-pilsner.md", "beer/pilot-briefs/05-witbier.md"):
    if not os.path.exists(p): fail(f"missing {p}")
txt = open("research/CORE5-PRODUCT-SYSTEM.md", encoding="utf-8").read()
if re.search(r"\b(tastes? (great|good)|validated dish|customer[- ]validated|proven)\b", txt, re.I): fail("CORE5-PRODUCT-SYSTEM.md contains validation language")
print("CORE5: " + ("FAIL\n  " + "\n  ".join(errs) if errs else "ok (5 foods, 5 beers, 25 pairing hypotheses, glass family, costing/allergen structures, honesty checks)"))
sys.exit(1 if errs else 0)
