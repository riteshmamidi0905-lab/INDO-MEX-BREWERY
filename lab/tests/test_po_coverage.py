"""Block 4.5 (NEW finding/fix): an open purchase order resolves a shortage only if its quantity covers the demand through the lead time that usable stock does not.
Found by the independent-style evaluation (rule-gap probes, 0/8 under the frozen v1 rule). The frozen v1 rule stays the default so Block 3 reproduces."""
import pytest

from nasha_lab import eval_planners as EP, scenarios as S, tools as T

ING, LOC = "goat", "L01"            # supplier S02 ACTIVE, lead time 5 days


def _world(po_coverage="v2"):
    return S.fresh_world(1, "v2", po_coverage)


def _needs(w, cover=0.8):
    S.clear_pos(w, ING); S.set_cover(w, LOC, ING, cover, True)
    inv = T.t_query_inventory(w, T.InventoryIn(location_id=LOC, ingredient=ING), None); lead = S.ING[ING][1]
    return inv, max(0.0, inv["avg_daily_usage_14d"] * lead - (inv["on_hand_estimate"] or 0.0)), lead


def _run(pos, cover=0.8, mutate=None, po_coverage="v2"):
    """pos: list of (fraction_of_required_or_absolute, days_out, absolute?) -> run the full deterministic agent on that situation; return the proposed action and the risk output."""
    def setup(w):
        inv, req, lead = _needs(w, cover)
        for i, (q, d) in enumerate(pos): S.add_po(w, ING, S.ING[ING][0], round(q(req) if callable(q) else q, 3), d, f"PO-T{i}")
        if mutate: mutate(w)
        return dict(location_id=LOC, ingredient=ING, subtype="LOW_COVER")
    sc = S.Scenario("T-PO", "t", "t", "INVENTORY", setup, dict(action={"X"}, abstain=None, required=set()), menu_version="v2", po_coverage=po_coverage)
    r = EP.run_scenario(sc, lambda: EP.PL.DeterministicPlanner())
    return r["action"]


def test_fully_covering_po_resolves_the_shortage():
    assert _run([(lambda r: r * 1.2, 4)]) == "NO_ACTION"


def test_partially_covering_po_does_not_and_the_draft_accounts_for_it():
    assert _run([(lambda r: r * 0.4, 4)]) == "DRAFT_PURCHASE_RECOMMENDATION"


def test_zero_quantity_po_does_not_cover():
    assert _run([(0.0, 4)]) == "DRAFT_PURCHASE_RECOMMENDATION"


def test_multiple_pos_are_summed_but_only_those_arriving_in_time():
    two = [(lambda r: r * 0.55, 3), (lambda r: r * 0.55, 4)]
    assert _run(two) == "NO_ACTION"                                                # 1.1 x required together
    assert _run(two[:1]) == "DRAFT_PURCHASE_RECOMMENDATION"                       # either alone is not enough
    assert _run([(lambda r: r * 0.55, 3), (lambda r: r * 5, 9)]) == "DRAFT_PURCHASE_RECOMMENDATION"   # the big one arrives after the 5-day lead time


def test_late_po_never_counts_however_large():
    assert _run([(500.0, 9)]) == "DRAFT_PURCHASE_RECOMMENDATION"


def test_boundary_equal_quantity_covers_and_a_hair_less_does_not():
    assert _run([(lambda r: r + 0.0005, 4)]) == "NO_ACTION"
    assert _run([(lambda r: r - 0.01, 4)]) == "DRAFT_PURCHASE_RECOMMENDATION"


def test_stale_or_quarantined_inventory_is_not_usable_and_asks_for_a_recount_instead_of_no_action():
    def stale(w):
        for d in ("2026-04-27", "2026-04-20"): w.con.execute("DELETE FROM fact_inventory_count WHERE location_id=? AND ingredient=? AND count_date=?", (LOC, ING, d))
    assert _run([(500.0, 4)], mutate=stale) == "REQUEST_RECOUNT"
    def quarantined(w): w.con.execute("INSERT INTO quarantine VALUES('inventory_counts', ?, 'unit_mismatch', 0)", (f"{LOC}:2026-04-28:{ING}",))
    assert _run([(500.0, 4)], mutate=quarantined) == "REQUEST_RECOUNT"             # a newer count was quarantined by the data-quality layer: stock is not trusted


def test_usable_stock_is_zero_when_the_count_is_stale_in_the_tool_output():
    w = _world()
    for d in ("2026-04-27", "2026-04-20"): w.con.execute("DELETE FROM fact_inventory_count WHERE location_id=? AND ingredient=? AND count_date=?", (LOC, ING, d))
    out = T.t_assess_inventory_risk(w, T.RiskIn(location_id=LOC, ingredient=ING), None)
    assert out["po_coverage_rule"] == "v2" and out["usable_on_hand_kg"] == 0.0 and out["required_qty_through_lead_kg"] > 0


def test_frozen_v1_rule_is_unchanged_by_default_so_block3_reproduces():
    assert _run([(1.0, 4)], po_coverage="v1") == "NO_ACTION"                       # a 1 kg order still "covers" under the frozen rule (the documented simplification)
    w = _world("v1"); out = T.t_assess_inventory_risk(w, T.RiskIn(location_id=LOC, ingredient=ING), None)
    assert "po_coverage_rule" not in out                                          # v1 tool output is byte-identical to Block 3


def test_current_state_worlds_use_the_quantity_aware_rule():
    from nasha_lab import world as W
    assert W.CURRENT_PO_COVERAGE == "v2"
