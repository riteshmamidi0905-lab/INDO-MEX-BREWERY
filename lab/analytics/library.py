"""The advanced-SQL library: files in sql/library/Qnn_*.sql with a metadata header; checks are in tests/test_analytics_sql_library.py."""
import glob
import os
import re

from .metrics import TOKENS

HERE = os.path.dirname(os.path.abspath(__file__))
META = ("id", "title", "question", "technique", "expected_shape", "sqlite_specific")


def load_all():
    out = []
    for path in sorted(glob.glob(os.path.join(HERE, "sql", "library", "Q*.sql"))):
        text = open(path, encoding="utf-8").read()
        meta = {m.group(1): m.group(2).strip() for m in re.finditer(r"^-- (\w+): (.*)$", text, re.M) if m.group(1) in META}
        sql = "\n".join(l for l in text.splitlines() if not l.startswith("--"))
        for k, v in TOKENS.items():
            sql = sql.replace(k, v)
        out.append({**meta, "file": os.path.basename(path), "sql": sql})
    return out


def run(con, qid):
    q = next(q for q in load_all() if q["id"] == qid)
    cur = con.execute(q["sql"])
    return [c[0] for c in cur.description], cur.fetchall()
