"""PostgreSQL hardening for the scenario tables (D-89): primary keys, foreign keys, CHECK constraints, indexes, and a SAFE migration runner.

Why a runner and not a script: constraints added to tables that already contain bad rows fail half-way. Each migration here is (1) pre-flighted against the data (violations are counted
and reported, nothing is changed), (2) applied in ONE transaction (all or nothing), (3) recorded with a checksum in `schema_migrations` so a re-run is a no-op and an edited migration is detected.
Foreign keys are added NOT VALID and then VALIDATEd, the low-lock pattern for large tables. SYNTHETIC data; nothing here touches a production database.

    python3 -m nasha_lab.warehouse.pg_hardening --dsn postgresql://... [--dry-run]"""
import hashlib
import json
import statistics
import time

SCHEMA = "nasha_wh"

# (kind, table, details). kind: pk(cols) | fk(cols, ref_table, ref_cols) | check(name, expr) | index(name, cols)
SPECS = {
    "001": ("primary keys", [
        ("pk", "scn_ingredient", ["ingredient_id"]), ("pk", "scn_supplier", ["supplier_id"]), ("pk", "scn_supplier_quote", ["quote_id"]), ("pk", "scn_menu_item", ["menu_item_id"]),
        ("pk", "scn_recipe_bom", ["recipe_id", "recipe_version", "ingredient_id"]), ("pk", "scn_inventory_week", ["location_id", "week", "ingredient_id"]),
        ("pk", "scn_variance_flag", ["location_id", "week", "ingredient_id"]), ("pk", "scn_variance_week", ["location_id", "week", "ingredient_id"]),
        ("pk", "scn_depletion_week", ["location_id", "week", "ingredient_id"]), ("pk", "scn_depletion_day", ["location_id", "date", "ingredient_id"]),
        ("pk", "scn_demand_forecast", ["location_id", "ingredient_id", "day_ahead"]), ("pk", "scn_procurement_reco", ["reco_id"])]),
    "002": ("foreign keys", [
        ("fk", "scn_supplier_quote", ["supplier_id"], "scn_supplier", ["supplier_id"]), ("fk", "scn_supplier_quote", ["ingredient_id"], "scn_ingredient", ["ingredient_id"]),
        ("fk", "scn_recipe_bom", ["ingredient_id"], "scn_ingredient", ["ingredient_id"]), ("fk", "scn_inventory_week", ["ingredient_id"], "scn_ingredient", ["ingredient_id"]),
        ("fk", "scn_variance_flag", ["ingredient_id"], "scn_ingredient", ["ingredient_id"]), ("fk", "scn_demand_forecast", ["ingredient_id"], "scn_ingredient", ["ingredient_id"]),
        ("fk", "scn_procurement_reco", ["ingredient_id"], "scn_ingredient", ["ingredient_id"]), ("fk", "scn_procurement_reco", ["supplier_id"], "scn_supplier", ["supplier_id"]),
        ("fk", "scn_procurement_reco", ["quote_id"], "scn_supplier_quote", ["quote_id"])]),
    "003": ("check constraints", [
        ("check", "scn_demand_forecast", "forecast_qty_nonneg", "forecast_qty >= 0"), ("check", "scn_procurement_reco", "reco_order_qty_positive", "order_qty > 0"),
        ("check", "scn_procurement_reco", "reco_cost_nonneg", "est_cost_usd >= 0"), ("check", "scn_menu_item", "menu_price_nonneg", "price_cents >= 0"),
        ("check", "scn_supplier_quote", "quote_price_positive", "unit_price > 0"), ("check", "scn_inventory_week", "inventory_qty_nonneg", "opening_qty >= 0 AND receipts_qty >= 0 AND closing_counted_qty >= 0"),
        ("check", "scn_serving", "serving_volume_positive", "volume_ml > 0 AND fl_oz > 0"), ("check", "scn_variance_flag", "flag_severity_known", "severity IN ('low','medium','high')")]),
    "004": ("indexes for the hot read paths", [
        ("index", "scn_depletion_day", "ix_depl_day_site_ing_date", ["location_id", "ingredient_id", "date"]), ("index", "scn_procurement_reco", "ix_reco_site_ing", ["location_id", "ingredient_id"]),
        ("index", "scn_supplier_quote", "ix_quote_ing_supplier", ["ingredient_id", "supplier_id"])]),
}


