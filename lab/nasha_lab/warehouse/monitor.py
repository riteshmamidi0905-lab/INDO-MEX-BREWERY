"""Pipeline monitoring: last runs, step timings, partition freshness, quarantine, gate results, lineage."""
import json

from . import db


def report(db_path):
    con = db.connect(db_path)
    q = lambda s: con.execute(s).fetchall()
    out = {
        "runs": q("SELECT run_id, started, finished, status, detail FROM pipeline_runs ORDER BY started DESC LIMIT 5"),
        "status": q("SELECT * FROM warehouse_status") if q("SELECT 1 FROM sqlite_master WHERE name='warehouse_status'") else None,
        "slowest_steps": q("SELECT step, seconds, rows FROM pipeline_steps ORDER BY seconds DESC LIMIT 8"),
        "partitions": q("SELECT tbl, count(*), sum(rows), min(partition), max(partition) FROM load_partitions WHERE status='complete' GROUP BY tbl"),
        "latest_order_date": (q("SELECT max(date) FROM dim_date") or [[None]])[0][0] if q("SELECT 1 FROM sqlite_master WHERE name='dim_date'") else None,
        "quarantined": q("SELECT tbl, count(*) FROM quarantine GROUP BY tbl"),
        "gates_failed": q("SELECT gate, name, severity, observed, expected FROM dq_results WHERE passed=0"),
        "gate_counts": q("SELECT severity, passed, count(*) FROM dq_results GROUP BY 1,2"),
        "lineage_edges": q("SELECT count(*) FROM lineage")[0][0],
    }
    con.close()
    return out


def lineage_markdown(db_path):
    con = db.connect(db_path)
    rows = con.execute("SELECT model, depends_on, kind FROM lineage ORDER BY model, depends_on").fetchall()
    con.close()
    g = {}
    for m, d, k in rows:
        g.setdefault(m, []).append(f"{d} ({k})")
    return "\n".join(f"- `{m}` <- " + ", ".join(v) for m, v in g.items())


if __name__ == "__main__":
    import sys
    print(json.dumps(report(sys.argv[1]), indent=1, default=str))
