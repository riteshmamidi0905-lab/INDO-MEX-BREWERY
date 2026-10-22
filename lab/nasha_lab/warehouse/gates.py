"""Quality gates and reconciliation.

Gate 1 (raw): partitions complete, no duplicate keys, referential integrity, quarantine rate. Gate 2 (warehouse): independent recomputation from
the SOURCE files (streamed with pandas, not through the warehouse SQL) must match the warehouse by month and by location. Blocking failures set
warehouse_status to 'blocked' so dashboards refuse to render; warnings are recorded and shown."""
from pathlib import Path

import numpy as np
import pandas as pd

from . import db
from .ingest import CHUNK, _order_partition_map, _partition_of

QUARANTINE_MAX_RATE = 0.001


def source_totals(source, through=None):
    """Independent aggregation of the source CSVs by month (and by month x location for orders)."""
    source = Path(source)
    ids, months = _order_partition_map(source)
    order = np.argsort(ids, kind="stable")
    ids, months = ids[order], months[order]
    o_month, o_loc, lines = {}, {}, {}
    for ch in pd.read_csv(source / "orders.csv.gz", chunksize=CHUNK, usecols=["order_id", "location_id", "ts", "subtotal_cents", "discount_cents", "total_cents"], dtype={"order_id": str, "location_id": str, "ts": str}):
        ch["m"] = ch.ts.str[:7]
        if through:
            ch = ch[ch.m <= through]
        for m, g in ch.groupby("m"):
            a = o_month.setdefault(m, [0, 0, 0, 0]); a[0] += len(g); a[1] += int(g.subtotal_cents.sum()); a[2] += int(g.discount_cents.sum()); a[3] += int(g.total_cents.sum())
        for (m, l), g in ch.groupby(["m", "location_id"]):
            o_loc[(m, l)] = o_loc.get((m, l), 0) + int(g.total_cents.sum())
    for ch in pd.read_csv(source / "order_lines.csv.gz", chunksize=CHUNK, dtype={"order_id": str}):
        part = _partition_of("order_lines", ch.astype({"order_id": str}), ids, months, "order_id")
        ch["m"] = part.to_numpy()
        if through:
            ch = ch[ch.m <= through]
        ch["gross"] = ch.qty * ch.unit_price_cents
        for m, g in ch.groupby("m"):
            a = lines.setdefault(m, [0, 0]); a[0] += len(g); a[1] += int(g.gross.sum())
    return {"orders": o_month, "orders_loc": o_loc, "lines": lines}


def _rec(con, rid, gate, name, sev, passed, observed, expected):
    con.execute("INSERT INTO dq_results VALUES (?,?,?,?,?,?,?)", (rid, gate, name, sev, int(passed), str(observed), str(expected)))


def raw_gate(con, rid):
    res = []

    def one(name, sql, sev="blocking", expected=0):
        v = con.execute(sql).fetchone()[0]
        _rec(con, rid, "raw", name, sev, v == expected, v, expected)
        res.append((name, sev, v == expected))

    one("duplicate order_id in raw_orders", "SELECT count(*) FROM (SELECT order_id FROM stg_orders GROUP BY 1 HAVING count(*)>1)")
    one("duplicate (order_id,line_no) in raw_order_lines", "SELECT count(*) FROM (SELECT 1 FROM stg_order_lines GROUP BY order_id, line_no HAVING count(*)>1)")
    one("duplicate member_id", "SELECT count(*) FROM (SELECT member_id FROM stg_loyalty_profiles GROUP BY 1 HAVING count(*)>1)")
    one("order lines without an order", "SELECT count(*) FROM stg_order_lines l LEFT JOIN stg_orders o USING(order_id) WHERE o.order_id IS NULL")
    one("orders at an unknown location", "SELECT count(*) FROM stg_orders o LEFT JOIN stg_locations l USING(location_id) WHERE l.location_id IS NULL")
    one("order lines with an unknown item", "SELECT count(*) FROM stg_order_lines o LEFT JOIN stg_menu_items m USING(item_id) WHERE m.item_id IS NULL")
    one("orders by an unknown loyalty member", "SELECT count(*) FROM stg_orders o LEFT JOIN stg_loyalty_profiles m USING(member_id) WHERE o.member_id IS NOT NULL AND m.member_id IS NULL")
    one("returns without an order line", "SELECT count(*) FROM stg_returns r LEFT JOIN stg_order_lines l ON l.order_id=r.order_id AND l.line_no=r.line_no WHERE l.order_id IS NULL")
    one("orders before the site opened", "SELECT count(*) FROM stg_orders o JOIN stg_locations l USING(location_id) WHERE substr(o.ts,1,10) < l.open_date")
    q = con.execute("SELECT count(*) FROM quarantine WHERE run_id IN (SELECT run_id FROM pipeline_runs)").fetchone()[0]
    n = max(1, con.execute("SELECT sum(rows) FROM load_partitions WHERE status='complete'").fetchone()[0] or 1)
    _rec(con, rid, "raw", "quarantine rate", "blocking", q / n <= QUARANTINE_MAX_RATE, f"{q}/{n} = {q / n:.5f}", f"<= {QUARANTINE_MAX_RATE}")
    res.append(("quarantine rate", "blocking", q / n <= QUARANTINE_MAX_RATE))
    con.commit()
    return res


