"""Build the NASHA analytics mart (SQLite) from the lab's synthetic generator + the analytics-layer simulations.

    python -m analytics.mart [--seed 1] [--db path.sqlite]

Pipeline:  generator.generate (raw, labelled defects) -> lab pipeline (quarantine) -> src_* copy of the lab's modeled tables
           -> star schema (analytics/sql/ddl.sql) via SQL INSERT..SELECT.   SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.
SQLite-specific: date() arithmetic, ATTACH, ROW_NUMBER surrogate keys. The DDL and the set-based loads are otherwise portable SQL.
"""
import argparse
import datetime as dt
import json
import os
import sqlite3
from collections import Counter

from nasha_lab import dq, generator, pipeline, world

from . import config as C
from . import synth

HERE = os.path.dirname(os.path.abspath(__file__))
D = dt.date.fromisoformat
DQ_DIMENSION = {"malformed_timestamp": "validity", "missing_location": "completeness", "future_timestamp": "timeliness", "duplicate_order": "uniqueness",
                "near_duplicate_order": "uniqueness", "order_total_mismatch": "consistency", "orphan_item": "referential_integrity",
                "nonpositive_qty": "validity", "price_drift": "validity", "forbidden_protein": "policy", "unit_mismatch": "validity"}
DK = lambda d: int(d.replace("-", ""))


def read_sql(name):
    with open(os.path.join(HERE, "sql", name), encoding="utf-8") as f:
        return f.read()


