"""Pricing engine and segmentation, checked against independent hand/brute-force calculations (not against the module's own helpers). NASHA values come from the existing recipe-costing module. SYNTHETIC."""
import math
import sqlite3
from datetime import date

import pytest

from nasha_lab.growth import pricing as GP, segments as GS
from nasha_lab.recipes import pricing as P


def test_margin_and_unit_profit_by_hand():
    t = GP.margin_table(1850, 555)
    assert t["unit_profit_cents"] == 1295 and math.isclose(t["margin"], 1295 / 1850)


@pytest.mark.parametrize("price,cost,d", [(1850, 555, 10), (900, 270, 25), (1350, 400, 50), (1850, 1700, 5), (1000, 600, 40)])
def test_discount_breakeven_uplift_actually_recovers_gross_profit(price, cost, d):
    r = GP.discount_analysis(price, cost, d)
    p1 = price * (1 - d / 100)
    if p1 <= cost:
        assert r["breakeven_volume_uplift"] is None
    else:
        q0 = 1000.0
        assert math.isclose((p1 - cost) * q0 * (1 + r["breakeven_volume_uplift"]), (price - cost) * q0, rel_tol=1e-9)


def test_bundle_math_and_a_bundle_discount_cannot_raise_margin():
    items = [GP.Item("main", 1850, 555), GP.Item("glass", 900, 270)]
    b = GP.bundle(items, 10)
    assert b["list_price_cents"] == 2750 and math.isclose(b["bundle_price_cents"], 2475) and b["cost_cents"] == 825 and b["saving_cents"] == 275
    assert b["margin"] < b["margin_at_list"]


def test_inflation_and_breakeven_by_hand():
    rows = GP.inflation(1850, 555, shocks=(0.0, 0.2))
    assert math.isclose(rows[1]["cost_cents"], 666) and math.isclose(rows[1]["margin"], (1850 - 666) / 1850)
    assert math.isclose(GP.breakeven_units(100_000, 1850, 555), 100_000 / 1295) and GP.breakeven_units(1, 500, 500) is None


def test_sensitivity_is_labelled_as_an_assumption_and_matches_brute_force():
    r = GP.sensitivity(1850, 555, 1000, -1.5, [1700, 1850, 2000])
    assert "assumed" in r["assumption"]
    for row in r["rows"]:
        q = 1000 * (row["price_cents"] / 1850) ** -1.5
        assert math.isclose(row["units"], q) and math.isclose(row["gross_profit_cents"], (row["price_cents"] - 555) * q)
    assert r["best_price_cents"] == max([1700, 1850, 2000], key=lambda p: (p - 555) * 1000 * (p / 1850) ** -1.5)


def test_nasha_dish_economics_come_from_the_existing_costing_module_and_lamb_stays_below_target():
    items = GP.nasha_items()
    assert items["tandoori-lamb-tacos"]["price_cents"] == 1850 and items["chaat-elote"]["price_cents"] == 1350
    e = P.economics("tandoori-lamb-tacos")
    assert math.isclose(1 - items["tandoori-lamb-tacos"]["cost_cents"] / 1850, e["gross_margin_pct"], rel_tol=1e-9)
    assert GP.margin_table(1850, items["tandoori-lamb-tacos"]["cost_cents"])["margin"] < 0.70 < GP.margin_table(1850, items["paneer-tikka-taco"]["cost_cents"])["margin"]
    assert "goat-birria" not in items


# ---------------------------------------------------------------- segmentation vs a brute-force oracle
@pytest.fixture(scope="module")
def wh(tmp_path_factory):
    from nasha_lab.governed import tenants as T
    d = tmp_path_factory.mktemp("seg"); a, b = T.default_pair(d)
    return a.warehouse


def test_segments_match_an_independent_pure_python_recomputation(wh):
    seg, assign = GS.segment(wh)
    con = sqlite3.connect(wh)
    lines = con.execute("SELECT m.member_id, d.date, o.total_cents FROM fact_order o JOIN dim_member m USING(member_key) JOIN dim_date d USING(date_key)").fetchall()
    con.close()
    by = {}
    for mid, dt, tot in lines:
        e = by.setdefault(mid, [0, 0, "0000-00-00"]); e[0] += 1; e[1] += tot; e[2] = max(e[2], dt)
    ref = max(d for _, d, _ in lines)
    spends = sorted(v[1] for v in by.values()); q75 = spends[int(0.75 * (len(spends) - 1))]
    def oracle(n, spend, last):
        days = (date.fromisoformat(ref) - date.fromisoformat(last)).days
        if days <= 30 and n >= 5 and spend >= q75: return "champions"
        if n >= 5 and days <= 60: return "loyal"
        if n <= 2 and days <= 30: return "new"
        if n >= 3 and 61 <= days <= 120: return "at_risk"
        if days > 120: return "lapsed"
        return "occasional"
    want = {m: oracle(*v) for m, v in by.items()}
    assert assign == want
    assert sum(s["n"] for s in seg.values()) == len(by) and all(s["evidence_basis"] if "evidence_basis" in s else True for s in seg.values())
    for name, s in seg.items():
        assert s["est_value_cents"] == sum(by[m][1] for m, g in want.items() if g == name)
        assert 0 <= s["confidence"] < 1


def test_segment_confidence_grows_with_size_and_is_never_certain(wh):
    seg, _ = GS.segment(wh)
    big = max(seg.values(), key=lambda s: s["n"])
    assert big["confidence"] == big["n"] / (big["n"] + GS.CONF_K) < 1
