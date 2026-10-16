"""Data-quality framework: SQL rules over the RAW landing zone, scored against the generator's labelled injected defects.

The rules are written in SQL (portable except where noted), see sql/dq/*.sql-style inline definitions below. They never read the truth labels.
Dimensions covered: completeness, uniqueness, referential integrity, range/unit sanity, timeliness/freshness, consistency, policy, reconciliation.
SYNTHETIC DATA. Same-author caveat: one author wrote the generator, the defects and these rules.
"""
import datetime as dt
import sqlite3
from collections import defaultdict
from dataclasses import dataclass

from nasha_lab import dq as lab_dq, generator, pipeline

from . import config as C

TS_GLOB = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    dimension: str
    table: str
    targets: str          # injected defect type this rule is designed to catch ('' = no injected target: a control / guard rule)
    sql: str              # returns one column: the entity key (same key format as the generator truth)
    note: str = ""


def landing_db(raw):
    """Load raw dict-of-rows into an in-memory SQLite landing zone (all TEXT, defects included) plus reference tables."""
    con = sqlite3.connect(":memory:")
    for t, rows in raw.items():
        cols = [c for c in rows[0].keys() if not c.startswith("_")]
        con.execute(f"CREATE TABLE raw_{t}({', '.join(c + ' TEXT' for c in cols)})")
        con.executemany(f"INSERT INTO raw_{t} VALUES({','.join('?' * len(cols))})", [tuple(r[c] for c in cols) for r in rows])
    con.execute("CREATE INDEX ix_rol ON raw_order_lines(order_id)"); con.execute("CREATE INDEX ix_ro ON raw_orders(order_id)")
    con.execute("CREATE TABLE ref_sites(site_id TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO ref_sites VALUES(?)", [(l[0],) for l in generator.LOCATIONS])
    con.execute("CREATE TABLE ref_ingredient_unit(ingredient TEXT PRIMARY KEY, unit TEXT)")
    con.executemany("INSERT INTO ref_ingredient_unit VALUES(?,?)", list(generator.INGREDIENT_UNIT.items()))
    con.execute("CREATE TABLE ref_forbidden(token TEXT)")
    con.executemany("INSERT INTO ref_forbidden VALUES(?)", [(t,) for t in lab_dq.FORBIDDEN_TOKENS])   # D-54 domain policy list (a reference table, not detection logic)
    # basket signature per order, built once (GROUP_CONCAT over an ordered subquery; PostgreSQL: STRING_AGG(... ORDER BY ...))
    con.execute("""CREATE TABLE t_sig AS SELECT order_id, GROUP_CONCAT(x, '|') AS basket FROM
        (SELECT order_id, item_id || 'x' || qty || '@' || unit_price_cents AS x FROM raw_order_lines ORDER BY order_id, item_id, qty, unit_price_cents) GROUP BY order_id""")
    con.execute("CREATE INDEX ix_sig ON t_sig(order_id)")
    con.execute("CREATE TABLE t_sig_h AS SELECT DISTINCT h.order_id, h.location_id, h.ts, g.basket FROM raw_orders h JOIN t_sig g USING (order_id)")
    con.execute("CREATE INDEX ix_sigh ON t_sig_h(location_id, basket)")
    return con


VALID_TS = f"(ts GLOB '{TS_GLOB}' AND datetime(replace(ts,'T',' ')) IS NOT NULL)"
BASKET = """(SELECT GROUP_CONCAT(item_id || 'x' || qty || '@' || unit_price_cents, '|') FROM
              (SELECT item_id, qty, unit_price_cents FROM raw_order_lines l WHERE l.order_id = o.order_id ORDER BY item_id, qty, unit_price_cents))"""

