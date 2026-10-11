#!/usr/bin/env python3
"""5 x 5 STRUCTURAL PAIRING LOGIC v2 (Sprint 17). NOT SENSORY TESTED. Sprint 16 showed the numeric 0-3 heuristic did not discriminate (spreads of 0.1-0.3), so v2
DROPS the numeric scores. Each of the 25 pairings now carries: rule-derived predicted MECHANISMS and RISKS (from the attr_* columns in the two Core 5 matrices:
style-typical/ANALYSIS values on a 0-5 scale, not measurements) and its place in the first physical flight (food/CORE5-PAIRING-FLIGHT-1.csv, designed with the
sensory-scientist agent: 6 CORE pairings in 2 sittings + 2 OPTIONAL). Mechanisms: CONTRAST (carbonation/dryness cuts fat), HEAT (low bitterness, cold, carbonated beside chile),
BRIDGE (malt toast with char/richness), ECHO (yeast spice or citrus with spice/acid), ACID, SWEET (cloy risk or relief), BODY (body matches richness). Tags prioritise tasting;
they are not probabilities and never validate a pairing. The flight set must cover every dish, every beer and every mechanism.
  python3 tools/pairing_matrix.py write      writes food/CORE5-PAIRING-MATRIX.csv and the first-flight columns in both matrices
  python3 tools/pairing_matrix.py check      verify flight coverage (also run by validate_core5)
  python3 tools/pairing_matrix.py selftest"""
import csv, sys
F, B, FL, OUT = "food/CORE5-FOOD-MATRIX.csv", "beer/CORE5-BEER-MATRIX.csv", "food/CORE5-PAIRING-FLIGHT-1.csv", "food/CORE5-PAIRING-MATRIX.csv"
MECHS = {"CONTRAST", "HEAT", "BRIDGE", "ECHO", "ACID", "SWEET", "BODY"}
def n(x, k): return float(x.get(k) or 0)
def mechanisms(d, b):
    heat, rich, acid, char, fried, sweet = (n(d, f"attr_{k}") for k in ("heat", "richness", "acid", "char", "fried", "sweet"))
    carb, bit, malt, body, yeast, cit, dry = (n(b, f"attr_{k}") for k in ("carb", "bitter", "malt", "body", "yeast", "citrus", "dry"))
    m, r = [], []
    if rich >= 3 and (carb >= 3 or dry >= 3): m.append("CONTRAST")
    if heat >= 2 and bit <= 2 and carb >= 3: m.append("HEAT")
    if (char >= 2 and malt >= 3) or (rich >= 4 and malt >= 3): m.append("BRIDGE")
    if yeast >= 3 or cit >= 4: m.append("ECHO") if (acid >= 2 or heat >= 2) else None
    if acid >= 3 and (cit >= 3 or dry >= 3): m.append("ACID")
    if sweet >= 2 and malt >= 3: m.append("SWEET")
    if abs(rich / 5 * 4 - body) <= 1: m.append("BODY")
    if heat >= 2 and bit >= 3: r.append("BITTERNESS_AMPLIFIES_HEAT")
    if (sweet >= 2 or rich >= 4) and malt >= 3: r.append("CLOY_RISK")
    if yeast >= 4 and cit >= 4: r.append("SOAPY_CITRUS_CLASH_RISK")
    if rich >= 4 and body <= 1: r.append("THIN_BEER_VS_RICH_DISH")
    return sorted(set(x for x in m if x)), r
def check(flight, foods, beers):
    core = [x for x in flight if x["tier"] == "CORE"]; errs = []
    if {x["food_id"] for x in core} != set(foods): errs.append("CORE flight must cover every dish")
    if {x["beer_id"] for x in core} != set(beers): errs.append("CORE flight must cover every beer")
    mc = {m for x in core for m in x["agent_mechanisms"].replace("(risk)", "").replace("(counter-test)", "").replace(" ", "").replace("|", ",").split(",") if m}
    if not MECHS <= mc: errs.append(f"CORE flight misses mechanisms: {sorted(MECHS - mc)}")
    per = {}
    for x in core: per[x["sitting"]] = per.get(x["sitting"], 0) + 1
    if any(v > 4 for v in per.values()): errs.append("more than 4 CORE pairings in one sitting (palate fatigue)")
    if any("NOT SENSORY TESTED" not in x["status"] for x in flight): errs.append("flight rows must say NOT SENSORY TESTED")
    return errs
def write():
    foods, beers, flight = list(csv.DictReader(open(F, encoding="utf-8"))), list(csv.DictReader(open(B, encoding="utf-8"))), list(csv.DictReader(open(FL, encoding="utf-8")))
    errs = check(flight, [d["id"] for d in foods], [b["id"] for b in beers])
    if errs: raise SystemExit("; ".join(errs))
    fl = {(x["food_id"], x["beer_id"]): x for x in flight}; rows = []
    for d in foods:
        for b in beers:
            m, r = mechanisms(d, b); f = fl.get((d["id"], b["id"]))
            rows.append(dict(food_id=d["id"], beer_id=b["id"], rule_mechanisms="|".join(m), rule_risks="|".join(r), first_flight=(f"{f['pairing_id']} sitting {f['sitting']} {f['tier']}" if f else "LATER"), agent_mechanisms=(f["agent_mechanisms"] if f else ""), status="PAIRING HYPOTHESIS - NOT SENSORY TESTED"))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    for tab, path, key, col in ((foods, F, "food_id", "pairing_first_flight"), (beers, B, "beer_id", "pairing_first_flight")):
        other = "beer_id" if key == "food_id" else "food_id"
        for r in tab:
            r[col] = ", ".join(f"{x[other]} ({x['pairing_id']})" for x in flight if x[key] == r["id"])
            for old in ("pairing_primary", "pairing_secondary", "pairing_experimental", "pairs_primary_for", "pairs_secondary_for", "pairs_experimental_for"): r.pop(old, None)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(tab[0].keys())); w.writeheader(); w.writerows(tab)
    return rows
def selftest():
    d = dict(attr_heat=3, attr_richness=3, attr_acid=2, attr_char=1, attr_fried=4, attr_sweet=1)
    b = dict(attr_carb=3, attr_bitter=1, attr_malt=1, attr_body=1, attr_yeast=0, attr_citrus=1, attr_dry=4)
    m, r = mechanisms(d, b); assert "HEAT" in m and "CONTRAST" in m, m
    hot = dict(b, attr_bitter=4); assert "BITTERNESS_AMPLIFIES_HEAT" in mechanisms(d, hot)[1]
    flight = [dict(food_id="f", beer_id="a", sitting="1", tier="CORE", agent_mechanisms="CONTRAST|HEAT|BRIDGE|ECHO|ACID|SWEET|BODY", status="NOT SENSORY TESTED")]
    assert not check(flight, ["f"], ["a"]) and check(flight, ["f", "g"], ["a"])
    print("selftest ok: mechanism tags, risk flags and flight coverage logic")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["selftest"]: selftest()
    elif a[:1] == ["check"]:
        e = check(list(csv.DictReader(open(FL))), [r["id"] for r in csv.DictReader(open(F))], [r["id"] for r in csv.DictReader(open(B))]); print("flight coverage ok" if not e else "\n".join(e)); sys.exit(1 if e else 0)
    elif a[:1] == ["write"]:
        rows = write()
        for r in rows:
            if r["first_flight"] != "LATER": print(r["food_id"], r["beer_id"], r["first_flight"], "| rule:", r["rule_mechanisms"], "| risks:", r["rule_risks"])
    else: print(__doc__)
