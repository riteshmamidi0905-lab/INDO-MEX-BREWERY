#!/usr/bin/env python3
"""Validate the Core 5 x Core 5 program files (Sprint 16, D-75). Exit 1 on failure. Checks structure and honesty, never taste:
exact five foods and five beers; every physical status NOT PERFORMED / NOT BREWED; pairing matrix complete (25 rows, bounded scores, hypothesis label, each beer primary once);
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
    for k in ("heat_relief", "richness_cut", "carbonation_role", "char_compat", "malt_bridge", "acid_interaction", "spice_interaction", "body_match", "intensity_match"):
        if not 0 <= int(x[k]) <= 3: fail(f"pairing score out of range {k}")
prim = [x["beer_id"] for x in pm if x["role"].startswith("PRIMARY")]
if sorted(prim) != sorted(BEERS): fail(f"each beer must be primary for exactly one dish (got {prim})")
for r in rd("food/costing/ingredients.csv"):
    if r["price_per_unit"].strip() and not (r["price_source"].strip() and r["price_date"].strip()): fail(f"ingredient {r['ingredient_id']}: price without source/date (never invent prices)")
al = {r["dish_id"] for r in rd("food/ALLERGEN-MATRIX.csv")}
if al != FOODS: fail("allergen matrix must cover exactly the Core 5 foods")
for r in rd("visuals/glass-studies/core5/core5-summary.csv"):
    if float(r["serving_ml_target"]) >= float(r["brimful_ml"]) or r["watertight"] != "True" or "UNVERIFIED" not in r["status"]: fail(f"glass {r['name']}: geometry/label check failed")
    if abs(float(r["analytic_check_ml"]) - float(r["brimful_ml"])) / float(r["brimful_ml"]) > 0.03: fail(f"glass {r['name']}: analytic and mesh capacity disagree >3%")
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
