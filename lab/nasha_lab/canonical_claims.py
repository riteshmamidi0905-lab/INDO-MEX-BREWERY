"""Single canonical source for the quantitative claims made in public documents.

Every value is DERIVED from a committed result file or from the code (never typed by hand).
  python -m nasha_lab.canonical_claims          -> results/canonical_claims.json
  python -m nasha_lab.canonical_claims --check  -> exit 1 if the committed file is stale
tests/test_claim_consistency.py then requires each public document to contain the rendered claim strings.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "canonical_claims.json"


def _j(name): return json.loads((RES / name).read_text())


def _k(o, key): return o["overall"][key]["k"], o["overall"][key]["n"]


def wrong_silent_no_action(rows):
    """Metric definition: the planner's final action is NO_ACTION although the scenario required action (action_ok is False)."""
    return sum(1 for r in rows if r["action"] == "NO_ACTION" and r["action_ok"] is False)


def compute():
    from . import generator, mcp_server, tools as T
    det, q15, q15g = _j("planner_deterministic.json"), _j("planner_qwen1.5b_run2_raw.json"), _j("planner_qwen1.5b_run2_guardrail.json")
    q7, q7g = _j("planner_qwen7b_raw.json"), _j("planner_qwen7b_guardrail.json")
    ts2, ts2g = _j("planner_qwen1.5b_ts2_raw.json"), _j("planner_qwen1.5b_ts2_guardrail.json")
    ret = {r["retriever"].split(" ")[0]: r for r in _j("rag2_retrieval_ci.json")["table"]}
    ev = _j("eval_v1.json")["injected"]["per_rule"]
    perfect = sorted(k for k, v in ev.items() if v["recall"] == 1.0 and v["precision"] == 1.0)
    missed = sorted(k for k, v in ev.items() if v["recall"] < 1.0)
    mut = _j("mutation_block4.json"); fi = _j("failure_injection.json")
    return {
        "tools": {"registered": len(T.TOOLS), "exposed": sum(1 for t in T.TOOLS.values() if t.exposed), "mcp": len(mcp_server.MCP_TOOLS)},
        "planner": {
            "deterministic_pass": "%d/%d" % _k(det, "pass_rate"),
            "qwen1.5b_raw_pass": "%d/%d" % _k(q15, "pass_rate"), "qwen1.5b_guardrail_pass": "%d/%d" % _k(q15g, "pass_rate"),
            "qwen7b_raw_pass": "%d/%d" % _k(q7, "pass_rate"), "qwen7b_guardrail_pass": "%d/%d" % _k(q7g, "pass_rate"),
            "qwen1.5b_ts1_required_tools": "%d/%d" % _k(q15, "required_tools"), "qwen1.5b_ts2_required_tools": "%d/%d" % _k(ts2, "required_tools"),
            "wrong_silent_no_action_ts1_raw": wrong_silent_no_action(q15["rows"]),
            "wrong_silent_no_action_ts1_guardrail": wrong_silent_no_action(q15g["rows"]),
            "wrong_silent_no_action_ts2_raw": wrong_silent_no_action(ts2["rows"]),
            "wrong_silent_no_action_ts2_guardrail": wrong_silent_no_action(ts2g["rows"]),
        },
        "retrieval_mrr": {k: ret[k]["mrr"] for k in ("bm25", "minilm", "hybrid_minilm", "static_neural")},
        "data_quality": {"injected_defect_types": len(generator.DEFECT_TYPES), "eval_rule_keys": len(ev),
                         "detected_precision_recall_1": len(perfect), "undetected": missed,
                         "clean_dataset_findings": _j("eval_v1.json")["clean_dataset_findings"]},
        "mutation": {"killed": mut["killed"], "valid": mut["valid"]},
        "failure_injection_scenarios": len(fi),
    }


def main(argv):
    text = json.dumps(compute(), indent=1, sort_keys=True) + "\n"
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text() != text:
            print("canonical_claims.json is stale: run python -m nasha_lab.canonical_claims"); return 1
        print("canonical claims fresh"); return 0
    OUT.write_text(text); print(text); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
