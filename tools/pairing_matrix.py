#!/usr/bin/env python3
"""Attribute scale: every attr_* column is 0-5 (dish: heat, richness, acid, char, fried, sweet, fresh; beer: carbonation, bitterness, malt, body, yeast, citrus, dryness, hop aroma), style-typical or ANALYSIS values from the two matrices, not measurements. Attributes describe the dish as a whole (salsa/crema/dip served apart are not scored separately). Flat neutral scores (2) are used when a dimension barely applies; this dilutes the signal and is a known weakness.
5 x 5 PAIRING HYPOTHESIS matrix (Sprint 16). NOT SENSORY TESTED. Scores are rule-of-thumb heuristics computed from the attribute columns of
food/CORE5-FOOD-MATRIX.csv (attr_*) and beer/CORE5-BEER-MATRIX.csv (attr_*), which are themselves style-typical or ANALYSIS values, not measurements.
Dimensions (0-3): heat_relief, richness_cut, carbonation_role, char_compat, malt_bridge, acid_interaction, spice_interaction, body_match, intensity_match.
A high score is a reason to TASTE that pairing, never a result. Rank 1 = primary hypothesis, 2 = secondary, the highest-contrast of the rest = experimental.
  python3 tools/pairing_matrix.py write    writes food/CORE5-PAIRING-MATRIX.csv and fills pairing columns in both matrices
  python3 tools/pairing_matrix.py selftest"""
import csv, sys
F, B, OUT = "food/CORE5-FOOD-MATRIX.csv", "beer/CORE5-BEER-MATRIX.csv", "food/CORE5-PAIRING-MATRIX.csv"
DIMS = ["heat_relief", "richness_cut", "carbonation_role", "char_compat", "malt_bridge", "acid_interaction", "spice_interaction", "body_match", "intensity_match"]
import math
def c3(x): return max(0, min(3, int(math.floor(x + 0.5))))   # round half up (not banker's rounding)
def score(d, b):
    heat, rich, acid, char, fried, sweet, fresh = (float(d[k]) for k in ("attr_heat", "attr_richness", "attr_acid", "attr_char", "attr_fried", "attr_sweet", "attr_fresh"))
    carb, bit, malt, body, yeast, cit, dry = (float(b[k]) for k in ("attr_carb", "attr_bitter", "attr_malt", "attr_body", "attr_yeast", "attr_citrus", "attr_dry")); hop = float(b.get("attr_hop") or 0)
    s = {}
    s["heat_relief"] = c3((carb + dry) / 3.5 - max(0, bit - 2) * 0.8 * (heat - 1) / 2) if heat >= 2 else 2   # below heat 2 there is little heat to relieve: neutral 2
    s["richness_cut"] = c3(((carb + dry + bit * 0.7) / 3.5) * (rich / 3) ) if rich >= 3 else 2
    s["carbonation_role"] = c3(carb * (0.55 + 0.15 * (rich >= 3) + 0.2 * fried))
    s["char_compat"] = c3(0.8 * malt * (char / 3) + (1 if char <= 1 else 0) + 0.3 * cit * (char >= 3)) if char >= 2 else 2
    s["malt_bridge"] = c3(malt * (0.45 + 0.15 * char + 0.12 * rich) - bit * 0.15)
    s["acid_interaction"] = c3(1 + (acid >= 3) * (cit * 0.35 + dry * 0.25) + (acid < 3) * (1 - bit * 0.1) - (sweet >= 3) * (bit * 0.2))
    s["spice_interaction"] = c3(1 + yeast * 0.35 * (0.5 + heat * 0.15) - (heat >= 3) * bit * 0.15)
    s["body_match"] = c3(3 - abs((rich / 5 * 4) - body) * 0.9)
    s["intensity_match"] = c3(3 - abs((heat + rich + acid) / 3 - (malt + yeast + bit + cit + hop) / 5) * 0.9)
    return s
