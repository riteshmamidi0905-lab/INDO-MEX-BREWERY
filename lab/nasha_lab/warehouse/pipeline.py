"""End to end: ingest -> models -> gates -> publish status, with run bookkeeping."""
import time

from . import build, db, gates, ingest


def run(source, db_path, through=None, fail_after_partitions=None, force_full=False):
    con = db.connect(db_path)
    rid = db.new_run(con, "pipeline")
    t0 = time.perf_counter()
    out = {"run_id": rid}
    try:
        out["ingest"] = ingest.ingest(con, source, through=through, fail_after_partitions=fail_after_partitions, run_id=rid)
        con.execute("DELETE FROM dq_results WHERE gate IN ('raw','warehouse')")
        build.create_source_views(con)
        tg = time.perf_counter()
        res = gates.raw_gate(con, rid)
        if any(sev == "blocking" and not ok for _, sev, ok in res):
            out["build"] = "SKIPPED: raw gate failed; models are not rebuilt and the previous warehouse content is not republished"
            out["gate_seconds"] = round(time.perf_counter() - tg, 1)
            out["status"], out["blocking_failures"], out["warnings"] = gates.publish_status(con, rid, res)
        else:
            tb = time.perf_counter()
            out["build"] = build.build(con, rid, force_full=force_full)
            out["build_seconds"] = round(time.perf_counter() - tb, 1)
            res += gates.warehouse_gate(con, rid, source, through)
            out["gate_seconds"] = round(time.perf_counter() - tg - out["build_seconds"], 1)
            out["status"], out["blocking_failures"], out["warnings"] = gates.publish_status(con, rid, res)
        db.finish_run(con, rid, out["status"], f"blocking={out['blocking_failures']} warnings={out['warnings']}")
    except Exception as e:
        db.finish_run(con, rid, "failed", f"{type(e).__name__}: {e}")
        out["status"], out["error"] = "failed", f"{type(e).__name__}: {e}"
        con.close()
        raise
    out["seconds"] = round(time.perf_counter() - t0, 1)
    con.close()
    return out
