"""P2: GAP-08 migration with rollback, GAP-09 secrets scan and config boundary, FC-17 re-verification. SYNTHETIC / OFFLINE."""
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from nasha_lab import agent, api, identity as ID, knowledge, world as W
from nasha_lab.ops import hardening as H


def seeded():
    con = sqlite3.connect(":memory:"); m = H.Migrator(con, H.MIGRATIONS); m.migrate(target=1)
    con.execute("BEGIN")
    for i in range(20): con.execute("INSERT INTO ops_runs VALUES(?,?)", (f"r{i}", json.dumps(dict(outcome_category="COMPLETED_ACTION", timing=dict(run_ms=1.0 + i)))))
    con.execute("COMMIT"); return con, m


def test_migration_applies_in_order_and_backfills():
    con, m = seeded(); assert m.migrate() == [2, 3] and m.version() == 3
    assert con.execute("SELECT COUNT(*) FROM ops_runs WHERE run_ms IS NOT NULL AND outcome_category IS NOT NULL").fetchone()[0] == 20


def test_failed_migration_rolls_back_ddl_and_data_and_version():
    con, m = seeded(); before = con.execute("SELECT COUNT(*), SUM(LENGTH(record_json)) FROM ops_runs").fetchone()
    def bad(c): c.execute("ALTER TABLE ops_runs ADD COLUMN outcome_category TEXT"); raise RuntimeError("boom")
    mm = H.Migrator(con, [(1, "c", H._m1), (2, "bad", bad)])
    with pytest.raises(H.MigrationError, match="rolled back"): mm.migrate()
    assert mm.version() == 1 and "outcome_category" not in [r[1] for r in con.execute("PRAGMA table_info(ops_runs)")]
    assert con.execute("SELECT COUNT(*), SUM(LENGTH(record_json)) FROM ops_runs").fetchone() == before
    assert H.Migrator(con, H.MIGRATIONS).migrate() == [2, 3]            # the good path still works afterwards


def test_backup_restore_round_trip():
    con, m = seeded(); b = m.backup(); con.execute("DELETE FROM ops_runs"); m.restore(b)
    assert con.execute("SELECT COUNT(*) FROM ops_runs").fetchone()[0] == 20


def test_secret_scanner_finds_planted_secrets_and_respects_the_allowlist(tmp_path):
    planted = "API_KEY = \"" + "s" + "k-" + "abcdefghijklmnopqrstuvwxyz123456\"\npassword = \"hunter2" + "hunter2\"\n" + "AK" + "IAABCDEFGHIJKLMNOP\n"      # assembled at runtime so this file does not trip its own scanner
    (tmp_path / "a.py").write_text(planted)
    f, a = H.scan_tree(str(tmp_path), {"entries": []}); assert {x["rule"] for x in f} >= {"provider_style_api_key", "assigned_secret", "aws_access_key"} and not a
    f2, a2 = H.scan_tree(str(tmp_path), {"entries": [{"path_suffix": "a.py", "rule": "assigned_secret", "contains": "hunter2", "reason": "test"}]}); assert len(a2) >= 1 and len(f2) < len(f)
    assert all("hunter2hunter2" not in json.dumps(x) for x in f)           # excerpts are masked


def test_lab_tree_has_no_unallowlisted_secrets():
    f, a = H.scan_tree(); assert f == [], f
    assert {x["rule"] for x in a} == {"dev_passcode_literal"}               # the only tolerated items are the documented dev passcodes


def test_config_boundary():
    r = H.config_boundary_report(); assert r["authority_secret_is_random_bytes"] and r["authority_secret_in_repr"] and r["redaction_hides_secret_keys"]


def test_fc17_unauthenticated_decision_does_not_reveal_whether_a_run_exists():
    """FC-17 re-verified at this commit: approve/reject/review authenticate FIRST, so an unknown and a real run both answer 401. (Read endpoints are unauthenticated by design.)"""
    w = W.build_world(1)[0]; svc = agent.AgentService(w, knowledge.default_kb(), authority=ID.Authority.dev()); c = TestClient(api.create_app(service=svc))
    rid = c.post("/agent/runs", json={"event_id": "EV-A1"}).json()["run"]["run_id"]
    real = c.post(f"/agent/runs/{rid}/approve", json={}); fake = c.post("/agent/runs/run-doesnotexist/approve", json={})
    assert real.status_code == fake.status_code == 401 and real.json()["error"]["code"] == fake.json()["error"]["code"]
    assert c.get(f"/agent/runs/{rid}").status_code == 200 and c.get("/agent/runs/run-doesnotexist").status_code == 404         # residual: reads reveal existence
