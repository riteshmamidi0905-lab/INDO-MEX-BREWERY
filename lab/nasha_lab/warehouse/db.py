"""SQLite connection, metadata tables and run bookkeeping."""
import datetime as dt
import sqlite3
import uuid

META = """
CREATE TABLE IF NOT EXISTS pipeline_runs (run_id TEXT PRIMARY KEY, started TEXT, finished TEXT, status TEXT, step TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS pipeline_steps (run_id TEXT, step TEXT, started TEXT, seconds REAL, rows INTEGER, status TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS load_partitions (tbl TEXT, partition TEXT, rows INTEGER, fingerprint TEXT, source_sha256 TEXT, loaded_at TEXT, run_id TEXT, status TEXT, PRIMARY KEY (tbl, partition));
CREATE TABLE IF NOT EXISTS quarantine (run_id TEXT, tbl TEXT, key TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS dq_results (run_id TEXT, gate TEXT, name TEXT, severity TEXT, passed INTEGER, observed TEXT, expected TEXT);
CREATE TABLE IF NOT EXISTS lineage (model TEXT, depends_on TEXT, kind TEXT, run_id TEXT);
CREATE TABLE IF NOT EXISTS model_runs (run_id TEXT, model TEXT, rows INTEGER, seconds REAL, fingerprint TEXT);
"""


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path):
    con = sqlite3.connect(str(path), timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute("PRAGMA cache_size=-400000")
    con.executescript(META)
    return con


def new_run(con, step="pipeline"):
    rid = uuid.uuid4().hex[:12]
    con.execute("INSERT INTO pipeline_runs VALUES (?,?,?,?,?,?)", (rid, now(), None, "running", step, ""))
    con.commit()
    return rid


def finish_run(con, rid, status, detail=""):
    con.execute("UPDATE pipeline_runs SET finished=?, status=?, detail=? WHERE run_id=?", (now(), status, detail[:2000], rid))
    con.commit()


def step_log(con, rid, step, t0, seconds, rows, status="ok", detail=""):
    con.execute("INSERT INTO pipeline_steps VALUES (?,?,?,?,?,?,?)", (rid, step, t0, round(seconds, 2), rows, status, detail[:500]))
    con.commit()
