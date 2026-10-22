"""Model runner: SQL files with `-- model:`, `-- kind:` and `-- depends:` headers run in dependency order.

kind tables: dropped and rebuilt when any input changed. kind incremental_partition: only month partitions whose input fingerprint changed
are deleted and rebuilt ({PARTS} is replaced by the quoted list). Dimensions are rebuilt only when a dimension source changed; a dimension
rebuild forces a full fact rebuild (surrogate keys may move). Lineage (model -> inputs) is recorded from the headers on every run."""
import hashlib
import re
import time
from pathlib import Path

from . import db
from .ingest import DIMENSIONS, FACTS

MODELS = Path(__file__).with_name("models")
PART_RE = re.compile(r"^\d{4}-\d{2}$")
INCREMENTAL_INPUTS = {"fact_order": ("orders", "order_lines"), "fact_order_line": ("order_lines", "orders")}
REF_TABLES = ("ref_cost_assumptions", "ref_ingredient_cost")


RAW_INDEXES = {"orders": ["order_id", "location_id"], "order_lines": ["order_id"], "returns": ["order_id"], "loyalty_profiles": ["member_id"], "locations": ["location_id"], "menu_items": ["item_id"], "employees": ["location_id"]}


def create_source_views(con):
    for t, cols in RAW_INDEXES.items():                       # created after load: faster inserts, and joins/anti-joins in models and gates stay linear
        for c in cols:
            con.execute(f"CREATE INDEX IF NOT EXISTS ix_raw_{t}_{c} ON raw_{t}({c})")
    for t in DIMENSIONS:
        con.execute(f"DROP VIEW IF EXISTS stg_{t}")
        con.execute(f"CREATE VIEW stg_{t} AS SELECT * FROM raw_{t} WHERE _partition = 'all'")
    for t in FACTS:
        con.execute(f"DROP VIEW IF EXISTS stg_{t}")
        con.execute(f"CREATE VIEW stg_{t} AS SELECT * FROM raw_{t} WHERE _partition IN (SELECT partition FROM load_partitions WHERE tbl = '{t}' AND status = 'complete')")
    con.commit()


def parse_models():
    out = []
    for f in sorted(MODELS.glob("*.sql")):
        txt = f.read_text()
        h = {k: re.search(rf"^-- {k}:\s*(.*)$", txt, re.M) for k in ("model", "kind", "depends")}
        out.append({"file": f.name, "name": h["model"].group(1).strip(), "kind": h["kind"].group(1).strip(), "depends": [x.strip() for x in h["depends"].group(1).split(",") if x.strip()],
                    "creates": re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", txt), "sql": txt})
    return out


def _fp(rows):
    return hashlib.sha256(repr(sorted(rows)).encode()).hexdigest()[:16]


def build(con, run_id, force_full=False):
    con.execute("CREATE TABLE IF NOT EXISTS model_state (model TEXT, partition TEXT, fingerprint TEXT, PRIMARY KEY (model, partition))")
    create_source_views(con)
    models = parse_models()
    lp = con.execute("SELECT tbl, partition, rows, fingerprint, source_sha256 FROM load_partitions WHERE status='complete'").fetchall()
    dims_fp = _fp([r for r in lp if r[0] in DIMENSIONS])
    all_fp = _fp(lp)
    last = {m_: f_ for m_, f_ in con.execute("SELECT model, fingerprint FROM model_state WHERE partition IN ('dims','all')")}
    con.execute("DELETE FROM lineage")
    for m in models:
        for d in m["depends"]:
            for tgt in (m["creates"] or [m["name"]]):
                con.execute("INSERT INTO lineage VALUES (?,?,?,?)", (tgt, d, "source" if d.startswith("stg_") else "model", run_id))
    con.commit()
    summary = {"rebuilt": [], "skipped": [], "partitions": {}}
    if not force_full and last.get("pipeline") == all_fp:
        summary["skipped"] = [m["name"] for m in models]
        return summary
    have_dims = bool(con.execute("SELECT 1 FROM sqlite_master WHERE name='dim_location'").fetchone())
    dims_changed = force_full or not have_dims or last.get("dims") != dims_fp
    for m in models:
        t0 = time.perf_counter()
        name, kind = m["name"], m["kind"]
        if name == "sources":
            continue
        if name == "dimensions":
            if not dims_changed:
                summary["skipped"].append(name)
                continue
            for t in m["creates"]:
                con.execute(f"DROP TABLE IF EXISTS {t}")
            con.executescript(m["sql"])
            con.execute("INSERT OR REPLACE INTO model_state VALUES ('dims','dims',?)", (dims_fp,))
            con.commit()
        elif kind == "incremental_partition":
            a, b = INCREMENTAL_INPUTS[name]
            rows_of = {(t, p): (r, f) for t, p, r, f, s in lp}
            want = {p: f"{rows_of[(a, p)]}|{rows_of.get((b, p), '-')}" for (t, p) in rows_of if t == a}
            done = {} if dims_changed else dict(con.execute("SELECT partition, fingerprint FROM model_state WHERE model=?", (name,)).fetchall())
            if dims_changed and con.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
                con.execute(f"DROP TABLE {name}")
                con.execute("DELETE FROM model_state WHERE model=?", (name,))
            head, _, body = m["sql"].partition("\nINSERT INTO")
            con.executescript(head)
            todo = sorted(p for p in want if done.get(p) != want[p] and PART_RE.match(p))
            gone = sorted(p for p in done if p not in want)
            summary["partitions"][name] = todo
            for p in gone + todo:
                con.execute(f"DELETE FROM {name} WHERE _partition = ?", (p,))
            if todo:
                parts = ",".join(repr(p) for p in todo)
                con.execute("INSERT INTO" + body.replace("{PARTS}", parts))
                con.executemany("INSERT OR REPLACE INTO model_state VALUES (?,?,?)", [(name, p, want[p]) for p in todo])
            con.commit()
        else:
            for t in m["creates"]:
                con.execute(f"DROP TABLE IF EXISTS {t}")
            con.executescript(m["sql"])
            con.commit()
        rows = sum(con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in m["creates"] if t not in REF_TABLES)
        con.execute("INSERT INTO model_runs VALUES (?,?,?,?,?)", (run_id, name, rows, round(time.perf_counter() - t0, 2), ""))
        db.step_log(con, run_id, f"model:{name}", db.now(), time.perf_counter() - t0, rows)
        summary["rebuilt"].append(name)
    con.execute("INSERT OR REPLACE INTO model_state VALUES ('pipeline','all',?)", (all_fp,))
    con.commit()
    return summary
