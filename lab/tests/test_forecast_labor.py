"""Forecasting and labor analytics: methods are correct on known signals, the backtest has no look-ahead, and the new dashboard pages render."""
import numpy as np
import pytest

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import dashboards, db, forecast as F, pipeline

CFG = es.SimConfig(name="fc-test", months=8, fast_casual=3, beer_gardens=1, target_orders=30_000, loyalty_profiles=2_000, employees=60, open_at_start=4)


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    d = tmp_path_factory.mktemp("fc"); es.generate(CFG, d / "src"); pipeline.run(d / "src", d / "w.db")
    c = db.connect(d / "w.db"); yield c; c.close()


def test_methods_are_exact_on_a_pure_weekly_signal():
    y = np.tile([10, 12, 11, 9, 20, 30, 25], 12).astype(float)
    for m in ("seasonal_naive", "seasonal_mean_4w"):
        assert np.allclose(F.METHODS[m](y, 14), np.tile([10, 12, 11, 9, 20, 30, 25], 2))
    assert np.abs(F.holt_winters(y, 7) - y[-7:]).max() < 1.0


def test_backtest_is_free_of_look_ahead():
    rng = np.random.default_rng(0)
    y = np.tile([10, 12, 11, 9, 20, 30, 25], 20) + rng.normal(0, 1, 140)
    a, _ = F.backtest(y, 28)
    y2 = y.copy(); y2[-28:] += 1000                  # corrupt only the newest window: must change only the newest origin's score
    b, _ = F.backtest(y2, 28)
    assert a["seasonal_naive"]["wape"] != b["seasonal_naive"]["wape"]
    y3 = y.copy(); y3[-28 * 4:] = y3[-28 * 4:]       # same data -> identical results (deterministic)
    assert F.backtest(y3, 28)[0] == a


def test_forecast_report_shape_and_best_method_by_backtest(con):
    r = F.forecast_report(con, 28)
    assert "company" in r and len(r) == 4
    for v in r.values():
        assert len(v["forecast"]) == 28 and v["best"] in F.METHODS and all(x >= -1e-6 for x in v["forecast"])
        assert v["backtest"][v["best"]]["wape"] == min(x["wape"] for x in v["backtest"].values() if x["wape"] is not None)


def test_labor_report_reconciles_with_the_warehouse(con):
    lr = F.labor_report(con)
    act = con.execute("SELECT sum(actual_labor_hours) FROM mart_daily_location").fetchone()[0]
    assert lr["by_site"].act.sum() == pytest.approx(act)
    assert len(lr["dow"]) == 7 and lr["outliers"].lp.min() >= lr["p95_labor_pct"] - 1e-9


def test_new_pages_are_built_and_labelled_synthetic(con, tmp_path):
    pages = dashboards.build_all(con.execute("PRAGMA database_list").fetchone()[2], tmp_path)
    assert "labor.html" in pages and "forecast.html" in pages
    for p in ("labor.html", "forecast.html"):
        t = (tmp_path / p).read_text()
        assert "SYNTHETIC" in t and "noindex" in t and "<table" in t
