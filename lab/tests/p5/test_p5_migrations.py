"""Migration tests against a real PostgreSQL: fresh up, down, idempotent re-run, checksum tamper, failed migration rollback, drift, concurrency."""
from __future__ import annotations

import shutil
import threading

import psycopg
import pytest

from nasha_lab.service.migrations import MIG_DIR, MigrationError, Migrator, latest_version, load_migrations

pytestmark = pytest.mark.p5_pg


def tables(dsn: str) -> set[str]:
    with psycopg.connect(dsn) as c: return {r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")}


def test_fresh_up_applies_all_in_order_and_records_checksums(fresh_db):
    m = Migrator(fresh_db); assert m.up() == [1, 2, 3]
    s = m.status(); assert s["current"] == s["latest"] == latest_version() == 3 and s["pending"] == [] and s["problems"] == []
    assert {"runs", "approvals", "audit_log", "idempotency_keys", "dead_letters", "schema_migrations"} <= tables(fresh_db)
    with psycopg.connect(fresh_db) as c:
        rows = c.execute("SELECT version, checksum FROM schema_migrations ORDER BY version").fetchall()
    assert [r[0] for r in rows] == [1, 2, 3] and all(len(r[1]) == 64 for r in rows)


def test_rerun_is_idempotent(fresh_db):
    m = Migrator(fresh_db); m.up(); assert m.up() == [] and m.status()["current"] == 3


def test_down_to_each_version_and_back_up(fresh_db):
    m = Migrator(fresh_db); m.up()
    assert m.down(2) == [3] and m.status()["current"] == 2
    assert m.down(0) == [2, 1] and m.status()["current"] == 0 and "runs" not in tables(fresh_db)
    assert m.up() == [1, 2, 3] and "runs" in tables(fresh_db)


def test_up_to_a_target_stops_there(fresh_db):
    m = Migrator(fresh_db); assert m.up(target=1) == [1] and m.status()["pending"] == [2, 3]


def test_checksum_tamper_is_detected_and_blocks_further_migration(fresh_db, tmp_path):
    d = tmp_path / "m"; shutil.copytree(MIG_DIR, d)
    Migrator(fresh_db, str(d)).up(target=2)
    p = d / "0001_core.up.sql"; p.write_text(p.read_text() + "\n-- edited after it was applied\n")
    m = Migrator(fresh_db, str(d))
    assert any(x.startswith("CHECKSUM_MISMATCH") for x in m.status()["problems"])
    with pytest.raises(MigrationError) as e: m.up()
    assert e.value.kind == "CHECKSUM_MISMATCH"
    with pytest.raises(MigrationError): m.down(0)
    with psycopg.connect(fresh_db) as c: assert c.execute("SELECT max(version) FROM schema_migrations").fetchone()[0] == 2


def test_failed_migration_rolls_back_schema_and_version(fresh_db, tmp_path):
    d = tmp_path / "m"; shutil.copytree(MIG_DIR, d)
    (d / "0004_bad.up.sql").write_text("CREATE TABLE half_done (id int);\nINSERT INTO half_done VALUES (1);\nSELECT 1/0;\n"); (d / "0004_bad.down.sql").write_text("DROP TABLE half_done;\n")
    m = Migrator(fresh_db, str(d))
    with pytest.raises(MigrationError) as e: m.up()
    assert e.value.kind == "MIGRATION_FAILED" and "rolled back" in str(e.value) and "version stays 3" in str(e.value)
    assert "half_done" not in tables(fresh_db) and m.status()["current"] == 3
    (d / "0004_bad.up.sql").write_text("CREATE TABLE fixed (id int);\n")
    assert Migrator(fresh_db, str(d)).up() == [4] and "fixed" in tables(fresh_db)          # the same version applies after the fix


def test_failed_down_rolls_back_too(fresh_db, tmp_path):
    d = tmp_path / "m"; shutil.copytree(MIG_DIR, d)
    Migrator(fresh_db, str(d)).up()
    (d / "0003_query_indexes.down.sql").write_text("DROP INDEX ix_audit_at;\nDROP INDEX does_not_exist;\n")
    m = Migrator(fresh_db, str(d))
    with pytest.raises(MigrationError) as e: m.down(2)
    assert e.value.kind == "ROLLBACK_FAILED" and m.status()["current"] == 3
    with psycopg.connect(fresh_db) as c: assert c.execute("SELECT to_regclass('ix_audit_at')").fetchone()[0] is not None     # first statement was rolled back


def test_database_ahead_of_code_is_reported_as_drift(fresh_db, tmp_path):
    d = tmp_path / "m"; shutil.copytree(MIG_DIR, d)
    (d / "0004_future.up.sql").write_text("CREATE TABLE future (id int);\n"); (d / "0004_future.down.sql").write_text("DROP TABLE future;\n")
    Migrator(fresh_db, str(d)).up()
    old = Migrator(fresh_db)                                       # the code that only knows 1..3
    s = old.status(); assert s["current"] == 4 and s["latest"] == 3 and s["problems"][0].startswith("SCHEMA_NEWER")
    with pytest.raises(MigrationError) as e: old.up()
    assert e.value.kind == "SCHEMA_NEWER"


def test_gap_in_applied_versions_is_drift(fresh_db):
    m = Migrator(fresh_db); m.up()
    with psycopg.connect(fresh_db, autocommit=True) as c: c.execute("DELETE FROM schema_migrations WHERE version=2")
    assert m.status()["problems"][0].startswith("VERSION_GAP")


def test_concurrent_migrators_apply_each_version_once(fresh_db):
    out: list = []; errs: list = []

    def go():
        try: out.append(Migrator(fresh_db).up())
        except Exception as e: errs.append(e)
    ts = [threading.Thread(target=go) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert not errs and sorted(sum(out, [])) == [1, 2, 3] and Migrator(fresh_db).status()["current"] == 3


def test_audit_log_is_append_only(migrated_db):
    with psycopg.connect(migrated_db, autocommit=True) as c:
        c.execute("INSERT INTO audit_log(request_id, principal_hash, action, resource, outcome) VALUES ('r','p','a','x','ok')")
        with pytest.raises(psycopg.errors.InsufficientPrivilege): c.execute("UPDATE audit_log SET outcome='tampered'")
        with pytest.raises(psycopg.errors.InsufficientPrivilege): c.execute("DELETE FROM audit_log")


def test_migration_files_are_complete_pairs_without_gaps():
    ms = load_migrations(); assert [m.version for m in ms] == list(range(1, len(ms) + 1)) and all(m.down for m in ms)


def test_cli_status_and_down_requires_target(fresh_db, monkeypatch, capsys):
    from nasha_lab.service import migrations as M
    monkeypatch.setenv("NASHA_SVC_MIGRATE_DSN", fresh_db)
    assert M.main(["up"]) == 0 and M.main(["status"]) == 0 and M.main(["verify"]) == 0 and M.main(["down"]) == 2
    assert M.main(["down", "--target", "0"]) == 0 and Migrator(fresh_db).status()["current"] == 0
