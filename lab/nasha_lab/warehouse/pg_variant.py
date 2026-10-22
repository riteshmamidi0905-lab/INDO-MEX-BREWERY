"""PostgreSQL variant of the warehouse models (SYNTHETIC data).

Builds the same dimensions, facts and marts in a PostgreSQL schema from the same staged data, by transpiling the SQLite model SQL with sqlglot
(sqlite -> postgres) and hand-writing the one model that uses SQLite date arithmetic (the calendar). `reconcile` then compares every table with the
SQLite warehouse: row counts and per-column sums for all numeric columns. It does NOT re-implement ingestion, contracts or the quality gates in
PostgreSQL: staging rows are copied from the already-published SQLite warehouse. Requires: sqlglot, psycopg, a reachable PostgreSQL.

    python -m nasha_lab.warehouse.pg_variant --sqlite wh.db --dsn postgresql://...
"""
import argparse
import math
import re
import sqlite3
import sys

import pandas as pd
import sqlglot

from .build import MODELS, parse_models
from .ingest import DIMENSIONS, FACTS

HELPERS = """
-- SQLite round() rounds half AWAY from zero; PostgreSQL round(double precision) rounds half to EVEN (found by reconciliation: waste cost differed by 11 cents).
-- These schema-local functions shadow the built-ins because the schema comes before pg_catalog in search_path.
CREATE OR REPLACE FUNCTION round(double precision, integer) RETURNS double precision LANGUAGE sql IMMUTABLE AS $$ SELECT round($1::numeric, $2)::double precision $$;
CREATE OR REPLACE FUNCTION round(double precision) RETURNS double precision LANGUAGE sql IMMUTABLE AS $$ SELECT round($1::numeric)::double precision $$;
"""
DIM_DATE_PG = """
CREATE TABLE dim_date AS
WITH d AS (SELECT generate_series((SELECT min(open_date) FROM stg_locations)::date, (SELECT max(substr(ts,1,10)) FROM stg_orders)::date, interval '1 day')::date AS dday)
SELECT CAST(to_char(dday,'YYYYMMDD') AS INTEGER) AS date_key, to_char(dday,'YYYY-MM-DD') AS date, to_char(dday,'YYYY-MM') AS month, CAST(extract(dow FROM dday) AS INTEGER) AS dow,
       CASE WHEN extract(dow FROM dday) IN (0,5,6) THEN 1 ELSE 0 END AS is_weekend_ish FROM d;
CREATE UNIQUE INDEX ux_dim_date ON dim_date(date_key);
"""
STAGED = list(DIMENSIONS) + list(FACTS)


def _pgtype(s: pd.Series):
    k = s.dtype.kind
    return "BIGINT" if k in "iu" or str(s.dtype).startswith("Int") else "DOUBLE PRECISION" if k == "f" else "TEXT"


def copy_staging(lite, con, schema):
    for t in STAGED:
        df = pd.read_sql_query(f"SELECT * FROM stg_{t}", lite).convert_dtypes()
        cols = list(df.columns)
        con.execute(f'CREATE TABLE "{schema}".stg_{t} (' + ", ".join(f'"{c}" {_pgtype(df[c])}' for c in cols) + ")")
        if len(df):
            with con.cursor().copy(f'COPY "{schema}".stg_{t} FROM STDIN') as cp:
                for row in df.itertuples(index=False):
                    cp.write_row([None if (v is pd.NA or (isinstance(v, float) and math.isnan(v))) else (v.item() if hasattr(v, "item") else v) for v in row])


def translate(sql):
    return [sqlglot.transpile(st.strip(), read="sqlite", write="postgres")[0] for st in re.split(r";\s*\n", sql) if st.strip().strip(";") and not st.strip().startswith("--") or re.search(r"\bCREATE|INSERT\b", st)]


def build_pg(sqlite_path, dsn, schema="nasha_wh"):
    import psycopg
    lite = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    parts = [r[0] for r in lite.execute("SELECT DISTINCT partition FROM load_partitions WHERE status='complete' AND partition <> 'all' ORDER BY 1")]
    plist = ",".join(f"'{p}'" for p in parts)
    with psycopg.connect(dsn, autocommit=True) as con:
        con.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        con.execute(f'CREATE SCHEMA "{schema}"')
        con.execute(f'SET search_path TO "{schema}", pg_catalog, public')
        con.execute(HELPERS)
        copy_staging(lite, con, schema)
        for m in parse_models():
            if m["name"] == "sources":
                continue
            sql = DIM_DATE_PG if m["name"] == "calendar" else m["sql"].replace("{PARTS}", plist)
            if m["name"] == "calendar":
                for st in re.split(r";\s*\n", sql):
                    if st.strip():
                        con.execute(st)
                continue
            body = "\n".join(l for l in sql.splitlines() if not l.startswith("--"))
            body = re.sub(r"(?i)\bsum\(\s*([\w.]+ IS (?:NOT )?NULL)\s*\)", r"sum(CASE WHEN \1 THEN 1 ELSE 0 END)", body)   # SQLite sums booleans; PostgreSQL does not
            for st in sqlglot.parse(body, read="sqlite"):
                if st is not None:
                    con.execute(st.sql(dialect="postgres"))
    lite.close()
    return parts


def reconcile(sqlite_path, dsn, schema="nasha_wh", rel_tol=1e-5):
    import psycopg
    lite = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    tables = [r[0] for r in lite.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'dim_%' OR name LIKE 'fact_%' OR name LIKE 'mart_%') ORDER BY 1")]
    out = []
    with psycopg.connect(dsn, autocommit=True) as con:
        con.execute(f'SET search_path TO "{schema}", public')
        for t in tables:
            num = [r[0] for r in con.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s AND data_type IN ('integer','bigint','smallint','numeric','double precision','real') AND column_name NOT LIKE '\\_%%' ORDER BY ordinal_position", (schema, t))]
            sums_l = lite.execute("SELECT count(*)," + ",".join(f'sum(CAST("{c}" AS REAL))' for c in num) + f" FROM {t}").fetchone() if num else (lite.execute(f"SELECT count(*) FROM {t}").fetchone()[0],)
            sums_p = con.execute("SELECT count(*)," + ",".join(f'sum("{c}"::double precision)' for c in num) + f" FROM {t}").fetchone() if num else (con.execute(f"SELECT count(*) FROM {t}").fetchone()[0],)
            bad = []
            if sums_l[0] != sums_p[0]:
                bad.append(("rows", sums_l[0], sums_p[0]))
            for c, a, b in zip(num, sums_l[1:], sums_p[1:]):
                if a is None and b is None:
                    continue
                if a is None or b is None or abs(a - b) > rel_tol * max(1.0, abs(a)):
                    bad.append((c, a, b))
            out.append({"table": t, "rows": sums_l[0], "numeric_columns": len(num), "mismatches": bad})
    lite.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True); ap.add_argument("--dsn", required=True); ap.add_argument("--schema", default="nasha_wh")
    a = ap.parse_args(argv)
    build_pg(a.sqlite, a.dsn, a.schema)
    rep = reconcile(a.sqlite, a.dsn, a.schema)
    for r in rep:
        print(("OK  " if not r["mismatches"] else "FAIL"), r["table"], r["rows"], r["mismatches"] or "")
    return 0 if all(not r["mismatches"] for r in rep) else 1


if __name__ == "__main__":
    sys.exit(main())
