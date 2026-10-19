"""Typed, deterministic specialist services for NASHA's synthetic business concept.

Twelve individually invocable roles. These are offline analytical services,
NOT twelve autonomous LLMs or permission-granting agents. Protected execution
is not exposed here. Missing evidence fails closed rather than being invented.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json
from .ai_team import BY_NAME

@dataclass(frozen=True)
class SpecialistResult:
    role: str
    status: str
    output: dict[str, Any]
    sources: tuple[str, ...]
    requires_approval: bool
    evaluation: dict[str, Any]

def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0 <= value < 1e12):
        raise ValueError("nonnegative finite numeric input required")
    return float(value)

def _required(d: Mapping[str, Any], *keys: str) -> None:
    if not isinstance(d, Mapping) or any(k not in d for k in keys):
        raise ValueError("required structured evidence missing")

def _run(role: str, d: Mapping[str, Any]) -> dict[str, Any]:
    if role == "ATLAS":
        _required(d, "objective", "evidence")
        return {"objective": str(d["objective"]), "evidence_count": len(d["evidence"]),
                "decision": "FOUNDER_REVIEW_REQUIRED"}
    if role == "BREWMASTER":
        _required(d, "style", "batch_liters", "ingredient_requirements")
        return {"style": str(d["style"]), "batch_liters": _number(d["batch_liters"]),
                "ingredients": dict(d["ingredient_requirements"]), "status": "UNBREWED_PLAN"}
    if role == "FORGE":
        _required(d, "dish", "ingredients", "estimated_cost")
        ingredients = [str(x).lower() for x in d["ingredients"]]
        if any(x in {"beef", "pork", "bacon", "ham"} for x in ingredients):
            raise ValueError("NASHA dietary policy violation")
        return {"dish": str(d["dish"]), "estimated_cost": _number(d["estimated_cost"]),
                "dietary_check": "NO_BEEF_NO_PORK", "status": "UNTESTED_MENU_PROPOSAL"}
    if role == "SENTINEL":
        _required(d, "on_hand", "reorder_point")
        qty, threshold = _number(d["on_hand"]), _number(d["reorder_point"])
        return {"shortfall": max(0.0, threshold - qty), "reorder_review": qty < threshold}
    if role == "MERIDIAN":
        _required(d, "supplier_quotes")
        quotes = d["supplier_quotes"]
        if not isinstance(quotes, list) or not quotes:
            raise ValueError("supplier quotes missing")
        offers = sorted(((_number(q["price"]), str(q["supplier_id"])) for q in quotes))
        return {"recommended_supplier_id": offers[0][1], "quoted_price": offers[0][0],
                "status": "DRAFT_ONLY", "requires_weir": True}
    if role == "PULSE":
        _required(d, "units", "unit_price", "unit_cost")
        units, price, cost = (_number(d[k]) for k in ("units", "unit_price", "unit_cost"))
        return {"scenario_revenue": round(units * price, 2),
                "scenario_cost": round(units * cost, 2),
                "scenario_margin": round(units * (price - cost), 2)}
    if role == "ECHO":
        _required(d, "synthetic_feedback")
        feedback = d["synthetic_feedback"]
        if not isinstance(feedback, list):
            raise ValueError("feedback must be a list")
        positives = ("good", "great", "love", "excellent")
        negatives = ("bad", "slow", "poor", "dislike")
        labels = ["positive" if any(w in str(s).lower().split() for w in positives)
                  else "negative" if any(w in str(s).lower().split() for w in negatives)
                  else "neutral" for s in feedback]
        return {"sentiment_labels": labels, "sample_count": len(labels), "data": "SYNTHETIC"}
    if role == "SPARK":
        _required(d, "insight", "campaign_goal")
        return {"campaign_goal": str(d["campaign_goal"]), "insight": str(d["insight"]),
                "status": "DRAFT_NOT_PUBLISHED", "requires_human_review": True}
    if role == "NEXUS":
        _required(d, "handoffs")
        steps = d["handoffs"]
        if not isinstance(steps, list) or not steps:
            raise ValueError("handoff evidence missing")
        return {"completed_handoffs": len(steps), "roles": [str(x["role"]) for x in steps],
                "status": "FOUNDER_REVIEW_REQUIRED"}
    if role == "GUARDIAN":
        _required(d, "ingredients", "evidence")
        prohibited = {"beef", "pork", "bacon", "ham"}
        found = sorted(prohibited.intersection(str(x).lower() for x in d["ingredients"]))
        return {"dietary_pass": not found, "violations": found,
                "evidence_present": bool(d["evidence"])}
    if role == "SCRIBE":
        _required(d, "question", "documents")
        docs = d["documents"]
        if not isinstance(docs, list) or not docs:
            raise ValueError("no documents for grounded retrieval")
        terms = set(str(d["question"]).lower().split())
        matches = sorted(((len(terms.intersection(str(doc["text"]).lower().split())),
                           str(doc["id"])) for doc in docs), key=lambda x: (-x[0], x[1]))
        return {"source_ids": [i for score, i in matches if score > 0],
                "status": "EVIDENCE_FOUND" if matches[0][0] > 0 else "INSUFFICIENT_EVIDENCE"}
    if role == "LUMEN":
        _required(d, "checks")
        checks = d["checks"]
        if not isinstance(checks, list) or not checks:
            raise ValueError("evaluation checks missing")
        passed = sum(x is True for x in checks)
        return {"passed": passed, "total": len(checks),
                "status": "PASS" if passed == len(checks) else "FAIL"}
    raise ValueError("unknown specialist")

def invoke(role: str, payload: Mapping[str, Any]) -> SpecialistResult:
    if role not in BY_NAME:
        raise ValueError("unknown NASHA role")
    try:
        output = _run(role, payload)
        status = "OK"
    except (ValueError, TypeError, KeyError, OverflowError):
        output, status = {"error": "INVALID_OR_INSUFFICIENT_EVIDENCE"}, "REQUIRES_REVIEW"
    return SpecialistResult(role, status, output, tuple(BY_NAME[role].sources),
                            role in {"ATLAS", "BREWMASTER", "FORGE", "MERIDIAN", "SPARK", "NEXUS"},
                            {"contract": "deterministic_v1", "valid": status == "OK"})
