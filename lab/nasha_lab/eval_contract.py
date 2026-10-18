"""Versioned, provider-neutral evaluation result contract.

Raw historical result files remain immutable evidence. Adapters normalize them into
this schema so release policy can compare unlike workflows without inventing
missing measurements.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

MetricStatus = Literal["MEASURED", "UNAVAILABLE", "NOT_APPLICABLE"]
Direction = Literal["HIGHER_IS_BETTER", "LOWER_IS_BETTER", "INFORMATIONAL"]


class Metric(BaseModel):
    name: str
    status: MetricStatus
    value: float | None = None
    numerator: int | None = None
    denominator: int | None = None
    sample_count: int | None = None
    unit: str
    direction: Direction
    method: str
    source: str

    def model_post_init(self, __context):
        if self.status == "MEASURED" and self.value is None:
            raise ValueError("MEASURED metric requires value")
        if self.status != "MEASURED" and self.value is not None:
            raise ValueError("unavailable/not-applicable metric cannot carry a value")
        if self.numerator is not None and self.denominator is None:
            raise ValueError("numerator requires denominator")
        if self.denominator is not None and self.denominator < 0:
            raise ValueError("denominator cannot be negative")


class Provenance(BaseModel):
    benchmark: str
    dataset_version: str
    evaluator_version: str
    measured_at: datetime
    commit_sha: str
    model: str | None = None
    provider: str | None = None


class EvaluationResult(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    workflow: str
    evaluation: str
    dataset: str
    split: str
    synthetic: bool
    measurement_scope: str
    provenance: Provenance
    metrics: list[Metric]
    limitations: list[str] = Field(default_factory=list)

    def metric(self, name: str) -> Metric:
        return next(m for m in self.metrics if m.name == name)
