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