RULES = [
    Rule("COMP-01 order site missing/unknown", "completeness", "orders", "missing_location",
         "SELECT DISTINCT order_id FROM raw_orders WHERE location_id IS NULL OR location_id = '' OR location_id NOT IN (SELECT site_id FROM ref_sites)"),
    Rule("COMP-02 order timestamp missing", "completeness", "orders", "",
         "SELECT order_id FROM raw_orders WHERE ts IS NULL OR ts = ''", "control: no injected target"),
    Rule("VALID-01 timestamp not parseable", "validity", "orders", "malformed_timestamp",
         f"SELECT order_id FROM raw_orders WHERE ts IS NOT NULL AND ts <> '' AND NOT {VALID_TS}"),
    Rule("TIME-01 timestamp after as-of", "timeliness", "orders", "future_timestamp",
         f"SELECT order_id FROM raw_orders WHERE {VALID_TS} AND replace(ts,'T',' ') > '{C.AS_OF} 00:00:00'"),
    Rule("UNIQ-01 order_id appears more than once", "uniqueness", "orders", "duplicate_order",
         "SELECT order_id FROM (SELECT order_id, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY rowid) AS rn FROM raw_orders) WHERE rn > 1"),
    Rule("UNIQ-02 same site, timestamp and basket under another id", "uniqueness", "orders", "near_duplicate_order",
         f"""WITH h AS (SELECT DISTINCT order_id, location_id, ts FROM raw_orders), s AS (SELECT o.order_id, o.location_id, o.ts, g.basket FROM h o JOIN t_sig g USING (order_id))
             SELECT order_id FROM (SELECT order_id, ROW_NUMBER() OVER (PARTITION BY location_id, ts, basket ORDER BY order_id) AS rn FROM s WHERE basket IS NOT NULL) WHERE rn > 1"""),
    Rule("UNIQ-03 same site and basket within 2 seconds under another id", "uniqueness", "orders", "near_duplicate_shifted",
         f"""SELECT DISTINCT b.order_id FROM t_sig_h a JOIN t_sig_h b ON a.location_id = b.location_id AND a.basket = b.basket AND a.order_id < b.order_id
              AND {VALID_TS.replace('ts', 'a.ts')} AND {VALID_TS.replace('ts', 'b.ts')}
              AND ABS(strftime('%s', replace(a.ts,'T',' ')) - strftime('%s', replace(b.ts,'T',' '))) <= 2""",
         "tolerance window rule; wider than UNIQ-02 by design"),
    Rule("CONS-01 header total differs from sum of lines", "consistency", "orders", "order_total_mismatch",
         """WITH ln AS (SELECT order_id, SUM(CAST(qty AS INTEGER) * CAST(unit_price_cents AS INTEGER)) AS lc FROM raw_order_lines GROUP BY order_id)
            SELECT DISTINCT o.order_id FROM raw_orders o JOIN ln USING (order_id) WHERE CAST(o.total_cents AS INTEGER) <> ln.lc"""),
    Rule("RI-01 line item not in menu", "referential_integrity", "order_lines", "orphan_item",
         "SELECT order_id || ':' || line_no FROM raw_order_lines l WHERE NOT EXISTS (SELECT 1 FROM raw_menu_items m WHERE m.item_id = l.item_id)"),
    Rule("RI-02 line without a parent order", "referential_integrity", "order_lines", "",
         "SELECT order_id || ':' || line_no FROM raw_order_lines l WHERE NOT EXISTS (SELECT 1 FROM raw_orders o WHERE o.order_id = l.order_id)", "control: no injected target"),
    Rule("RANGE-01 quantity not positive", "range", "order_lines", "nonpositive_qty",
         "SELECT order_id || ':' || line_no FROM raw_order_lines WHERE CAST(qty AS INTEGER) <= 0"),
    Rule("RANGE-02 price outside 0.8-1.2 x item median (n >= 5)", "range", "order_lines", "price_drift",
         """WITH p AS (SELECT order_id, line_no, item_id, CAST(unit_price_cents AS INTEGER) AS price,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY CAST(unit_price_cents AS INTEGER)) AS rn, COUNT(*) OVER (PARTITION BY item_id) AS n FROM raw_order_lines),
                 med AS (SELECT item_id, AVG(price) AS m FROM p WHERE rn IN ((n + 1) / 2, (n + 2) / 2) AND n >= 5 GROUP BY item_id)
            SELECT p.order_id || ':' || p.line_no FROM p JOIN med USING (item_id) WHERE 1.0 * p.price / med.m NOT BETWEEN 0.8 AND 1.2""",
         "data-derived reference (item median), independent of the menu table"),
    Rule("UNIT-01 count unit differs from ingredient's expected unit", "range", "inventory_counts", "unit_mismatch",
         "SELECT location_id || ':' || count_date || ':' || c.ingredient FROM raw_inventory_counts c JOIN ref_ingredient_unit r ON r.ingredient = c.ingredient WHERE c.unit <> r.unit"),
    Rule("RANGE-03 inventory quantity not positive or implausibly large", "range", "inventory_counts", "",
         "SELECT location_id || ':' || count_date || ':' || ingredient FROM raw_inventory_counts WHERE CAST(qty AS REAL) <= 0 OR CAST(qty AS REAL) > 500", "control: no injected target"),
    Rule("POLICY-01 forbidden ingredient token on a menu item", "policy", "menu_items", "forbidden_protein",
         """SELECT DISTINCT m.item_id FROM raw_menu_items m JOIN ref_forbidden f
            ON ' ' || replace(lower(m.ingredients), ';', ' ') || ' ' LIKE '% ' || f.token || ' %'"""),
]


