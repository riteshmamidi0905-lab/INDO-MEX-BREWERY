"""Difficult SQL cases. PUBLIC tests always run (candidate-facing material, manifest). KEY tests need the private answer keys and run only when
NASHA_PRIVATE_KEYS points at the private directory; they SKIP cleanly otherwise."""
import os
import re

import pytest

from analytics import difficult as D

CASES = D.case_dirs()
IDS = [os.path.basename(c) for c in CASES]
KD = D.keys_dir()
needs_keys = pytest.mark.skipif(KD is None, reason="NASHA_PRIVATE_KEYS not set: private answer keys not available")


def test_there_are_ten_cases_with_candidate_facing_files_only():
    assert len(CASES) == 10
    for d in CASES:
        assert sorted(os.listdir(d)) == ["fixture.sql", "prompt.md", "trap.sql"], d
        for f in ("prompt.md", "fixture.sql", "trap.sql"):
            assert os.path.getsize(os.path.join(d, f)) > 50, (d, f)


def test_manifest_covers_all_thirty_removed_key_files():
    mf = D.manifest()
    assert len(mf) == 30
    for d in CASES:
        for f in D.KEY_FILES:
            h = mf[f"{os.path.basename(d)}/{f}"]
            assert re.fullmatch(r"[0-9a-f]{64}", h)


@pytest.mark.parametrize("d", CASES, ids=IDS)
def test_fixture_loads_and_trap_query_runs(d):
    cols, rows = D.run_trap(d)
    assert cols and rows is not None


def test_prompt_does_not_leak_the_answer():
    for d in CASES:
        p = open(os.path.join(d, "prompt.md"), encoding="utf-8").read().lower()
        assert "trap" not in p and "wrong" not in p and "solution" not in p


def test_cases_are_labelled_synthetic():
    for d in CASES:
        assert "SYNTHETIC" in open(os.path.join(d, "prompt.md"), encoding="utf-8").read()


def test_no_answer_key_material_in_repo_tree():
    root = os.path.dirname(D.HERE)
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            assert f not in ("solution.sql", "expected.json", "explanation.md"), os.path.join(dp, f)


@needs_keys
def test_private_keys_match_the_public_manifest():
    mf = D.manifest()
    for rel, h in mf.items():
        assert D.sha256_file(os.path.join(KD, rel)) == h, rel


@needs_keys
@pytest.mark.parametrize("d", CASES, ids=IDS)
def test_solution_matches_expected_and_trap_does_not(d):
    r = D.run_case(d, KD)
    exp = r["expected"]
    assert r["solution"]["columns"] == exp["columns"]
    assert D.same(r["solution"]["rows"], exp["rows"], exp["ordered"])
    assert not D.same(r["trap"]["rows"], exp["rows"], exp["ordered"]), "the trap query must give a wrong answer"
    assert D.same(r["trap"]["rows"], exp["trap_rows"], exp["ordered"]), "documented trap output must be what the trap really returns"


@needs_keys
def test_private_keys_are_complete():
    for d in CASES:
        for f in D.KEY_FILES:
            assert os.path.getsize(os.path.join(KD, os.path.basename(d), f)) > 50, (d, f)
