"""Evidence-first multi-role workflow planner for synthetic NASHA business scenarios.

This module generates structured handoff plans, not autonomous tool execution.
Protected calls MUST be dispatched through THE WEIR; no direct execution path exists here.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .ai_team import BY_NAME

WORKFLOWS = {
    "seasonal_beer": (
        ("SCRIBE", "research"), ("BREWMASTER", "brewing_plan"),
        ("SENTINEL", "inventory_review"), ("MERIDIAN", "procurement_draft"),
        ("PULSE", "financial_scenario"), ("FORGE", "food_pairings"),
        ("GUARDIAN", "quality_review"), ("ATLAS", "founder_brief"),
    ),
    "inventory_procurement": (
        ("SENTINEL", "investigate_anomaly"), ("SCRIBE", "source_verification"),
        ("MERIDIAN", "supplier_comparison"), ("GUARDIAN", "quality_review"),
        ("NEXUS", "human_approval_checkpoint"),
    ),
    "customer_marketing": (
        ("ECHO", "synthetic_sentiment"), ("PULSE", "insight_validation"),
        ("SPARK", "campaign_draft"), ("GUARDIAN", "claims_review"),
        ("NEXUS", "human_approval_checkpoint"),
    ),
}

@dataclass(frozen=True)
class Handoff:
    step: int
    role: str
    task: str
    depends_on: tuple[int, ...]
    status: str

def plan(workflow: str, *, synthetic: bool = True) -> dict:
    if not synthetic:
        raise ValueError("only synthetic/offline scenario planning is supported")
    if workflow not in WORKFLOWS:
        raise ValueError("unsupported workflow")
    steps = []
    for index, (name, task) in enumerate(WORKFLOWS[workflow]):
        assert name in BY_NAME
        steps.append(Handoff(index + 1, name, task, (index,) if index else (),
                             "NOT_EXECUTED"))
    return {
        "workflow": workflow, "scenario": "SYNTHETIC",
        "execution": "PLAN_ONLY",
        "external_actions": 0,
        "protected_execution": "THE_WEIR_REQUIRED",
        "human_approval": "REQUIRED_BEFORE_PROTECTED_ACTION",
        "steps": [asdict(s) for s in steps],
    }
