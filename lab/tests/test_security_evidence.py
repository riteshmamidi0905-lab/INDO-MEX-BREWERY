import pytest
from pydantic import ValidationError
from nasha_lab.security_evidence import SecurityProvenance, SecurityScenarioResult, normalize_legacy_failure_cases

def prov():
    return SecurityProvenance(commit_sha="abc",evaluator_version="1.0",measured_at="2026-10-18T00:00:00Z")

def test_pass_requires_actual_behavior_and_evidence():
    with pytest.raises(ValidationError):
        SecurityScenarioResult(scenario_id="x",attack_category="injection",target="tool",
            expected_behavior="deny",actual_behavior=None,decision="PASS",provenance=prov())

def test_legacy_boolean_is_preserved_without_inventing_policy_fields():
    rows=normalize_legacy_failure_cases({"prompt_injection":{"passed":True,"detail":"injection flagged; no action"}},prov())
    r=rows[0]
    assert r.decision=="PASS" and r.policy_decision is None and r.approval_required is None
    assert r.evidence==["injection flagged; no action"]

def test_incomplete_legacy_evidence_requires_review():
    r=normalize_legacy_failure_cases({"old":{"detail":"no recorded verdict"}},prov())[0]
    assert r.decision=="REQUIRES_REVIEW" and r.actual_behavior is None