def run_rules(con, rules=RULES):
    """Return list of (rule_id, table, key)."""
    out = []
    for r in rules:
        out += [(r.rule_id, r.table, k[0]) for k in con.execute(r.sql).fetchall()]
    return out


def freshness(con, as_of=C.AS_OF, max_age_days=C.FRESHNESS_MAX_AGE_DAYS):
    """Dataset-level check: newest valid order timestamp vs the as-of date."""
    newest = con.execute(f"SELECT MAX(substr(ts,1,10)) FROM raw_orders WHERE {VALID_TS} AND replace(ts,'T',' ') <= '{as_of} 00:00:00'").fetchone()[0]
    age = (dt.date.fromisoformat(as_of) - dt.date.fromisoformat(newest)).days
    return {"newest_valid_order_date": newest, "as_of": as_of, "age_days": age, "max_age_days": max_age_days, "ok": age <= max_age_days}


def reconciliation(raw):
    """Row-count conservation through the lab pipeline: raw rows = modeled + quarantined, per table."""
    con, rep = pipeline.run(raw)
    out = {t: {"raw": a, "modeled": b, "quarantined": c, "ok": a == b + c} for t, (a, b, c) in rep["lineage"].items()}
    return out


def score(seeds, defects=C.DEFECTS_PER_TYPE, rules=RULES):
    """Precision/recall of each rule against its target defect type, recall of each defect type by ANY rule, clean-data false alarms."""
    tp, fp_other, fp_clean, fn = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)
    by_type = defaultdict(lambda: [0, 0])                  # type -> [found by any rule, total]
    per_seed = defaultdict(dict)
    misses, fp_examples = [], []
    for seed in seeds:
        raw, truth = generator.generate(seed, defects, menu_version=C.MENU_VERSION_SOURCE)
        con = landing_db(raw)
        found = run_rules(con, rules)
        truth_keys = {(t, tbl, k) for t, tbl, k in truth}
        any_truth_keys = {(tbl, k) for _t, tbl, k in truth}
        found_any = {(tbl, k) for _r, tbl, k in found}
        by_rule = defaultdict(set)
        for rid, tbl, k in found:
            by_rule[rid].add((tbl, k))
        for r in rules:
            got = by_rule.get(r.rule_id, set())
            if r.targets:
                tgt = {(tbl, k) for t, tbl, k in truth_keys if t == r.targets}
                hit = got & tgt
                tp[r.rule_id] += len(hit); fn[r.rule_id] += len(tgt - hit)
                for tbl, k in got - tgt:
                    if (tbl, k) in any_truth_keys:
                        fp_other[r.rule_id] += 1
                    else:
                        fp_clean[r.rule_id] += 1
                        if len(fp_examples) < 12: fp_examples.append({"seed": seed, "rule": r.rule_id, "key": k})
                per_seed[r.rule_id][seed] = (len(hit), len(tgt))
            else:
                for tbl, k in got:
                    fp_clean[r.rule_id] += 1
        for t, tbl, k in truth_keys:
            by_type[t][1] += 1
            if (tbl, k) in found_any:
                by_type[t][0] += 1
            elif len(misses) < 50:
                misses.append({"seed": seed, "defect": t, "key": k})
    rows = {}
    for r in rules:
        a, b, c, d = tp[r.rule_id], fp_other[r.rule_id], fp_clean[r.rule_id], fn[r.rule_id]
        rows[r.rule_id] = {"dimension": r.dimension, "targets": r.targets or None, "tp": a, "fp_other_injected_defect": b, "fp_clean_row": c, "fn": d,
                           "precision": round(a / (a + b + c), 4) if (a + b + c) else None, "precision_vs_clean_rows_only": round(a / (a + c), 4) if (a + c) else None,
                           "recall": round(a / (a + d), 4) if r.targets and (a + d) else None}
    return {"seeds": list(seeds), "defects_per_type": defects, "per_rule": rows,
            "per_defect_type_any_rule_recall": {t: {"found": v[0], "total": v[1], "recall": round(v[0] / v[1], 4)} for t, v in sorted(by_type.items())},
            "misses_sample": misses, "false_positive_examples": fp_examples}


