import gzip
import hashlib
import json
import sqlite3

import pandas as pd
import pytest

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import db, gates, ingest, monitor, pipeline

CFG = es.SimConfig(name="wh-test", months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_500, employees=60, open_at_start=3)
TABLES = ["fact_order", "fact_order_line", "fact_return", "fact_waste", "fact_labor_daily", "mart_daily_location", "mart_company_month", "mart_loyalty_cohort", "mart_product_month", "dim_member", "dim_location"]


@pytest.fixture(scope="module")
def src(tmp_path_factory):
    d = tmp_path_factory.mktemp("src")
    es.generate(CFG, d)
    return d


def snap(path):
    con = sqlite3.connect(path)
    out = {}
    for t in TABLES:
        rows = con.execute(f"SELECT * FROM {t} ORDER BY 1,2,3").fetchall()
        out[t] = (len(rows), hashlib.sha256(repr(rows).encode()).hexdigest())
    con.close()
    return out


@pytest.fixture(scope="module")
def clean(src, tmp_path_factory):
    p = tmp_path_factory.mktemp("wh") / "clean.db"
    r = pipeline.run(src, p)
    return p, r


def test_full_load_publishes_and_reconciles(clean, src):
    p, r = clean
    assert r["status"] == "published" and r["blocking_failures"] == 0
    con = db.connect(p)
    m = json.loads((src / "manifest.json").read_text())
    assert con.execute("SELECT count(*) FROM fact_order").fetchone()[0] == m["tables"]["orders"]["rows"]
    assert con.execute("SELECT count(*) FROM fact_order_line").fetchone()[0] == m["tables"]["order_lines"]["rows"]
    failed = con.execute("SELECT name FROM dq_results WHERE passed=0 AND severity='blocking'").fetchall()
    assert failed == []
    assert con.execute("SELECT count(*) FROM dq_results").fetchone()[0] >= 20


def test_rerun_is_a_no_op(clean, src, tmp_path):
    p, _ = clean
    before = snap(p)
    r = pipeline.run(src, p)
    assert r["ingest"]["partitions_loaded"] == 0 and r["ingest"]["rows_loaded"] == 0
    assert r["build"]["rebuilt"] == [] and r["status"] == "published"
    assert snap(p) == before


def test_incremental_arrival_equals_one_shot(clean, src, tmp_path):
    p2 = tmp_path / "inc.db"
    r1 = pipeline.run(src, p2, through="2024-02")
    assert r1["status"] == "published"
    con = db.connect(p2)
    assert con.execute("SELECT max(partition) FROM load_partitions WHERE tbl='orders'").fetchone()[0] == "2024-02"
    n1 = con.execute("SELECT count(*) FROM fact_order").fetchone()[0]
    con.close()
    r2 = pipeline.run(src, p2)
    assert r2["ingest"]["partitions_skipped"] > 0                                       # months 1-2 were not reloaded
    assert r2["build"]["partitions"]["fact_order"] == ["2024-03", "2024-04"]            # only the new months were built
    assert n1 < sqlite3.connect(p2).execute("SELECT count(*) FROM fact_order").fetchone()[0]
    assert snap(p2) == snap(clean[0])


def test_crash_mid_load_recovers_to_the_same_result(clean, src, tmp_path):
    p3 = tmp_path / "crash.db"
    with pytest.raises(ingest.InjectedFailure):
        pipeline.run(src, p3, fail_after_partitions=3)
    con = db.connect(p3)
    assert con.execute("SELECT status FROM pipeline_runs ORDER BY started DESC").fetchone()[0] == "failed"
    con.close()
    r = pipeline.run(src, p3)
    assert r["status"] == "published"
    assert snap(p3) == snap(clean[0])
    con = db.connect(p3)
    assert con.execute("SELECT count(*) FROM (SELECT order_id FROM raw_orders GROUP BY 1 HAVING count(*)>1)").fetchone()[0] == 0


def test_late_correction_reloads_only_the_changed_partition(clean, src, tmp_path):
    import shutil
    d = tmp_path / "src2"
    shutil.copytree(src, d)
    df = pd.read_csv(d / "orders.csv.gz", keep_default_na=False)
    i = df.index[df.ts.str[:7] == "2024-03"][0]
    df.loc[i, ["subtotal_cents", "total_cents"]] = [df.loc[i, "subtotal_cents"] + 100, df.loc[i, "total_cents"] + 100]
    with gzip.open(d / "orders.csv.gz", "wt") as fh:
        df.to_csv(fh, index=False)
    p4 = tmp_path / "late.db"
    shutil.copy(clean[0], p4)
    r = pipeline.run(d, p4)
    assert r["ingest"]["partitions_loaded"] == 1 and r["build"]["partitions"]["fact_order"] == ["2024-03"]
    assert r["status"] == "blocked"                                                  # subtotal no longer equals the line sum in the lines? total==subtotal-discount still holds, so the failing check is lines vs order totals
    con = db.connect(p4)
    names = [n for (n,) in con.execute("SELECT name FROM dq_results WHERE passed=0 AND severity='blocking'")]
    assert any("sum of line gross" in n or "line net" in n for n in names)


def test_contract_violations_are_quarantined_and_duplicates_block_publication(src, tmp_path):
    import shutil
    d = tmp_path / "src3"
    shutil.copytree(src, d)
    df = pd.read_csv(d / "orders.csv.gz", keep_default_na=False)
    df.loc[0, "channel"] = "carrier-pigeon"
    df = pd.concat([df, df.iloc[[5]]], ignore_index=True)                           # duplicate order_id
    with gzip.open(d / "orders.csv.gz", "wt") as fh:
        df.to_csv(fh, index=False)
    r = pipeline.run(d, tmp_path / "bad.db")
    con = db.connect(tmp_path / "bad.db")
    assert con.execute("SELECT count(*) FROM quarantine WHERE reason LIKE 'channel%'").fetchone()[0] == 1
    assert r["status"] == "blocked"
    assert any("duplicate order_id" in n for (n,) in con.execute("SELECT name FROM dq_results WHERE passed=0 AND severity='blocking'"))


def test_reconciliation_detects_tampering_in_the_warehouse(clean, src, tmp_path):
    import shutil
    p = tmp_path / "tamper.db"
    shutil.copy(clean[0], p)
    con = db.connect(p)
    con.execute("DELETE FROM fact_order_line WHERE rowid IN (SELECT rowid FROM fact_order_line LIMIT 1)")
    con.commit()
    res = gates.warehouse_gate(con, "t", src)
    assert any(not ok and sev == "blocking" for _, sev, ok in res)


def test_structural_contract_break_rejects_the_file(src, tmp_path):
    import shutil
    d = tmp_path / "src4"
    shutil.copytree(src, d)
    df = pd.read_csv(d / "shifts.csv.gz").drop(columns=["actual_labor_hours"])
    with gzip.open(d / "shifts.csv.gz", "wt") as fh:
        df.to_csv(fh, index=False)
    from nasha_lab.warehouse.contracts import ContractError
    with pytest.raises(ContractError):
        pipeline.run(d, tmp_path / "s.db")


def test_lineage_and_monitoring(clean):
    p, _ = clean
    rep = monitor.report(p)
    assert rep["lineage_edges"] > 15 and rep["gates_failed"] is not None and rep["status"][0][1] == "published"
    md = monitor.lineage_markdown(p)
    assert "fact_order_line" in md and "stg_order_lines" in md
