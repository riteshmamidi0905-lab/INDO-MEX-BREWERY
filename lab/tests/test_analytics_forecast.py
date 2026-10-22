"""Forecast baselines: correctness of each method on constructed series, no look-ahead, and a small backtest sanity run. SYNTHETIC data."""
import numpy as np
import pytest

from analytics import forecast as F


def test_naive_and_seasonal_naive_on_known_series():
    x = np.array([1., 2, 3, 4, 5, 6, 7] * 4)
    assert (F.f_naive(x) == 7).all()
    assert list(F.f_snaive(x)) == [1, 2, 3, 4, 5, 6, 7]
    assert list(F.f_seasonal_mean(x)) == [1, 2, 3, 4, 5, 6, 7]
    assert F.f_ma7(x)[0] == 4


def test_hw_learns_pure_seasonality():
    x = np.array([10., 12, 11, 9, 20, 25, 22] * 6)
    f = F.f_hw(x)
    assert np.abs(f - x[:7]).max() < 1.0


def test_ses_is_flat_and_between_min_and_max():
    x = np.array([5., 7, 6, 8, 7, 6, 9, 8, 7, 6] * 3)
    f = F.f_ses(x)
    assert len(set(f)) == 1 and x.min() <= f[0] <= x.max()


def test_no_lookahead_changing_future_does_not_change_forecast():
    rng = np.random.default_rng(0); x = rng.uniform(1, 5, 56)
    for name, fn in F.FUNCS.items():
        a = fn(x[:35]); y = x.copy(); y[35:] = 999
        assert np.allclose(a, fn(y[:35])), name


@pytest.fixture(scope="module")
def res():
    return F.run(seeds=(1, 2))


def test_backtest_structure_and_labels(res):
    assert res["synthetic"] and "says nothing about real demand" in res["disclaimer"]
    assert set(res["overall"]) == set(F.MODELS)
    assert res["overall"]["naive"]["n_forecasts"] == 2 * 24 * 4
    for m in F.MODELS:
        assert res["overall"][m]["WAPE"] > 0 and 0.5 < res["interval_80"][m]["empirical"] < 1


def test_smoothing_models_beat_last_value_naive(res):
    # measured on this synthetic data: daily usage is noisy, so averaging beats copying the last day
    for m in ("moving_average_7", "seasonal_mean", "ses", "holt_winters_add"):
        assert res["overall"][m]["WAPE"] < res["overall"]["naive"]["WAPE"]
        assert res["paired_vs_naive"][m]["ci95"][1] < 0
