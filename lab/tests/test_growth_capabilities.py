"""The capability tracker may not overclaim: its validator must reject unsupported statuses, and the committed tracker must validate."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bgc", LAB / "tools/build_growth_capabilities.py")
B = importlib.util.module_from_spec(spec); sys.modules["bgc"] = B; spec.loader.exec_module(B)
DOC = json.loads(B.SRC.read_text())


def test_committed_tracker_validates_and_has_all_25():
    assert B.problems(DOC) == [] and len(DOC["capabilities"]) == 25


def test_only_crm_automation_is_integrated_and_no_capability_beyond_what_exists_is_marked_tested():
    assert [c["n"] for c in DOC["capabilities"] if c["status"] == "INTEGRATED"] == [14]
    assert {c["n"] for c in DOC["capabilities"] if c["status"] == "TESTED"} == {1, 5, 8, 15, 24}


def test_validator_rejects_overclaims():
    d = copy.deepcopy(DOC); d["capabilities"][1]["status"] = "TESTED"                 # #2 has no tests
    assert any("without a test" in p for p in B.problems(d))
    d = copy.deepcopy(DOC); d["capabilities"][0]["tests"] = ["lab/tests/test_growth_foundation.py::test_that_does_not_exist"]
    assert any("test missing" in p for p in B.problems(d))
    d = copy.deepcopy(DOC); d["capabilities"][4]["status"] = "INTEGRATED"              # #5 has no UI and no workflow/api/ui tests
    assert any("INTEGRATED needs" in p for p in B.problems(d))
    d = copy.deepcopy(DOC); d["capabilities"][13]["tests"] = [x for x in d["capabilities"][13]["tests"] if "test_growth_ui" not in x]
    assert any("needs a ui test" in p for p in B.problems(d))
    d = copy.deepcopy(DOC); d["capabilities"][5]["code"] = []
    assert any("without code" in p for p in B.problems(d))
    d = copy.deepcopy(DOC); d["capabilities"].pop()
    assert any("1..25" in p for p in B.problems(d))
