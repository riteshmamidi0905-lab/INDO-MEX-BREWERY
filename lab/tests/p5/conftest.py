"""P5 fixtures. PostgreSQL comes from (1) NASHA_PG_DSN (CI service container) or (2) the `pgserver` package; if neither is available the PostgreSQL tests SKIP cleanly.
Every test that needs a database gets its own freshly created database (dropped afterwards). All secrets are generated at test time; none is a literal."""
from __future__ import annotations

import json
import os
import secrets
import socket
import tempfile
import threading
import time
import uuid
from typing import Any, Iterator, Optional

import pytest

from nasha_lab import agent, generator, knowledge, world as W
from nasha_lab.service.auth import TokenService
from nasha_lab.service.config import Settings, load_settings
from nasha_lab.service.gateway import BridgedAuthority

psycopg = pytest.importorskip("psycopg")


# ------------------------------------------------------------------------------------------------ PostgreSQL provider
@pytest.fixture(scope="session")
def pg_admin_dsn() -> Iterator[str]:
    dsn = os.environ.get("NASHA_PG_DSN")
    if dsn:
        try:
            with psycopg.connect(dsn, connect_timeout=3, autocommit=True) as c: c.execute("SELECT 1")
            yield dsn; return
        except psycopg.Error: pass
    try:
        import pgserver
    except Exception:
        pytest.skip("PostgreSQL unavailable: set NASHA_PG_DSN or install pgserver"); return
    d = tempfile.mkdtemp(prefix="p5pg-")
    try:
        srv = pgserver.get_server(d, cleanup_mode="delete")
    except Exception as e:
        pytest.skip(f"pgserver could not start PostgreSQL here: {type(e).__name__}"); return
    try:
        yield srv.get_uri()
    finally:
        try: srv.cleanup()
        except Exception: pass


def _swap_db(dsn: str, name: str) -> str:
    info = psycopg.conninfo.conninfo_to_dict(dsn); info["dbname"] = name
    return psycopg.conninfo.make_conninfo(**info)


@pytest.fixture()
def fresh_db(pg_admin_dsn: str) -> Iterator[str]:
    name = "p5_" + uuid.uuid4().hex[:12]
    with psycopg.connect(pg_admin_dsn, autocommit=True) as c: c.execute(f'CREATE DATABASE "{name}"')
    try:
        yield _swap_db(pg_admin_dsn, name)
    finally:
        with psycopg.connect(pg_admin_dsn, autocommit=True) as c: c.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture()
def migrated_db(fresh_db: str) -> str:
    from nasha_lab.service.migrations import Migrator
    Migrator(fresh_db).up(); return fresh_db


# ------------------------------------------------------------------------------------------------ a TCP proxy that can fail on command
class FlakyProxy:
    """127.0.0.1:port -> the real PostgreSQL (TCP host:port or unix socket). Modes: 'pass', 'down' (drop live connections, refuse new), 'slow' (delay each chunk)."""
    def __init__(self, upstream_dsn: str) -> None:
        info = psycopg.conninfo.conninfo_to_dict(upstream_dsn)
        host = info.get("host", "localhost"); self.up: tuple[str, Any] = (host, int(info.get("port", 5432))) if not host.startswith("/") else (host, None)
        self.info = info; self.mode, self.delay = "pass", 0.0
        self.lsock = socket.socket(); self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); self.lsock.bind(("127.0.0.1", 0)); self.lsock.listen(50)
        self.port = self.lsock.getsockname()[1]; self.conns: list[socket.socket] = []; self.stop = False; self.lock = threading.Lock()
        threading.Thread(target=self._accept, daemon=True).start()

    def dsn(self, dbname: Optional[str] = None) -> str:
        i = dict(self.info); i["host"], i["port"] = "127.0.0.1", self.port
        if dbname: i["dbname"] = dbname
        return psycopg.conninfo.make_conninfo(**i)

    def _connect_up(self) -> socket.socket:
        if self.up[1] is None:
            s = socket.socket(socket.AF_UNIX); s.connect(os.path.join(self.up[0], f".s.PGSQL.{self.info.get('port', 5432)}")); return s
        return socket.create_connection((self.up[0], self.up[1]), timeout=3)

    def _accept(self) -> None:
        while not self.stop:
            try: c, _ = self.lsock.accept()
            except OSError: return
            if self.mode == "down": c.close(); continue
            threading.Thread(target=self._serve, args=(c,), daemon=True).start()

    def _serve(self, c: socket.socket) -> None:
        try: u = self._connect_up()
        except OSError: c.close(); return
        with self.lock: self.conns += [c, u]

        def pump(a: socket.socket, b: socket.socket) -> None:
            try:
                while True:
                    d = a.recv(65536)
                    if not d: break
                    if self.mode == "slow": time.sleep(self.delay)
                    if self.mode == "down": break
                    b.sendall(d)
            except OSError: pass
            finally:
                for s in (a, b):
                    try: s.close()
                    except OSError: pass
        threading.Thread(target=pump, args=(c, u), daemon=True).start(); threading.Thread(target=pump, args=(u, c), daemon=True).start()

    def set_mode(self, mode: str, delay: float = 0.0) -> None:
        self.mode, self.delay = mode, delay
        if mode == "down":
            with self.lock:
                for s in self.conns:
                    try: s.close()
                    except OSError: pass
                self.conns = []

    def close(self) -> None:
        self.stop = True; self.set_mode("down")
        try: self.lsock.close()
        except OSError: pass


