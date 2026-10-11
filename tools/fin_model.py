#!/usr/bin/env python3
"""Restaurant/brewery scenario model (Sprint 14, hardened Sprint 22). Reads ops/finance/assumptions.csv (every value blank today) and REFUSES to compute when any required
input is missing, invalid or of unknown provenance: it never invents revenue, costs, rent, labor or prices. Output is arithmetic on stated assumptions, not a forecast.
  python3 tools/fin_model.py            check required inputs
  python3 tools/fin_model.py selftest   P&L, break-even, capacity and provenance rules on in-memory TEST_FIXTURE numbers (never saved)
Required assumption_ids: covers, avg_check, food_cogs_pct, bev_cogs_pct, bev_mix_pct, labor_monthly, occupancy_monthly, other_fixed_monthly, days_open.
Optional lines (insurance, utilities, maintenance, marketing, commissary, licensing_annual, transaction_fee_pct, variable_cost_per_cover): if omitted the run is NEVER investor grade and the omission is listed.
*_pct inputs are fractions 0-1 (food_costing.py yield_pct and waste_pct columns are 0-100: convert before entering). Cost of goods, other variable cost and contribution are reported separately."""
import csv, math, os, re, sys
# PROVENANCE CLASSES. GRADE A may feed decision-grade output; B is professional/public reference; C is scenario-only; UNKNOWN and TEST_FIXTURE never feed real output.
GRADE = {"ACTUAL": "A", "SUPPLIER_QUOTE": "A", "PROFESSIONAL_ESTIMATE": "B", "PUBLIC_PRIMARY": "B", "PUBLIC_SECONDARY": "C", "RETAIL_RECEIPT": "C", "FOUNDER_ASSUMPTION": "C", "MODEL_ASSUMPTION": "C"}
ALIASES = {"QUOTE": "SUPPLIER_QUOTE", "VENDOR_QUOTE": "SUPPLIER_QUOTE", "EMAIL_QUOTE": "SUPPLIER_QUOTE"}
def norm(c): return ALIASES.get(re.sub(r"[\s\-]+", "_", (c or "UNKNOWN").strip().upper()) or "UNKNOWN", re.sub(r"[\s\-]+", "_", (c or "UNKNOWN").strip().upper()) or "UNKNOWN")
def pclass(r): return norm(r.get("provenance_class"))
def usable(r, fixture=False):   # unknown, blank, unrecognised classes never feed a model; TEST_FIXTURE only when a selftest passes fixture=True
    c = pclass(r); return c in GRADE or (fixture and c == "TEST_FIXTURE")
def worst(classes):   # lowest grade among the inputs actually used: A best, C weakest; an empty set is NOT grade A
    if not classes: return "NONE"
    g = {GRADE.get(c, "F") for c in classes}; return "FIXTURE ONLY" if "F" in g else ("C" if "C" in g else "B" if "B" in g else "A")
F = "ops/finance/assumptions.csv"
REQ = ["covers", "avg_check", "food_cogs_pct", "bev_cogs_pct", "bev_mix_pct", "labor_monthly", "occupancy_monthly", "other_fixed_monthly", "days_open"]
OPTIONAL_FIXED = ("insurance_monthly", "utilities_monthly", "maintenance_monthly", "marketing_monthly", "commissary_monthly")   # debt service and depreciation sit BELOW EBITDA and are deliberately not included
OPTIONAL_ALL = OPTIONAL_FIXED + ("licensing_annual", "transaction_fee_pct", "variable_cost_per_cover")
PCT_IDS = {"food_cogs_pct", "bev_cogs_pct", "bev_mix_pct", "transaction_fee_pct", "tax_rate_pct", "waste_pct", "food_mix_pct"}
DEMAND_IDS = {"covers", "avg_check", "days_open", "bev_mix_pct", "max_covers_per_day"}   # a supplier quote can price a cost, never a guest count or a check
SCENARIOS = ("private_tasting", "invited_validation", "popup", "brewery_residency", "food_trailer", "food_truck", "small_permanent", "flagship")   # fields per scenario: ops/finance/scenario-fields.csv
def check(k, v):   # returns an error string or ""
    if not math.isfinite(v): return "not finite"
    if v < 0: return "negative"
    if k in PCT_IDS and v > 1: return "a *_pct input must be a fraction 0-1 (did you type a percent?)"
    if k == "days_open" and not 0 < v <= 31: return "days_open must be 1-31"
    if k == "max_covers_per_day" and v <= 0: return "capacity must be above zero"
    return ""
