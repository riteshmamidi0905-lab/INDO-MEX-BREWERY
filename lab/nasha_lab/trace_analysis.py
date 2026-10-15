"""Why did a model miss required tools? Reads a trace1 JSONL (eval_planners --trace-out) and classifies each missing required tool:
  NEVER_REQUESTED          the model did not ask for it
  UNKNOWN_NAME             the model asked for a tool name that does not exist (e.g. a near-miss spelling)
  REQUESTED_BAD_ARGUMENTS  the right tool was requested but the arguments were refused (INVALID_ARGUMENTS)
  REQUESTED_OTHER_ERROR    requested, refused or failed for another reason
  python -m nasha_lab.trace_analysis TRACE.jsonl [OUT.json]"""
import collections
import json
import sys


def analyse(traces):
    cat = collections.Counter(); unknown = collections.Counter(); never = collections.Counter(); per = []
    for t in traces:
        need = set(t["expected"]["required_tools"]); calls = [c for c in t["tool_calls"] if c["requested_by"] == "planner"]
        ok = {c["tool"] for c in calls if c["ok"]}; asked = {c["tool"] for c in calls}
        for c in calls:
            if c["error_code"] == "UNKNOWN_TOOL": unknown[c["tool"]] += 1
        miss = need - ok; row = dict(id=t["scenario_id"], missing=sorted(miss), passed=t["checks"]["pass"])
        for m in miss:
            if m not in asked and not any(c["tool"] == m for c in t["tool_calls"]):
                k = "NEVER_REQUESTED"; never[m] += 1
            else:
                errs = [c for c in calls if c["tool"] == m]; k = "REQUESTED_BAD_ARGUMENTS" if any(c["error_code"] == "INVALID_ARGUMENTS" for c in errs) else "REQUESTED_OTHER_ERROR"
            if k == "NEVER_REQUESTED" and (unknown and any(u for u in unknown)): pass
            cat[k] += 1
        if miss and unknown and any(c["error_code"] == "UNKNOWN_TOOL" for c in calls): row["asked_unknown_tool"] = True
        per.append(row)
    n_unknown_scen = sum(1 for r in per if r.get("asked_unknown_tool"))
    return dict(n=len(traces), scenarios_with_a_missing_required_tool=sum(1 for r in per if r["missing"]), missing_required_tool_instances=sum(cat.values()), by_cause=dict(cat), never_requested_by_tool=dict(never),
                unknown_tool_names_requested=dict(unknown), scenarios_that_asked_an_unknown_tool=n_unknown_scen, mean_planner_requests=round(sum(len([c for c in t["tool_calls"] if c["requested_by"] == "planner"]) for t in traces) / max(1, len(traces)), 2), per_scenario=per)


if __name__ == "__main__":
    tr = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]; a = analyse(tr)
    if len(sys.argv) > 2: open(sys.argv[2], "w").write(json.dumps(a, indent=1))
    print({k: v for k, v in a.items() if k != "per_scenario"})