class MigrationBlocked(Exception):
    """Pre-flight found rows that violate a constraint; nothing was changed."""
    def __init__(self, version, violations):
        super().__init__(f"migration {version} blocked by existing data: {violations}")
        self.version, self.violations = version, violations


class MigrationChanged(Exception):
    """An already-applied migration's definition differs from what was recorded."""


def _cname(kind, table, cols=None, ref=None):
    return f"{kind}_{table}_{'_'.join(cols or [])}"[:60]


def statements(version):
    """-> (apply_sql list, preflight list of (description, count_sql))."""
    sql, pre = [], []
    for s in SPECS[version][1]:
        k, t = s[0], s[1]
        if k == "pk":
            cols = ", ".join(s[2])
            sql.append(f"ALTER TABLE {t} ADD CONSTRAINT {_cname('pk', t, s[2])} PRIMARY KEY ({cols})")
            pre.append((f"{t}: duplicate or NULL key ({cols})", f"SELECT (SELECT count(*) FROM (SELECT 1 FROM {t} GROUP BY {cols} HAVING count(*) > 1) d) + (SELECT count(*) FROM {t} WHERE " + " OR ".join(f"{c} IS NULL" for c in s[2]) + ")"))
        elif k == "fk":
            n = _cname("fk", t, s[2], s[3])
            sql.append(f"ALTER TABLE {t} ADD CONSTRAINT {n} FOREIGN KEY ({', '.join(s[2])}) REFERENCES {s[3]} ({', '.join(s[4])}) NOT VALID")
            sql.append(f"ALTER TABLE {t} VALIDATE CONSTRAINT {n}")
            pre.append((f"{t}: orphan rows for ({', '.join(s[2])}) -> {s[3]}", f"SELECT count(*) FROM {t} c WHERE c.{s[2][0]} IS NOT NULL AND NOT EXISTS (SELECT 1 FROM {s[3]} p WHERE p.{s[4][0]} = c.{s[2][0]})"))
        elif k == "check":
            sql.append(f"ALTER TABLE {t} ADD CONSTRAINT {s[2]} CHECK ({s[3]})")
            pre.append((f"{t}: rows violating {s[2]}", f"SELECT count(*) FROM {t} WHERE NOT COALESCE({s[3]}, false)"))
        elif k == "index":
            sql.append(f"CREATE INDEX {s[2]} ON {t} ({', '.join(s[3])})")
    return sql, pre


def checksum(version, sql=None):
    sql = sql if sql is not None else statements(version)[0]
    return hashlib.sha256("\n".join(sql).encode()).hexdigest()


def _connect(dsn, schema):
    import psycopg
    con = psycopg.connect(dsn, autocommit=True)
    con.execute(f'SET search_path TO "{schema}", pg_catalog, public')
    return con


def preflight(con, version, specs_sql=None):
    sql, pre = specs_sql or statements(version)
    out = []
    for desc, q in pre:
        n = con.execute(q).fetchone()[0]
        if n:
            out.append(dict(check=desc, violating_rows=n))
    return out


