"""Observability: structured JSON logs with redaction, Prometheus text metrics, W3C trace-context propagation and spans.

Logs: one JSON object per line; only whitelisted fields; the principal appears only as a keyed hash; free text is scrubbed of bearer tokens, JWT-shaped strings
and credentials inside connection URLs. Spans: recorded in a BOUNDED ring (ops.telemetry.JsonLogger, bounded here because the stock one grows without limit)
and emitted as log lines; there is no OpenTelemetry SDK because there is no collector in this repository to export to (see P5-HARDENED-SERVICE.md)."""
from __future__ import annotations

import contextvars
import hashlib
import hmac
import json
import logging
import math
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Any, Deque, Iterator, Optional

from ..ops import telemetry as TM

REDACTIONS = [
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)(postgres(?:ql)?://[^:/@\s]+:)[^@\s]+@"), r"\1[REDACTED]@"),
    (re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\b(\s*[=:]\s*)[^\s,;&\"']+"), r"\1\2[REDACTED]"),
]
LOG_FIELDS = ("request_id", "trace_id", "span_id", "principal", "method", "route", "status", "ms", "code", "failure_class", "attempts", "detail", "name", "parent", "kind", "count", "state", "ip_hash", "where")


def scrub(text: str) -> str:
    for rx, rep in REDACTIONS: text = rx.sub(rep, text)
    return text


class Hasher:
    """Keyed, truncated hash for principal ids and client addresses in logs (stable within a process, not reversible without the salt)."""
    def __init__(self, salt: Optional[bytes] = None) -> None: self._salt = salt or secrets.token_bytes(16)
    def __call__(self, value: str) -> str: return hmac.new(self._salt, value.encode(), hashlib.sha256).hexdigest()[:12]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {"ts": round(record.created, 3), "level": record.levelname, "logger": record.name, "event": scrub(record.getMessage()), "synthetic": True}
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            for k in LOG_FIELDS:
                if k in fields and fields[k] is not None: out[k] = scrub(fields[k]) if isinstance(fields[k], str) else fields[k]
        if record.exc_info and record.exc_info[0] is not None: out["exc_type"] = record.exc_info[0].__name__      # type only: messages may carry values
        return json.dumps(out, sort_keys=True, default=str)


def configure_logging(level: str = "INFO", stream: Any = None) -> logging.Logger:
    log = logging.getLogger("nasha.service")
    log.setLevel(level); log.propagate = False
    for h in list(log.handlers): log.removeHandler(h)
    h = logging.StreamHandler(stream); h.setFormatter(JsonFormatter()); log.addHandler(h)
    return log


def emit(log: logging.Logger, level: int, event: str, **fields: Any) -> None:
    log.log(level, event, extra={"fields": fields})


# ------------------------------------------------------------------------------------------------ Prometheus text exposition
BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def _esc(v: str) -> str: return v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
def _lbl(k: tuple[tuple[str, str], ...]) -> str: return "{" + ",".join(f'{a}="{_esc(b)}"' for a, b in k) + "}" if k else ""


