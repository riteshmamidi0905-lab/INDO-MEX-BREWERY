"""Structured run traces + run registry (SQLite). Secrets are redacted by tools.redact before they reach a trace."""
import json
import sqlite3
import threading
import time
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_runs(run_id TEXT PRIMARY KEY, request_id TEXT, event_id TEXT, status TEXT, created REAL, finished REAL, outcome TEXT);
CREATE TABLE IF NOT EXISTS trace_events(run_id TEXT, seq INTEGER, ts REAL, kind TEXT, data TEXT, PRIMARY KEY(run_id, seq));
"""


class Store:
    def __init__(self, path=":memory:"):
        self.con = sqlite3.connect(path, check_same_thread=False); self.con.executescript(SCHEMA); self.lock = threading.RLock(); self.path = path

    def create_run(self, event_id, request_id=""):
        run_id = "run-" + uuid.uuid4().hex[:10]
        with self.lock:
            self.con.execute("INSERT INTO agent_runs VALUES(?,?,?,?,?,NULL,NULL)", (run_id, request_id, event_id, "RUNNING", time.time())); self.con.commit()
        return run_id

    def active_run_for(self, event_id):
        with self.lock:
            r = self.con.execute("SELECT run_id, status FROM agent_runs WHERE event_id=? AND status NOT IN ('FAILED') ORDER BY created LIMIT 1", (event_id,)).fetchone()
        return r

    def set_status(self, run_id, status, outcome=None, finished=False):
        with self.lock:
            self.con.execute("UPDATE agent_runs SET status=?, outcome=COALESCE(?,outcome), finished=CASE WHEN ? THEN ? ELSE finished END WHERE run_id=?", (status, outcome, int(finished), time.time(), run_id)); self.con.commit()

    def run(self, run_id):
        with self.lock:
            r = self.con.execute("SELECT run_id, request_id, event_id, status, created, finished, outcome FROM agent_runs WHERE run_id=?", (run_id,)).fetchone()
        return None if not r else dict(zip(("run_id", "request_id", "event_id", "status", "created", "finished", "outcome"), r))

    def events(self, run_id):
        with self.lock:
            rows = self.con.execute("SELECT seq, ts, kind, data FROM trace_events WHERE run_id=? ORDER BY seq", (run_id,)).fetchall()
        return [dict(seq=s, ts=t, kind=k, **json.loads(d)) for s, t, k, d in rows]

    def trace(self, run_id, request_id=""):
        return Trace(self, run_id, request_id)


class Trace:
    def __init__(self, store, run_id, request_id=""):
        self.store, self.run_id, self.request_id = store, run_id, request_id

    def event(self, kind, **data):
        with self.store.lock:
            seq = (self.store.con.execute("SELECT COALESCE(MAX(seq),0)+1 FROM trace_events WHERE run_id=?", (self.run_id,)).fetchone()[0])
            data.setdefault("request_id", self.request_id)
            self.store.con.execute("INSERT INTO trace_events VALUES(?,?,?,?,?)", (self.run_id, seq, time.time(), kind, json.dumps(data, default=str))); self.store.con.commit()