def warehouse_gate(con, rid, source, through=None):
    src = source_totals(source, through)
    res = []

    def cmp(name, got, want, sev="blocking"):
        ok = got == want
        _rec(con, rid, "warehouse", name, sev, ok, got, want)
        res.append((name, sev, ok))

    wo = {m: list(v) for m, *v in con.execute("SELECT substr(d.date,1,7), count(*), sum(subtotal_cents), sum(discount_cents), sum(total_cents) FROM fact_order f JOIN dim_date d ON d.date_key=f.date_key GROUP BY 1")}
    cmp("orders: count/subtotal/discount/total by month == source", {m: wo.get(m) for m in src["orders"]}, src["orders"])
    wl = {m: list(v) for m, *v in con.execute("SELECT substr(d.date,1,7), count(*), sum(gross_cents) FROM fact_order_line f JOIN dim_date d ON d.date_key=f.date_key GROUP BY 1")}
    cmp("order lines: count/gross by month == source", {m: wl.get(m) for m in src["lines"]}, src["lines"])
    ml = {(m, l): v for m, l, v in con.execute("SELECT month, location_id, sum(net_cents) FROM mart_daily_location GROUP BY 1,2")}
    cmp("mart net sales by month x location == source", {k: ml.get(k) for k in src["orders_loc"]}, src["orders_loc"])
    a, b, c = con.execute("SELECT sum(discount_alloc_cents), sum(net_cents), sum(gross_cents) FROM fact_order_line").fetchone()
    d, t, s = con.execute("SELECT sum(discount_cents), sum(total_cents), sum(subtotal_cents) FROM fact_order").fetchone()
    cmp("line discount allocation == order discount (exact)", a, d)
    cmp("sum of line net == sum of order total (exact)", b, t)
    cmp("sum of line gross == sum of order subtotal (exact)", c, s)
    cmp("company month net == fact total", con.execute("SELECT sum(net_cents) FROM mart_company_month").fetchone()[0], t)
    cmp("dim_member rows == source", con.execute("SELECT count(*) FROM dim_member").fetchone()[0], con.execute("SELECT count(*) FROM stg_loyalty_profiles").fetchone()[0])
    cmp("dim_employee rows == source", con.execute("SELECT count(*) FROM dim_employee").fetchone()[0], con.execute("SELECT count(*) FROM stg_employees").fetchone()[0])
    cmp("orders in warehouse == orders in raw", con.execute("SELECT count(*) FROM fact_order").fetchone()[0], con.execute("SELECT count(*) FROM stg_orders").fetchone()[0])
    bad = con.execute("SELECT count(*) FROM fact_order_line WHERE net_cents <= 0 OR qty <= 0").fetchone()[0]
    cmp("non-positive net or qty in fact_order_line", bad, 0)
    gm = con.execute("SELECT min(gross_margin_pct), max(gross_margin_pct) FROM mart_company_month").fetchone()
    ok = gm[0] is not None and 0.5 <= gm[0] and gm[1] <= 0.9
    _rec(con, rid, "warehouse", "gross margin % within the placeholder sanity band 0.5-0.9", "warning", ok, gm, "0.5..0.9")
    res.append(("gross margin band", "warning", ok))
    lab = con.execute("SELECT max(labor_pct_of_sales) FROM mart_company_month").fetchone()[0]
    ok = lab is not None and lab < 0.6
    _rec(con, rid, "warehouse", "labor % of sales below 0.6", "warning", ok, lab, "< 0.6")
    res.append(("labor band", "warning", ok))
    con.commit()
    return res


def publish_status(con, rid, results):
    con.execute("CREATE TABLE IF NOT EXISTS warehouse_status (run_id TEXT, status TEXT, blocking_failures INTEGER, warnings INTEGER, at TEXT)")
    blocking = sum(1 for n, sev, ok in results if sev == "blocking" and not ok)
    warns = sum(1 for n, sev, ok in results if sev == "warning" and not ok)
    status = "published" if blocking == 0 else "blocked"
    con.execute("DELETE FROM warehouse_status")
    con.execute("INSERT INTO warehouse_status VALUES (?,?,?,?,?)", (rid, status, blocking, warns, db.now()))
    con.commit()
    return status, blocking, warns
