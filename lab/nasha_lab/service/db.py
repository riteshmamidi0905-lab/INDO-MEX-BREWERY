"""PostgreSQL access: psycopg 3 connection pool with statement/lock/pool timeouts, a circuit breaker (ops.resilience) so a dead database fails fast instead of
making every request wait, and one place that translates driver errors into the service's error codes."""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import psycopg
from psycopg import errors as pgerr
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolClosed, PoolTimeout

from ..ops.resilience import CircuitBreaker
from .config import Settings
from .errors import ApiError
from .obs import Metrics, emit



class Deadline:
    """A per-request deadline. `check()` is called before a commit so a request that already answered 504 does not commit afterwards (best effort: see P5-HARDENED-SERVICE.md)."""
    def __init__(self, seconds: float, clock: Any = time.monotonic) -> None:
        self.clock, self.at, self.cancelled = clock, clock() + seconds, False

    def remaining(self) -> float: return max(0.0, self.at - self.clock())
    def cancel(self) -> None: self.cancelled = True
    def check(self) -> None:
        if self.cancelled or self.clock() >= self.at: raise ApiError("DEADLINE_EXCEEDED", "the request deadline passed before the work completed; its outcome is not guaranteed")


def translate_db_error(e: BaseException) -> ApiError:
    """Driver exception -> ApiError. Messages never include SQL text, parameters or the DSN."""
    if isinstance(e, ApiError): return e
    if isinstance(e, PoolTimeout): return ApiError("DB_POOL_EXHAUSTED", "no database connection became available in time", retry_after_s=1.0)
    if isinstance(e, PoolClosed): return ApiError("DB_UNAVAILABLE", "database pool is closed", retry_after_s=1.0)
    if isinstance(e, pgerr.QueryCanceled): return ApiError("DB_TIMEOUT", "the database statement exceeded its time limit")
    if isinstance(e, pgerr.LockNotAvailable): return ApiError("IDEMPOTENCY_BUSY", "a concurrent request holds the lock; retry with the same key", retry_after_s=1.0)
    if isinstance(e, (psycopg.OperationalError, psycopg.InterfaceError)): return ApiError("DB_UNAVAILABLE", "the database is unavailable", retry_after_s=2.0)
    return ApiError("INTERNAL_ERROR", "internal error")


HEALTH_ERRORS = (PoolTimeout, PoolClosed, pgerr.QueryCanceled, pgerr.AdminShutdown, pgerr.CannotConnectNow, psycopg.InterfaceError)


def _is_health(e: BaseException) -> bool:
    if isinstance(e, pgerr.LockNotAvailable): return False
    return isinstance(e, HEALTH_ERRORS) or (isinstance(e, psycopg.OperationalError) and not isinstance(e, pgerr.LockNotAvailable))


class Database:
    def __init__(self, s: Settings, metrics: Optional[Metrics] = None, *, clock: Any = time.monotonic) -> None:
        self.s, self.metrics = s, metrics or Metrics()
        self.breaker = CircuitBreaker(s.db_breaker_threshold, s.db_breaker_reset_s, clock=clock)
        self.pool: Optional[ConnectionPool] = None

    def open(self) -> None:
        s = self.s
        opts = f"-c statement_timeout={s.db_statement_timeout_ms} -c lock_timeout={s.db_lock_timeout_ms} -c idle_in_transaction_session_timeout=15000 -c application_name=nasha-lab-api"
        self.pool = ConnectionPool(s.database_url.get_secret_value(), min_size=s.db_pool_min, max_size=s.db_pool_max, timeout=s.db_pool_timeout_s, open=False,
                                   kwargs={"autocommit": False, "connect_timeout": s.db_connect_timeout_s, "options": opts, "row_factory": dict_row},
                                   check=ConnectionPool.check_connection, max_lifetime=1800, reconnect_timeout=30, name="nasha-api")
        self.pool.open(wait=False)

    def wait_ready(self, seconds: float) -> bool:
        if self.pool is None: return False
        try: self.pool.wait(timeout=seconds); return True
        except PoolTimeout: return False

    def close(self) -> None:
        if self.pool is not None: self.pool.close(timeout=2.0)

    @contextmanager
    def tx(self, deadline: Optional[Deadline] = None) -> Iterator["psycopg.Connection[dict[str, Any]]"]:
        """One transaction on a pooled connection: commit on success, rollback on any exception. Driver errors surface as ApiError."""
        if self.pool is None: raise ApiError("DB_UNAVAILABLE", "database pool is not open", retry_after_s=2.0)
        if not self.breaker.allow("db"):
            self.metrics.inc("nasha_db_errors_total", help="database errors by kind", kind="circuit_open")
            raise ApiError("DB_UNAVAILABLE", "the database circuit is open; not attempted", retry_after_s=self.s.db_breaker_reset_s)
        timeout = min(self.s.db_pool_timeout_s, deadline.remaining()) if deadline else self.s.db_pool_timeout_s
        try:
            with self.pool.connection(timeout=max(timeout, 0.01)) as conn:
                yield conn
                if deadline: deadline.check()
        except ApiError:
            self.breaker.record("db", True)         # a business error is not a database health signal
            raise
        except psycopg.Error as e:
            self.breaker.record("db", not _is_health(e)); err = translate_db_error(e)
            emit(logging.getLogger("nasha.service"), logging.WARNING, "db_error", code=err.code, kind=type(e).__name__, detail=f"sqlstate={getattr(e, 'sqlstate', None)} {str(e).splitlines()[0][:160] if str(e) else ''}")
            self.metrics.inc("nasha_db_errors_total", help="database errors by kind", kind=err.code)
            raise err from None
        except PoolTimeout as e:
            self.breaker.record("db", False); self.metrics.inc("nasha_db_errors_total", help="database errors by kind", kind="DB_POOL_EXHAUSTED")
            raise translate_db_error(e) from None
        except PoolClosed as e:
            raise translate_db_error(e) from None
        else:
            self.breaker.record("db", True)

    def stats(self) -> dict[str, int]:
        if self.pool is None: return {}
        st = self.pool.get_stats()
        return {"size": st.get("pool_size", 0), "available": st.get("pool_available", 0), "waiting": st.get("requests_waiting", 0), "max": st.get("pool_max", 0)}
