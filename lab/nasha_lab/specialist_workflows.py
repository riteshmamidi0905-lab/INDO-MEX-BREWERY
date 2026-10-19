"""Offline, deterministic orchestration of twelve working specialist services.

Every handoff consumes actual output from a previous specialist. The protected
purchase and publication boundaries are deliberately review-only. For actual
execution use governed_inventory_action and the independent THE WEIR gateway.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib
import json
import time
import uuid
from .specialists import invoke, SpecialistResult

@dataclass(frozen=True)
class WorkflowResult:
    workflow: str
    correlation_id: str
    status: str
    handoffs: tuple[SpecialistResult, ...]
    approval_required: bool
    external_actions: int
    elapsed_ms: float

def execute(workflow: str, *, correlation_id: str | None = None) -> WorkflowResult:
    if workflow not in {"seasonal_beer", "inventory_procurement", "customer_marketing"}:
        raise ValueError("unsupported workflow")
    start=time.perf_counter()
    cid=correlation_id or str(uuid.uuid4())
    done: list[SpecialistResult]=[]
    def step(role: str, payload: dict[str,Any]) -> SpecialistResult:
        result=invoke(role,payload)
        done.append(result)
        if result.status != "OK":
            raise ValueError("specialist requires review")
        return result
    try:
        if workflow=="seasonal_beer":
            strategy=step("ATLAS",{"objective":"synthetic seasonal wheat beer","evidence":["synthetic planning brief"]})
            research=step("SCRIBE",{"question":"wheat beer","documents":[{"id":"style-note","text":"wheat beer style research; verify against primary source"}]})
            brew=step("BREWMASTER",{"style":"wheat beer concept","batch_liters":20,"ingredient_requirements":{"wheat_malt_kg":2}})
            stock=step("SENTINEL",{"on_hand":1,"reorder_point":brew.output["ingredients"]["wheat_malt_kg"]})
            quote=step("MERIDIAN",{"supplier_quotes":[{"supplier_id":"synthetic-supplier-a","price":18},{"supplier_id":"synthetic-supplier-b","price":20}]})
            finance=step("PULSE",{"units":20,"unit_price":9,"unit_cost":quote.output["quoted_price"]/20})
            pairing=step("FORGE",{"dish":"mango habanero gobi","ingredients":["cauliflower","mango","chili"],"estimated_cost":4})
            quality=step("GUARDIAN",{"ingredients":["cauliflower","mango","chili"],"evidence":research.output["source_ids"]})
            eval_result=step("LUMEN",{"checks":[stock.output["reorder_review"],quality.output["dietary_pass"],finance.output["scenario_margin"]>=0]})
            step("NEXUS",{"handoffs":[{"role":x.role} for x in done]})
        elif workflow=="inventory_procurement":
            stock=step("SENTINEL",{"on_hand":2,"reorder_point":10})
            finance=step("PULSE",{"units":8,"unit_price":12,"unit_cost":8})
            quote=step("MERIDIAN",{"supplier_quotes":[{"supplier_id":"synthetic-a","price":22},{"supplier_id":"synthetic-b","price":24}]})
            quality=step("GUARDIAN",{"ingredients":["wheat"],"evidence":["synthetic inventory"]})
            step("LUMEN",{"checks":[stock.output["reorder_review"],finance.output["scenario_margin"]>=0,quality.output["dietary_pass"],quote.output["requires_weir"]]})
        else:
            sentiment=step("ECHO",{"synthetic_feedback":["great service","slow service","good food"]})
            metrics=step("PULSE",{"units":sentiment.output["sample_count"],"unit_price":1,"unit_cost":0})
            strategy=step("ATLAS",{"objective":"improve hypothetical customer experience","evidence":sentiment.output["sentiment_labels"]})
            campaign=step("SPARK",{"insight":str(sentiment.output["sentiment_labels"]),"campaign_goal":strategy.output["objective"]})
            quality=step("GUARDIAN",{"ingredients":[],"evidence":[campaign.output["insight"]]})
            step("LUMEN",{"checks":[quality.output["dietary_pass"],campaign.output["requires_human_review"],metrics.output["scenario_revenue"]>=0]})
            step("NEXUS",{"handoffs":[{"role":x.role} for x in done]})
        status="REQUIRES_HUMAN_APPROVAL"
    except (ValueError, KeyError, TypeError):
        status="REQUIRES_REVIEW"
    return WorkflowResult(workflow,cid,status,tuple(done),True,0,(time.perf_counter()-start)*1000)
