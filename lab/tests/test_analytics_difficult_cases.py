"""Each difficult case: the reference solution matches expected.json, the documented trap query demonstrably does NOT, and the case is complete."""
import os

import pytest

from analytics import difficult as D

CASES = D.case_dirs()


def test_there_are_ten_complete_cases():
    assert 8 <= len(CASES) <= 10 and len(CASES) == 10
    for d in CASES:
        for f in ("prompt.md", "fixture.sql", "trap.sql", "solution.sql", "expected.json", "explanation.md"):
            assert os.path.getsize(os.path.join(d, f)) > 50, (d, f)


@pytest.mark.parametrize("d", CASES, ids=[os.path.basename(c) for c in CASES])
def test_solution_matches_expected_and_trap_does_not(d):
    r = D.run_case(d)
    exp = r["expected"]
    assert r["solution"]["columns"] == exp["columns"]
    assert D.same(r["solution"]["rows"], exp["rows"], exp["ordered"])
    assert not D.same(r["trap"]["rows"], exp["rows"], exp["ordered"]), "the trap query must give a wrong answer"
    assert D.same(r["trap"]["rows"], exp["trap_rows"], exp["ordered"]), "documented trap output must be what the trap really returns"


def test_prompt_does_not_leak_the_answer():
    for d in CASES:
        p = open(os.path.join(d, "prompt.md"), encoding="utf-8").read().lower()
        assert "trap" not in p and "wrong" not in p and "solution" not in p


def test_cases_are_labelled_synthetic():
    for d in CASES:
        assert "SYNTHETIC" in open(os.path.join(d, "prompt.md"), encoding="utf-8").read()
