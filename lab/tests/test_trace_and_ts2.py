"""Block 4: per-scenario model trace format (trace1) and the simplified tool presentation (ts2). Scripted client: NOT a language model."""
import json

from nasha_lab import eval_planners as EP, llm_planner as LP, scenarios as S
from nasha_lab.llm import ScriptedClient

REQUIRED_FIELDS = {"trace_format", "scenario_id", "planner", "model", "prompt_version", "tool_schema_version", "requested_tools", "tool_calls", "schema_failures", "retries", "llm_calls", "recommendation", "abstained",
                   "approval_required", "latency_ms", "tokens", "guardrail_intervention", "final_outcome", "expected", "checks"}


def _capture():
    seen = []

    def responder(messages, schema, i):
        seen.append(messages[-1]["content"])
        if "tool_calls" in schema.get("properties", {}): return dict(reasoning_summary="nothing to request", tool_calls=[], done=True)
        return dict(assessment="insufficient evidence collected", reasoning_summary="No tools were called.", action="ESCALATE_INSUFFICIENT_EVIDENCE", abstain=True, requires_human_review=True, claims=[], uncertainties=["no evidence"])
    return seen, ScriptedClient(responder)


def _first(family):
    dev, _h, _a = S.build(); return next(s for s in dev if s.event_family == family)


def test_trace_record_has_every_required_field_and_records_the_model_requests():
    sink = []; EP.TRACE_SINK = sink
    try:
        seen, client = _capture(); sc = _first("INVENTORY")
        row = EP.run_scenario(sc, lambda: LP.LLMPlanner(client, guardrail=True))
    finally: EP.TRACE_SINK = None
    t = sink[0]
    assert REQUIRED_FIELDS <= set(t) and t["trace_format"] == "trace1" and t["scenario_id"] == sc.id
    assert t["tool_schema_version"] == "ts1" and t["prompt_version"] == "p1" and t["planner"] == "llm+guardrail"
    assert t["requested_tools"][0]["tools"] == [] and [c for c in t["tool_calls"] if c["requested_by"] == "planner"] == [] and all("prompt_tokens" in c for c in t["llm_calls"])
    assert t["guardrail_intervention"] is None and t["recommendation"]["action"] == "ESCALATE_INSUFFICIENT_EVIDENCE" and t["approval_required"] is True
    assert row["pass"] is False                                                     # a model that requests no tools fails the required-tools check
    json.dumps(t)                                                                   # serialisable


def test_trace_records_tool_arguments_and_results_for_a_working_planner():
    from nasha_lab import scripted_models as SM
    sink = []; EP.TRACE_SINK = sink
    try: EP.run_scenario(_first("INVENTORY"), lambda: LP.LLMPlanner(SM.rule_model()))
    finally: EP.TRACE_SINK = None
    t = sink[0]; names = [c["tool"] for c in t["tool_calls"]]
    assert "query_inventory" in names and t["tool_calls"][0]["arguments"] and t["tool_calls"][0]["result_summary"] and t["checks"]["pass"] is True


def test_ts2_presents_a_scoped_catalog_with_call_skeletons_and_changes_nothing_else():
    seen, client = _capture(); sink = []; EP.TRACE_SINK = sink
    try: EP.run_scenario(_first("INVENTORY"), lambda: LP.LLMPlanner(client, presentation="ts2"))
    finally: EP.TRACE_SINK = None
    first = seen[0]
    assert "call: " in first and "query_inventory" in first and "get_supplier_proposal" not in first and "assess_policy_ingredient" not in first       # scoped to the event family
    assert "EVENT FIELDS:" in first and sink[0]["tool_schema_version"] == "ts2" and sink[0]["prompt_version"] == "p2"
    seen1, client1 = _capture(); EP.run_scenario(_first("INVENTORY"), lambda: LP.LLMPlanner(client1))
    assert "get_supplier_proposal" in seen1[0] and "call: " not in seen1[0]            # ts1 (the Block 3 default) is untouched


def test_ts2_does_not_touch_permissions_or_scoring():
    assert LP.MODEL_VISIBLE == {LP.T.READ, LP.T.ANALYZE}
    for fam, tools in LP.TOOLS_BY_FAMILY.items():
        assert all(LP.T.TOOLS[n].permission in LP.MODEL_VISIBLE for n in tools)       # the simplified menu never offers DRAFT / MUTATE / EXTERNAL tools
