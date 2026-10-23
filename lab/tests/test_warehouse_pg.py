"""PostgreSQL variant of the warehouse: builds the same 22 dim/fact/mart tables and reconciles them to the SQLite warehouse (row counts + numeric column sums).
Skips (with an explicit reason, not silently) when sqlglot or a PostgreSQL server is unavailable: set NASHA_PG_DSN or `pip install pixeltable-pgserver`."""
import os
import pytest

sqlglot = pytest.importorskip("sqlglot", reason="INTEGRATION UNAVAILABLE: sqlglot not installed")
pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import pg_variant as V, pipeline

CFG = es.SimConfig(name="pg-test", months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_000, employees=60, open_at_start=3)


@pytest.fixture(scope="module")
def dsn(tmp_path_factory):
    if os.environ.get("NASHA_PG_DSN"):
        yield os.environ["NASHA_PG_DSN"]; return
    try:
        import pixeltable_pgserver as pg
        srv = pg.get_server(str(tmp_path_factory.mktemp("pgdata")), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__}); set NASHA_PG_DSN or install pixeltable-pgserver")
    yield srv.get_uri(); srv.cleanup()


@pytest.fixture(scope="module")
def built(dsn, tmp_path_factory):
    d = tmp_path_factory.mktemp("w"); es.generate(CFG, d / "src"); pipeline.run(d / "src", d / "w.db")
    V.build_pg(d / "w.db", dsn)
    return d / "w.db", dsn


def test_every_table_reconciles_to_sqlite(built):
    rep = V.reconcile(*built)
    assert len(rep) >= 20 and all(r["rows"] > 0 for r in rep if r["table"] not in ("fact_return", "fact_quality_event"))
    assert [r for r in rep if r["mismatches"]] == []


def test_round_half_away_from_zero_matches_sqlite(built):
    import psycopg
    with psycopg.connect(built[1], autocommit=True) as c:
        c.execute('SET search_path TO "nasha_wh", pg_catalog, public')
        assert c.execute("SELECT round(2.5::double precision), round(0.5::double precision), round(-2.5::double precision), round(1.00005::double precision, 4)").fetchone() == (3.0, 1.0, -3.0, 1.0001)


def test_d87_scenario_tables_reconcile_in_postgresql(built):
    """The scenario's SQL-derived tables are rebuilt in PostgreSQL from the same transpiled statements and must match SQLite (rows + numeric sums)."""
    from nasha_lab.warehouse import scenario
    path, dsn = built
    scenario.build(path)
    V.build_pg(path, dsn)
    V.build_scn(path, dsn)
    rep = V.reconcile(path, dsn)
    scn = [r for r in rep if r["table"].startswith("scn_")]
    assert len(scn) == len(scenario.ALL_TABLES) and [r for r in scn if r["mismatches"]] == []


TIES = [(1148.1, 1200.0, 0.9568), (737.8, 800.0, 0.9223), (1016.7, 1000.0, 1.0167), (500.0, 500.0, 1.0), (0.1, 3.0, 0.0333)]


def _yield_expr():
    import re
    from nasha_lab.warehouse.build import MODELS
    sql = (MODELS / "22_fact_other.sql").read_text()
    return re.search(r"(CASE WHEN b\.planned_liters > 0 THEN .*? END) AS yield_ratio", sql).group(1)


def test_yield_ratio_rounding_ties_are_identical_in_sqlite_and_postgresql(built):
    """REGRESSION (D-88): float round() of a decimal tie such as 1148.1/1200 (0.95675 exactly; 0.95674999... in binary) gave 0.9567 in SQLite and 0.9568 in PostgreSQL.
    The model now computes the ratio in exact integer tenths; both engines must agree on every tie, and a zero plan must give NULL (not an error)."""
    import psycopg, sqlite3, sqlglot
    expr = _yield_expr()
    lite = sqlite3.connect(":memory:")
    pg_expr = sqlglot.transpile(f"SELECT {expr}", read="sqlite", write="postgres")[0][len("SELECT "):]
    with psycopg.connect(built[1], autocommit=True) as c:
        for yl, pl, want in TIES:
            got_l = lite.execute(f"SELECT {expr.replace('b.yield_liters', str(yl)).replace('b.planned_liters', str(pl))}").fetchone()[0]
            got_p = c.execute(f"SELECT {pg_expr.replace('b.yield_liters', str(yl) + '::double precision').replace('b.planned_liters', str(pl) + '::double precision')}").fetchone()[0]
            assert got_l == pytest.approx(want, abs=1e-12) and float(got_p) == pytest.approx(want, abs=1e-12), (yl, pl, got_l, got_p)
        assert lite.execute(f"SELECT {expr.replace('b.yield_liters', '5.0').replace('b.planned_liters', '0.0')}").fetchone()[0] is None


def test_every_brew_batch_yield_ratio_matches_row_by_row(built):
    import psycopg, sqlite3
    lite = sqlite3.connect(f"file:{built[0]}?mode=ro", uri=True)
    a = lite.execute("SELECT batch_id, yield_ratio FROM fact_brew_batch ORDER BY 1").fetchall()
    with psycopg.connect(built[1], autocommit=True) as c:
        c.execute('SET search_path TO "nasha_wh", public')
        b = c.execute("SELECT batch_id, yield_ratio FROM fact_brew_batch ORDER BY 1").fetchall()
    assert a == [(x, float(y)) for x, y in b] and len(a) > 0
