"""Runner for the deliberately difficult SQL cases (analytics/difficult_cases/NN_name/).

PUBLIC material per case: prompt.md, fixture.sql, trap.sql. The answer keys (solution.sql, expected.json, explanation.md) are NOT in this
repository; they live in a private directory named by the env var NASHA_PRIVATE_KEYS (layout: <dir>/<case>/{solution.sql,expected.json,explanation.md}).
The public sha256 manifest (difficult_cases/KEYS-MANIFEST.sha256) lets the owner prove the private files are the ones that were removed.
SYNTHETIC fixtures. SQLite dialect.
"""
import glob
import hashlib
import json
import os
import sqlite3

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "difficult_cases")
ENV = "NASHA_PRIVATE_KEYS"
KEY_FILES = ("solution.sql", "expected.json", "explanation.md")


def case_dirs():
    return sorted(glob.glob(os.path.join(HERE, "[0-9][0-9]_*")))


def keys_dir():
    """Private key directory if the env var is set and exists, else None."""
    p = os.environ.get(ENV)
    return p if p and os.path.isdir(p) else None


def manifest():
    """{relative path: sha256} from the public manifest."""
    out = {}
    with open(os.path.join(HERE, "KEYS-MANIFEST.sha256"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                h, p = line.split(None, 1)
                out[p.strip()] = h
    return out


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _rows(con, sql):
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return cols, [list(r) for r in cur.fetchall()]


def _loaded(d):
    con = sqlite3.connect(":memory:")
    con.executescript(open(os.path.join(d, "fixture.sql"), encoding="utf-8").read())
    return con


def run_trap(d):
    """Public: run the candidate-facing trap query on the fixture. Returns (columns, rows)."""
    return _rows(_loaded(d), open(os.path.join(d, "trap.sql"), encoding="utf-8").read())


def run_case(d, kd):
    """Needs the private key directory `kd`. Returns the solution, the trap and the expected answer."""
    kc = os.path.join(kd, os.path.basename(d))
    con = _loaded(d)
    sol = _rows(con, open(os.path.join(kc, "solution.sql"), encoding="utf-8").read())
    trap = _rows(con, open(os.path.join(d, "trap.sql"), encoding="utf-8").read())
    exp = json.load(open(os.path.join(kc, "expected.json")))
    return {"case": os.path.basename(d), "expected": exp, "solution": {"columns": sol[0], "rows": sol[1]}, "trap": {"columns": trap[0], "rows": trap[1]}}


def same(rows_a, rows_b, ordered=True, tol=1e-9):
    norm = lambda rs: [[round(v, 9) if isinstance(v, float) else v for v in r] for r in rs]
    a, b = norm(rows_a), norm(rows_b)
    if not ordered:
        a, b = sorted(a, key=repr), sorted(b, key=repr)
    return a == b