def fixed_total(a): return a["labor_monthly"] + a["occupancy_monthly"] + a["other_fixed_monthly"] + sum(a.get(k, 0) for k in OPTIONAL_FIXED) + a.get("licensing_annual", 0) / 12   # other_fixed_monthly must EXCLUDE any line entered separately (no double counting)
def pnl(a):
    rev = a["covers"] * a["avg_check"] * a["days_open"]
    fb = rev * ((1 - a["bev_mix_pct"]) * a["food_cogs_pct"] + a["bev_mix_pct"] * a["bev_cogs_pct"])
    other = rev * a.get("transaction_fee_pct", 0) + a["covers"] * a["days_open"] * a.get("variable_cost_per_cover", 0)
    fixed = fixed_total(a); cm = rev - fb - other
    base = dict(revenue=rev, cogs=fb + other, cogs_food_beverage=fb, variable_other=other, contribution=cm, gross_profit=cm, fixed=fixed, ebitda=cm - fixed)   # ebitda = before debt service and depreciation
    if rev <= 0 or cm <= 0: return dict(base, breakeven_revenue=float("inf"))
    return dict(base, breakeven_revenue=fixed / (cm / rev))
def contribution_per_cover(a):   # revenue per cover less variable cost per cover (COGS mix, payment fees, other per-cover cost); labor and rent are fixed here
    rev = a["avg_check"]; var = rev * ((1 - a["bev_mix_pct"]) * a["food_cogs_pct"] + a["bev_mix_pct"] * a["bev_cogs_pct"]) + rev * a.get("transaction_fee_pct", 0) + a.get("variable_cost_per_cover", 0)
    return rev - var
def breakeven_covers(a):
    """Covers per open day needed to cover monthly fixed cost; None if contribution per cover is not positive or days_open is not positive. Arithmetic only (no demand claim)."""
    cpc = contribution_per_cover(a)
    return None if cpc <= 0 or a["days_open"] <= 0 else fixed_total(a) / (cpc * a["days_open"])
def capacity_warning(a):   # compares break-even covers with the physical ceiling when 'max_covers_per_day' is entered (seats x turns or station limit)
    need = breakeven_covers(a)
    if need is None: return "NO BREAK-EVEN: contribution per cover is not positive"
    cap = a.get("max_covers_per_day")
    if cap is None or cap <= 0: return "CAPACITY NOT ENTERED: break-even cannot be compared with the physical limit"
    return f"WARNING: break-even needs {need:.1f} covers/day but physical capacity is {cap:.1f}" if need > cap else "ok: break-even is within entered capacity"
def event_breakeven(fixed_event_cost, cpc, max_covers=None):
    """Event-level break-even: covers needed = event fixed cost / contribution per cover. Warns when above the entered physical limit."""
    if not (math.isfinite(fixed_event_cost) and math.isfinite(cpc)) or fixed_event_cost < 0: raise ValueError("invalid event inputs")
    if cpc <= 0: return dict(covers=None, warning="NO BREAK-EVEN: contribution per cover is not positive")
    n = fixed_event_cost / cpc; w = f"WARNING: needs {n:.1f} covers, above physical limit {max_covers}" if max_covers is not None and max_covers > 0 and n > max_covers else ""
    return dict(covers=n, warning=w)
