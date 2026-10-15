"""Unit tests that exercise each defensive layer ALONE (found by mutation testing: two redundant layers masked each other, and one validator had no direct test)."""
import copy
import pytest
from nasha_lab import agent, planners as PL, tools as T

BASE_INV = dict(location_id="L01", ingredient="goat", unit="kg", last_count_date="2026-04-27", last_count_qty=2.0, days_since_count=1, receipts_since_count=0.0, usage_since_count_est=0.0, on_hand_estimate=2.0,
                avg_daily_usage_14d=1.0, days_of_cover=2.0, newer_counts_quarantined=[], data_flags=[])
BASE_RISK = dict(lead_time_days=5, supplier_id="S02", days_of_cover=2.0, open_po_qty_arriving_in_time=0.0, shortfall_before_lead_time=True, count_variance_ratio=1.0, recommended_qty_kg=12.0, reasons=[])
SUP = dict(suppliers=[dict(supplier_id="S02", name="x", status="ACTIVE", ingredient="goat", lead_time_days=5, spec_sheet_status="ON_FILE", min_order_qty=10.0)])


def entry(tool, data): return dict(tool=tool, ok=True, args={}, data=data)


def state(evidence, gaps):
    return dict(family="INVENTORY", event=dict(payload=dict(location_id="L01", ingredient="goat"), detected_at="2026-04-28"), evidence=evidence, assessment=dict(policy_citations=["D-81", "D-54"], policy_found=True, gaps=gaps, injection=False), policy={"items": []})


def ev(with_supplier=True, extra=None):
    e = {"E1:query_inventory": entry("query_inventory", BASE_INV), "E2:assess_inventory_risk": entry("assess_inventory_risk", BASE_RISK), "E3:get_open_purchase_orders": entry("get_open_purchase_orders", dict(purchase_orders=[]))}
    if with_supplier: e["E4:get_supplier_status"] = entry("get_supplier_status", SUP)
    e.update(extra or {}); return e


def test_missing_supplier_evidence_escalates_even_when_no_gap_was_recorded():
    """Layer 1 alone: short cover + no supplier evidence must escalate (kills the regression mutant that restores NO_ACTION)."""
    p = PL.deterministic_decide(state(ev(with_supplier=False), gaps=[]))
    assert p["action"] == "ESCALATE_INSUFFICIENT_EVIDENCE" and p["abstain"]


def test_a_recorded_gap_blocks_no_action_even_when_the_data_looks_healthy():
    """Layer 2 alone: healthy-looking evidence plus a failed check must not conclude NO_ACTION."""
    healthy = copy.deepcopy(ev()); healthy["E2:assess_inventory_risk"]["data"].update(shortfall_before_lead_time=False, days_of_cover=9.0)
    healthy["E1:query_inventory"]["data"].update(days_of_cover=9.0)
    assert PL.deterministic_decide(state(healthy, gaps=[dict(tool="list_quality_findings", code="UPSTREAM_FAILURE")]))["action"] == "ESCALATE_INSUFFICIENT_EVIDENCE"
    assert PL.deterministic_decide(state(healthy, gaps=[]))["action"] == "NO_ACTION"


@pytest.mark.parametrize("tool", ["place_purchase_order", "contact_supplier", "adjust_inventory_record", "drop_table", None])
def test_validate_mutations_refuses_any_tool_outside_the_two_allowed(tool):
    class Tr:
        def __init__(self): self.events = []
        def event(self, kind, **kw): self.events.append((kind, kw))
    tr = Tr(); pr = dict(mutating_actions=[dict(tool=tool, args=dict(table="orders", key="O000001", reason="x" * 12))], draft_id=None)
    n = agent.validate_mutations(pr, {"E1": entry("query_inventory", {"key": "O000001"})}, dict(payload={}), tr)
    assert n == 1 and pr["mutating_actions"] == [] and tr.events[0][0] == "mutation_rejected"


def test_validate_mutations_keeps_a_grounded_flag_and_this_runs_own_draft_only():
    class Tr:
        def event(self, *a, **k): pass
    ok = dict(tool="flag_record_for_review", args=dict(table="inventory_counts", key="L01:2026-04-27:goat", reason="recount"))
    pr = dict(mutating_actions=[ok, dict(tool="release_draft", args=dict(draft_id="DR-aaaaaaaa"))], draft_id="DR-bbbbbbbb")
    assert agent.validate_mutations(pr, {"E1": entry("query_inventory", BASE_INV)}, dict(payload={}), Tr()) == 1 and pr["mutating_actions"] == [ok]
