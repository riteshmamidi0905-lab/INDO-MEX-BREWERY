"""Versioned, transactional, checksummed SQL migrations for PostgreSQL (psycopg 3) with up/down and a migration table.

Files: <dir>/NNNN_name.up.sql and NNNN_name.down.sql. Each migration runs inside ONE transaction together with its bookkeeping row, so a failure leaves both the
schema and the version untouched. A session-level advisory lock serialises concurrent migrators. Applied migrations are verified against the SHA-256 of their
up file (tamper / drift detection); a database ahead of the code (unknown versions) is reported, never silently accepted.
The SQLite Migrator in ops/hardening.py is the design this follows (transactional apply, rollback on failure, version in the store); PostgreSQL needs a table instead of PRAGMA user_version."""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

import psycopg

MIG_DIR = os.path.join(os.path.dirname(__file__), "migrations")
LOCK_KEY = 727_001
FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.(up|down)\.sql$")
TABLE = "schema_migrations"


class MigrationError(Exception):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(f"{kind}: {message}"); self.kind = kind


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up: str
    down: Optional[str]

    @property
    def checksum(self) -> str: return hashlib.sha256(self.up.encode()).hexdigest()


def load_migrations(directory: str = MIG_DIR) -> list[Migration]:
    ups: dict[int, tuple[str, str]] = {}; downs: dict[int, str] = {}
    for f in sorted(os.listdir(directory)):
        m = FILE_RE.match(f)
        if not m: continue
        v, name, kind = int(m.group(1)), m.group(2), m.group(3)
        with open(os.path.join(directory, f), encoding="utf-8") as fh: text = fh.read()
        if kind == "up":
            if v in ups: raise MigrationError("DUPLICATE_VERSION", f"two up files for version {v}")
            ups[v] = (name, text)
        else: downs[v] = text
    vs = sorted(ups)
    if vs and vs != list(range(1, len(vs) + 1)): raise MigrationError("VERSION_GAP", f"versions must be 1..N without gaps, found {vs}")
    return [Migration(v, ups[v][0], ups[v][1], downs.get(v)) for v in vs]


def latest_version(directory: str = MIG_DIR) -> int:
    ms = load_migrations(directory); return ms[-1].version if ms else 0


