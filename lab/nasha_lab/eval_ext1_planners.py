"""Run a planner on the EXTERNALIZED / INDEPENDENT-STYLE EVAL v1 scenarios (ext1) and report headline vs rule-gap probes vs metamorphic relations.
  python -m nasha_lab.eval_ext1_planners deterministic OUT.json        (any key of eval_planners.FACTORIES)"""
import json
import sys

from . import eval_planners as EP, scenarios_ext as X


def run(factory, label, scenarios=None):
    scs = scenarios or X.build_ext1(); rows = [EP.run_scenario(sc, factory) for sc in scs]
    head = [r for r in rows if r.get("attack") != "rule_gap_probe"]; probes = [r for r in rows if r.get("attack") == "rule_gap_probe"]
    byid = {r["id"]: r for r in rows}; rel = []
    for k in sorted({r["id"].split("-")[2] for r in rows if "-meta" in r["id"]}):
        base = byid.get(f"EXT-INV-{k}-base")
        for tag in ("site", "noise"):
            v = byid.get(f"EXT-INV-{k}-{tag}")
            if base and v: rel.append(dict(relation="same_outcome_" + tag, base=base["id"], variant=v["id"], holds=base["action"] == v["action"]))
        f = byid.get(f"EXT-INV-{k}-flip")
        if base and f: rel.append(dict(relation="flip_changes_outcome", base=base["id"], variant=f["id"], holds=base["action"] != f["action"]))
    return dict(planner=label, eval="EXTERNALIZED / INDEPENDENT-STYLE EVAL v1 (planner scenarios)", independence="structural; same author", n=len(rows), headline=EP.aggregate(head), probes=EP.aggregate(probes) if probes else None,
                by_family={f: EP.aggregate([r for r in rows if r["family"] == f]) for f in sorted({r["family"] for r in rows})}, relations=dict(n=len(rel), hold=sum(1 for x in rel if x["holds"]), detail=rel),
                failures=[dict(id=r["id"], family=r["family"], action=r["action"], error=r["error"]) for r in rows if not r["pass"]], rows=rows)


if __name__ == "__main__":
    name = sys.argv[1]; res = run(EP.FACTORIES[name], name)
    if len(sys.argv) > 2: open(sys.argv[2], "w").write(json.dumps(res, indent=1, default=str))
    h = res["headline"]; print(name, "n", res["n"], "headline pass", h["pass_rate"]["k"], "/", h["pass_rate"]["n"], "| probes", (res["probes"] or {}).get("pass_rate", {}).get("k"), "/", (res["probes"] or {}).get("pass_rate", {}).get("n"), "| relations", res["relations"]["hold"], "/", res["relations"]["n"])
    for f, a in res["by_family"].items(): print(f"  {f:28s} {a['pass_rate']['k']}/{a['pass_rate']['n']} action_ok {a['correct_action']['k']}/{a['correct_action']['n']} required {a['required_tools']['k']}/{a['required_tools']['n']}")
    for f in res["failures"][:14]: print("   FAIL", f)
