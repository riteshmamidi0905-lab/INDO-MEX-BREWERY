"""Incremental, idempotent ingestion of the simulator's gzip CSVs into raw_* tables.

Dimensions (small) are fully refreshed inside one transaction. Facts are loaded by month partition: pass 1 fingerprints every partition
(row count plus a checksum of a numeric column) without loading anything; a partition is (re)loaded only if it is new or its fingerprint
changed (a late correction). Rows are written with _partition and the partition becomes visible to models only when load_partitions says
'complete', so a crash mid-partition leaves no visible partial data, and a rerun deletes and reloads it. Contract violations are quarantined.
"""
import hashlib
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import db
from .contracts import CONTRACTS, SQL_TYPE, ContractError, check_chunk

DIMENSIONS = ["locations", "menu_items", "suppliers", "promotions", "loyalty_profiles", "employees"]
FACTS = ["orders", "order_lines", "returns", "inventory_counts", "waste_events", "quality_events", "shifts", "brew_batches"]
CHUNK = 300_000
CHECKSUM_COL = {"orders": "total_cents", "order_lines": "unit_price_cents", "returns": "refund_cents", "inventory_counts": "qty", "waste_events": "qty_kg",
                "quality_events": None, "shifts": "actual_labor_hours", "brew_batches": "yield_liters"}


class InjectedFailure(RuntimeError):
    pass


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _create_raw(con, table):
    cols = ", ".join(f'"{c}" {SQL_TYPE[t.rstrip("?")]}' for c, t in CONTRACTS[table]["cols"].items())
    con.execute(f'CREATE TABLE IF NOT EXISTS raw_{table} ({cols}, _partition TEXT, _run_id TEXT)')
    if CONTRACTS[table]["partition"]:
        con.execute(f"CREATE INDEX IF NOT EXISTS ix_raw_{table}_part ON raw_{table}(_partition)")


def _read(path, chunk=CHUNK):
    return pd.read_csv(path, chunksize=chunk, dtype=str, keep_default_na=False, na_values=[])


def _order_partition_map(source):
    """order_id -> month partition, as ordered boundaries (order ids are chronological; verified, else a dict fallback)."""
    ids, months = [], []
    for ch in pd.read_csv(Path(source) / "orders.csv.gz", usecols=["order_id", "ts"], chunksize=CHUNK, dtype=str):
        ids.append(ch.order_id.str[1:].astype("int64").to_numpy())
        months.append(ch.ts.str[:7].to_numpy())
    ids, months = np.concatenate(ids), np.concatenate(months)
    return ids, months


def _partition_of(table, df, ids_sorted, months_sorted, col):
    if col == "ts":
        return df["ts"].str[:7]
    if col == "order_id":
        n = df["order_id"].str[1:].astype("int64").to_numpy()
        pos = np.searchsorted(ids_sorted, n)
        pos = np.clip(pos, 0, len(ids_sorted) - 1)
        ok = ids_sorted[pos] == n
        return pd.Series(np.where(ok, months_sorted[pos], "orphan"), index=df.index)
    return df[col].str[:7]


def _check_header(path, table):
    cols = list(pd.read_csv(path, nrows=0).columns)
    if cols != list(CONTRACTS[table]["cols"]):
        raise ContractError(f"{table}: columns {cols} differ from the contract {list(CONTRACTS[table]['cols'])}")


def _fingerprints(source, table, ids, months):
    cfg = CONTRACTS[table]
    cs = CHECKSUM_COL[table]
    fp = {}
    for ch in _read(Path(source) / f"{table}.csv.gz"):
        part = _partition_of(table, ch, ids, months, cfg["partition"])
        vals = pd.to_numeric(ch[cs], errors="coerce").fillna(0) if cs else pd.Series(0.0, index=ch.index)
        g = pd.DataFrame({"p": part.to_numpy(), "v": vals.to_numpy()}).groupby("p")["v"].agg(["count", "sum"])
        for p, r in g.iterrows():
            a = fp.setdefault(p, [0, 0.0])
            a[0] += int(r["count"]); a[1] += float(r["sum"])
    return {p: (a[0], f"{a[1]:.2f}") for p, a in fp.items()}