def brewery_capacity(fermenter_bbl, fermenters, cycle_days, utilization, days=365):
    """Maximum fermenter-limited output in bbl/year = fermenter size x fermenter count x (days / cycle) x utilization (0-1). Brewhouse and packaging limits are separate. Arithmetic only."""
    vals = (fermenter_bbl, fermenters, cycle_days, utilization, days)
    if not all(math.isfinite(v) for v in vals) or min(fermenter_bbl, fermenters, cycle_days) <= 0 or not 0 <= utilization <= 1 or not 0 < days <= 366 or fermenters != int(fermenters): raise ValueError("invalid brewery capacity inputs")
    return fermenter_bbl * fermenters * (days / cycle_days) * utilization
def sensitivity(a, key, deltas=(-.1, 0, .1)): return {d: round(pnl({**a, key: a[key] * (1 + d)})["ebitda"], 2) for d in deltas}
def run_all(rows=None, fixture=False):
    rows = rows if rows is not None else list(csv.DictReader(open(F, encoding="utf-8"))) if os.path.exists(F) else []
    res = {}
    stray = sorted({(r.get("scenario") or "").strip() for r in rows} - set(SCENARIOS) - {""})
    if stray: print("WARNING: rows tagged with unknown scenarios are ignored:", ", ".join(stray))
    for sc in SCENARIOS:
        scopes = {"": {}, sc: {}}; info = {}; problems = []; seen = {"": set(), sc: set()}
        for r in rows:
            scn = (r.get("scenario") or "").strip()
            if scn and scn != sc: continue
            if not usable(r, fixture): continue   # UNKNOWN or unclassified rows never feed a model
            k = (r.get("assumption_id") or "").strip(); c = pclass(r)
            try: v = float(r["value"])
            except (ValueError, KeyError, TypeError): continue
            e = check(k, v)
            if not e and c == "SUPPLIER_QUOTE" and k in DEMAND_IDS: e = "a supplier quote cannot price a demand input"
            if e: problems.append(f"{k}: {e}"); continue
            if k in seen[scn]: problems.append(f"{k}: duplicate value in the same scope"); continue
            seen[scn].add(k); scopes[scn][k] = v; info[(scn, k)] = (c, bool((r.get("basis_source") or "").strip() and (r.get("evidence_tier") or "").strip()))
        a = {**scopes[""], **scopes[sc]}   # a scenario-specific row always beats a global row
        used = {}
        for k in a: used[k] = info[(sc, k)] if (sc, k) in info and k in scopes[sc] else info[("", k)]
        miss = [k for k in REQ if k not in a]
        if problems or miss: res[sc] = {"status": "NOT RUN", "missing": miss, "problems": problems}; continue
        classes = {c for c, _ in used.values()}; omitted = [k for k in OPTIONAL_ALL if k not in a]; blockers = []
        if worst(classes) != "A": blockers.append("input grade is " + worst(classes))
        if omitted: blockers.append("optional cost lines not entered: " + ", ".join(omitted))
        if "max_covers_per_day" not in a: blockers.append("physical capacity not entered")
        if a["labor_monthly"] <= 0: blockers.append("labor_monthly is zero (founder labor is not free in mature economics)")
        if not all(b for _, b in used.values()): blockers.append("a used row lacks basis_source or evidence_tier")
        res[sc] = {"status": "RUN", "investor_grade": not blockers, "investor_blockers": blockers, "input_grade": worst(classes), "omitted_optional": omitted, "breakeven_covers_per_day": breakeven_covers(a), "capacity_warning": capacity_warning(a), **pnl(a)}
    return res
