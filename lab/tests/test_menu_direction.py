"""Founder decision D-84: MANGO HABANERO GOBI is an appetizer / shareable, not a taco. Current-state data and knowledge use it; the frozen Block 3 baseline does not change."""
import pytest

from nasha_lab import generator, knowledge as K, world as W


@pytest.fixture(scope="module")
def cur():
    return K.default_kb("current")


def test_current_menu_master_is_mango_habanero_gobi_no_tortilla():
    w, _, _ = W.build_world(1, menu_version=generator.CURRENT_MENU_VERSION)
    m4 = w.q("SELECT * FROM dim_menu_item WHERE item_id='M04'")[0]
    assert m4["name"] == "Mango Habanero Gobi" and "taco" not in m4["name"].lower()
    assert generator.MENU_COURSE_V2["M04"] == "appetizer / shareable"
    assert "corn masa" not in w.recipes["M04"] and w.recipes["M04"] == {"cauliflower": .20}      # cauliflower stays the main ingredient, no tortilla
    assert not any("taco" in r["name"].lower() and r["item_id"] == "M04" for r in w.q("SELECT * FROM dim_menu_item"))


def test_frozen_default_menu_is_unchanged_so_block3_reproduces():
    w, _, _ = W.build_world(1)
    assert w.menu_version == "v1" and w.q("SELECT name FROM dim_menu_item WHERE item_id='M04'")[0]["name"] == "Gobi Taco" and "corn masa" in w.recipes["M04"]


def test_menu_item_id_and_foreign_keys_are_stable_across_versions():
    a, _, _ = W.build_world(1); b, _, _ = W.build_world(1, menu_version="v2")
    q = "SELECT COUNT(*) n, SUM(qty) s FROM fact_order_line WHERE item_id='M04'"
    assert a.q(q) == b.q(q) and a.q("SELECT COUNT(*) n FROM fact_order_line")[0] == b.q("SELECT COUNT(*) n FROM fact_order_line")[0]
    assert b.q("SELECT COUNT(*) n FROM fact_order_line l LEFT JOIN dim_menu_item m USING(item_id) WHERE m.item_id IS NULL")[0]["n"] == 0


def test_block3_corpus_is_pinned_and_excludes_the_new_decision():
    old = K.default_kb("block3"); new = K.default_kb("current")
    assert "D-84" not in old.chunks and "D-84" in new.chunks and len(old.chunks) == 758 and len(new.chunks) > len(old.chunks)  # Block 4.5: the migrated current-state files add chunks; the frozen corpus stays at 758
    assert not any(c.get("amended_by") for c in old.chunks.values())


def test_old_taco_direction_is_not_retrievable_as_current_menu_direction(cur):
    for q in ("What is the current Gobi dish on the NASHA menu?", "Is Gobi a taco?", "Is the Gobi Taco on the current menu?"):
        a = cur.ask(q, use_gate=False)
        assert not a["abstained"], q
        assert a["citations"][0]["document_id"] == "D-84", (q, a["citations"][:2])
        assert any("superseded item" in n or "D-84" in n for n in a.get("status_notes", [])) or "D-84" in a["citations"][0]["document_id"]
        assert "APPETIZER" in " ".join(a["answer_sentences"]).upper() or "appetizer" in a["answer"].lower()


def test_historical_decisions_are_kept_but_labelled(cur):
    d75 = cur.chunks["D-75"]
    assert "Gobi Taco" in d75["text"]                                   # history is not rewritten
    assert d75["amended_by"] == "D-84" and "Mango Habanero Gobi" in d75["item_caveat"] and d75["effective_status"] in K.AUTHORITATIVE   # the other Core 5 items still stand


def test_d54_and_other_policies_unaffected(cur):
    a = cur.ask("Can NASHA use pork lard in tortillas?", use_gate=False)
    assert a["abstained"] or all(c["document_id"] != "D-84" for c in a["citations"])


def test_block45_current_state_files_use_the_new_dish_and_keep_untested_labels():
    """Block 4.5: current-state data names Mango Habanero Gobi (appetizer, no tortilla); legacy id kept; nothing claims a test."""
    import csv, pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    rows = {r["id"]: r for r in csv.DictReader(open(root / "food/CORE5-FOOD-MATRIX.csv", encoding="utf-8"))}
    g = rows["gobi-taco"]
    assert g["name"] == "Mango Habanero Gobi" and g["physical_test_status"] == "NOT PERFORMED" and "NOT a taco" in g["status"]
    assert "tortilla" not in (g["core_ingredients"] + g["proposed_construction"] + g["equipment"]).lower().replace("no tortilla", "")
    rec = [r for r in csv.DictReader(open(root / "food/costing/recipes.csv", encoding="utf-8")) if r["dish_id"] == "gobi-taco"]
    ids = {r["ingredient_id"] for r in rec}
    assert "i-corn-tortilla" not in ids and {"i-mango", "i-habanero", "i-cauliflower"} <= ids and all(not r["qty_per_portion"] for r in rec)
    assert [r["dish"] for r in csv.DictReader(open(root / "food/ALLERGEN-MATRIX.csv", encoding="utf-8")) if r["dish_id"] == "gobi-taco"][0].startswith("Mango Habanero Gobi")
    import json
    cap = json.loads((root / "ops/kitchen/capacity-assumptions.json").read_text())
    assert cap["dishes"]["gobi-taco"]["comal"] == [0.0, 0.0, 0.0] and "ASSUMPTION" in cap["d84_amendment"]
    assert "Gobi Taco" not in (root / "website/data/dishes.json").read_text()
