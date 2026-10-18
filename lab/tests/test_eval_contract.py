import pytest
from pydantic import ValidationError
from nasha_lab.eval_contract import EvaluationResult, Metric

def metric(**overrides):
    d=dict(name="task_success",status="MEASURED",value=1.0,numerator=10,denominator=10,
           sample_count=10,unit="rate",direction="HIGHER_IS_BETTER",
           method="deterministic assertion",source="eval/golden.jsonl")
    d.update(overrides); return Metric(**d)

def provenance():
    return dict(benchmark="operations-golden",dataset_version="v1",evaluator_version="1.0",
                measured_at="2026-10-18T00:00:00Z",commit_sha="abc123")

def test_measured_metric_requires_value():
    with pytest.raises(ValidationError): metric(value=None)

def test_unavailable_metric_cannot_fake_zero():
    with pytest.raises(ValidationError): metric(status="UNAVAILABLE",value=0.0)

def test_not_applicable_metric_cannot_fake_success():
    with pytest.raises(ValidationError): metric(status="NOT_APPLICABLE",value=1.0)

def test_unavailable_metric_preserves_none():
    m=metric(status="UNAVAILABLE",value=None,numerator=None,denominator=None,sample_count=None)
    assert m.value is None and m.status=="UNAVAILABLE"

def test_result_preserves_truth_boundary_and_provenance():
    r=EvaluationResult(workflow="operations_copilot",evaluation="golden-v1",
        dataset="synthetic NASHA incidents",split="heldout",synthetic=True,
        measurement_scope="offline deterministic evaluation",provenance=provenance(),
        metrics=[metric()],limitations=["No production traffic or user-adoption evidence."])
    assert r.synthetic is True
    assert r.metric("task_success").denominator==10
    assert r.provenance.commit_sha=="abc123"
    assert "production traffic" in r.limitations[0]