def migrate(dsn, schema=SCHEMA, dry_run=False, specs=None):
    """Apply every pending migration in order. `specs` (tests only) overrides the version -> (apply_sql, preflight) mapping."""
    con = _connect(dsn, schema)
    exists = con.execute("SELECT to_regclass('schema_migrations') IS NOT NULL").fetchone()[0]
    if not exists and not dry_run:                              # a dry run creates nothing, not even the bookkeeping table
        con.execute("CREATE TABLE schema_migrations (version text PRIMARY KEY, name text NOT NULL, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
        exists = True
    done = {v: c for v, c in con.execute("SELECT version, checksum FROM schema_migrations")} if exists else {}
    report = []
    for v in (sorted(specs) if specs else sorted(SPECS)):
        sql, pre = specs[v] if specs else statements(v)
        cs = checksum(v, sql)
        if v in done:
            if done[v] != cs:
                con.close(); raise MigrationChanged(f"migration {v} was edited after it was applied (recorded {done[v][:12]}, now {cs[:12]})")
            report.append(dict(version=v, status="already_applied")); continue
        bad = preflight(con, v, (sql, pre))
        if bad:
            con.close(); raise MigrationBlocked(v, bad)
        if dry_run:
            report.append(dict(version=v, status="would_apply", statements=len(sql))); continue
        with con.transaction():                                   # all or nothing, including the bookkeeping row
            for st in sql:
                con.execute(st)
            con.execute("INSERT INTO schema_migrations (version, name, checksum) VALUES (%s,%s,%s)", (v, (SPECS.get(v) or ("custom",))[0], cs))
        report.append(dict(version=v, status="applied", statements=len(sql)))
    con.close()
    return report


def describe(dsn, schema=SCHEMA):
    """Constraints and indexes as PostgreSQL reports them (not as this module intended them)."""
    con = _connect(dsn, schema)
    cons = con.execute("SELECT conrelid::regclass::text, conname, contype FROM pg_constraint WHERE connamespace = %s::regnamespace AND contype IN ('p','f','c') ORDER BY 1,2", (schema,)).fetchall()
    idx = con.execute("SELECT tablename, indexname FROM pg_indexes WHERE schemaname = %s ORDER BY 1,2", (schema,)).fetchall()
    con.close()
    return dict(constraints=[dict(table=t.split(".")[-1], name=n, type={"p": "PRIMARY KEY", "f": "FOREIGN KEY", "c": "CHECK"}[k]) for t, n, k in cons if "schema_migrations" not in t],
                indexes=[dict(table=t, name=n) for t, n in idx if t != "schema_migrations"])


# ---------------------------------------------------------------- query plans and a small benchmark
QUERIES = {
    "depletion_series_for_one_site_ingredient": "SELECT date, theoretical_qty FROM scn_depletion_day WHERE location_id = %s AND ingredient_id = %s AND date BETWEEN %s AND %s ORDER BY date",
    "recommendation_lookup_by_site_ingredient": "SELECT reco_id, order_qty, est_cost_usd FROM scn_procurement_reco WHERE location_id = %s AND ingredient_id = %s",
    "quotes_for_one_ingredient": "SELECT quote_id, supplier_id, unit_price FROM scn_supplier_quote WHERE ingredient_id = %s ORDER BY unit_price",
}


def _args(con, name):
    """A real (site, ingredient) that has both recommendations and depletion rows, and a 60-day window that starts at its first depletion date."""
    loc, ing, d0, d1 = con.execute("SELECT d.location_id, d.ingredient_id, min(d.date), (min(d.date)::date + 60)::text FROM scn_depletion_day d JOIN scn_procurement_reco r "
                                   "ON r.location_id = d.location_id AND r.ingredient_id = d.ingredient_id GROUP BY 1, 2 ORDER BY count(*) DESC, 1, 2 LIMIT 1").fetchone()
    return {"depletion_series_for_one_site_ingredient": (loc, ing, d0, d1), "recommendation_lookup_by_site_ingredient": (loc, ing), "quotes_for_one_ingredient": (ing,)}[name]


def plan(con, name):
    j = con.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + QUERIES[name], _args(con, name)).fetchone()[0][0]
    nodes = []
    def walk(n):
        nodes.append(n["Node Type"]); [walk(c) for c in n.get("Plans", [])]
    walk(j["Plan"])
    return dict(nodes=nodes, uses_index=any("Index" in n for n in nodes), execution_ms=j["Execution Time"], rows=j["Plan"]["Actual Rows"])


def benchmark(dsn, schema=SCHEMA, repeats=15):
    """Median / min / max wall time per query over `repeats` executions (after one warm-up) on THIS machine's embedded PostgreSQL. A local measurement, not a performance claim about any deployment."""
    con = _connect(dsn, schema)
    out = {}
    for name, q in QUERIES.items():
        a = _args(con, name)
        con.execute(q, a).fetchall()
        ts = []
        for _ in range(repeats):
            t0 = time.perf_counter(); n = len(con.execute(q, a).fetchall()); ts.append((time.perf_counter() - t0) * 1000)
        out[name] = dict(rows=n, median_ms=round(statistics.median(ts), 3), min_ms=round(min(ts), 3), max_ms=round(max(ts), 3), repeats=repeats, plan=plan(con, name))
    con.close()
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--dsn", required=True); ap.add_argument("--schema", default=SCHEMA); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(migrate(a.dsn, a.schema, a.dry_run), indent=1))


if __name__ == "__main__":
    main()
