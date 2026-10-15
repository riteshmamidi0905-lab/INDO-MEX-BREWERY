"""The synthetic operating world the agent investigates (SYNTHETIC DATA / SIMULATED OPERATION).

Starts from the block-1 pipeline output (including its injected defects and quarantine), then adds the MINIMUM extra entities the
three scenario families need: suppliers, supplier lead times and spec-sheet status, purchase orders, inventory movements, supplier
substitution proposals and operational incidents. Inventory counts are re-simulated from actual (modeled) order usage so that
variance and days-of-cover are meaningful; keys that block 1 quarantined (unit mismatch) stay missing.
"""
import datetime as dt
import json
import sqlite3
import random
import threading

from . import generator, pipeline

TODAY = dt.date(2026, 4, 28)
STALE_DAYS = 10
RECIPES = {  # item_id -> {ingredient: kg per unit sold}   PLACEHOLDER planning inputs, not tested recipes
    "M01": {"chicken thigh": .18, "corn masa": .05}, "M02": {"paneer": .15, "corn masa": .05}, "M03": {"goat": .20, "corn masa": .05},
    "M04": {"cauliflower": .20, "corn masa": .05}, "M05": {"chicken thigh": .15, "cheese": .06, "corn masa": .05},
    "B01": {"malt": .03, "hops": .001}, "B02": {"malt": .03, "hops": .001}, "B03": {"malt": .03, "hops": .001},
}
RECIPES_V2 = {**RECIPES, "M04": {"cauliflower": .20}}      # Mango Habanero Gobi (D-84): cauliflower stays the main ingredient; NO tortilla, so no corn masa
SUPPLIERS = [  # fictional; names are labelled synthetic
    ("S01", "Synthetic Poultry Supply (S01)", "ACTIVE"), ("S02", "Synthetic Goat and Lamb Supply (S02)", "ACTIVE"),
    ("S03", "Synthetic Produce Supply (S03)", "ON_HOLD"), ("S04", "Synthetic Dairy Supply (S04)", "ACTIVE"),
    ("S05", "Synthetic Dry Goods and Malt Supply (S05)", "ACTIVE"),
]
SUPPLIER_INGREDIENTS = [  # supplier, ingredient, lead_time_days, spec_sheet_status, min_order_kg
    ("S01", "chicken thigh", 2, "ON_FILE", 10), ("S02", "goat", 5, "ON_FILE", 10), ("S03", "cauliflower", 2, "ON_FILE", 10),
    ("S04", "paneer", 3, "ON_FILE", 5), ("S04", "cheese", 3, "ON_FILE", 5), ("S05", "corn masa", 4, "ON_FILE", 20),
    ("S05", "malt", 7, "ON_FILE", 25), ("S05", "hops", 7, "ON_FILE", 1),
]
PROPOSALS = [  # supplier substitution proposals for the D-54 scenario family
    ("P-01", "S05", "flour tortilla blend with beef tallow", "beef tallow", "ON_FILE"),
    ("P-02", "S01", "chicken bouillon base, natural flavors", "animal source unspecified", "MISSING"),
    ("P-03", "S05", "vegetable shortening for frying", "vegetable oil (supplier statement on file)", "ON_FILE"),
]

SCHEMA = """
CREATE TABLE ingredients(ingredient TEXT PRIMARY KEY, unit TEXT);
CREATE TABLE suppliers(supplier_id TEXT PRIMARY KEY, name TEXT, status TEXT, synthetic INTEGER DEFAULT 1);
CREATE TABLE supplier_ingredients(supplier_id TEXT, ingredient TEXT, lead_time_days INTEGER, spec_sheet_status TEXT, min_order_qty REAL);
CREATE TABLE purchase_orders(po_id TEXT PRIMARY KEY, supplier_id TEXT, status TEXT, created TEXT, expected_date TEXT);
CREATE TABLE purchase_order_lines(po_id TEXT, ingredient TEXT, qty REAL, unit TEXT);
CREATE TABLE inventory_movements(movement_id INTEGER PRIMARY KEY AUTOINCREMENT, location_id TEXT, ingredient TEXT, move_date TEXT, kind TEXT, qty REAL);
CREATE TABLE supplier_proposals(proposal_id TEXT PRIMARY KEY, supplier_id TEXT, ingredient_text TEXT, declared_source TEXT, spec_sheet_status TEXT);
CREATE TABLE operational_incidents(event_id TEXT PRIMARY KEY, event_type TEXT, payload TEXT, detected_at TEXT);
CREATE TABLE drafts(draft_id TEXT PRIMARY KEY, run_id TEXT, kind TEXT, payload TEXT, status TEXT, created TEXT);
CREATE TABLE review_queue(item_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, kind TEXT, payload TEXT, status TEXT, created TEXT);
"""


