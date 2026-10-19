"""Reproducible synthetic workflow acceptance evaluation (not historical benchmarks).

No network, no LLM, no purchases. Prints measured JSON to stdout.
"""
from __future__ import annotations
import hashlib
import json
from .specialist_workflows import execute

CASES = {
    "seasonal_beer": ("ATLAS", "SCRIBE", "BREWMASTER", "SENTINEL", "MERIDIAN",
                      "PULSE", "FORGE", "GUARDIAN", "LUMEN", "NEXUS"),
    "inventory_procurement": ("SENTINEL", "PULSE", "MERIDIAN", "GUARDIAN", "LUMEN"),
    "customer_marketing": ("ECHO", "PULSE", "ATLAS", "SPARK", "GUARDIAN", "LUMEN", "NEXUS"),
}

def evaluate() -> dict:
    cases = []
    for name, expected in CASES.items():
        cid = "eval-" + name
        first = execute(name, correlation_id=cid)
        second = execute(name, correlation_id=cid)
        actual = tuple(h.role for h in first.handoffs)
        record = {
            "workflow": name,
            "handoff_correct": actual == expected,
            "specialist_valid": all(h.status == "OK" and h.evaluation.get("valid") is True for h in first.handoffs),
            "human_review_required": first.approval_required and first.status == "REQUIRES_HUMAN_APPROVAL",
            "no_external_side_effects": first.external_actions == 0,
            "reproducible": first.handoffs == second.handoffs,
            "observed_steps": len(first.handoffs),
            "expected_steps": len(expected),
        }
        cases.append(record)
    measures = ("handoff_correct", "specialist_valid", "human_review_required",
                "no_external_side_effects", "reproducible")
    passed = sum(bool(case[k]) for case in cases for k in measures)
    total = len(cases) * len(measures)
    return {
        "dataset": "synthetic_workflow_acceptance_v1",
        "workflow_count": len(cases),
        "checks_passed": passed,
        "checks_total": total,
        "pass_rate": round(passed / total, 6),
        "cases": cases,
        "note": "Deterministic contract checks only; no real-world model accuracy or production outcomes.",
    }

def main() -> None:
    result = evaluate()
    print(json.dumps(result, sort_keys=True, indent=2))
    assert result["checks_passed"] == result["checks_total"], result

if __name__ == "__main__":
    main()
