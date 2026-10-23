"""Governed-workflow evaluation: independent oracles, reproducibility, mutation kill."""
import pytest
from nasha_lab.governed import evaluation, tenants


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("eval")
    return evaluation.full_report(tmp, tenants.default_pair(tmp))


def test_baseline_cases_pass(report):
    bad = [c for c in report["results"] if not c["passed"]]
    assert not bad, bad


def test_reproducible(report):
    assert report["reproducible"] is True


def test_all_mutants_killed(report):
    survivors = [m for m in report["mutants"] if not m["killed"]]
    assert not survivors, survivors


def test_metrics_shape(report):
    m = report["metrics"]
    assert m["cases"] == len(report["results"]) and m["unauthorized_action_rate"] == 0.0
    assert report["mutants_killed"] == report["mutants_total"] == len(report["mutants"])
