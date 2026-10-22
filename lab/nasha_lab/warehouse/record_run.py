"""Write a small, committable summary of a full run (counts, timings, gate results, reconciliation) from a source manifest and a warehouse."""
import datetime as dt
import json
import os
import sqlite3
import sys


def summarize(source, db_path):
    m = json.load(open(os.path.join(source, "manifest.json")))
    con = sqlite3.connect(db_path)
    f = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    runs = con.execute("SELECT started, finished, status FROM pipeline_runs WHERE step='pipeline' ORDER BY started").fetchall()
    first = next((r for r in runs if r[2] in ("published", "blocked")), runs[0])
    steps = [(s, round(sec, 1), rows) for s, sec, rows in con.execute("SELECT step, seconds, rows FROM pipeline_steps WHERE run_id=(SELECT run_id FROM pipeline_runs WHERE step='pipeline' ORDER BY started LIMIT 1) AND seconds>=1 ORDER BY rowid")]
    gates = con.execute("SELECT gate, severity, passed, count(*) FROM dq_results GROUP BY 1,2,3").fetchall()
    tot = con.execute("SELECT sum(orders), sum(net_cents), sum(gross_cents), sum(discount_cents), sum(cogs_cents), sum(labor_cost_cents), sum(waste_cost_cents), sum(member_orders) FROM mart_daily_location").fetchone()
    return {
        "synthetic": True,
        "disclaimer": "SYNTHETIC DATA. Placeholder prices, wages and costs; uncalibrated volumes. Not NASHA results: NASHA is a concept and no business operates.",
        "source": {"profile": m["config"]["name"], "seed": m["config"]["seed"], "locations": m["locations"], "scenario_days": m["scenario_days"], "orders": m["summary"]["orders"], "order_lines": m["summary"]["order_lines"],
                   "loyalty_profiles": m["tables"]["loyalty_profiles"]["rows"], "employees": m["tables"]["employees"]["rows"], "generation_seconds": m["generation_seconds"],
                   "orders_above_hourly_capacity_after_queueing": m["summary"]["orders_still_above_site_hourly_capacity_after_queueing"], "compressed_bytes": sum(t["bytes"] for t in m["tables"].values()), "numpy": m["numpy"], "pandas": m["pandas"]},
        "first_full_run": {"seconds": round((f(first[1]) - f(first[0])).total_seconds(), 1), "status": first[2], "steps_over_1s": steps},
        "gates": [{"gate": g, "severity": s, "passed": bool(p), "count": c} for g, s, p, c in gates],
        "warehouse_totals_placeholder_cents": dict(zip(["orders", "net", "gross", "discount", "cogs", "labor", "waste", "member_orders"], tot)),
        "warehouse_db_bytes": os.path.getsize(db_path),
    }


if __name__ == "__main__":
    print(json.dumps(summarize(sys.argv[1], sys.argv[2]), indent=1))