def clean_run(seeds, rules=RULES):
    """No injected defects: every flag is a false alarm. Returns {rule: flags} summed over seeds."""
    out = defaultdict(int); rows = 0
    for seed in seeds:
        raw, _ = generator.generate(seed, 0, menu_version=C.MENU_VERSION_SOURCE)
        rows += len(raw["orders"])
        for rid, _t, _k in run_rules(landing_db(raw), rules):
            out[rid] += 1
    return {"orders_scanned": rows, "flags_by_rule": dict(out), "total_flags": sum(out.values())}


def lab_rules_score(seeds, defects=C.DEFECTS_PER_TYPE):
    """The lab's own rule set (nasha_lab/dq.py), scored the same way (per defect type, any finding on the labelled key)."""
    tot = defaultdict(lambda: [0, 0])
    for seed in seeds:
        raw, truth = generator.generate(seed, defects, menu_version=C.MENU_VERSION_SOURCE)
        _c, rep = pipeline.run(raw)
        found = {(f.table, f.key) for f in rep["findings"]}
        for t, tbl, k in truth:
            tot[t][1] += 1; tot[t][0] += (tbl, k) in found
    return {t: {"found": v[0], "total": v[1], "recall": round(v[0] / v[1], 4)} for t, v in sorted(tot.items())}


def novel_probe(seed=1, n=10):
    """Defect kinds the generator does NOT inject, planted by this function, to see what the rule set would miss. Rules are NOT tuned to these."""
    import copy
    import random
    rng = random.Random(seed)
    raw, _ = generator.generate(seed, 0, menu_version=C.MENU_VERSION_SOURCE)
    raw = copy.deepcopy(raw)
    planted = {}
    ls = raw["order_lines"]
    # (a) duplicated order line (same order_id + line_no twice)
    idx = rng.sample(range(len(ls)), n); planted["duplicate_order_line"] = [f'{ls[i]["order_id"]}:{ls[i]["line_no"]}' for i in idx]
    ls.extend(dict(ls[i]) for i in idx)
    # (b) absurd quantity (x100) on a line
    idx = rng.sample(range(len(ls) - n), n)
    for i in idx: ls[i]["qty"] = str(int(ls[i]["qty"]) * 100)
    planted["absurd_quantity"] = [f'{ls[i]["order_id"]}:{ls[i]["line_no"]}' for i in idx]
    # (c) negative inventory quantity
    inv = raw["inventory_counts"]; idx = rng.sample(range(len(inv)), n)
    for i in idx: inv[i]["qty"] = "-" + inv[i]["qty"]
    planted["negative_inventory_qty"] = [f'{inv[i]["location_id"]}:{inv[i]["count_date"]}:{inv[i]["ingredient"]}' for i in idx]
    # (d) timestamp shifted by +5 hours (timezone slip) -- structurally valid
    os_ = raw["orders"]; idx = rng.sample(range(len(os_)), n)
    for i in idx: os_[i]["ts"] = (dt.datetime.fromisoformat(os_[i]["ts"]) + dt.timedelta(hours=5)).isoformat()
    planted["timezone_slip_5h"] = [os_[i]["order_id"] for i in idx]
    found = {k for _r, _t, k in run_rules(landing_db(raw))}
    out = {}
    for kind, keys in planted.items():
        hit = sum(1 for k in set(keys) if k in found or k.split(':')[0] in found)   # a line-level defect counts as detected if its line OR its order is flagged
        out[kind] = {"planted": len(set(keys)), "detected": hit}
    return out
