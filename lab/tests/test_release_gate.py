import json
from nasha_lab import release_gate

def _write_results(root, *, planner=1.0, mrr=.91, dq_precision=1.0, dq_recall=1.0, evaluator_version=None):
    d=root/"results"; d.mkdir(parents=True, exist_ok=True)
    dq={"injected":{"per_rule":{"a":{"precision":dq_precision,"recall":dq_recall},"known_gap":{"precision":None,"recall":0.0}}}}
    if evaluator_version is not None: dq["evaluator_version"]=evaluator_version
    (d/"eval_v1.json").write_text(json.dumps(dq))
    (d/"planner_deterministic.json").write_text(json.dumps({"overall":{"pass_rate":{"rate":planner}}}))
    (d/"rag2_retrieval.json").write_text(json.dumps({"retrieval":{"bm25":{"all":{"ALL":{"mrr":mrr}}}}}))

def good_security():
    return {"timeout":{"passed":True},"injection":{"passed":True},"permission":{"passed":True}}

def test_valid_historical_evidence_passes(tmp_path):
    _write_results(tmp_path)
    r=release_gate.evaluate(tmp_path, failure_runner=good_security)
    assert r["decision"]=="PASS" and r["portfolio_release_ready"]

def test_security_failure_fails(tmp_path):
    _write_results(tmp_path)
    r=release_gate.evaluate(tmp_path, failure_runner=lambda:{"timeout":{"passed":True},"permission":{"passed":False}})
    assert r["decision"]=="FAIL"

def test_incomplete_security_evidence_requires_review(tmp_path):
    _write_results(tmp_path)
    r=release_gate.evaluate(tmp_path, failure_runner=lambda:{"timeout":{"detail":"no verdict"}})
    assert r["decision"]=="REQUIRES_REVIEW" and not r["portfolio_release_ready"]

def test_missing_evidence_requires_review(tmp_path):
    (tmp_path/"results").mkdir()
    r=release_gate.evaluate(tmp_path, failure_runner=good_security)
    assert r["decision"]=="REQUIRES_REVIEW"

def test_malformed_metric_requires_review(tmp_path):
    _write_results(tmp_path)
    p=tmp_path/"results"/"rag2_retrieval.json"
    p.write_text(json.dumps({"retrieval":{"bm25":{"all":{"ALL":{"mrr":"not-a-number"}}}}}))
    r=release_gate.evaluate(tmp_path, failure_runner=good_security)
    assert r["decision"]=="REQUIRES_REVIEW"

def test_null_metric_requires_review(tmp_path):
    _write_results(tmp_path)
    p=tmp_path/"results"/"rag2_retrieval.json"
    p.write_text(json.dumps({"retrieval":{"bm25":{"all":{"ALL":{"mrr":None}}}}}))
    assert release_gate.evaluate(tmp_path, failure_runner=good_security)["decision"]=="REQUIRES_REVIEW"

def test_unsupported_evaluator_version_requires_review(tmp_path):
    _write_results(tmp_path, evaluator_version="99")
    r=release_gate.evaluate(tmp_path, failure_runner=good_security)
    assert r["decision"]=="REQUIRES_REVIEW"

def test_supported_evaluator_version_passes(tmp_path):
    _write_results(tmp_path, evaluator_version="1.0")
    assert release_gate.evaluate(tmp_path, failure_runner=good_security)["decision"]=="PASS"

def test_retrieval_regression_fails(tmp_path):
    _write_results(tmp_path,mrr=.79)
    assert release_gate.evaluate(tmp_path, failure_runner=good_security)["decision"]=="FAIL"

def test_dq_regression_fails(tmp_path):
    _write_results(tmp_path,dq_recall=.89)
    assert release_gate.evaluate(tmp_path, failure_runner=good_security)["decision"]=="FAIL"

def test_planner_regression_fails(tmp_path):
    _write_results(tmp_path,planner=.98)
    assert release_gate.evaluate(tmp_path, failure_runner=good_security)["decision"]=="FAIL"

def test_improvement_and_unchanged_results_pass(tmp_path):
    _write_results(tmp_path,planner=1.0,mrr=.95)
    assert release_gate.evaluate(tmp_path, failure_runner=good_security)["decision"]=="PASS"
    _write_results(tmp_path/"second",planner=1.0,mrr=.95)
    assert release_gate.evaluate(tmp_path/"second", failure_runner=good_security)["decision"]=="PASS"


def test_dq_malformed_recall_requires_review(tmp_path):
    _write_results(tmp_path)
    p = tmp_path / "results" / "eval_v1.json"
    d = json.loads(p.read_text())
    d["injected"]["per_rule"]["a"]["recall"] = "not-a-number"
    p.write_text(json.dumps(d))
    r = release_gate.evaluate(tmp_path, failure_runner=good_security)
    assert r["decision"] == "REQUIRES_REVIEW"
    assert not r["portfolio_release_ready"]


def test_nonfinite_metric_requires_review(tmp_path):
    _write_results(tmp_path, planner=float("nan"))
    r = release_gate.evaluate(tmp_path, failure_runner=good_security)
    assert r["decision"] == "REQUIRES_REVIEW"
    assert not r["portfolio_release_ready"]


def test_measured_failure_dominates_malformed_evidence(tmp_path):
    _write_results(tmp_path, planner=.5)
    p = tmp_path / "results" / "eval_v1.json"
    d = json.loads(p.read_text())
    d["injected"]["per_rule"]["a"]["recall"] = "bad"
    p.write_text(json.dumps(d))
    assert release_gate.evaluate(tmp_path, failure_runner=good_security)["decision"] == "FAIL"
