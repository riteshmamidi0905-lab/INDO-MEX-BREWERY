"""Data-quality framework: rules score against the generator's labelled defects; misses and cross-flags are reported, not hidden."""
import pytest

from analytics import dqf
from nasha_lab import generator


@pytest.fixture(scope="module")
def sc():
    return dqf.score(range(1, 6))


def test_every_dimension_is_covered():
    assert {r.dimension for r in dqf.RULES} >= {"completeness", "uniqueness", "referential_integrity", "range", "timeliness", "consistency", "validity", "policy"}


def test_rules_never_read_truth_labels():
    import inspect
    assert "truth" not in "".join(r.sql for r in dqf.RULES).lower()


def test_each_injected_type_is_found_by_some_rule(sc):
    for t, v in sc["per_defect_type_any_rule_recall"].items():
        assert v["total"] > 0 and v["recall"] == 1.0, (t, v)       # measured: all 12 types caught (injected defects are easy by construction)


def test_targeted_rule_recall_and_precision(sc):
    for rid, v in sc["per_rule"].items():
        if v["targets"]:
            assert v["recall"] == 1.0, rid
            if not rid.startswith("UNIQ-03"):
                assert v["precision"] >= 0.95, (rid, v)


def test_tolerance_rule_cross_flags_exact_copies(sc):
    v = next(v for k, v in sc["per_rule"].items() if k.startswith("UNIQ-03"))
    assert v["fp_other_injected_defect"] == v["tp"] and v["fp_clean_row"] == 0     # it also flags the exact-timestamp copies; no clean rows


def test_no_false_alarms_on_clean_data():
    out = dqf.clean_run(range(1, 4))
    assert out["total_flags"] == 0 and out["orders_scanned"] > 10000


def test_lab_rules_miss_shifted_near_duplicates_but_framework_finds_them():
    lab = dqf.lab_rules_score(range(1, 4))
    assert lab["near_duplicate_shifted"]["found"] == 0 and lab["duplicate_order"]["recall"] == 1.0


def test_freshness_and_reconciliation():
    raw, _ = generator.generate(1, 8, menu_version="v2")
    f = dqf.freshness(dqf.landing_db(raw))
    assert f["ok"] and f["newest_valid_order_date"] == "2026-04-26"
    assert all(v["ok"] for v in dqf.reconciliation(raw).values())
    assert not dqf.freshness(dqf.landing_db(raw), as_of="2026-06-30")["ok"]


def test_novel_defects_reveal_a_blind_spot():
    p = dqf.novel_probe()
    assert p["timezone_slip_5h"]["detected"] == 0           # structurally valid but wrong: no rule can see it
    assert p["negative_inventory_qty"]["detected"] == 10
