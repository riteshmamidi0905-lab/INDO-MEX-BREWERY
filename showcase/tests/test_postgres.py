"""Real PostgreSQL constraints and RLS, with a non-superuser reader.
The host owns tenant context. Direct arbitrary SQL access is outside this boundary.
"""
from pathlib import Path
import sqlite3
import pytest
import psycopg
from psycopg import sql
import pixeltable_pgserver as pg
from showcase.config import BusinessConfig
from showcase.scenario import build,export,TABLES
from showcase.postgres import migrate

def test_postgres_schema_reconciliation_rls_and_constraints(tmp_path):
    database=tmp_path/'fitness.db'
    build(BusinessConfig(tenant='meridian-fitness',industry='fitness',target_orders=5,start='2026-10-01',end='2026-10-02'),database)
    with sqlite3.connect(database) as local:
        snapshot=export(local,'meridian-fitness')
    second=tmp_path/'nasha.db'
    build(BusinessConfig(target_orders=5,industry='fitness',start='2026-10-01',end='2026-10-02'),second)
    with sqlite3.connect(second) as local:
        other=export(local,'nasha-brewery')
    srv=pg.get_server(tmp_path/'pg',cleanup_mode='stop')
    try:
        with psycopg.connect(srv.get_uri(),autocommit=True) as c:
            with pytest.raises(ValueError): migrate(c,'public')
            migrate(c,'showcase_v1_test')
            with pytest.raises(psycopg.errors.DuplicateSchema): migrate(c,'showcase_v1_test')
            c.execute('SET search_path TO showcase_v1_test')
            for table in TABLES:
                rows=snapshot['tables'][table]+other['tables'][table]
                if rows:
                    cols=list(rows[0])
                    statement=sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,cols)),sql.SQL(',').join(sql.Placeholder() for _ in cols))
                    with c.cursor() as cur: cur.executemany(statement,[[r[k] for k in cols] for r in rows])
            pg_summary=c.execute('SELECT net_revenue_cents,expense_cents,cash_cents,capital_cents FROM finance_summary WHERE tenant_id=%s',('meridian-fitness',)).fetchone()
            assert pg_summary==tuple(snapshot['summary'][k] for k in ('net_revenue_cents','expense_cents','cash_cents','capital_cents'))
            c.execute('CREATE ROLE showcase_test_reader NOLOGIN NOSUPERUSER NOBYPASSRLS')
            c.execute('GRANT USAGE ON SCHEMA showcase_v1_test TO showcase_test_reader')
            c.execute('GRANT SELECT,INSERT ON ALL TABLES IN SCHEMA showcase_v1_test TO showcase_test_reader')
            c.execute('SET ROLE showcase_test_reader')
            assert c.execute('SELECT count(*) FROM agents').fetchone()[0]==0
            c.execute("SELECT set_config('showcase.tenant_id','meridian-fitness',false)")
            assert c.execute('SELECT count(*) FROM agents').fetchone()[0]==15
            assert c.execute("SELECT count(*) FROM agents WHERE tenant_id='nasha-brewery'").fetchone()[0]==0
            assert c.execute('SELECT count(*) FROM finance_summary').fetchone()[0]==1
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                c.execute("INSERT INTO businesses VALUES ('nasha-brewery','bad','bad','2026-01-01','2026-01-02',1,'{}')")
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                c.execute("INSERT INTO tasks VALUES ('meridian-fitness','bad','foreign-project','maya','bad','queued')")
            c.execute("SELECT set_config('showcase.tenant_id','nasha-brewery',false)")
            assert c.execute('SELECT count(*) FROM agents').fetchone()[0]==15
            assert c.execute("SELECT count(*) FROM agents WHERE tenant_id='meridian-fitness'").fetchone()[0]==0
            assert c.execute('SELECT count(*) FROM finance_summary WHERE tenant_id=%s',('meridian-fitness',)).fetchone()[0]==0
    finally:
        srv.cleanup()
