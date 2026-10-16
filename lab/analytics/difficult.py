"""Runner for the deliberately difficult SQL cases (analytics/difficult_cases/NN_name/).

Each case: prompt.md + fixture.sql (candidate-facing), trap.sql (tempting wrong answer), solution.sql, expected.json, explanation.md.
SYNTHETIC fixtures. SQLite dialect.
"""
import glob
import json
import os
import sqlite3

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "difficult_cases")


def case_dirs():
    return sorted(glob.glob(os.path.join(HERE, "[0-9][0-9]_*")))


def _rows(con, sql):
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return cols, [list(r) for r in cur.fetchall()]


def run_case(d):
    rd = lambda f: open(os.path.join(d, f), encoding="utf-8").read()
    con = sqlite3.connect(":memory:")
    con.executescript(rd("fixture.sql"))
    sol, trap = _rows(con, rd("solution.sql")), _rows(con, rd("trap.sql"))
    exp = json.load(open(os.path.join(d, "expected.json")))
    return {"case": os.path.basename(d), "expected": exp, "solution": {"columns": sol[0], "rows": sol[1]}, "trap": {"columns": trap[0], "rows": trap[1]}}


def same(rows_a, rows_b, ordered=True, tol=1e-9):
    norm = lambda rs: [[round(v, 9) if isinstance(v, float) else v for v in r] for r in rs]
    a, b = norm(rows_a), norm(rows_b)
    if not ordered:
        a, b = sorted(a, key=repr), sorted(b, key=repr)
    return a == b
