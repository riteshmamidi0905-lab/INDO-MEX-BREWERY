"""Fault-injection building blocks (P1 item 6). SYNTHETIC / SIMULATED. Every fault is injected at an existing seam of the lab and is switchable, so that
the same object can be 'healed' to measure recovery. Nothing here changes a frozen module: faults ride on `World.faults`, the ExecStack, and proxies that
the caller passes in as `kb`, `client`, `world.con` or `authority`."""
import sqlite3
import time
from collections import defaultdict

from .. import knowledge as K, tools as T
from ..llm import ModelClient, ModelReply, ModelUnavailable


class FaultPlan:
    """Per-call faults applied inside ExecStack (below the retry layer, above the real tool)."""
    def __init__(self, delay_ms=None, transient=None, commit_then_timeout=(), db_break_on=None, sleep=time.sleep):
        self.delay_ms = dict(delay_ms or {})                  # {tool|'*': ms}   latency added before every attempt (below the tool timeout => a latency spike, not a failure)
        self.transient = {k: dict(v) for k, v in (transient or {}).items()}   # {tool: {fail_first: k, code: 'TIMEOUT'|'UPSTREAM_FAILURE'}}  per (run, tool)
        self.commit_then_timeout = set(commit_then_timeout)   # DRAFT tools whose first attempt commits and then reports TIMEOUT (ambiguous failure)
        self.db_break_on = db_break_on                        # (FlakyConnection, tool): break the database the first time `tool` is called
        self.sleep, self.seen, self.log = sleep, defaultdict(int), []

    def active(self): return bool(self.delay_ms or self.transient or self.commit_then_timeout or self.db_break_on)

    def before(self, stack, w, name, args, ctx, attempt):
        d = self.delay_ms.get(name, self.delay_ms.get("*"))
        if d: self.sleep(d / 1000.0); self.log.append(("delay", name, d))
        if self.db_break_on and self.db_break_on[1] == name and not self.db_break_on[0].broken:
            self.db_break_on[0].broken = True; self.log.append(("db_break", name))
        spec = T.TOOLS.get(name)
        tr = self.transient.get(name)
        if tr:
            key = (ctx.run_id, name)
            if self.seen[key] < tr["fail_first"]:
                self.seen[key] += 1; self.log.append(("transient", name, tr["code"]))
                return T._err(name, spec.permission if spec else "UNKNOWN", tr["code"], f"injected transient {tr['code']}", time.perf_counter(), ctx, args)
        if name in self.commit_then_timeout and self.seen[("ctt", ctx.run_id, name)] == 0:
            self.seen[("ctt", ctx.run_id, name)] += 1
            real = stack._orig(w, name, args, ctx)                  # the side effect is COMMITTED ...
            self.log.append(("commit_then_timeout", name, real["ok"]))
            return T._err(name, spec.permission, "TIMEOUT", "injected: the call committed but the response was lost", time.perf_counter(), ctx, args)   # ... and the caller sees a timeout
        return None

    def after(self, stack, w, name, args, ctx, res, attempt): return res


class FlakyConnection:
    """Proxy for the world's sqlite connection. `broken=True` makes every statement fail the way a locked/closed database does."""
    def __init__(self, inner, mode="locked"):
        object.__setattr__(self, "_c", inner); object.__setattr__(self, "broken", False); object.__setattr__(self, "mode", mode)

    def _check(self):
        if self.broken:
            raise (sqlite3.OperationalError("database is locked") if self.mode == "locked" else sqlite3.ProgrammingError("Cannot operate on a closed database."))

    def execute(self, *a, **k): self._check(); return self._c.execute(*a, **k)
    def executemany(self, *a, **k): self._check(); return self._c.executemany(*a, **k)
    def commit(self): self._check(); return self._c.commit()
    def __getattr__(self, n): return getattr(self._c, n)


_DEGRADED = {}


def degraded_kb(base):
    """A REAL knowledge base built from a corpus that lost its authoritative partition (as after a failed re-index): only non-authoritative chunks remain."""
    key = id(base)
    if key not in _DEGRADED:
        _DEGRADED[key] = K.KnowledgeBase([c for c in base.chunks.values() if c["effective_status"] not in K.AUTHORITATIVE | K.USABLE_WITH_CAVEAT])
    return _DEGRADED[key]


class FaultableKB:
    """Proxy for a KnowledgeBase with a switchable fault: None (healthy) | 'miss' (authoritative partition missing) | 'down' (retriever raises)."""
    def __init__(self, kb, fault=None, down_retrievers=("hybrid",)):
        self._kb, self.fault, self.down_retrievers = kb, fault, set(down_retrievers)

    def __getattr__(self, name): return getattr(self._kb, name)

    def _target(self, method, kw):
        if self.fault == "miss": return degraded_kb(self._kb)
        if self.fault == "down" and (kw.get("retriever") or self._kb.default) in self.down_retrievers: raise RuntimeError("retriever unavailable (injected)")
        return self._kb

    def ask(self, question, **kw): return self._target("ask", kw).ask(question, **kw)
    def search(self, query, **kw): return self._target("search", kw).search(query, **kw)


class FaultyClient(ModelClient):
    """Wraps a scripted model client. mode: None | 'timeout' (raises ModelUnavailable after `delay_s`, the way a timed-out request surfaces) |
    'schema' (replies with output that violates the schema for the first `bad_replies` calls of each phase, then recovers)."""
    version = "faulty"; runtime = "scripted"

    def __init__(self, inner, mode=None, delay_s=0.0, bad_replies=0, only_phase=None):
        self.inner, self.mode, self.delay_s, self.bad_replies, self.only_phase = inner, mode, delay_s, bad_replies, only_phase
        self.name, self.version = inner.name, getattr(inner, "version", "")
        self.calls_seen = 0; self.bad_left = {}

    @property
    def calls(self): return self.inner.calls

    def chat(self, messages, schema, max_tokens=700):
        self.calls_seen += 1
        phase = "collect" if "tool_calls" in schema.get("properties", {}) else "decide"
        applies = self.only_phase in (None, phase)
        if self.mode == "timeout" and applies:
            if self.delay_s: time.sleep(self.delay_s)
            raise ModelUnavailable("injected: model request timed out")
        if self.mode == "schema" and applies:
            left = self.bad_left.setdefault(phase, self.bad_replies)
            if left > 0:
                self.bad_left[phase] = left - 1
                return ModelReply('{"unexpected": "this reply violates the schema", "action": 12}', 10, 8, 1.0)
        return self.inner.chat(messages, schema, max_tokens)
