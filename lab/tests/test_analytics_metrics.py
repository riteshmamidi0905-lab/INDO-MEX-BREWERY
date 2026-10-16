"""Semantic-layer discipline: every metric is defined once (metrics.json) and reconciles between the mart and the source side."""
import pytest

from analytics import mart, metrics as M


@pytest.fixture(scope="module")
def con():
    return mart.build(seed=1)[0]


def test_every_metric_is_fully_specified():
    ms = M.load()["metrics"]
    assert len(ms) >= 14 and len({m["name"] for m in ms}) == len(ms)
    for m in ms:
        assert all(k in m for k in M.REQUIRED), m["name"]
        assert m["caveats"] and m["owner"] and m["formula"]
        assert ("raw_sql" in m) != ("raw_python" in m), m["name"]       # exactly one independent source-side definition
        assert m["group_by"] in ("site", "supplier", "all")


def test_assumption_dependent_metrics_say_so():
    for m in M.load()["metrics"]:
        if m["name"] in ("contribution_margin_usd", "gross_sales_usd"):
            assert m["assumption_dependent"] and any("ASSUMPTION" in c or "PLACEHOLDER" in c for c in m["caveats"] + [m["label"]])


def test_all_metrics_reconcile_mart_vs_source(con):
    bad = [r for r in M.reconcile(con) if not r["ok"]]
    assert bad == [], [(r["metric"], r["max_abs_diff"]) for r in bad]


def test_ratio_metrics_are_not_averages_of_site_ratios(con):
    # the documented trap: avg order value overall = total / orders, not the mean of per-site values
    aov = M.compute(con, next(m for m in M.load()["metrics"] if m["name"] == "avg_order_value_usd"))
    total = con.execute("SELECT SUM(order_total_cents)/100.0/COUNT(*) FROM fact_order").fetchone()[0]
    assert abs(sum(aov.values()) / len(aov) - total) > 1e-3


def test_known_value_shapes(con):
    sales = M.compute(con, next(m for m in M.load()["metrics"] if m["name"] == "gross_sales_usd"))
    assert set(sales) == {"L01", "L02", "L03"} and sales["L01"] > sales["L02"] > sales["L03"] > 0     # site volume factors 1.0 / 0.7 / 0.5
    q = M.compute(con, next(m for m in M.load()["metrics"] if m["name"] == "dq_quarantine_rate"))
    assert 0.005 < q["ALL"] < 0.05