def _dim_date(con, start, days):
    rows = []
    for i in range(days):
        d = start + dt.timedelta(days=i)
        ws = d - dt.timedelta(days=d.weekday())
        rows.append((int(d.strftime("%Y%m%d")), d.isoformat(), d.year, d.month, d.replace(day=1).isoformat(), d.isocalendar()[1], ws.isoformat(),
                     (ws - synth.START).days // 7, d.weekday(), d.strftime("%A"), int(d.weekday() >= 5)))
    con.executemany("INSERT INTO dim_date VALUES(?,?,?,?,?,?,?,?,?,?,?)", rows)


def build(seed=C.SEED, defects=C.DEFECTS_PER_TYPE, db_path=":memory:"):
    """Return (connection, info). info carries the injected-defect truth and simulation truth for scoring."""
    raw, truth = generator.generate(seed, defects, menu_version=C.MENU_VERSION_SOURCE)
    lab_con, report = pipeline.run(raw)            # the lab's own validate/quarantine/model step (no agent scenarios applied)
    con = sqlite3.connect(db_path)
    lab_con.backup(con)                           # copy the lab's modeled tables into the mart database, then re-label them src_*
    lab_con.close()
    con.executescript("DROP VIEW IF EXISTS v_daily_sales; DROP VIEW IF EXISTS v_item_mix;")
    for t in ("fact_order", "fact_order_line", "dim_menu_item", "dim_location", "quarantine", "dq_finding", "lineage"):
        con.execute(f"ALTER TABLE {t} RENAME TO src_{t}")
    con.execute("CREATE TABLE src_suppliers(supplier_id TEXT, name TEXT, status TEXT)")
    con.executemany("INSERT INTO src_suppliers VALUES(?,?,?)", world.SUPPLIERS)
    con.execute("CREATE TABLE src_supplier_ingredients(supplier_id TEXT, ingredient TEXT, lead_time_days INTEGER, spec_sheet_status TEXT, min_order_qty REAL)")
    con.executemany("INSERT INTO src_supplier_ingredients VALUES(?,?,?,?,?)", world.SUPPLIER_INGREDIENTS)
    con.execute("CREATE TABLE src_ingredients(ingredient TEXT, unit TEXT)")
    con.executemany("INSERT INTO src_ingredients VALUES(?,?)", list(generator.INGREDIENT_UNIT.items()))
    con.commit()
    con.execute("PRAGMA foreign_keys=OFF")
    # raw landing zone (all TEXT, defects included) -- what a CSV drop looks like before any validation
    for t, rows in raw.items():
        cols = [c for c in rows[0].keys() if not c.startswith("_")]
        con.execute(f"CREATE TABLE raw_{t}({', '.join(c + ' TEXT' for c in cols)})")
        con.executemany(f"INSERT INTO raw_{t} VALUES({','.join('?' * len(cols))})", [tuple(r[c] for c in cols) for r in rows])
    con.executescript(read_sql("ddl.sql"))
    info = {"seed": seed, "defects_per_type": defects, "config_hash": C.config_hash(), "injected_defects": sorted(truth)}

    # ---- dimensions
    _dim_date(con, synth.START, 70)
    con.execute("INSERT INTO dim_site VALUES(0,'UNKNOWN','Unknown',NULL,1)")
    con.executemany("INSERT INTO dim_site VALUES(?,?,?,?,1)", [(i + 1, l[0], l[1], l[2]) for i, l in enumerate(generator.LOCATIONS)])
    con.execute("INSERT INTO dim_channel VALUES(0,'UNKNOWN')")
    con.execute("INSERT INTO dim_channel(channel_key,channel) SELECT ROW_NUMBER() OVER (ORDER BY channel), channel FROM (SELECT DISTINCT channel FROM src_fact_order)")
    # SCD2 menu: v1 history row(s) + v2 current rows. M04 is the only item whose attributes change.
    v1 = {m[0]: m for m in generator.MENUS["v1"]}; v2 = {m[0]: m for m in generator.MENUS["v2"]}
    rows, key = [(0, "UNKNOWN", "Unknown / orphan item", "unknown", "unknown", "n/a", 0, "1900-01-01", C.HIGH_DATE, 1)], 0
    item_keys = {}
    for iid in sorted(v2):
        a, b = v1[iid], v2[iid]
        if (a[1], a[2], a[4]) != (b[1], b[2], b[4]):
            key += 1; item_keys[(iid, "v1")] = key
            rows.append((key, iid, a[1], a[2], "taco", "v1", a[3], "1900-01-01", C.MENU_CHANGE_DATE, 0))
            key += 1; item_keys[(iid, "v2")] = key
            rows.append((key, iid, b[1], b[2], generator.MENU_COURSE_V2.get(iid, b[2]), "v2", b[3], C.MENU_CHANGE_DATE, C.HIGH_DATE, 1))
        else:
            key += 1; item_keys[(iid, "v2")] = item_keys[(iid, "v1")] = key
            rows.append((key, iid, b[1], b[2], b[2], "v1+v2", b[3], "1900-01-01", C.HIGH_DATE, 1))
    con.executemany("INSERT INTO dim_menu_item VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute("INSERT INTO dim_supplier VALUES(0,'UNKNOWN','Unknown',NULL,1)")
    con.execute("INSERT INTO dim_supplier(supplier_key,supplier_id,supplier_name,status) SELECT ROW_NUMBER() OVER (ORDER BY supplier_id), supplier_id, name, status FROM src_suppliers")
    con.execute("INSERT INTO dim_ingredient VALUES(0,'UNKNOWN','',0,NULL,0,NULL)")
    con.execute("""INSERT INTO dim_ingredient(ingredient_key,ingredient,unit,is_perishable,assumed_cost_per_kg,primary_supplier_key,lead_time_days)
        SELECT ROW_NUMBER() OVER (ORDER BY i.ingredient), i.ingredient, i.unit, 0, NULL, s.supplier_key, si.lead_time_days
        FROM src_ingredients i JOIN src_supplier_ingredients si ON si.ingredient=i.ingredient JOIN dim_supplier s ON s.supplier_id=si.supplier_id""")
    for ing, cost in C.COST_PER_KG.items():
        con.execute("UPDATE dim_ingredient SET assumed_cost_per_kg=?, is_perishable=? WHERE ingredient=?", (cost, int(ing in C.PERISHABLE), ing))
    con.execute("INSERT INTO dim_dq_rule VALUES(0,'UNKNOWN','unknown','unknown')")
    con.executemany("INSERT INTO dim_dq_rule VALUES(?,?,?,?)", [(i + 1, r, DQ_DIMENSION[r], "BLOCKER" if r == "forbidden_protein" else "ERROR") for i, r in enumerate(dq.ALL_RULES)])
    con.execute("INSERT INTO dim_waste_reason VALUES(0,'UNKNOWN',0)")
    con.executemany("INSERT INTO dim_waste_reason VALUES(?,?,?)", [(1, "SPOILAGE", 1), (2, "PREP_TRIM", 1), (3, "SPILL", 1), (4, "EXPIRED", 1), (5, "COUNT_VARIANCE", 0)])
    ing_key = dict(con.execute("SELECT ingredient, ingredient_key FROM dim_ingredient"))
    for (iid, ver), ik in item_keys.items():
        recipe = world.RECIPES_V2.get(iid, {}) if (iid == "M04" and ver == "v2") else world.RECIPES.get(iid, {})
        for ing, kg in recipe.items():
            con.execute("INSERT OR IGNORE INTO bridge_item_ingredient VALUES(?,?,?)", (ik, ing_key[ing], kg))

    # ---- guests (synthetic) and order facts
    orders = con.execute("SELECT order_id, location_id, ts, order_date FROM src_fact_order").fetchall()
    guest_of = synth.assign_guests([(o, s, ts, (D(d) - synth.START).days // 7) for o, s, ts, d in orders], seed)
    con.execute("INSERT INTO dim_guest VALUES(0,'UNKNOWN',0,0,NULL,1)")
    first = {}
    for o, s, ts, d in sorted(orders, key=lambda r: r[2]):
        g = guest_of.get(o)
        if g and g not in first:
            first[g] = (s, d)
    site_key = dict(con.execute("SELECT site_id, site_key FROM dim_site"))
    con.executemany("INSERT INTO dim_guest VALUES(?,?,?,?,?,1)", [
        (i + 1, g, site_key[s], DK(d), (D(d) - dt.timedelta(days=D(d).weekday())).isoformat()) for i, (g, (s, d)) in enumerate(sorted(first.items()))])
    con.execute("CREATE TEMP TABLE t_order_guest(order_id TEXT PRIMARY KEY, guest_id TEXT)")
    con.executemany("INSERT INTO t_order_guest VALUES(?,?)", list(guest_of.items()))
    con.execute("""INSERT INTO fact_order SELECT ROW_NUMBER() OVER (ORDER BY o.order_id), o.order_id, dd.date_key, s.site_key, ch.channel_key,
        COALESCE(g.guest_key,0), o.ts, o.total_cents
        FROM src_fact_order o JOIN dim_date dd ON dd.date=o.order_date JOIN dim_site s ON s.site_id=o.location_id JOIN dim_channel ch ON ch.channel=o.channel
        LEFT JOIN t_order_guest tg ON tg.order_id=o.order_id LEFT JOIN dim_guest g ON g.guest_id=tg.guest_id""")
    # SCD2 as-of join: the item version in effect on the ORDER DATE. valid_from inclusive, valid_to exclusive. Unmatched -> unknown member 0.
    con.execute("""INSERT INTO fact_order_line SELECT ROW_NUMBER() OVER (ORDER BY l.order_id, l.line_no), fo.order_key, l.order_id, l.line_no, fo.date_key, fo.site_key,
        COALESCE(i.item_key,0), fo.channel_key, fo.guest_key, l.qty, l.unit_price_cents, l.qty*l.unit_price_cents, l.price_flag
        FROM src_fact_order_line l JOIN src_fact_order o ON o.order_id=l.order_id JOIN fact_order fo ON fo.order_id=l.order_id
        LEFT JOIN dim_menu_item i ON i.item_id=l.item_id AND o.order_date>=i.valid_from AND o.order_date<i.valid_to""")
    con.execute("""INSERT INTO fact_usage_daily SELECT l.date_key, l.site_key, b.ingredient_key, SUM(l.qty*b.kg_per_unit)
        FROM fact_order_line l JOIN bridge_item_ingredient b ON b.item_key=l.item_key GROUP BY 1,2,3""")

    # ---- inventory / PO / waste simulation (analytics layer)
    use = synth.usage_by_day(con.execute("SELECT o.location_id, o.order_date, l.item_id, l.qty FROM src_fact_order_line l JOIN src_fact_order o USING(order_id)").fetchall())
    sim = synth.simulate_inventory(use, seed)
    info["simulation_truth"] = sim["truth"]
    sup_key = dict(con.execute("SELECT supplier_id, supplier_key FROM dim_supplier"))
    day = lambda n: (synth.START + dt.timedelta(days=n)).isoformat()
    dk = lambda n: DK(day(n))
    units = dict(generator.INGREDIENT_UNIT)
    seqs, po_rows = Counter(), []
    for p in sorted(sim["pos"], key=lambda p: (p["site"], p["order_day"], p["supplier"], p["ingredient"])):
        po_id = f'PO-{p["site"]}-{p["supplier"]}-{day(p["order_day"]).replace("-", "")}'
        seqs[po_id] += 1
        rec = p["received_day"]
        po_rows.append((None, po_id, seqs[po_id], sup_key[p["supplier"]], site_key[p["site"]], ing_key[p["ingredient"]], dk(p["order_day"]), dk(p["expected_day"]),
                        dk(rec) if rec is not None else 0, p["qty_ordered"], p["qty_received"] if rec is not None else 0.0, units[p["ingredient"]],
                        "RECEIVED" if rec is not None else "OPEN", rec - p["expected_day"] if rec is not None else None, "ANALYTICS_SYNTH"))
    po_rows = [(i + 1,) + r[1:] for i, r in enumerate(po_rows)]
    con.executemany("INSERT INTO fact_po_line VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", po_rows)
    reason_key = dict(con.execute("SELECT reason, reason_key FROM dim_waste_reason"))
    con.executemany("INSERT INTO fact_waste_adjustment VALUES(?,?,?,?,?,?,?)", [
        (i + 1, dk(d), site_key[s], ing_key[ing], reason_key[rs], "LOGGED_WASTE", q) for i, (s, ing, d, rs, q) in enumerate(sorted(sim["waste"], key=lambda x: (x[2], x[0], x[1])))])
    con.execute("CREATE TEMP TABLE t_snap(date_key INT, site_key INT, ingredient_key INT, on_hand_qty REAL, unit TEXT)")
    con.executemany("INSERT INTO t_snap VALUES(?,?,?,?,?)", [(dk(d), site_key[s], ing_key[ing], q, units[ing]) for s, ing, d, q in sim["snapshots"]])
    con.execute("INSERT INTO fact_inventory_snapshot " + read_sql("load_inventory_snapshot.sql"))
    con.execute("""INSERT INTO fact_waste_adjustment SELECT (SELECT COALESCE(MAX(waste_key),0) FROM fact_waste_adjustment) + ROW_NUMBER() OVER (ORDER BY date_key, site_key, ingredient_key),
        date_key, site_key, ingredient_key, (SELECT reason_key FROM dim_waste_reason WHERE reason='COUNT_VARIANCE'), 'COUNT_ADJUSTMENT', ROUND(-variance_qty,4)
        FROM fact_inventory_snapshot WHERE variance_qty IS NOT NULL""")

    # ---- quality findings (lab pipeline)
    con.execute("""INSERT INTO fact_quality_finding SELECT ROW_NUMBER() OVER (ORDER BY f.rule, f.tbl, f.key), r.rule_key, f.severity, f.tbl, f.key,
        COALESCE((SELECT s.site_key FROM dim_site s WHERE s.site_id = CASE
            WHEN f.tbl='orders' THEN (SELECT MIN(ro.location_id) FROM raw_orders ro WHERE ro.order_id=f.key)
            WHEN f.tbl='order_lines' THEN (SELECT MIN(ro.location_id) FROM raw_orders ro WHERE ro.order_id=substr(f.key,1,instr(f.key,':')-1))
            WHEN f.tbl='inventory_counts' THEN substr(f.key,1,instr(f.key,':')-1) END),0),
        f.detail, EXISTS(SELECT 1 FROM src_quarantine q WHERE q.tbl=f.tbl AND q.key=f.key)
        FROM src_dq_finding f JOIN dim_dq_rule r ON r.rule=f.rule""")

    # ---- exception workflow (detection derived from the mart; approval/resolution SIMULATED)
    exc = con.execute(read_sql("detect_exceptions.sql")).fetchall()
    wf = synth.simulate_exception_workflow([(e[0], e[5]) for e in exc], seed)
    con.executemany("INSERT INTO fact_exception_event VALUES(?,?,?,?,?,?,?,?,?)", [
        (i + 1, e[0], e[1], e[2], e[3], e[4], e[5], wf[e[0]][0], wf[e[0]][1]) for i, e in enumerate(exc)])
    con.execute("CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT)")
    con.executemany("INSERT INTO meta VALUES(?,?)", [("banner", "SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED"), ("seed", str(seed)),
                    ("config_hash", C.config_hash()), ("menu_change_date_assumption", C.MENU_CHANGE_DATE)])
    con.commit()
    return con, info


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=C.SEED); ap.add_argument("--db", default=":memory:")
    a = ap.parse_args()
    con, info = build(a.seed, db_path=a.db)
    for t, in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'dim_%' OR name LIKE 'fact_%' OR name LIKE 'bridge_%') ORDER BY 1"):
        print(f"{t:28s}{con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>8d}")
