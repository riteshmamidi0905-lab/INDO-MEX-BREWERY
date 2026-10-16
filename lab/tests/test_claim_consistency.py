"""Claim drift guard: public numbers must equal values DERIVED from committed results/code (nasha_lab/canonical_claims.py)."""
import json
import re
from pathlib import Path

from nasha_lab import canonical_claims as C

L = Path(__file__).resolve().parent.parent
txt = lambda p: (L / p).read_text()
CL = C.compute()


def test_canonical_file_is_fresh():
    assert (L / "results" / "canonical_claims.json").read_text() == json.dumps(CL, indent=1, sort_keys=True) + "\n"


def test_wrong_silent_no_action_table_matches_results():
    # the experiment document table row must carry exactly the derived values 30 / 2 / 0
    row = next(l for l in txt("docs/TOOL-SCHEMA-EXPERIMENT.md").splitlines() if l.startswith("| wrong silent"))
    nums = [int(x) for x in re.findall(r"\*{0,2}(\d+)\*{0,2}\s*\|", row.rsplit(")", 1)[1])]
    p = CL["planner"]
    assert nums[:3] == [p["wrong_silent_no_action_ts1_raw"], p["wrong_silent_no_action_ts2_raw"], p["wrong_silent_no_action_ts2_guardrail"]]


def test_tool_schema_result_file_agrees_with_raw_rows():
    r = json.loads((L / "results" / "tool_schema_result.json").read_text())["rows"]
    p = CL["planner"]
    assert [x["wrong_silent_no_action"] for x in r] == [p["wrong_silent_no_action_ts1_raw"], p["wrong_silent_no_action_ts2_raw"], p["wrong_silent_no_action_ts2_guardrail"]]


def test_defect_type_wording():
    d = CL["data_quality"]
    assert d["injected_defect_types"] == d["eval_rule_keys"] == 12 and d["detected_precision_recall_1"] == 11 and d["undetected"] == ["near_duplicate_shifted"]
    readme = txt("README.md")
    assert "11 of 12 injected defect types" in readme and "10 of 11" not in readme


def test_headline_numbers_in_readme_and_case_study():
    p, m = CL["planner"], CL["retrieval_mrr"]
    readme, case = txt("README.md"), txt("docs/CASE-STUDY.md")
    assert p["deterministic_pass"] == "259/259" and "259/259" in readme and "259/259" in case
    for k in ("bm25", "minilm", "hybrid_minilm"):
        assert m[k] in readme and m[k] in case, k
    assert f"{CL['mutation']['killed']}/{CL['mutation']['valid']}" in readme
    assert "5/140" in case and p["qwen7b_raw_pass"] == "10/35" and "10/35" in case
    assert p["qwen1.5b_ts1_required_tools"] == "22/140" and p["qwen1.5b_ts2_required_tools"] == "67/140" and "22/140" in case and "67/140" in case


def test_test_count_is_never_bare_229_as_current():
    for f in ("README.md", "docs/CASE-STUDY.md"):
        for m in re.finditer(r"229", txt(f)):
            ctx = txt(f)[max(0, m.start() - 160): m.end() + 80].lower()
            assert "block 3" in ctx or "frozen" in ctx or "historical" in ctx, (f, ctx)
