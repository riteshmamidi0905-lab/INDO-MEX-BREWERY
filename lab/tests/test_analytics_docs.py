"""Docs and dashboard are rendered from the committed results files; results are reproducible; claims in the docs hold against the data."""
import json
import os

from analytics import render_docs as RD, dashboard
from analytics import config as C

LAB = RD.LAB


def read(p):
    return open(os.path.join(LAB, p), encoding="utf-8").read()


def test_docs_match_render_of_committed_results():
    assert read("docs/ANALYTICS-MART.md") == RD.render_mart()
    assert read("docs/ANALYTICS-EVALUATION.md") == RD.render_eval()
    assert read("docs/ANALYTICS-EXEC-MEMO.md") == RD.render_memo()
    assert read("results/analytics/dashboard.html") == dashboard.render()


def test_every_doc_carries_the_synthetic_banner_and_memo_has_not_claimed():
    for f in ("ANALYTICS-MART.md", "ANALYTICS-EVALUATION.md", "ANALYTICS-EXEC-MEMO.md"):
        assert "SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED" in read("docs/" + f)
    memo = read("docs/ANALYTICS-EXEC-MEMO.md")
    assert "## NOT CLAIMED" in memo and "Invalidated" in memo and len(memo.split()) < 1100


def test_results_files_record_config_hash():
    for f in os.listdir(os.path.join(LAB, "results", "analytics")):
        if f.endswith(".json") and f != "dashboard_check.json":
            assert json.loads(read("results/analytics/" + f))["_config_hash"] == C.config_hash(), f


def test_hard_coded_doc_claims_hold_against_results():
    dq = RD.R("dq_evaluation")["score"]["per_rule"]
    u3 = next(v for k, v in dq.items() if k.startswith("UNIQ-03"))
    assert u3["precision"] == 0.5 and u3["fp_clean_row"] == 0
    price = next(v for k, v in dq.items() if k.startswith("RANGE-02"))
    assert price["fp_other_injected_defect"] == 3 and price["fp_clean_row"] == 0
    assert RD.R("dq_evaluation")["lab_rules_for_comparison"]["near_duplicate_shifted"]["found"] == 0


def test_dashboard_is_self_contained():
    h = read("results/analytics/dashboard.html")
    assert "http://" not in h and "https://" not in h and "<script" not in h and 'lang="en"' in h
    chk = json.loads(read("results/analytics/dashboard_check.json"))
    assert all(not v["horizontalScroll"] and not v["externalRequests"] and v["svgLabelled"] for v in chk["views"])
