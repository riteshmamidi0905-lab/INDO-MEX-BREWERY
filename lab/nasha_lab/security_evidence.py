"""Provider-neutral security/red-team evidence contract."""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

SecurityDecision = Literal["PASS","FAIL","REQUIRES_REVIEW"]

class SecurityProvenance(BaseModel):
    commit_sha: str
    evaluator_version: str
    measured_at: datetime
    environment: str = "controlled-offline"

class SecurityScenarioResult(BaseModel):
    scenario_id: str
    attack_category: str
    target: str
    expected_behavior: str
    actual_behavior: str | None = None
    policy_decision: str | None = None
    approval_required: bool | None = None
    evidence: list[str] = Field(default_factory=list)
    decision: SecurityDecision
    provenance: SecurityProvenance

    def model_post_init(self, __context):
        if self.decision in ("PASS","FAIL") and not self.actual_behavior:
            raise ValueError("measured security verdict requires actual_behavior")
        if self.decision == "PASS" and not self.evidence:
            raise ValueError("PASS requires evidence")

def normalize_legacy_failure_cases(cases: dict, provenance: SecurityProvenance) -> list[SecurityScenarioResult]:
    """Normalize only facts historical failure tests actually recorded; unknown fields stay unknown."""
    out=[]
    for scenario_id, row in cases.items():
        if not isinstance(row,dict) or not isinstance(row.get("passed"),bool):
            decision="REQUIRES_REVIEW"; actual=None; evidence=[]
        else:
            decision="PASS" if row["passed"] else "FAIL"
            actual=row.get("detail") or ("legacy scenario passed" if row["passed"] else "legacy scenario failed")
            evidence=[row["detail"]] if row.get("detail") else [f"legacy boolean verdict={row['passed']}"]
        out.append(SecurityScenarioResult(
            scenario_id=scenario_id, attack_category="legacy_failure_injection", target="NASHA controlled environment",
            expected_behavior="scenario-specific historical assertion", actual_behavior=actual,
            policy_decision=None, approval_required=None, evidence=evidence, decision=decision, provenance=provenance))
    return out
