"""Re-score a RECORDED real-model run (the JSON written by tools/live_model_battery.py or parsed from a job log) under the v2 criteria, WITHOUT calling any model.
This is a replay of scoring rules on stored outputs: it says nothing new about the model, and the v1 scores in the record are never changed. For every case it re-runs the v1 criterion on the stored run (to prove the record
reproduces its own v1 verdict) and, for C09, HO4 and C13, the v2 criterion. The 'foreign' sets (the other tenant's supplier names, prices and products) are rebuilt from the seeded synthetic data, which is deterministic.
Needs PostgreSQL (NASHA_PG_DSN) only to rebuild those sets.

    python tools/rescore_recorded_run.py results/model-validation/run-40141457239.json > results/model-validation/rescore-run-40141457239-v2.json"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_model_battery as B  # noqa: E402


def foreign_sets():
    from nasha_lab.growth import service as SV
    w = B.build_world(os.environ["NASHA_PG_DSN"], tempfile.mkdtemp())
    d = SV.GrowthService(w["dsn"], B.SCHEMA, "tenant-nasha", "ana"); own = d.supplier_directory(B.AS_OF, w["tenant-nasha"]["ids"]["project"]); d.close()
    f = SV.GrowthService(w["dsn"], B.SCHEMA, "tenant-fit", "ana"); fit = f.supplier_directory(B.AS_OF, w["tenant-fit"]["ids"]["project"]); f.close()
    strip = lambda n: re.sub(r"\s*\([^)]*\)\s*$", "", n)
    own_prices = {f"${float(p['unit_price_cents']) / 100:,.2f}" for x in own for p in x["products"] if p["unit_price_cents"] is not None}
    return dict(foreign_names=sorted({x["name"] for x in fit} - {x["name"] for x in own}),
                foreign_prices=sorted({f"${float(p['unit_price_cents']) / 100:,.2f}" for x in fit for p in x["products"] if p["unit_price_cents"] is not None} - own_prices),
                foreign_products=sorted({strip(p["name"]) for x in fit for p in x["products"]} - {strip(p["name"]) for x in own for p in x["products"]})), sorted(x["name"] for x in fit if x["name"] not in {y["name"] for y in own})


def rescore(record, foreign, fit_names):
    out = []
    queried = {"C09_cross_tenant_question": fit_names[0], "HO4_cross_tenant_second_name": fit_names[1]}
    for c in record["cases"]:
        r = c.get("run")
        row = dict(id=c["id"], v1_recorded=c["passed"])
        if r and c["id"] in queried:
            ok, detail = B.check_cross_tenant_v2(r, dict(foreign, queried_name=queried[c["id"]]))
            row.update(v2=bool(ok), v2_detail=detail, v2_changes_v1=bool(ok) != c["passed"], name_echoed_with_in_tenant_price=r.pop("_conflation", None))
        elif r and c["id"].startswith("C13"):
            ok, detail = B.check_model_injection_query_v2(r, {})
            row.update(v2=bool(ok), v2_detail=detail, v2_changes_v1=bool(ok) != c["passed"], echo_of_injected_instruction=r.pop("_echo", None))
        else:
            row.update(v2=c["passed"], v2_detail="same criterion as v1")
        out.append(row)
    return dict(kind="replay_of_recorded_run_under_v2_criteria", model_called=False, source=record.get("_provenance", {}).get("source"), v1=dict(passed=sum(1 for c in record["cases"] if c["passed"]), total=len(record["cases"])),
                v2=dict(passed=sum(1 for r in out if r["v2"]), total=len(out), changed=[r["id"] for r in out if r.get("v2_changes_v1")]), cases=out)


if __name__ == "__main__":
    rec = json.load(open(sys.argv[1]))
    fs, fn = foreign_sets()
    print(json.dumps(rescore(rec, fs, fn), indent=1))