def ingest(con, source, through=None, fail_after_partitions=None, run_id=None):
    """Load `source` into `con`. through='YYYY-MM' ignores later partitions (simulates data that has not arrived yet).
    fail_after_partitions=N raises InjectedFailure after N partitions are committed (crash-recovery tests). Returns a stats dict."""
    source = Path(source)
    rid = run_id or db.new_run(con, "ingest")
    stats = {"run_id": rid, "partitions_loaded": 0, "partitions_skipped": 0, "rows_loaded": 0, "quarantined": 0, "tables": {}}
    t_all = time.perf_counter()
    for t in DIMENSIONS + FACTS:
        _create_raw(con, t)
    con.commit()
    done = 0
    # --- dimensions: full refresh in one transaction
    for t in DIMENSIONS:
        t0 = time.perf_counter(); sha = _sha(source / f"{t}.csv.gz")
        prev = con.execute("SELECT source_sha256 FROM load_partitions WHERE tbl=? AND partition='all' AND status='complete'", (t,)).fetchone()
        if prev and prev[0] == sha:
            stats["partitions_skipped"] += 1
            continue
        con.execute("BEGIN")
        con.execute(f"DELETE FROM raw_{t}")
        rows = 0
        for ch in _read(source / f"{t}.csv.gz"):
            clean, q = check_chunk(t, ch)
            con.executemany("INSERT INTO quarantine VALUES (?,?,?,?)", [(rid, t, k, r) for k, r in q])
            stats["quarantined"] += len(q)
            _insert(con, t, clean, "all", rid)
            rows += len(clean)
        con.execute("INSERT OR REPLACE INTO load_partitions VALUES (?,?,?,?,?,?,?,?)", (t, "all", rows, str(rows), sha, db.now(), rid, "complete"))
        con.execute("COMMIT")
        stats["partitions_loaded"] += 1; stats["rows_loaded"] += rows
        db.step_log(con, rid, f"ingest:{t}", db.now(), time.perf_counter() - t0, rows)
    # --- facts by month partition
    ids, months = _order_partition_map(source)
    order = np.argsort(ids, kind="stable")
    ids, months = ids[order], months[order]
    for t in FACTS:
        t0 = time.perf_counter()
        _check_header(source / f"{t}.csv.gz", t)
        sha = _sha(source / f"{t}.csv.gz")
        fps = _fingerprints(source, t, ids, months)
        if through:
            fps = {p: v for p, v in fps.items() if p <= through}
        have = {p: (r, f) for p, r, f in con.execute("SELECT partition, rows, fingerprint FROM load_partitions WHERE tbl=? AND status='complete'", (t,))}
        todo = sorted(p for p, v in fps.items() if have.get(p) != v)
        stats["partitions_skipped"] += len(fps) - len(todo)
        if not todo:
            continue
        for p in todo:                                         # invalidate first: a changed/new partition is not visible until complete
            con.execute("DELETE FROM load_partitions WHERE tbl=? AND partition=?", (t, p))
            con.execute(f"DELETE FROM raw_{t} WHERE _partition=?", (p,))
        con.commit()
        loaded = {p: 0 for p in todo}
        wanted = set(todo)
        for ch in _read(source / f"{t}.csv.gz"):
            part = _partition_of(t, ch, ids, months, CONTRACTS[t]["partition"])
            for p in sorted(set(part.unique()) & wanted):
                sub = ch[part.to_numpy() == p]
                clean, q = check_chunk(t, sub)
                con.executemany("INSERT INTO quarantine VALUES (?,?,?,?)", [(rid, t, k, r) for k, r in q])
                stats["quarantined"] += len(q)
                _insert(con, t, clean, p, rid)
                loaded[p] += len(clean)
            con.commit()
        for p in todo:
            con.execute("INSERT OR REPLACE INTO load_partitions VALUES (?,?,?,?,?,?,?,?)", (t, p, fps[p][0], fps[p][1], sha, db.now(), rid, "complete"))
            con.commit()
            stats["partitions_loaded"] += 1; stats["rows_loaded"] += loaded[p]
            done += 1
            if fail_after_partitions is not None and done >= fail_after_partitions:
                raise InjectedFailure(f"injected failure after {done} partitions")
        db.step_log(con, rid, f"ingest:{t}", db.now(), time.perf_counter() - t0, sum(loaded.values()), detail=f"{len(todo)} partitions")
        stats["tables"][t] = sum(loaded.values())
    stats["seconds"] = round(time.perf_counter() - t_all, 1)
    return stats


def _insert(con, table, df, partition, rid):
    if df.empty:
        return
    cols = list(CONTRACTS[table]["cols"])
    df = df[cols].astype(object).where(df[cols].notna(), None)
    q = f'INSERT INTO raw_{table} ({",".join(chr(34) + c + chr(34) for c in cols)}, _partition, _run_id) VALUES ({",".join("?" * (len(cols) + 2))})'
    con.executemany(q, [tuple(r) + (partition, rid) for r in df.itertuples(index=False, name=None)])
