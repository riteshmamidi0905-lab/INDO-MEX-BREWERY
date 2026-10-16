"""Structural checks on the built mart: row-count reconciliation, referential integrity, grain uniqueness, SCD2 integrity."""
FACT_GRAIN = {
    "fact_order": ["order_id"], "fact_order_line": ["order_id", "line_no"], "fact_usage_daily": ["date_key", "site_key", "ingredient_key"],
    "fact_inventory_snapshot": ["date_key", "site_key", "ingredient_key"], "fact_po_line": ["po_id", "line_no"],
    "fact_waste_adjustment": ["waste_key"], "fact_quality_finding": ["finding_key"], "fact_exception_event": ["event_id"],
}
DIM_NATURAL = {"dim_date": ["date_key"], "dim_site": ["site_id"], "dim_channel": ["channel"], "dim_menu_item": ["item_id", "valid_from"],
               "dim_supplier": ["supplier_id"], "dim_ingredient": ["ingredient"], "dim_guest": ["guest_id"], "dim_dq_rule": ["rule"], "dim_waste_reason": ["reason"]}
# (fact table, column) -> (dimension table, column). date_key columns are joined to dim_date (0 = 'no date' allowed only where documented).
FK = {
    ("fact_order", "date_key"): ("dim_date", "date_key"), ("fact_order", "site_key"): ("dim_site", "site_key"), ("fact_order", "channel_key"): ("dim_channel", "channel_key"),
    ("fact_order", "guest_key"): ("dim_guest", "guest_key"),
    ("fact_order_line", "order_key"): ("fact_order", "order_key"), ("fact_order_line", "date_key"): ("dim_date", "date_key"), ("fact_order_line", "site_key"): ("dim_site", "site_key"),
    ("fact_order_line", "item_key"): ("dim_menu_item", "item_key"), ("fact_order_line", "channel_key"): ("dim_channel", "channel_key"), ("fact_order_line", "guest_key"): ("dim_guest", "guest_key"),
    ("fact_usage_daily", "date_key"): ("dim_date", "date_key"), ("fact_usage_daily", "site_key"): ("dim_site", "site_key"), ("fact_usage_daily", "ingredient_key"): ("dim_ingredient", "ingredient_key"),
    ("fact_inventory_snapshot", "date_key"): ("dim_date", "date_key"), ("fact_inventory_snapshot", "site_key"): ("dim_site", "site_key"),
    ("fact_inventory_snapshot", "ingredient_key"): ("dim_ingredient", "ingredient_key"),
    ("fact_po_line", "supplier_key"): ("dim_supplier", "supplier_key"), ("fact_po_line", "site_key"): ("dim_site", "site_key"), ("fact_po_line", "ingredient_key"): ("dim_ingredient", "ingredient_key"),
    ("fact_po_line", "order_date_key"): ("dim_date", "date_key"), ("fact_po_line", "expected_date_key"): ("dim_date", "date_key"),
    ("fact_waste_adjustment", "date_key"): ("dim_date", "date_key"), ("fact_waste_adjustment", "site_key"): ("dim_site", "site_key"),
    ("fact_waste_adjustment", "ingredient_key"): ("dim_ingredient", "ingredient_key"), ("fact_waste_adjustment", "reason_key"): ("dim_waste_reason", "reason_key"),
    ("fact_quality_finding", "rule_key"): ("dim_dq_rule", "rule_key"), ("fact_quality_finding", "site_key"): ("dim_site", "site_key"),
    ("fact_exception_event", "site_key"): ("dim_site", "site_key"), ("fact_exception_event", "ingredient_key"): ("dim_ingredient", "ingredient_key"),
    ("fact_exception_event", "detected_date_key"): ("dim_date", "date_key"),
    ("bridge_item_ingredient", "item_key"): ("dim_menu_item", "item_key"), ("bridge_item_ingredient", "ingredient_key"): ("dim_ingredient", "ingredient_key"),
}
# nullable-by-design date keys: received_date_key = 0 while open; prev_date_key = 0 for the first snapshot
ZERO_OK = {("fact_po_line", "received_date_key"), ("fact_inventory_snapshot", "prev_date_key")}


