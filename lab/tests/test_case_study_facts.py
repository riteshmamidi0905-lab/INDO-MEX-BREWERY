"""Numbers quoted in the website case-study pages must match the repo (tests counts, evaluation case count), so the prose cannot drift from the evidence."""
import pathlib
import re
import subprocess
import sys

import pytest

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import ops_ai_eval, pipeline

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = ROOT / "website/preview-courtyard/case-studies"


def collected(path):
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", path], capture_output=True, text=True, cwd=ROOT / "lab")
    m = re.search(r"(\d+) tests? collected", r.stdout)
    return int(m.group(1)) if m else None


def page(name):
    return (PAGES / f"{name}.html").read_text()


def test_quoted_test_counts_match_collection():
    assert f"({collected('tests/test_ops_ai_warehouse.py')})" in page("ops-ai-gate")
    assert collected("tests/test_ops_ai_weir.py") in (4, None) and "(4 tests against the real gateway)" in page("ops-ai-weir")
    assert "708 − 7 + 1 = 702" in page("ci-test-count")


def test_quoted_evaluation_size_matches_the_harness(tmp_path):
    d = tmp_path; es.generate(es.SimConfig(name="f", months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_000, employees=60, open_at_start=3), d / "s"); pipeline.run(d / "s", d / "w.db")
    n = len(ops_ai_eval.build_cases(d / "w.db"))
    assert f"{n} cases" in page("ops-ai-gate") and f"{n} of {n} pass" in page("ops-ai-gate")


def test_every_page_states_its_limits_and_synthetic_status():
    for f in PAGES.glob("*.html"):
        t = f.read_text()
        assert "Limits and what is not claimed" in t and "synthetic" in t.lower() and 'noindex' in t


def test_recipe_to_analytics_case_study_numbers(tmp_path):
    t = page("recipe-to-analytics")
    n_s, n_r = collected("tests/test_scenario_d87.py"), collected("tests/test_recipes_d87.py")
    assert f"{n_s + n_r} new tests ({n_r} recipe, pricing and approval; {n_s} warehouse scenario)" in t
    from nasha_lab.warehouse import scenario
    d = tmp_path; es.generate(es.SimConfig(name="f2", months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_000, employees=60, open_at_start=3), d / "s"); pipeline.run(d / "s", d / "w.db")
    scenario.build(d / "w.db")
    assert f"{len(ops_ai_eval.build_cases(d / 'w.db'))} Ops AI evaluation cases" in t
