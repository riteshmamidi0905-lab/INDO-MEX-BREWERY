import math
import sqlite3

import numpy as np
import pytest
from scipy import stats

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import analytics, dashboards, db, experiments, pipeline

CFG = es.SimConfig(name="bi-test", months=6, fast_casual=4, beer_gardens=1, target_orders=40_000, loyalty_profiles=6_000, employees=80, open_at_start=4)


@pytest.fixture(scope="module")
def wh(tmp_path_factory):
    d = tmp_path_factory.mktemp("bi")
    es.generate(CFG, d / "src")
    r = pipeline.run(d / "src", d / "wh.db")
    assert r["status"] == "published"
    return d / "wh.db"


def test_dashboards_render_and_carry_the_synthetic_banner(wh, tmp_path):
    files = dashboards.build_all(wh, tmp_path)
    assert files == sorted(f for f, _ in dashboards.PAGES)
    for f in files:
        t = (tmp_path / f).read_text()
        assert "SYNTHETIC DATA" in t and 'content="noindex,nofollow"' in t and "NaN" not in t and "nan%" not in t
        assert "<svg" in t or "<table" in t
    assert (tmp_path / "experiment-results.json").exists()


def test_dashboards_and_analytics_refuse_an_unpublished_warehouse(wh, tmp_path):
    import shutil
    p = tmp_path / "blocked.db"
    shutil.copy(wh, p)
    con = db.connect(p)
    con.execute("UPDATE warehouse_status SET status='blocked'")
    con.commit()
    with pytest.raises(analytics.NotPublished):
        analytics.cohort_matrix(con)
    with pytest.raises(analytics.NotPublished):
        dashboards.build_all(p, tmp_path / "out")


def test_two_proportion_matches_scipy_and_srm_catches_a_bad_split():
    r = experiments.two_proportion(540, 5000, 500, 5000)
    z = (0.108 - 0.1) / math.sqrt(0.108 * 0.892 / 5000 + 0.1 * 0.9 / 5000)
    assert abs(r["p"] - 2 * (1 - stats.norm.cdf(abs(z)))) < 1e-9
    assert experiments.srm_check(5000, 5000)["ok"] and not experiments.srm_check(6200, 3800)["ok"]
    assert experiments.n_per_arm(0.10, 0.02) > experiments.n_per_arm(0.10, 0.04)


def test_portfolio_reports_every_kind_of_outcome_including_the_invalid_one():
    out = {x["id"]: x["verdict"].split(":")[0] for x in experiments.run_portfolio(0.6)}
    assert out["E1"] == "WIN" and out["E4"] == "HARM" and out["E5"] == "REJECT" and out["E2"] in ("INCONCLUSIVE", "WIN") and out["E3"] in ("NO EFFECT detected (consistent with the null)", "WIN", "HARM")
    assert out["E5"] == "REJECT"


def test_assignment_is_deterministic_and_roughly_balanced():
    a = [experiments.assign(f"M{i}", "X1") for i in range(4000)]
    assert a == [experiments.assign(f"M{i}", "X1") for i in range(4000)]
    assert abs(a.count("treatment") / 4000 - 0.5) < 0.03
    assert a != [experiments.assign(f"M{i}", "X2") for i in range(4000)]


def test_funnel_cohorts_and_segments_are_internally_consistent(wh):
    con = db.connect(wh)
    f = analytics.loyalty_funnel(con)
    assert f["members"] == CFG.loyalty_profiles and f["ever_ordered"] <= f["members"] and 0 <= f["first_order_within_30d_rate"] <= 1
    m = analytics.cohort_matrix(con)
    assert m.iloc[:, 0].between(0, 1).all() and (m.stack().dropna() <= 1.0).all()
    df, seg = analytics.rfm_segments(con)
    assert seg.members.sum() == len(df) and set(df.R) == {1, 2, 3}
    promo = analytics.promotion_analysis(con)
    assert all(("p" in x) or ("note" in x) for x in promo)
