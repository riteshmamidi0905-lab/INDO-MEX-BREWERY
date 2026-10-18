import json

from nasha_lab import release_gate


def _write_results(root, *, planner=1.0, mrr=0.91):
    d = root / "results"
    d.mkdir()
    (d / "eval_v1.json").write_text(json.dumps({"injected":{"per_rule":{
        "a":{"precision":1.0,"recall":1.0},
        "known_gap":{"precision":None,"recall":0.0}}}}))
    (d / "planner_deterministic.json").write_text(json.dumps({"overall":{"pass_rate":{"rate":planner}}}))
    (d / "rag2_retrieval.json").write_text(json.dumps({"retrieval":{"bm25":{"all":{"ALL":{"mrr":mrr}}}}}))


def test_release_gate_passes_only_with_complete_failure_suite(tmp_path):
    _write_results(tmp_path)
    failures = {"timeout":{"passed":True}, "injection":{"passed":True}, "permission":{"passed":True}}
    report = release_gate.evaluate(tmp_path, failure_runner=lambda: failures)
    assert report["portfolio_release_ready"] is True
    assert all(x["passed"] for x in report["checks"])


def test_release_gate_fails_closed_on_any_failure_injection_regression(tmp_path):
    _write_results(tmp_path)
    failures = {"timeout":{"passed":True}, "permission":{"passed":False}}
    report = release_gate.evaluate(tmp_path, failure_runner=lambda: failures)
    assert report["portfolio_release_ready"] is False
    check = next(x for x in report["checks"] if x["name"] == "failure_injection")
    assert check["measured"] == 0.5


def test_release_gate_fails_on_retrieval_regression(tmp_path):
    _write_results(tmp_path, mrr=0.79)
    report = release_gate.evaluate(tmp_path, failure_runner=lambda: {"x":{"passed":True}})
    assert report["portfolio_release_ready"] is False
    assert next(x for x in report["checks"] if x["name"] == "retrieval_bm25")["passed"] is False
