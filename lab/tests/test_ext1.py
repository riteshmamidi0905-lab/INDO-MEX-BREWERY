"""EXTERNALIZED / INDEPENDENT-STYLE EVAL v1: generators are deterministic, labels come from oracles/metadata, and the committed results match a re-run."""
import json

from nasha_lab import eval_ext1 as E1, eval_ext1_planners as EXP, knowledge as K, scenarios_ext as X, scenarios as S, eval_planners as EP


def test_ext1_scenarios_are_deterministic_and_disjoint_from_the_block3_registry():
    a = [(s.id, sorted(s.expected["action"])) for s in X.build_ext1()]; b = [(s.id, sorted(s.expected["action"])) for s in X.build_ext1()]
    assert a == b and len(a) == 106
    dev, held, adv = S.build(); old = {s.id for s in dev + held + adv + S.build_b()}
    assert not (old & {i for i, _ in a}) and all(s.menu_version == "v2" for s in X.build_ext1())


def test_oracle_is_a_decision_table_not_a_planner_call():
    assert X.oracle_inventory(dict(ing="goat", ratio=0.5, po="none"))["action"] == {"DRAFT_PURCHASE_RECOMMENDATION"}
    assert X.oracle_inventory(dict(ing="goat", ratio=2.0, po="none"))["action"] == {"NO_ACTION"}
    assert X.oracle_inventory(dict(ing="cauliflower", ratio=0.5, po="none"))["action"] == {"ESCALATE_SUPPLIER_UNAVAILABLE"}     # supplier S03 is ON_HOLD
    assert X.oracle_inventory(dict(ing="goat", ratio=0.5, po="in_time_big"))["action"] == {"NO_ACTION"}


def test_cross_document_vocabulary_comes_from_the_policy_checklist():
    rows = X.checklist_rows(); assert len(rows) >= 7 and any("gelatin" in r[0].lower() for r in rows)


def test_committed_deterministic_ext1_results_match_a_rerun():
    c = json.load(open(EP.__file__.replace("nasha_lab/eval_planners.py", "results/ext1_planner_deterministic.json")))
    r = EXP.run(EP.FACTORIES["deterministic"], "deterministic")
    assert r["headline"]["pass_rate"]["k"] == c["headline"]["pass_rate"]["k"] == 98 and r["relations"]["hold"] == c["relations"]["hold"] == 24
    assert [f["id"] for f in r["failures"]] == [f["id"] for f in c["failures"]]


def test_known_gap_in_open_order_quantity_is_pinned_not_hidden():
    r = EXP.run(EP.FACTORIES["deterministic"], "deterministic", [s for s in X.build_ext1() if s.family == "ext_po_quantity_probe"])
    assert r["headline"]["pass_rate"]["n"] == 0 and r["probes"]["pass_rate"]["k"] == 0 and r["probes"]["pass_rate"]["n"] == 8      # OPEN FINDING: any in-time open order is treated as covering the shortfall


def test_retrieval_ext1_labels_are_metadata_or_validated_by_construction():
    kb = K.default_kb("block3"); rows = E1.build(kb)
    assert {r["family"] for r in rows} == {"R1_supersession_metadata", "R2_terse_keyword", "R3_mutated_paraphrase"}
    for r in rows: assert all(d in {c["document_id"] for c in kb.chunks.values()} for d in r["gold_docs"])
    for r in [x for x in rows if x["family"] == "R2_terse_keyword"]:
        words = set(r["question"].split()); holders = {c["document_id"] for c in kb.chunks.values() if words <= set(K.tokenize(c["text"]))}
        assert holders and (holders == set(r["gold_docs"]) or set(r["gold_docs"]) <= holders)
