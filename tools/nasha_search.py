#!/usr/bin/env python3
"""Local full-text search over canonical NASHA sources (SQLite FTS5). One index, rebuilt on demand; the index is a cache (git-ignored), never a source of truth.
  python3 tools/nasha_search.py build
  python3 tools/nasha_search.py q "D-66 logo" [--decisions|--evidence|--food|--beer|--dir PREFIX]   ranked passages with file:line (filters restrict the path)
  python3 tools/nasha_search.py decision D-74            exact decision lookup from docs/decisions/DECISIONS.md
  python3 tools/nasha_search.py selftest"""
import os, re, sqlite3, sys, tempfile
DB = ".cache/nasha-fts.sqlite"
SKIP = {".git", "node_modules", "dist", ".cache", "__pycache__", ".baseline", "results"}
EXT = (".md", ".csv", ".txt", ".py", ".json")
def files(root="."):
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in SKIP]
        for f in fs:
            if f.endswith(EXT) and os.path.getsize(os.path.join(d, f)) < 600_000: yield os.path.join(d, f)
def build(root=".", db=DB):
    os.makedirs(os.path.dirname(db) or ".", exist_ok=True)
    if os.path.exists(db): os.remove(db)
    c = sqlite3.connect(db); c.execute("create virtual table t using fts5(path unindexed, line unindexed, body, tokenize='porter unicode61')")
    n = 0
    for p in files(root):
        try: lines = open(p, encoding="utf-8").read().splitlines()
        except Exception: continue
        for i in range(0, len(lines), 6):   # 6-line passages
            body = "\n".join(lines[i:i + 6]).strip()
            if body: c.execute("insert into t values(?,?,?)", (os.path.relpath(p, root), i + 1, body)); n += 1
    c.commit(); return n
def q(term, db=DB, k=8, under=None):
    """under: restrict to a path prefix (e.g. 'docs/decisions', 'research', 'food'). An exact ID like 'V-57' or 'D-66' is matched literally."""
    c = sqlite3.connect(db); safe = " ".join('"' + w.replace('"', "") + '"' for w in term.split())
    sql = "select path,line,snippet(t,2,'[',']','…',24) from t where t match ?" + (" and path like ?" if under else "") + " order by rank limit ?"
    return c.execute(sql, (safe, f"{under}%", k) if under else (safe, k)).fetchall()
def decision(did, p="docs/decisions/DECISIONS.md"):
    txt = open(p, encoding="utf-8").read(); m = re.search(rf"(^|\n)(#+ *|\*\*|\| *){re.escape(did)}\b.*?(?=\n(#+ *|\*\*|\| *)D-\d+|\Z)", txt, re.S)
    return m.group(0).strip() if m else None
def selftest():
    d = tempfile.mkdtemp(); open(f"{d}/a.md", "w").write("# Decisions\nD-66 logo protection is absolute\n"); open(f"{d}/b.md", "w").write("other things about chicken 65")
    assert build(d, f"{d}/x.sqlite") == 2; r = q("logo protection", f"{d}/x.sqlite"); assert r and r[0][0] == "a.md"
    os.makedirs(f"{d}/sub"); open(f"{d}/sub/c.md", "w").write("logo notes in sub dir")
    build(d, f"{d}/y.sqlite"); r = q("logo", f"{d}/y.sqlite", under="sub"); assert r and all(x[0].startswith("sub") for x in r)
    print("selftest ok: build + ranked query + path filter")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["selftest"]: selftest()
    elif a[:1] == ["build"]: print("indexed passages:", build())
    elif a[:1] == ["q"]:
        if not os.path.exists(DB): build()
        under = None; rest = a[1:]
        for flag, pref in (("--decisions", "docs/decisions"), ("--evidence", "research"), ("--food", "food"), ("--beer", "beer")):
            if flag in rest: under = pref; rest = [x for x in rest if x != flag]
        if "--dir" in rest: i = rest.index("--dir"); under = rest[i + 1]; rest = rest[:i] + rest[i + 2:]
        for r in q(" ".join(rest), under=under): print(f"{r[0]}:{r[1]}  {r[2]!r}")
    elif a[:1] == ["decision"]: print(decision(a[1]) or "NOT FOUND")
    else: print(__doc__)
