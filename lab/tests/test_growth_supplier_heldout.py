"""Held-out supplier-intelligence cases, kept SEPARATE from the development sets in supplier_eval. They were written after the rules were frozen (engineering commit 168fdb5) and run once; their results are pinned here as a
record, INCLUDING the misses, so the numbers cannot be quietly improved by tuning rules to them. If a rule changes and these results move, that is a deliberate, visible decision, and the cases stop being held out.
Small, author-labelled sets: they say nothing about general accuracy on the supplier market."""
from nasha_lab.growth import supplier_eval as DEV, supplier_heldout as HO


def test_held_out_results_are_pinned_misses_included():
    r = HO.run()
    d, c, a = r["dedupe"], r["classification"], r["service_area"]
    assert r["frozen_at"] == "168fdb5"
    assert (d["cases"], d["true_positive"], d["false_positive"], d["false_negative"]) == (22, 8, 0, 4) and d["precision"] == 1.0 and round(d["recall"], 3) == 0.667
    assert sorted(d["misses"]) == sorted(["Austin Homebrew Supply | Austin Home Brew Supply", "Restaurant Depot | Restaurant Depot Austin", "WebstaurantStore | Webstaurant Store", "Hill Country Dairies | Hill Country Dairy"])
    assert (c["cases"], c["correct"]) == (24, 23) and c["misses"] == ["Fitness studio fit-out contractor -> fitness_equipment"]
    assert (a["cases"], a["correct"]) == (12, 12)


def test_held_out_cases_are_disjoint_from_the_development_cases_and_the_rules_do_not_regress_on_either():
    dev_pairs = {frozenset((a, b)) for a, _, b, _, _ in DEV.DEDUPE}; ho_pairs = {frozenset((a, b)) for a, _, b, _, _ in HO.DEDUPE}
    assert not dev_pairs & ho_pairs
    assert not {(c, n) for c, n, *_ in DEV.CLASSIFY} & {(c, n) for c, n, *_ in HO.CLASSIFY}
    assert not {(l, s) for l, s, _ in DEV.AREA} & {(l, s) for l, s, _ in HO.AREA}
    r = DEV.run_eval()
    assert r["dedupe"]["false_positive"] == 0 and r["dedupe"]["false_negative"] == 0 and r["classification"]["accuracy"] == 1.0 and r["service_area"]["accuracy"] == 1.0