class Migrator:
    def __init__(self, dsn: str, directory: str = MIG_DIR, *, lock_timeout_ms: int = 5000, connect_timeout_s: int = 5) -> None:
        self.dsn, self.dir, self.lock_timeout_ms, self.connect_timeout_s = dsn, directory, lock_timeout_ms, connect_timeout_s
        self.migrations = load_migrations(directory)

    def _connect(self) -> "psycopg.Connection[Any]":
        c: "psycopg.Connection[Any]" = psycopg.connect(self.dsn, autocommit=True, connect_timeout=self.connect_timeout_s)
        c.execute(f"SET lock_timeout = {int(self.lock_timeout_ms)}")
        return c

    def _ensure_table(self, c: "psycopg.Connection[Any]") -> None:
        c.execute(f"CREATE TABLE IF NOT EXISTS {TABLE} (version integer PRIMARY KEY, name text NOT NULL, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")

    def _applied(self, c: "psycopg.Connection[Any]") -> dict[int, tuple[str, str]]:
        return {int(v): (n, ck) for v, n, ck in c.execute(f"SELECT version, name, checksum FROM {TABLE} ORDER BY version").fetchall()}

    def _problems(self, applied: dict[int, tuple[str, str]]) -> list[str]:
        known = {m.version: m for m in self.migrations}; out: list[str] = []
        for v, (name, ck) in sorted(applied.items()):
            if v not in known: out.append(f"SCHEMA_NEWER: database has version {v} ({name}) that this build does not know")
            elif known[v].checksum != ck: out.append(f"CHECKSUM_MISMATCH: migration {v} ({name}) was edited after it was applied")
            elif known[v].name != name: out.append(f"NAME_MISMATCH: migration {v} was applied as {name!r}, code calls it {known[v].name!r}")
        vs = sorted(applied)
        if vs != list(range(1, len(vs) + 1)): out.append(f"VERSION_GAP: applied versions {vs} are not contiguous")
        return out

    def status(self) -> dict[str, Any]:
        with self._connect() as c:
            self._ensure_table(c); applied = self._applied(c)
        cur = max(applied) if applied else 0
        return {"current": cur, "latest": self.migrations[-1].version if self.migrations else 0, "applied": sorted(applied),
                "pending": [m.version for m in self.migrations if m.version not in applied], "problems": self._problems(applied)}

    def verify(self) -> dict[str, Any]:
        s = self.status()
        if s["problems"]: raise MigrationError(s["problems"][0].split(":")[0], "; ".join(s["problems"]))
        return s

    def up(self, target: Optional[int] = None) -> list[int]:
        done: list[int] = []
        with self._connect() as c:
            c.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
            try:
                self._ensure_table(c)
                applied = self._applied(c)
                prob = self._problems(applied)
                if prob: raise MigrationError(prob[0].split(":")[0], "refusing to migrate: " + "; ".join(prob))
                for m in self.migrations:
                    if m.version in applied or (target is not None and m.version > target): continue
                    try:
                        with c.transaction():
                            c.execute(m.up.encode())
                            c.execute(f"INSERT INTO {TABLE}(version, name, checksum) VALUES (%s, %s, %s)", (m.version, m.name, m.checksum))
                    except psycopg.Error as e:
                        raise MigrationError("MIGRATION_FAILED", f"migration {m.version} ({m.name}) failed and was rolled back; version stays {max(applied) if applied else 0}: {type(e).__name__}: {str(e).splitlines()[0][:160]}") from None
                    done.append(m.version); applied[m.version] = (m.name, m.checksum)
            finally:
                c.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
        return done

    def down(self, target: int) -> list[int]:
        """Roll back to `target` (0 = empty). Runs each migration's down file in its own transaction, newest first."""
        undone: list[int] = []
        with self._connect() as c:
            c.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
            try:
                self._ensure_table(c)
                applied = self._applied(c)
                prob = [p for p in self._problems(applied) if not p.startswith("SCHEMA_NEWER")]
                if prob: raise MigrationError(prob[0].split(":")[0], "refusing to roll back: " + "; ".join(prob))
                known = {m.version: m for m in self.migrations}
                for v in sorted(applied, reverse=True):
                    if v <= target: break
                    m = known.get(v)
                    if m is None or not m.down: raise MigrationError("NO_DOWN_SCRIPT", f"migration {v} has no down script in this build")
                    try:
                        with c.transaction():
                            c.execute(m.down.encode())
                            c.execute(f"DELETE FROM {TABLE} WHERE version = %s", (v,))
                    except psycopg.Error as e:
                        raise MigrationError("ROLLBACK_FAILED", f"down {v} failed and was rolled back: {type(e).__name__}: {str(e).splitlines()[0][:160]}") from None
                    undone.append(v)
            finally:
                c.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
        return undone


def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    import json
    import sys
    from .config import ConfigError, load_settings
    ap = argparse.ArgumentParser(prog="python -m nasha_lab.service.migrations", description="PostgreSQL migrations (SYNTHETIC / NOT PRODUCTION DEPLOYED)")
    ap.add_argument("command", choices=["up", "down", "status", "verify"]); ap.add_argument("--target", type=int, default=None)
    a = ap.parse_args(argv)
    dsn = os.environ.get("NASHA_SVC_MIGRATE_DSN")
    try:
        if not dsn: dsn = load_settings().database_url.get_secret_value()
        m = Migrator(dsn)
        if a.command == "up": print(json.dumps({"applied": m.up(a.target)}))
        elif a.command == "down":
            if a.target is None: print("down requires --target N (0 = empty schema)", file=sys.stderr); return 2
            print(json.dumps({"rolled_back": m.down(a.target)}))
        elif a.command == "status": print(json.dumps(m.status()))
        else: print(json.dumps(m.verify()))
    except (ConfigError, MigrationError) as e:
        print(f"ERROR {e}", file=sys.stderr); return 1
    except psycopg.OperationalError as e:
        print(f"ERROR DB_UNAVAILABLE: {type(e).__name__}", file=sys.stderr); return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
