"""raw -> staging -> validated -> modeled (SQLite star schema) -> analytics views, with quarantine and lineage.

Why SQLite and plain Python: zero cost, zero services, deterministic CI. The same layer contract maps onto
PostgreSQL/dbt or a warehouse; that migration is a documented tradeoff (docs/ARCHITECTURE.md), not claimed here.
"""
import csv
import datetime as dt
import os
import sqlite3
from collections import Counter

from . import dq
from .generator import LOCATIONS

QUARANTINE_SEVERITIES = {dq.ERROR}
TS_FMT = "%Y-%m-%dT%H:%M:%S"


def write_raw(raw, outdir):
    os.makedirs(outdir, exist_ok=True)
    for t, rows in raw.items():
        with open(os.path.join(outdir, f"{t}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)


def stage(raw):
    """Type and normalise. Rows that cannot be typed are rejected here with a reason (never silently dropped)."""
    st = {"locations": [l[0] for l in LOCATIONS], "menu_items": [], "orders": [], "order_lines": [], "inventory_counts": []}
    rejects = []  # (table, key, reason)
    for m in raw["menu_items"]:
        st["menu_items"].append({**m, "price_cents": int(m["price_cents"]), "ingredients": [i.strip() for i in m["ingredients"].split(";") if i.strip()]})
    for o in raw["orders"]:
        try:
            ts = dt.datetime.strptime(o["ts"], TS_FMT)
        except ValueError:
            rejects.append(("orders", o["order_id"], "malformed_timestamp"))
            continue
        st["orders"].append({**o, "ts": ts, "total_cents": int(o["total_cents"])})
    for l in raw["order_lines"]:
        st["order_lines"].append({**l, "line_no": int(l["line_no"]), "qty": int(l["qty"]), "unit_price_cents": int(l["unit_price_cents"])})
    for r in raw["inventory_counts"]:
        st["inventory_counts"].append({**r, "qty": float(r["qty"])})
    return st, rejects


def run(raw, db_path=":memory:", enabled_rules=None):
    """Execute all layers. Returns (conn, report). Conservation: raw rows = modeled + quarantined, per table."""
    st, rejects = stage(raw)
    findings = dq.run_rules(st, enabled_rules)
    rej_findings = [dq.Finding("malformed_timestamp", t, k, dq.ERROR, r) for t, k, r in rejects]
    if enabled_rules is not None and "malformed_timestamp" not in enabled_rules:
        rej_findings = []
    findings = rej_findings + findings

    bad = {(f.table, f.key): f.rule for f in findings if f.severity in QUARANTINE_SEVERITIES}
    rejected_orders = {k for t, k, _ in rejects}
    # quarantine: first occurrence of a duplicated order_id is kept, later ones are flagged by key == order_id (first wins)
    quarantine = []  # (table, row_index, key, reason, cascade)
    q_orders, q_lines = set(), set()
    first_seen = set()
    keep_orders = []
    for o in sorted(st["orders"], key=lambda r: r["order_id"]):
        reason = bad.get(("orders", o["order_id"]))
        if reason == "duplicate_order":   # the rule keys on order_id, so it also matches the first (legitimate) copy: keep that one
            reason = None
        if o["order_id"] in first_seen:   # later occurrence of an already-seen order_id
            quarantine.append(("orders", o["order_id"], "duplicate_order", False)); continue
        first_seen.add(o["order_id"])
        if reason:
            q_orders.add(o["order_id"]); quarantine.append(("orders", o["order_id"], reason, False))
        else:
            keep_orders.append(o)
    for t, k, r in rejects:
        quarantine.append(("orders", k, r, False)); q_orders.add(k)
    bad_line_orders = {k.split(":")[0] for (t, k) in bad if t == "order_lines"}
    for o in list(keep_orders):
        if o["order_id"] in bad_line_orders:
            keep_orders.remove(o); q_orders.add(o["order_id"]); quarantine.append(("orders", o["order_id"], "cascade:child_line_quarantined", True))
    kept_ids = {o["order_id"] for o in keep_orders}
    keep_lines = []
    for l in st["order_lines"]:
        key = f'{l["order_id"]}:{l["line_no"]}'
        if (("order_lines", key) in bad):
            quarantine.append(("order_lines", key, bad[("order_lines", key)], False))
        elif l["order_id"] not in kept_ids:
            quarantine.append(("order_lines", key, "cascade:parent_quarantined", True))
        else:
            keep_lines.append(l)
    keep_inv = []
    for r in st["inventory_counts"]:
        key = f'{r["location_id"]}:{r["count_date"]}:{r["ingredient"]}'
        if ("inventory_counts", key) in bad:
            quarantine.append(("inventory_counts", key, bad[("inventory_counts", key)], False))
        else:
            keep_inv.append(r)
    blocked_items = {f.key for f in findings if f.severity == dq.BLOCKER and f.table == "menu_items"}

    con = sqlite3.connect(db_path)
    con.executescript("""
    DROP TABLE IF EXISTS dim_location; DROP TABLE IF EXISTS dim_menu_item; DROP TABLE IF EXISTS fact_order;
    DROP TABLE IF EXISTS fact_order_line; DROP TABLE IF EXISTS fact_inventory_count; DROP TABLE IF EXISTS dq_finding;
    DROP TABLE IF EXISTS quarantine; DROP TABLE IF EXISTS lineage;
    CREATE TABLE dim_location(location_id TEXT PRIMARY KEY, name TEXT, synthetic INTEGER DEFAULT 1);
    CREATE TABLE dim_menu_item(item_id TEXT PRIMARY KEY, name TEXT, category TEXT, price_cents INTEGER, compliance_blocked INTEGER);
    CREATE TABLE fact_order(order_id TEXT PRIMARY KEY, location_id TEXT REFERENCES dim_location, order_date TEXT, ts TEXT, channel TEXT, total_cents INTEGER);
    CREATE TABLE fact_order_line(order_id TEXT REFERENCES fact_order, line_no INTEGER, item_id TEXT REFERENCES dim_menu_item, qty INTEGER, unit_price_cents INTEGER, price_flag INTEGER, PRIMARY KEY(order_id, line_no));
    CREATE TABLE fact_inventory_count(location_id TEXT, count_date TEXT, ingredient TEXT, qty REAL, unit TEXT, PRIMARY KEY(location_id,count_date,ingredient));
    CREATE TABLE dq_finding(rule TEXT, tbl TEXT, key TEXT, severity TEXT, detail TEXT);
    CREATE TABLE quarantine(tbl TEXT, key TEXT, reason TEXT, cascade INTEGER);
    CREATE TABLE lineage(tbl TEXT, raw_rows INTEGER, modeled_rows INTEGER, quarantined_rows INTEGER);
    """)
    con.executemany("INSERT INTO dim_location VALUES(?,?,1)", [(l[0], l[1]) for l in LOCATIONS])
    con.executemany("INSERT INTO dim_menu_item VALUES(?,?,?,?,?)", [(m["item_id"], m["name"], m["category"], m["price_cents"], int(m["item_id"] in blocked_items)) for m in st["menu_items"]])
    con.executemany("INSERT INTO fact_order VALUES(?,?,?,?,?,?)", [(o["order_id"], o["location_id"], o["ts"].date().isoformat(), o["ts"].isoformat(), o["channel"], o["total_cents"]) for o in keep_orders])
    warn_lines = {f.key for f in findings if f.severity == dq.WARN and f.table == "order_lines"}
    con.executemany("INSERT INTO fact_order_line VALUES(?,?,?,?,?,?)", [(l["order_id"], l["line_no"], l["item_id"], l["qty"], l["unit_price_cents"], int(f'{l["order_id"]}:{l["line_no"]}' in warn_lines)) for l in keep_lines])
    con.executemany("INSERT INTO fact_inventory_count VALUES(?,?,?,?,?)", [(r["location_id"], r["count_date"], r["ingredient"], r["qty"], r["unit"]) for r in keep_inv])
    con.executemany("INSERT INTO dq_finding VALUES(?,?,?,?,?)", [(f.rule, f.table, f.key, f.severity, f.detail) for f in findings])
    con.executemany("INSERT INTO quarantine VALUES(?,?,?,?)", [(t, k, r, int(c)) for t, k, r, c in quarantine])
    qn = Counter(t for t, *_ in quarantine)
    modeled = {"orders": len(keep_orders), "order_lines": len(keep_lines), "inventory_counts": len(keep_inv), "menu_items": len(st["menu_items"])}
    for t in ("orders", "order_lines", "inventory_counts", "menu_items"):
        con.execute("INSERT INTO lineage VALUES(?,?,?,?)", (t, len(raw[t]), modeled[t], qn.get(t, 0)))
    con.executescript("""
    CREATE VIEW IF NOT EXISTS v_daily_sales AS SELECT o.location_id, o.order_date, COUNT(*) orders, SUM(o.total_cents) revenue_cents
      FROM fact_order o GROUP BY 1,2;
    CREATE VIEW IF NOT EXISTS v_item_mix AS SELECT m.item_id, m.name, m.category, SUM(l.qty) units, SUM(l.qty*l.unit_price_cents) revenue_cents
      FROM fact_order_line l JOIN dim_menu_item m USING(item_id) GROUP BY 1,2,3;
    """)
    con.commit()
    gate = sorted({f.rule for f in findings if f.severity == dq.BLOCKER})
    report = {"findings": findings, "gate": "FAILED: " + ", ".join(gate) if gate else "PASSED", "lineage": {t: (len(raw[t]), modeled[t], qn.get(t, 0)) for t in modeled}}
    return con, report