class Metrics:
    """Counters, gauges and fixed-bucket histograms (memory is bounded by label cardinality, not by request count)."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(dict)
        self.gauges: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(dict)
        self.hists: dict[str, dict[tuple[tuple[str, str], ...], list[float]]] = defaultdict(dict)
        self.help: dict[str, str] = {}

    @staticmethod
    def _k(labels: dict[str, Any]) -> tuple[tuple[str, str], ...]: return tuple(sorted((a, str(b)) for a, b in labels.items()))

    def inc(self, name: str, value: float = 1.0, help: str = "", **labels: Any) -> None:
        with self._lock:
            self.help.setdefault(name, help); d = self.counters[name]; k = self._k(labels); d[k] = d.get(k, 0.0) + value

    def set(self, name: str, value: float, help: str = "", **labels: Any) -> None:
        with self._lock: self.help.setdefault(name, help); self.gauges[name][self._k(labels)] = value

    def observe(self, name: str, value: float, help: str = "", **labels: Any) -> None:
        with self._lock:
            self.help.setdefault(name, help); d = self.hists[name]; k = self._k(labels)
            h = d.setdefault(k, [0.0] * (len(BUCKETS) + 2))        # buckets..., +Inf count in [-2], sum in [-1]
            for i, b in enumerate(BUCKETS):
                if value <= b: h[i] += 1
            h[-2] += 1; h[-1] += value

    def counter_value(self, name: str, **labels: Any) -> float: return self.counters.get(name, {}).get(self._k(labels), 0.0)

    def render(self) -> str:
        with self._lock:
            out: list[str] = []
            for name in sorted(self.counters):
                out += [f"# HELP {name} {self.help.get(name, '')}", f"# TYPE {name} counter"]
                out += [f"{name}{_lbl(k)} {_num(v)}" for k, v in sorted(self.counters[name].items())]
            for name in sorted(self.gauges):
                out += [f"# HELP {name} {self.help.get(name, '')}", f"# TYPE {name} gauge"]
                out += [f"{name}{_lbl(k)} {_num(v)}" for k, v in sorted(self.gauges[name].items())]
            for name in sorted(self.hists):
                out += [f"# HELP {name} {self.help.get(name, '')}", f"# TYPE {name} histogram"]
                for k, h in sorted(self.hists[name].items()):
                    for i, b in enumerate(BUCKETS): out.append(f"{name}_bucket{_lbl(k + (('le', str(b)),))} {_num(h[i])}")
                    out.append(f"{name}_bucket{_lbl(k + (('le', '+Inf'),))} {_num(h[-2])}")
                    out += [f"{name}_sum{_lbl(k)} {_num(h[-1])}", f"{name}_count{_lbl(k)} {_num(h[-2])}"]
            return "\n".join(out) + "\n"


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() and not math.isinf(v) else repr(round(v, 6))


# ------------------------------------------------------------------------------------------------ trace context + spans
TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
_current: contextvars.ContextVar[Optional[tuple[str, str]]] = contextvars.ContextVar("nasha_span", default=None)


def parse_traceparent(h: Optional[str]) -> Optional[tuple[str, str]]:
    m = TRACEPARENT_RE.match(h or "")
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16: return None
    return m.group(1), m.group(2)


def new_trace() -> tuple[str, str]: return secrets.token_hex(16), secrets.token_hex(8)


class BoundedJsonLogger(TM.JsonLogger):
    """ops.telemetry.JsonLogger keeps every line forever; a service must not. Same record shape, last `maxlen` kept."""
    def __init__(self, maxlen: int = 2000, **kw: Any) -> None:
        super().__init__(**kw); self.lines: Deque[dict[str, Any]] = deque(maxlen=maxlen)       # type: ignore[assignment]


class Tracer:
    def __init__(self, log: logging.Logger, ring: Optional[BoundedJsonLogger] = None) -> None:
        self.log, self.ring = log, ring or BoundedJsonLogger()

    def start(self, traceparent: Optional[str]) -> tuple[str, str, Optional[str]]:
        """Continue an incoming trace or start one. Returns (trace_id, span_id, parent_span_id)."""
        p = parse_traceparent(traceparent)
        trace_id, parent = p if p else (new_trace()[0], None)
        span_id = secrets.token_hex(8)
        _current.set((trace_id, span_id))
        return trace_id, span_id, parent

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Iterator[None]:
        cur = _current.get()
        trace_id = cur[0] if cur else new_trace()[0]
        span_id = secrets.token_hex(8)
        tok = _current.set((trace_id, span_id)); t0 = time.perf_counter(); state = "ok"
        try:
            yield
        except BaseException:
            state = "error"; raise
        finally:
            ms = round((time.perf_counter() - t0) * 1000, 3)
            _current.reset(tok)
            self.ring.info("span", name=name, trace_id=trace_id, span_id=span_id, parent=cur[1] if cur else None, ms=ms, state=state, **attrs)
            emit(self.log, logging.DEBUG, "span", name=name, trace_id=trace_id, span_id=span_id, parent=cur[1] if cur else None, ms=ms, state=state)

    def current(self) -> Optional[tuple[str, str]]: return _current.get()