@pytest.fixture()
def proxy(pg_admin_dsn: str) -> Iterator[FlakyProxy]:
    p = FlakyProxy(pg_admin_dsn)
    try: yield p
    finally: p.close()


# ------------------------------------------------------------------------------------------------ settings, keys, tokens (generated at test time)
class Keys:
    def __init__(self) -> None:
        self.k1, self.k2 = secrets.token_hex(32), secrets.token_hex(32)


@pytest.fixture(scope="session")
def keys() -> Keys: return Keys()


def make_settings(dsn: str, keys: Keys, tmp: str, **over: Any) -> Settings:
    env = {"NASHA_SVC_ENV": "test", "NASHA_SVC_DATABASE_URL": dsn, "NASHA_SVC_JWT_KEYS": json.dumps({"k1": keys.k1, "k2": keys.k2}), "NASHA_SVC_JWT_ACTIVE_KID": "k1",
           "NASHA_SVC_DATA_DIR": tmp, "NASHA_SVC_DOCS_ENABLED": "true", "NASHA_SVC_DB_POOL_MAX": "6", "NASHA_SVC_DB_POOL_TIMEOUT_S": "1.0", "NASHA_SVC_RATE_IP_CAPACITY": "1000",
           "NASHA_SVC_RATE_IP_REFILL_PER_S": "1000", "NASHA_SVC_RATE_PRINCIPAL_CAPACITY": "1000", "NASHA_SVC_RATE_PRINCIPAL_REFILL_PER_S": "1000"}
    for k, v in over.items(): env["NASHA_SVC_" + k.upper()] = v if isinstance(v, str) else json.dumps(v) if isinstance(v, (dict, list)) else str(v).lower() if isinstance(v, bool) else str(v)
    return load_settings(env)


# ------------------------------------------------------------------------------------------------ agent pieces (knowledge base is expensive: build once)
@pytest.fixture(scope="session")
def shared_kb() -> Any: return knowledge.default_kb()


def new_service(kb: Any) -> agent.AgentService:
    w = W.build_world(1, menu_version=generator.CURRENT_MENU_VERSION, po_coverage=W.CURRENT_PO_COVERAGE)[0]
    return agent.AgentService(w, kb, authority=BridgedAuthority.dev())


@pytest.fixture()
def svc(shared_kb: Any) -> agent.AgentService: return new_service(shared_kb)


def tok(keys: Keys, sub: str, role: str, ttl: int = 900, **kw: Any) -> str:
    return TokenService({"k1": keys.k1, "k2": keys.k2}, "k1", "nasha-lab-dev", "nasha-lab-api").issue(sub, role, ttl, **kw)


def auth(keys: Keys, sub: str = "alice", role: str = "BUYER", **kw: Any) -> dict[str, str]:
    return {"Authorization": "Bearer " + tok(keys, sub, role, **kw)}


# ------------------------------------------------------------------------------------------------ app fixture
@pytest.fixture()
def app_env(migrated_db: str, keys: Keys, svc: agent.AgentService, tmp_path: Any) -> Iterator[Any]:
    from fastapi.testclient import TestClient
    from nasha_lab.service.app import create_hardened_app
    s = make_settings(migrated_db, keys, str(tmp_path))
    app = create_hardened_app(s, service=svc)
    with TestClient(app, raise_server_exceptions=False) as client:
        class Env: pass
        e = Env(); e.client, e.app, e.settings, e.service, e.keys, e.dsn, e.tmp = client, app, s, svc, keys, migrated_db, str(tmp_path)    # type: ignore[attr-defined]
        yield e


def pytest_sessionfinish(session: Any, exitstatus: Any) -> None:
    try:
        from results_recorder import flush
        flush()
    except Exception:
        pass