def run(foods, beers):
    """PRIMARY is coverage-constrained: an optimal one-to-one assignment so each beer is the primary hypothesis for at most one dish (the 5x5 system needs
    every beer to have a job). The unconstrained best beer per dish is reported separately (unconstrained_top) so the trade-off is visible."""
    from scipy.optimize import linear_sum_assignment
    import numpy as np
    S = [[(score(d, b), 0) for b in beers] for d in foods]
    M = np.array([[sum(s.values()) / len(DIMS) for s, _ in row] for row in S])
    ri, ci = linear_sum_assignment(-M) if len(foods) <= len(beers) else (None, None)
    prim = dict(zip(ri, ci)); rows = []
    for fi, d in enumerate(foods):
        order = sorted(range(len(beers)), key=lambda j: -M[fi][j])
        sec = next(j for j in order if j != prim[fi])
        rest = [j for j in order if j not in (prim[fi], sec)]
        exp = max(rest, key=lambda j: S[fi][j][0]["spice_interaction"] + S[fi][j][0]["acid_interaction"] + M[fi][j])
        for j, b in enumerate(beers):
            role = "PRIMARY hypothesis (coverage assignment, not necessarily best)" if j == prim[fi] else "SECONDARY hypothesis" if j == sec else "EXPERIMENTAL hypothesis" if j == exp else "not prioritised"
            rows.append(dict(food_id=d["id"], beer_id=b["id"], **S[fi][j][0], mean_score=round(float(M[fi][j]), 2), role=role, unconstrained_top=("yes" if j == order[0] else ""), status="PAIRING HYPOTHESIS - NOT SENSORY TESTED"))
    return rows
def selftest():
    foods = [dict(id="f", attr_heat=3, attr_richness=3, attr_acid=2, attr_char=1, attr_fried=1, attr_sweet=1, attr_fresh=2)]
    beers = [dict(id="a", attr_carb=4, attr_bitter=1, attr_malt=1, attr_body=1, attr_yeast=0, attr_citrus=1, attr_dry=4), dict(id="b", attr_carb=1, attr_bitter=5, attr_malt=5, attr_body=5, attr_yeast=0, attr_citrus=0, attr_dry=0), dict(id="c", attr_carb=3, attr_bitter=2, attr_malt=2, attr_body=2, attr_yeast=3, attr_citrus=2, attr_dry=2)]
    r = run(foods, beers); roles = {x["beer_id"]: x["role"] for x in r}
    assert sum(v.startswith("PRIMARY") for v in roles.values()) == 1 and all(0 <= x[d] <= 3 for x in r for d in DIMS) and len(r) == 3, roles
    assert c3(2.5) == 3 and c3(0.5) == 1 and c3(-1) == 0 and c3(9) == 3, "round half up and clamp"
    print("selftest ok: heuristics bounded 0-3, exactly one primary per dish, rounding half up")
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest(); sys.exit()
    foods = list(csv.DictReader(open(F, encoding="utf-8"))); beers = list(csv.DictReader(open(B, encoding="utf-8")))
    rows = run(foods, beers)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["food_id", "beer_id"] + DIMS + ["mean_score", "role", "unconstrained_top", "status"]); w.writeheader(); w.writerows(rows)
    for tab, path, key, cols in ((foods, F, "food_id", ("pairing_primary", "pairing_secondary", "pairing_experimental")), (beers, B, "beer_id", ("pairs_primary_for", "pairs_secondary_for", "pairs_experimental_for"))):
        for r in tab:
            for col, role in zip(cols, ("PRIMARY", "SECONDARY", "EXPERIMENTAL")):
                if key == "food_id": r[col] = ", ".join(x["beer_id"] for x in rows if x["food_id"] == r["id"] and x["role"].startswith(role))
                else: r[col] = ", ".join(x["food_id"] for x in rows if x["beer_id"] == r["id"] and x["role"].startswith(role))
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(tab[0].keys())); w.writeheader(); w.writerows(tab)
    for x in rows:
        if x["role"] != "not prioritised": print(x["food_id"], x["beer_id"], x["role"], x["mean_score"])