def selftest():
    a = dict(covers=10, avg_check=10, food_cogs_pct=.3, bev_cogs_pct=.2, bev_mix_pct=.5, labor_monthly=1000, occupancy_monthly=500, other_fixed_monthly=500, days_open=30)
    r = pnl(a); assert r["revenue"] == 3000 and abs(r["cogs"] - 750) < 1e-9 and abs(r["ebitda"] - 250) < 1e-9 and r["contribution"] == r["gross_profit"] == 2250 and r["variable_other"] == 0
    assert sensitivity(a, "covers")[0.1] > sensitivity(a, "covers")[-0.1]
    rows = [dict(assumption_id=k, value=str(v), scenario="popup", provenance_class="TEST_FIXTURE", basis_source="TEST", evidence_tier="TEST") for k, v in a.items()]
    assert run_all(rows)["popup"]["status"] == "NOT RUN"   # fixtures never feed real output unless a selftest asks
    out = run_all(rows, fixture=True); assert out["popup"]["status"] == "RUN" and out["popup"]["input_grade"] == "FIXTURE ONLY" and not out["popup"]["investor_grade"]
    assert out["flagship"]["status"] == "NOT RUN" and out["food_trailer"]["status"] == "NOT RUN"   # scenario isolation
    unk = [dict(r, provenance_class="UNKNOWN") for r in rows]; assert run_all(unk, fixture=True)["popup"]["status"] == "NOT RUN"   # a typed value on an UNKNOWN row must not feed the model
    blank = [{k: v for k, v in r.items() if k != "provenance_class"} for r in rows]; assert run_all(blank, fixture=True)["popup"]["status"] == "NOT RUN"
    for cls, g in (("ACTUAL", "A"), ("QUOTE", "A"), ("Supplier Quote", "A"), ("supplier-quote", "A"), ("PROFESSIONAL_ESTIMATE", "B"), ("PROFESSIONAL ESTIMATE", "B"), ("FOUNDER_ASSUMPTION", "C"), ("MODEL ASSUMPTION", "C"), ("RETAIL RECEIPT", "C")):
        rr = [dict(r, provenance_class=cls) for r in rows if r["assumption_id"] not in DEMAND_IDS] + [dict(r, provenance_class="ACTUAL") for r in rows if r["assumption_id"] in DEMAND_IDS]
        o = run_all(rr)["popup"]
        assert o["status"] == "RUN" and o["input_grade"] == g, (cls, o.get("input_grade"))
        assert not o["investor_grade"], "optional cost lines are missing: never investor grade"
    full = [dict(r, provenance_class="ACTUAL") for r in rows] + [dict(assumption_id=k, value="0", scenario="popup", provenance_class="ACTUAL", basis_source="T", evidence_tier="T") for k in OPTIONAL_ALL + ("max_covers_per_day",) if k != "max_covers_per_day"] + [dict(assumption_id="max_covers_per_day", value="500", scenario="popup", provenance_class="ACTUAL", basis_source="T", evidence_tier="T")]
    o = run_all(full)["popup"]; assert o["investor_grade"] and not o["omitted_optional"], o["investor_blockers"]
    nb = [dict(r, basis_source="") if r["assumption_id"] == "covers" else r for r in full]; assert not run_all(nb)["popup"]["investor_grade"]   # no basis, no investor grade
    lz = [dict(r, value="0") if r["assumption_id"] == "labor_monthly" else r for r in full]; assert not run_all(lz)["popup"]["investor_grade"]   # zero labor is not investor grade
    ins = [r for r in full if r["assumption_id"] != "insurance_monthly"]; o = run_all(ins)["popup"]; assert not o["investor_grade"] and "insurance_monthly" in o["omitted_optional"]   # a missing optional cost is listed, never silently zero-and-good
    insu = [r for r in full if r["assumption_id"] != "insurance_monthly"] + [dict(assumption_id="insurance_monthly", value="900", scenario="popup", provenance_class="UNKNOWN")]; assert "insurance_monthly" in run_all(insu)["popup"]["omitted_optional"]   # UNKNOWN row stays omitted
    sq = [dict(r, provenance_class="SUPPLIER_QUOTE") if r["assumption_id"] == "covers" else r for r in full]; assert run_all(sq)["popup"]["status"] == "NOT RUN"   # a quote cannot be a guest count
    for bad, v in (("covers", "inf"), ("covers", "nan"), ("bev_mix_pct", "50"), ("food_cogs_pct", "30"), ("days_open", "0"), ("days_open", "45"), ("covers", "-5")):
        assert run_all([dict(r, value=v) if r["assumption_id"] == bad else r for r in full])["popup"]["status"] == "NOT RUN", (bad, v)
    glob = [dict(r, scenario="") if r["assumption_id"] == "covers" else r for r in full] + [dict(assumption_id="covers", value="99", scenario="popup", provenance_class="ACTUAL", basis_source="T", evidence_tier="T")]
    g2 = run_all(glob)["popup"]; assert g2["status"] == "RUN" and g2["revenue"] == 99 * 10 * 30   # the scenario-specific row beats the global one
    dup = full + [dict(r, value="11") for r in full if r["assumption_id"] == "covers"]; assert run_all(dup)["popup"]["status"] == "NOT RUN"   # duplicate id in one scope is an error
    leak = rows + [dict(assumption_id="covers", value="999", scenario="flagship", provenance_class="TEST_FIXTURE")]; assert run_all(leak, fixture=True)["popup"]["revenue"] == 3000   # another scenario's row must not leak
    assert pnl(dict(a, covers=0))["breakeven_revenue"] == float("inf")   # a free event has zero revenue but cost: no division crash
    assert pnl(dict(a, insurance_monthly=100))["fixed"] == pnl(a)["fixed"] + 100 and abs(pnl(dict(a, licensing_annual=1200))["fixed"] - pnl(a)["fixed"] - 100) < 1e-9
    assert pnl(dict(a, debt_service_monthly=9999, depreciation_monthly=9999))["ebitda"] == pnl(a)["ebitda"]   # EBITDA excludes debt and depreciation
    assert abs(contribution_per_cover(a) - 7.5) < 1e-9 and abs(breakeven_covers(a) - 2000 / (7.5 * 30)) < 1e-9   # 2000 fixed / (7.5 per cover x 30 days)
    assert breakeven_covers(dict(a, food_cogs_pct=1.2, bev_cogs_pct=1.2)) is None and breakeven_covers(dict(a, days_open=0)) is None   # no break-even, and no crash
    assert capacity_warning(dict(a, max_covers_per_day=5)).startswith("WARNING") and capacity_warning(dict(a, max_covers_per_day=500)).startswith("ok") and capacity_warning(a).startswith("CAPACITY NOT ENTERED") and capacity_warning(dict(a, max_covers_per_day=0)).startswith("CAPACITY NOT ENTERED")
    assert event_breakeven(100, 5, 10)["warning"].startswith("WARNING") and event_breakeven(100, 5, 50)["warning"] == "" and event_breakeven(100, 0)["covers"] is None
    for args in ((100, float("nan")), (-20, 5), (float("inf"), 5)):
        try: event_breakeven(*args); raise SystemExit("bad event inputs accepted: %r" % (args,))
        except ValueError: pass
    assert abs(brewery_capacity(10, 4, 14, .5, 364) - 520) < 1e-9   # 10 bbl x 4 tanks x 26 turns x 0.5
    for args in ((10, 0, 14, .5), (float("nan"), 4, 14, .5), (10, 2.5, 14, .5), (10, 4, 14, 50), (10, 4, 14, .5, 400), (10, 4, 14, .5, 0), (10, 4, float("inf"), .5)):
        try: brewery_capacity(*args); raise SystemExit("bad brewery inputs accepted: %r" % (args,))
        except ValueError: pass
    print("selftest ok (TEST numbers only, not a NASHA result):", {k: round(v, 1) for k, v in r.items()})
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest(); sys.exit()
    res = run_all(); ran = {k: v for k, v in res.items() if v["status"] == "RUN"}
    for k, v in res.items(): print(k, "RUN" if v["status"] == "RUN" else "NOT RUN (missing: " + ", ".join(v["missing"][:3]) + ("..." if len(v["missing"]) > 3 else "") + (("; problems: " + "; ".join(v["problems"][:3])) if v.get("problems") else "") + ")")
    if not ran: print("NO MODEL RUN: nothing is invented; enter real or clearly marked scenario assumptions (assumption_id, value, scenario, provenance_class, basis_source, evidence_tier)."); sys.exit(2)
    for k, v in ran.items(): print(k, {a: (round(b, 1) if isinstance(b, float) else b) for a, b in v.items() if a not in ("status",)}, "" if v["investor_grade"] else "NOT INVESTOR-GRADE (" + "; ".join(v["investor_blockers"]) + "): label any output as a scenario")