class World:
    def __init__(self, con, seed):
        self.con, self.seed, self.faults, self.today, self.lock = con, seed, {}, TODAY, threading.RLock()
        self.menu_version = "v1"; self.recipes = RECIPES; self.po_coverage = "v1"                      # v1 = frozen Block 3 menu; v2 = current (D-84)

    def q(self, sql, *a):
        cur = self.con.execute(sql, a); cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _usage_by_day(con, recipes=None):
    recipes = recipes or RECIPES
    rows = con.execute("""SELECT o.location_id, o.order_date, l.item_id, SUM(l.qty) FROM fact_order_line l JOIN fact_order o USING(order_id) GROUP BY 1,2,3""").fetchall()
    use = {}
    for loc, d, item, qty in rows:
        for ing, kg in recipes.get(item, {}).items():
            use[(loc, ing, d)] = use.get((loc, ing, d), 0.0) + qty * kg
    return use


def open_world(path, seed=1):
    return World(sqlite3.connect(path, check_same_thread=False), seed)


CURRENT_PO_COVERAGE = "v2"          # Block 4.5: current-state worlds use the quantity-aware open-order coverage rule; the frozen Block 3 default stays "v1"


def build_world(seed=1, defects_per_type=8, db_path=":memory:", menu_version="v1", po_coverage="v1"):
    raw, truth = generator.generate(seed, defects_per_type, menu_version=menu_version)
    con, report = pipeline.run(raw, db_path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO ingredients VALUES(?,?)", list(generator.INGREDIENT_UNIT.items()))
    con.executemany("INSERT INTO suppliers VALUES(?,?,?,1)", SUPPLIERS)
    con.executemany("INSERT INTO supplier_ingredients VALUES(?,?,?,?,?)", SUPPLIER_INGREDIENTS)
    con.executemany("INSERT INTO supplier_proposals VALUES(?,?,?,?,?)", PROPOSALS)
    use = _usage_by_day(con, RECIPES_V2 if menu_version == "v2" else RECIPES)
    rng = random.Random(seed * 7919)
    quarantined_counts = {k for (t, k) in con.execute("SELECT tbl, key FROM quarantine WHERE tbl='inventory_counts'").fetchall()}
    # re-simulate counts from real usage; replenish to par after each count
    con.execute("DELETE FROM fact_inventory_count")
    start = generator.START
    for loc, *_ in generator.LOCATIONS:
        for ing, unit in generator.INGREDIENT_UNIT.items():
            daily = [use.get((loc, ing, (start + dt.timedelta(days=i)).isoformat()), 0.0) for i in range(60)]
            weekly = sum(daily[:56]) / 8 or 1.0
            par = max(weekly * 1.6, 5.0); on_hand = par
            for w in range(9):
                d = start + dt.timedelta(days=7 * w)
                if w:
                    on_hand = max(0.0, on_hand - sum(daily[7 * (w - 1):7 * w]))
                key = f"{loc}:{d.isoformat()}:{ing}"
                if key not in quarantined_counts:
                    con.execute("INSERT INTO fact_inventory_count VALUES(?,?,?,?,?)", (loc, d.isoformat(), ing, round(on_hand * rng.uniform(.97, 1.03), 2), unit))
                if on_hand < par:
                    con.execute("INSERT INTO inventory_movements(location_id,ingredient,move_date,kind,qty) VALUES(?,?,?,?,?)", (loc, ing, (d + dt.timedelta(days=1)).isoformat(), "RECEIPT", round(par - on_hand, 2)))
                    on_hand = par
    w = World(con, seed); w.po_coverage = po_coverage; w.menu_version = menu_version; w.recipes = RECIPES_V2 if menu_version == "v2" else RECIPES
    _apply_scenarios(w, use)
    return w, report, truth


def _avg_daily(use, loc, ing, end, days=14):
    return sum(use.get((loc, ing, (end - dt.timedelta(days=i)).isoformat()), 0.0) for i in range(days)) / days


def _apply_scenarios(w, use):
    con = w.con
    last = dt.date(2026, 4, 27)
    # A1 LOW COVER: L01 goat has ~3 days of cover, the supplier needs 5 days, the open PO is late
    avg = _avg_daily(use, "L01", "goat", last) or 1.0
    con.execute("DELETE FROM inventory_movements WHERE location_id='L01' AND ingredient='goat' AND move_date>?", (last.isoformat(),))
    con.execute("UPDATE fact_inventory_count SET qty=? WHERE location_id='L01' AND ingredient='goat' AND count_date=?", (round(avg * 2.4, 2), last.isoformat()))
    con.execute("INSERT INTO purchase_orders VALUES('PO-0001','S02','OPEN','2026-04-22',?)", ((TODAY + dt.timedelta(days=6)).isoformat(),))
    con.execute("INSERT INTO purchase_order_lines VALUES('PO-0001','goat',20,'kg')")
    con.execute("INSERT INTO purchase_orders VALUES('PO-0002','S01','RECEIVED','2026-04-18','2026-04-21')")
    con.execute("INSERT INTO purchase_order_lines VALUES('PO-0002','chicken thigh',30,'kg')")
    con.execute("INSERT INTO purchase_orders VALUES('PO-0003','S04','OPEN','2026-04-26',?)", ((TODAY + dt.timedelta(days=2)).isoformat(),))
    con.execute("INSERT INTO purchase_order_lines VALUES('PO-0003','paneer',10,'kg')")
    # A2 STALE/MISSING COUNT: the two newest L02 paneer counts are gone (one quarantined for a unit mismatch in block 1's style)
    for d in ("2026-04-27", "2026-04-20"):
        con.execute("DELETE FROM fact_inventory_count WHERE location_id='L02' AND ingredient='paneer' AND count_date=?", (d,))
    k = "L02:2026-04-27:paneer"
    if not con.execute("SELECT 1 FROM quarantine WHERE tbl='inventory_counts' AND key=?", (k,)).fetchone():
        con.execute("INSERT INTO quarantine VALUES('inventory_counts',?,'unit_mismatch',0)", (k,))
        con.execute("INSERT INTO dq_finding VALUES('unit_mismatch','inventory_counts',?,'ERROR','lb')", (k,))
    # A3 COUNT VARIANCE: the L03 cauliflower count is 3.5x what usage and receipts allow
    row = con.execute("SELECT qty FROM fact_inventory_count WHERE location_id='L03' AND ingredient='cauliflower' AND count_date=?", (last.isoformat(),)).fetchone()
    if row: con.execute("UPDATE fact_inventory_count SET qty=? WHERE location_id='L03' AND ingredient='cauliflower' AND count_date=?", (round(row[0] * 3.5 + 6, 2), last.isoformat()))
    # incidents
    def first_finding(rule):
        r = con.execute("SELECT rowid FROM dq_finding WHERE rule=? ORDER BY key LIMIT 1", (rule,)).fetchone()
        return r[0] if r else None
    inc = [("EV-A1", "INVENTORY_EXCEPTION", {"location_id": "L01", "ingredient": "goat", "subtype": "LOW_COVER"}),
           ("EV-A2", "INVENTORY_EXCEPTION", {"location_id": "L02", "ingredient": "paneer", "subtype": "STALE_OR_MISSING_COUNT"}),
           ("EV-A3", "INVENTORY_EXCEPTION", {"location_id": "L03", "ingredient": "cauliflower", "subtype": "COUNT_VARIANCE"}),
           ("EV-B1", "DQ_INCIDENT", {"finding_id": first_finding("duplicate_order")}),
           ("EV-B2", "DQ_INCIDENT", {"finding_id": first_finding("near_duplicate_order")}),
           ("EV-B3", "DQ_INCIDENT", {"finding_id": first_finding("malformed_timestamp")}),
           ("EV-C1", "POLICY_REVIEW", {"proposal_id": "P-01"}), ("EV-C2", "POLICY_REVIEW", {"proposal_id": "P-02"}), ("EV-C3", "POLICY_REVIEW", {"proposal_id": "P-03"})]
    con.executemany("INSERT INTO operational_incidents VALUES(?,?,?,?)", [(e, t, json.dumps(p), TODAY.isoformat()) for e, t, p in inc])
    con.commit()
