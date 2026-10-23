"""PostgreSQL hardening: constraints are real (violations are rejected by the database), migrations are safe (pre-flight, atomic, idempotent, tamper-evident), and the indexes change the query plans.
Needs a PostgreSQL server (NASHA_PG_DSN or the embedded pixeltable-pgserver); skipped with an explicit reason otherwise."""
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("sqlglot", reason="INTEGRATION UNAVAILABLE: sqlglot not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import pg_hardening as H, pg_variant as V, pipeline, scenario

CFG = es.SimConfig(name="pg-hard", months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_000, employees=60, open_at_start=3)
SCN = scenario.BASE_TABLES + scenario.PY_TABLES + scenario.DERIVED_TABLES


@pytest.fixture(scope="module")
def dsn(tmp_path_factory):
    if os.environ.get("NASHA_PG_DSN"):
        yield os.environ["NASHA_PG_DSN"]; return
    try:
        import pixeltable_pgserver as pg
        srv = pg.get_server(str(tmp_path_factory.mktemp("pgdata")), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    yield srv.get_uri(); srv.cleanup()


@pytest.fixture(scope="module")
def built(dsn, tmp_path_factory):
    d = tmp_path_factory.mktemp("w"); es.generate(CFG, d / "src"); pipeline.run(d / "src", d / "w.db"); scenario.build(d / "w.db")
    V.build_pg(d / "w.db", dsn); V.build_scn(d / "w.db", dsn)
    return d / "w.db"


def clone_schema(dsn, name):
    """A fresh schema holding plain copies (no constraints) of the scenario tables, so each test can corrupt or migrate its own copy."""
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE'); c.execute(f'CREATE SCHEMA "{name}"')
        for t in SCN:
            c.execute(f'CREATE TABLE "{name}".{t} AS SELECT * FROM nasha_wh.{t}')
    return name


def conn(dsn, schema):
    c = psycopg.connect(dsn, autocommit=True); c.execute(f'SET search_path TO "{schema}", pg_catalog, public'); return c


def count(dsn, schema, table):
    with conn(dsn, schema) as c:
        return c.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_dry_run_reports_the_plan_and_changes_nothing(dsn, built):
    s = clone_schema(dsn, "h_dry")
    rep = H.migrate(dsn, s, dry_run=True)
    assert [r["status"] for r in rep] == ["would_apply"] * 4
    assert H.describe(dsn, s)["constraints"] == [] and H.describe(dsn, s)["indexes"] == []


def test_migrations_apply_and_PostgreSQL_reports_the_constraints(dsn, built):
    s = clone_schema(dsn, "h_apply")
    before = {t: count(dsn, s, t) for t in SCN}
    rep = H.migrate(dsn, s)
    assert [r["status"] for r in rep] == ["applied"] * 4
    d = H.describe(dsn, s)
    kinds = {k: sum(c["type"] == k for c in d["constraints"]) for k in ("PRIMARY KEY", "FOREIGN KEY", "CHECK")}
    assert kinds == {"PRIMARY KEY": 12, "FOREIGN KEY": 9, "CHECK": 8}, kinds
    assert {"ix_depl_day_site_ing_date", "ix_reco_site_ing", "ix_quote_ing_supplier"} <= {i["name"] for i in d["indexes"]}
    assert {t: count(dsn, s, t) for t in SCN} == before, "migrations must not change any data"


def test_rerun_is_a_no_op_and_an_edited_migration_is_detected(dsn, built):
    s = clone_schema(dsn, "h_idem"); H.migrate(dsn, s)
    assert [r["status"] for r in H.migrate(dsn, s)] == ["already_applied"] * 4
    edited = {v: H.statements(v) for v in H.SPECS}
    edited["003"] = (edited["003"][0] + ["ALTER TABLE scn_serving ADD CONSTRAINT extra CHECK (fl_oz < 1000)"], edited["003"][1])
    with pytest.raises(H.MigrationChanged):
        H.migrate(dsn, s, specs=edited)


@pytest.mark.parametrize("sql,ok", [
    ("INSERT INTO scn_ingredient SELECT * FROM scn_ingredient LIMIT 1", False),                                                                    # duplicate primary key
    ("UPDATE scn_procurement_reco SET supplier_id = 'NO-SUCH-SUPPLIER' WHERE reco_id = (SELECT min(reco_id) FROM scn_procurement_reco)", False),    # orphan foreign key
    ("UPDATE scn_demand_forecast SET forecast_qty = -1 WHERE ctid = (SELECT min(ctid) FROM scn_demand_forecast)", False),                          # negative forecast
    ("UPDATE scn_procurement_reco SET order_qty = 0 WHERE reco_id = (SELECT min(reco_id) FROM scn_procurement_reco)", False),                      # zero-quantity order
    ("UPDATE scn_supplier_quote SET unit_price = 0 WHERE quote_id = (SELECT min(quote_id) FROM scn_supplier_quote)", False),                       # free quote
    ("INSERT INTO scn_variance_flag VALUES ('L01', 999, (SELECT min(ingredient_id) FROM scn_ingredient), 0.1, 0.1, 0.1, 'spike', 'catastrophic')", False),                       # unknown severity
    ("UPDATE scn_procurement_reco SET rationale = rationale WHERE reco_id = (SELECT min(reco_id) FROM scn_procurement_reco)", True)])              # control: a valid change succeeds
def test_the_database_itself_rejects_violations(dsn, built, sql, ok):
    s = "h_enforce"
    if not getattr(test_the_database_itself_rejects_violations, "ready", False):
        clone_schema(dsn, s); H.migrate(dsn, s); test_the_database_itself_rejects_violations.ready = True
    with conn(dsn, s) as c:
        if ok:
            c.execute(sql)
        else:
            with pytest.raises((psycopg.errors.IntegrityError, psycopg.errors.CheckViolation)):
                c.execute(sql)


def test_preflight_blocks_a_migration_when_data_would_violate_it_and_changes_nothing(dsn, built):
    s = clone_schema(dsn, "h_block")
    with conn(dsn, s) as c:
        c.execute("INSERT INTO scn_ingredient SELECT * FROM scn_ingredient LIMIT 1")               # duplicate key already present
    with pytest.raises(H.MigrationBlocked) as e:
        H.migrate(dsn, s)
    assert e.value.version == "001" and any("scn_ingredient" in v["check"] for v in e.value.violations)
    assert H.describe(dsn, s)["constraints"] == []
    with conn(dsn, s) as c:
        assert c.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 0


def test_a_failure_in_the_middle_of_a_migration_rolls_the_whole_migration_back(dsn, built):
    s = clone_schema(dsn, "h_atomic")
    good, pre = H.statements("001")
    bad = {"001": (good + ["ALTER TABLE no_such_table ADD CONSTRAINT x PRIMARY KEY (a)"], pre)}
    with pytest.raises(psycopg.errors.Error):
        H.migrate(dsn, s, specs=bad)
    assert H.describe(dsn, s)["constraints"] == [], "the primary keys added before the failing statement must be rolled back"
    with conn(dsn, s) as c:
        assert c.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 0


def test_indexes_change_the_query_plans_and_the_benchmark_is_recorded(dsn, built, tmp_path):
    s = clone_schema(dsn, "h_plan")
    pre_only = {v: H.statements(v) for v in ("001", "002", "003")}
    H.migrate(dsn, s, specs=pre_only)
    with conn(dsn, s) as c:
        c.execute("ANALYZE")
    before = H.benchmark(dsn, s, repeats=7)
    H.migrate(dsn, s)
    with conn(dsn, s) as c:
        c.execute("ANALYZE")
    after = H.benchmark(dsn, s, repeats=7)
    for q in ("depletion_series_for_one_site_ingredient", "recommendation_lookup_by_site_ingredient"):
        assert after[q]["rows"] == before[q]["rows"] > 0, "an index must not change the answer"
        assert after[q]["plan"]["uses_index"], (q, after[q]["plan"]["nodes"])
    assert not before["recommendation_lookup_by_site_ingredient"]["plan"]["uses_index"], "before the index the planner has only a sequential scan for this predicate"
    Path(os.environ.get("NASHA_PG_BENCH_OUT", tmp_path / "pg_bench.json")).write_text(json.dumps(dict(
        note="Local measurement on an embedded PostgreSQL with synthetic data; not a performance claim about any deployment.", rows={t: count(dsn, s, t) for t in ("scn_depletion_day", "scn_procurement_reco", "scn_supplier_quote")}, before_indexes=before, after_indexes=after), indent=1))
