"""Reproducibility check: generate + build the warehouse twice from scratch (separate temp dirs) and compare content hashes of every dimension/fact/mart
table and the Ops AI evaluation hash. Also records the environment (python and key package versions) so a difference can be attributed.

    python -m nasha_lab.warehouse.repro [--profile dev] [--out results/warehouse_repro.json]    exit 1 if anything differs
SYNTHETIC data; deterministic by construction (seeded PCG64), so a mismatch means a real nondeterminism bug (unordered iteration, timestamps in data, float summation order)."""
import argparse
import hashlib
import importlib.metadata as md
import json
import platform
import sqlite3
import sys
import tempfile
from pathlib import Path

from .. import enterprise_sim as es
from . import ops_ai_eval, pipeline

KEYS = ("numpy", "pandas", "sqlglot", "psycopg", "pydantic", "fastapi")


def table_hashes(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'dim_%' OR name LIKE 'fact_%' OR name LIKE 'mart_%' OR name LIKE 'scn_%') AND name <> 'scn_scenario_run' ORDER BY 1")]
    out = {}
    for t in names:
        h = hashlib.sha256()
        k = min(4, len(con.execute(f"PRAGMA table_info({t})").fetchall()))
        for row in con.execute(f"SELECT * FROM {t} ORDER BY {','.join(map(str, range(1, k + 1)))}"):
            h.update(repr(row).encode())
        out[t] = h.hexdigest()[:16]
    con.close()
    return out


def build_once(cfg):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        es.generate(cfg, d / "src")
        pipeline.run(d / "src", d / "w.db")
        hashes = table_hashes(d / "w.db")
        ev = ops_ai_eval.run_eval(d / "w.db", d / "a.db")
    return hashes, ev["result_sha256"]


def environment():
    pk = {}
    for k in KEYS:
        try:
            pk[k] = md.version(k)
        except md.PackageNotFoundError:
            pk[k] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": pk}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="dev"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    cfg = es.PROFILES[a.profile]
    h1, e1 = build_once(cfg)
    h2, e2 = build_once(cfg)
    diff = sorted(t for t in set(h1) | set(h2) if h1.get(t) != h2.get(t))
    rep = {"profile": a.profile, "tables": len(h1), "identical": not diff and e1 == e2, "differing_tables": diff, "eval_hash_equal": e1 == e2, "table_hashes": h1, "environment": environment()}
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1))
    print(f"{rep['tables']} tables; identical rebuild: {rep['identical']}; eval hash equal: {rep['eval_hash_equal']}; differing: {diff or 'none'}")
    return 0 if rep["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
