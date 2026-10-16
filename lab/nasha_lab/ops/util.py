"""Small shared helpers (deterministic, dependency free)."""
import hashlib
import json
import math
import os

OPS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ops"))          # lab/ops (declarative files, runbooks)
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "results", "ops"))   # lab/results/ops


def sha(obj, n=12):
    b = obj if isinstance(obj, bytes) else (obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, default=str)).encode()
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()[:n]


def quantile(values, q):
    """Nearest-rank quantile (no interpolation). None for an empty list."""
    v = sorted(x for x in values if x is not None)
    if not v: return None
    return v[min(len(v) - 1, max(0, math.ceil(q * len(v)) - 1))]


def wilson(k, n, z=1.96):
    if n == 0: return [None, None]
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 3), round((c + h) / d, 3)]


def rate(k, n):
    return dict(k=k, n=n, rate=round(k / n, 4) if n else None, ci95=wilson(k, n))


def load_json(path):
    with open(path, encoding="utf-8") as f: return json.load(f)


def dump_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")
