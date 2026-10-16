"""Token-bucket rate limiter, thread-safe, injectable clock, bounded key table (least-recently-used eviction).
LIMITATION (documented in P5-HARDENED-SERVICE.md): state is per process and in memory. N replicas allow N x the configured rate, a restart resets buckets, and
a flood of distinct keys can evict a victim's bucket (the table is bounded on purpose so the limiter cannot be used to exhaust memory)."""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Callable


class TokenBucketLimiter:
    def __init__(self, capacity: float, refill_per_s: float, *, max_keys: int = 10000, clock: Callable[[], float] = time.monotonic) -> None:
        self.capacity, self.refill, self.max_keys, self.clock = capacity, refill_per_s, max_keys, clock
        self._b: "OrderedDict[str, tuple[float, float]]" = OrderedDict()
        self._lock = threading.Lock()
        self.evictions = 0

    def take(self, key: str, cost: float = 1.0) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds). retry_after is 0 when allowed."""
        now = self.clock()
        with self._lock:
            tokens, last = self._b.pop(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill)
            ok = tokens >= cost
            if ok: tokens -= cost
            self._b[key] = (tokens, now)
            while len(self._b) > self.max_keys:
                self._b.popitem(last=False); self.evictions += 1
            return ok, 0.0 if ok else (cost - tokens) / self.refill

    def size(self) -> int:
        with self._lock: return len(self._b)