def orphan_counts(con):
    out = {}
    for (ft, fc), (dt_, dc) in FK.items():
        out[f"{ft}.{fc}->{dt_}.{dc}"] = con.execute(f"SELECT COUNT(*) FROM {ft} f LEFT JOIN {dt_} d ON d.{dc}=f.{fc} WHERE d.{dc} IS NULL").fetchone()[0]
    for ft, fc in ZERO_OK:
        out[f"{ft}.{fc}->dim_date(0 allowed)"] = con.execute(f"SELECT COUNT(*) FROM {ft} f LEFT JOIN dim_date d ON d.date_key=f.{fc} WHERE f.{fc}<>0 AND d.date_key IS NULL").fetchone()[0]
    return out


def grain_duplicates(con):
    out = {}
    for t, cols in {**FACT_GRAIN, **DIM_NATURAL}.items():
        c = ", ".join(cols)
        out[t] = con.execute(f"SELECT COUNT(*) FROM (SELECT {c} FROM {t} GROUP BY {c} HAVING COUNT(*)>1)").fetchone()[0]
    return out


def reconciliation(con):
    q = lambda s: con.execute(s).fetchone()[0]
    return {
        "orders: src = mart": (q("SELECT COUNT(*) FROM src_fact_order"), q("SELECT COUNT(*) FROM fact_order")),
        "order lines: src = mart": (q("SELECT COUNT(*) FROM src_fact_order_line"), q("SELECT COUNT(*) FROM fact_order_line")),
        "raw orders = mart + quarantined": (q("SELECT COUNT(*) FROM raw_orders"), q("SELECT COUNT(*) FROM fact_order") + q("SELECT COUNT(*) FROM src_quarantine WHERE tbl='orders'")),
        "raw order lines = mart + quarantined": (q("SELECT COUNT(*) FROM raw_order_lines"), q("SELECT COUNT(*) FROM fact_order_line") + q("SELECT COUNT(*) FROM src_quarantine WHERE tbl='order_lines'")),
        "gross sales: src = mart (cents)": (q("SELECT SUM(qty*unit_price_cents) FROM src_fact_order_line"), q("SELECT SUM(gross_sales_cents) FROM fact_order_line")),
        "order totals: src = mart (cents)": (q("SELECT SUM(total_cents) FROM src_fact_order"), q("SELECT SUM(order_total_cents) FROM fact_order")),
        "findings: src = mart": (q("SELECT COUNT(*) FROM src_dq_finding"), q("SELECT COUNT(*) FROM fact_quality_finding")),
        "PO qty received = receipts in snapshots (<= last snapshot)": (
            round(q("SELECT COALESCE(SUM(qty_received),0) FROM fact_po_line p JOIN dim_date d ON d.date_key=p.received_date_key WHERE p.received_date_key<>0 AND d.date > (SELECT MIN(date) FROM dim_date JOIN fact_inventory_snapshot USING(date_key)) AND d.date <= (SELECT MAX(date) FROM dim_date JOIN fact_inventory_snapshot USING(date_key))"), 3),
            round(q("SELECT COALESCE(SUM(receipts_since_prev),0) FROM fact_inventory_snapshot"), 3)),
    }


def scd2_problems(con):
    """Overlaps, gaps, or a wrong number of current rows, per item_id."""
    rows = con.execute("SELECT item_id, valid_from, valid_to, is_current FROM dim_menu_item ORDER BY item_id, valid_from").fetchall()
    bad, prev = [], None
    cur = {}
    for item, vf, vt, ic in rows:
        if vf >= vt: bad.append((item, "empty or inverted range"))
        if prev and prev[0] == item:
            if vf < prev[2]: bad.append((item, "overlap"))
            if vf > prev[2]: bad.append((item, "gap"))
        cur[item] = cur.get(item, 0) + ic
        prev = (item, vf, vt)
    bad += [(i, f"{n} current rows") for i, n in cur.items() if n != 1]
    bad += [(i, "last version not open-ended") for i, in con.execute("SELECT item_id FROM dim_menu_item d WHERE valid_to <> '9999-12-31' AND NOT EXISTS (SELECT 1 FROM dim_menu_item n WHERE n.item_id=d.item_id AND n.valid_from=d.valid_to)")]
    return bad


def order_lines_outside_scd2_window(con):
    return con.execute("""SELECT COUNT(*) FROM fact_order_line l JOIN dim_date d ON d.date_key=l.date_key JOIN dim_menu_item i ON i.item_key=l.item_key
        WHERE NOT (d.date >= i.valid_from AND d.date < i.valid_to)""").fetchone()[0]
