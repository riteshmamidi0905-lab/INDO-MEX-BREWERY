"""Star schema: reconciliation, referential integrity, grain uniqueness, SCD2, determinism. SYNTHETIC data."""
import hashlib

import pytest

from analytics import mart, mart_checks as MC, synth


@pytest.fixture(scope="module")
def built():
    return mart.build(seed=1)


def test_row_count_reconciliation(built):
    con, _ = built
    for name, (a, b) in MC.reconciliation(con).items():
        assert a == b, name


def test_lab_lineage_conserved(built):
    con, _ = built
    for tbl, raw, modeled, quar in con.execute("SELECT tbl, raw_rows, modeled_rows, quarantined_rows FROM src_lineage"):
        if tbl in ("orders", "order_lines", "inventory_counts"):
            assert raw == modeled + quar, tbl


def test_referential_integrity(built):
    con, _ = built
    orphans = {k: v for k, v in MC.orphan_counts(con).items() if v}
    assert orphans == {}


def test_grain_uniqueness(built):
    con, _ = built
    assert {k: v for k, v in MC.grain_duplicates(con).items() if v} == {}


def test_unknown_members_exist(built):
    con, _ = built
    for t, k in [("dim_site", "site_key"), ("dim_channel", "channel_key"), ("dim_menu_item", "item_key"), ("dim_supplier", "supplier_key"),
                 ("dim_ingredient", "ingredient_key"), ("dim_guest", "guest_key"), ("dim_dq_rule", "rule_key"), ("dim_waste_reason", "reason_key")]:
        assert con.execute(f"SELECT COUNT(*) FROM {t} WHERE {k}=0").fetchone()[0] == 1, t


def test_scd2_menu_item(built):
    con, _ = built
    assert MC.scd2_problems(con) == []
    assert MC.order_lines_outside_scd2_window(con) == 0
    rows = con.execute("SELECT item_name, valid_from, valid_to, course FROM dim_menu_item WHERE item_id='M04' ORDER BY valid_from").fetchall()
    assert [r[0] for r in rows] == ["Gobi Taco", "Mango Habanero Gobi"]       # renamed dish, internal id M04 unchanged
    assert rows[1][3] == "appetizer / shareable"
    # both versions actually carry sales, so the SCD2 join is exercised
    n = dict(con.execute("SELECT i.item_name, COUNT(*) FROM fact_order_line l JOIN dim_menu_item i USING(item_key) WHERE i.item_id='M04' GROUP BY 1"))
    assert n["Gobi Taco"] > 100 and n["Mango Habanero Gobi"] > 100


def test_v2_recipe_has_no_tortilla_and_v1_does(built):
    con, _ = built
    q = "SELECT COUNT(*) FROM bridge_item_ingredient b JOIN dim_menu_item i USING(item_key) JOIN dim_ingredient g USING(ingredient_key) WHERE i.item_id='M04' AND i.menu_version=? AND g.ingredient='corn masa'"
    assert con.execute(q, ("v1",)).fetchone()[0] == 1 and con.execute(q, ("v2",)).fetchone()[0] == 0


def test_usage_fact_matches_independent_python(built):
    con, _ = built
    py = synth.usage_by_day(con.execute("SELECT o.location_id, o.order_date, l.item_id, l.qty FROM src_fact_order_line l JOIN src_fact_order o USING(order_id)").fetchall())
    sql = {}
    for site, ing, d, q in con.execute("SELECT s.site_id, g.ingredient, dd.date, u.theoretical_qty FROM fact_usage_daily u JOIN dim_site s USING(site_key) JOIN dim_ingredient g USING(ingredient_key) JOIN dim_date dd USING(date_key)"):
        sql[(site, ing, (__import__("datetime").date.fromisoformat(d) - synth.START).days)] = q
    assert set(py) == set(sql)
    assert all(abs(py[k] - sql[k]) < 1e-9 for k in py)


def test_snapshot_balance_identity(built):
    con, _ = built
    bad = con.execute("""SELECT COUNT(*) FROM fact_inventory_snapshot f JOIN fact_inventory_snapshot p
        ON p.site_key=f.site_key AND p.ingredient_key=f.ingredient_key AND p.date_key=f.prev_date_key
        WHERE ABS(f.expected_on_hand - (p.on_hand_qty + f.receipts_since_prev - f.usage_since_prev - f.logged_waste_since_prev)) > 1e-3
           OR ABS(f.variance_qty - (f.on_hand_qty - f.expected_on_hand)) > 1e-3""").fetchone()[0]
    assert bad == 0
    assert con.execute("SELECT COUNT(*) FROM fact_inventory_snapshot WHERE prev_date_key=0").fetchone()[0] == 24     # 3 sites x 8 ingredients, first count
    assert con.execute("SELECT MIN(on_hand_qty) FROM fact_inventory_snapshot").fetchone()[0] >= 0


def test_po_dates_consistent(built):
    con, _ = built
    assert con.execute("""SELECT COUNT(*) FROM fact_po_line p JOIN dim_date o ON o.date_key=p.order_date_key JOIN dim_date e ON e.date_key=p.expected_date_key
        WHERE e.date <= o.date""").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM fact_po_line WHERE (status='OPEN') <> (received_date_key=0)").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM fact_po_line WHERE days_late IS NULL AND status='RECEIVED'").fetchone()[0] == 0


def _digest(con):
    h = hashlib.sha256()
    for t in ["fact_order", "fact_order_line", "fact_inventory_snapshot", "fact_po_line", "fact_waste_adjustment", "fact_exception_event", "dim_guest", "fact_quality_finding"]:
        for r in con.execute(f"SELECT * FROM {t} ORDER BY 1,2"):
            h.update(repr(r).encode())
    return h.hexdigest()


def test_build_is_deterministic_and_seed_sensitive(built):
    con, _ = built
    assert _digest(con) == _digest(mart.build(seed=1)[0])
    assert _digest(con) != _digest(mart.build(seed=2)[0])


def test_quality_findings_cover_injected_rules(built):
    con, info = built
    rules = {r for r, in con.execute("SELECT rule FROM fact_quality_finding f JOIN dim_dq_rule USING(rule_key)")}
    assert {"duplicate_order", "orphan_item", "unit_mismatch", "price_drift"} <= rules
    assert len(info["injected_defects"]) > 80
