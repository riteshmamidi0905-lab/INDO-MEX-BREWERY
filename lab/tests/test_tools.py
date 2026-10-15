import json, re
import pytest
from nasha_lab import knowledge as K, mcp_server, tools as T


def call(world, ctx, name, **a): return T.execute(world, name, a, ctx)


def test_permission_classes_are_assigned_and_external_tools_are_not_exposed():
    perms = {n: t.permission for n, t in T.TOOLS.items()}
    assert perms["query_inventory"] == T.READ and perms["assess_inventory_risk"] == T.ANALYZE and perms["draft_purchase_recommendation"] == T.DRAFT
    assert perms["adjust_inventory_record"] == T.MUTATE and perms["place_purchase_order"] == T.EXTERNAL and perms["contact_supplier"] == T.EXTERNAL
    assert not T.TOOLS["place_purchase_order"].exposed and "place_purchase_order" not in {t["name"] for t in T.tool_catalog()}


def test_mcp_surface_contains_only_read_analyze_draft():
    assert set(mcp_server.MCP_TOOLS) <= set(T.TOOLS)
    assert {T.TOOLS[n].permission for n in mcp_server.MCP_TOOLS} <= {T.READ, T.ANALYZE, T.DRAFT}
    assert len(mcp_server.MCP_TOOLS) <= 10


@pytest.mark.parametrize("name", ["place_purchase_order", "contact_supplier"])
def test_external_actions_always_refused_even_with_approval(world, name):
    r = T.execute(world, name, {}, T.ToolContext(run_id="r", approval={"grant": "anything"}))
    assert not r["ok"] and r["error"]["code"] == "FORBIDDEN_EXTERNAL_ACTION"


def test_mutation_requires_a_signed_grant_bound_to_run_tool_and_arguments(world):
    from nasha_lab import identity as ID
    au = ID.Authority.dev(); who = ID.Identity("founder", "FOUNDER")
    a = dict(location_id="L01", ingredient="goat", qty_delta=1.0, reason="approved one kilogram adjustment")
    grant = au.issue_grant(who, "r", [dict(tool="adjust_inventory_record", args=a, args_hash=T.args_hash("adjust_inventory_record", a))])
    mk = lambda run, g: T.ToolContext(run_id=run, approval={"grant": g} if g else None, authority=au)
    assert T.execute(world, "adjust_inventory_record", a, mk("r", None))["error"]["code"] == "APPROVAL_REQUIRED"
    assert T.execute(world, "adjust_inventory_record", dict(a, qty_delta=99.0), mk("r", grant))["error"]["code"] == "APPROVAL_REQUIRED"
    assert T.execute(world, "adjust_inventory_record", a, mk("other", grant))["error"]["code"] == "APPROVAL_REQUIRED"
    assert T.execute(world, "adjust_inventory_record", a, mk("r", grant))["ok"]
    assert T.execute(world, "adjust_inventory_record", a, mk("r", grant))["error"]["code"] == "APPROVAL_REQUIRED"      # replay
    assert world.q("SELECT COUNT(*) n FROM inventory_movements WHERE kind='ADJUSTMENT'")[0]["n"] == 1


@pytest.mark.parametrize("name,args", [("query_inventory", dict(location_id="L9", ingredient="goat")), ("query_inventory", dict(location_id="L01", ingredient="g")),
                                       ("get_quality_finding", dict(finding_id=0)), ("search_nasha_knowledge", dict(query="x")), ("draft_purchase_recommendation", dict(location_id="L01"))])
def test_invalid_arguments_return_structured_errors(world, ctx, name, args):
    r = call(world, ctx, name, **args)
    assert not r["ok"] and r["error"]["code"] == "INVALID_ARGUMENTS" and r["data"] is None


def test_unknown_tool_and_unknown_records(world, ctx):
    assert call(world, ctx, "drop_database")["error"]["code"] == "UNKNOWN_TOOL"
    assert call(world, ctx, "query_inventory", location_id="L01", ingredient="unobtainium")["error"]["code"] == "NOT_FOUND"
    assert call(world, ctx, "get_quality_finding", finding_id=999999)["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("fault,code", [("error", "UPSTREAM_FAILURE"), ("malformed", "MALFORMED_RESULT"), ("timeout", "TIMEOUT")])
def test_fault_hooks_become_typed_errors(world, kb, fault, code):
    world.faults["query_inventory"] = fault
    r = T.execute(world, "query_inventory", dict(location_id="L01", ingredient="goat"), T.ToolContext(kb=kb, timeout_s=0.05))
    assert not r["ok"] and r["error"]["code"] == code


def test_scenario_a1_low_cover_has_a_draftable_quantity(world, ctx):
    r = call(world, ctx, "assess_inventory_risk", location_id="L01", ingredient="goat")["data"]
    assert r["shortfall_before_lead_time"] and r["days_of_cover"] < r["lead_time_days"] and r["recommended_qty_kg"] >= 10


def test_scenario_a2_stale_and_quarantined_count_is_flagged(world, ctx):
    r = call(world, ctx, "query_inventory", location_id="L02", ingredient="paneer")["data"]
    assert "STALE_COUNT" in r["data_flags"] and "NEWER_COUNT_QUARANTINED" in r["data_flags"] and "L02:2026-04-27:paneer" in r["newer_counts_quarantined"]


def test_scenario_a3_count_variance_is_detected(world, ctx):
    r = call(world, ctx, "assess_inventory_risk", location_id="L03", ingredient="cauliflower")["data"]
    assert r["count_variance_ratio"] > 2 and any("recount" in x for x in r["reasons"])


def test_open_purchase_order_arriving_in_time_suppresses_shortfall(world, ctx):
    world.con.execute("UPDATE purchase_orders SET expected_date='2026-04-30' WHERE po_id='PO-0001'")
    r = call(world, ctx, "assess_inventory_risk", location_id="L01", ingredient="goat")["data"]
    assert not r["shortfall_before_lead_time"] and r["open_po_qty_arriving_in_time"] == 20


def test_lineage_of_duplicate_order_keeps_the_original(world, ctx):
    key = world.q("SELECT key FROM dq_finding WHERE rule='duplicate_order' LIMIT 1")[0]["key"]
    d = call(world, ctx, "get_lineage", table="orders", key=key)["data"]
    assert d["quarantined"] and "duplicate_order" in d["reasons"] and d["in_modeled_layer"]


def test_draft_rules(world, ctx):
    ok = dict(location_id="L01", ingredient="goat", qty_kg=15, supplier_id="S02", rationale="cover below lead time by evidence", evidence_ids=["E1"])
    assert call(world, ctx, "draft_purchase_recommendation", **ok)["data"]["status"] == "DRAFT_NOT_SUBMITTED"
    assert call(world, ctx, "draft_purchase_recommendation", **dict(ok, qty_kg=1))["error"]["code"] == "REJECTED"            # below minimum
    assert call(world, ctx, "draft_purchase_recommendation", **dict(ok, supplier_id="S01"))["error"]["code"] == "REJECTED"   # does not supply goat
    assert call(world, ctx, "draft_purchase_recommendation", **dict(ok, ingredient="cauliflower", supplier_id="S03", qty_kg=20))["error"]["code"] == "REJECTED"   # supplier ON_HOLD
    assert call(world, ctx, "draft_purchase_recommendation", **dict(ok, evidence_ids=[]))["error"]["code"] == "INVALID_ARGUMENTS"
    assert world.q("SELECT COUNT(*) n FROM purchase_orders WHERE status<>'OPEN' AND status<>'RECEIVED'")[0]["n"] == 0      # a draft never creates a purchase order


def test_policy_screening_verdicts(world, ctx):
    f = lambda t, s, st: call(world, ctx, "assess_policy_ingredient", ingredient_text=t, declared_source=s, spec_sheet_status=st)["data"]["verdict"]
    assert f("tortilla blend with beef tallow", "beef tallow", "ON_FILE") == "PROHIBITED"
    assert f("chicken bouillon base, natural flavors", "animal source unspecified", "MISSING") == "REQUIRES_REVIEW"
    assert f("chicken bouillon base", "animal source unspecified", "ON_FILE") == "REQUIRES_REVIEW"          # a file is not enough: the source must be established
    assert f("vegetable shortening", "vegetable oil (supplier statement on file)", "ON_FILE") == "CLEARED_PENDING_HUMAN"
    assert f("vegetable shortening", "vegetable oil", "MISSING") == "REQUIRES_REVIEW"
    assert f("cilantro", "farm", "ON_FILE") == "NO_POLICY_SIGNAL"
    assert f("chamoy sauce", "fruit", "ON_FILE") == "NO_POLICY_SIGNAL"      # word boundary: 'ham' inside 'chamoy'


def test_hidden_derivative_terms_come_from_the_dietary_specification():
    text = open(K.ROOT + "/food/DIETARY-POLICY-AND-INGREDIENT-SPEC.md", encoding="utf-8").read().lower()
    generic = {"base", "fining", "flavour base", "flavor base"}
    for t in T.HIDDEN_TERMS:
        if t not in generic: assert t.split()[0] in text, t


def test_trace_redacts_secrets(world, kb):
    from nasha_lab.trace import Store
    s = Store(); tr = s.trace("r1", "q1")
    r = T.execute(world, "get_supplier_status", dict(supplier_id="S01"), T.ToolContext(run_id="r1", kb=kb, trace=tr))
    assert r["ok"]
    assert T.redact({"api_key": "sk-123", "nested": {"token": "abc", "ok": 1}}) == {"api_key": "[REDACTED]", "nested": {"token": "[REDACTED]", "ok": 1}}
    assert "sk-123" not in json.dumps(s.events("r1"))


def test_every_tool_call_is_traced_with_request_id(world, kb):
    from nasha_lab.trace import Store
    s = Store(); tr = s.trace("r2", "REQ-9")
    T.execute(world, "query_inventory", dict(location_id="L01", ingredient="goat"), T.ToolContext(run_id="r2", kb=kb, trace=tr))
    T.execute(world, "query_inventory", dict(location_id="BAD", ingredient="goat"), T.ToolContext(run_id="r2", kb=kb, trace=tr))
    ev = s.events("r2")
    assert [e["kind"] for e in ev] == ["tool_call", "tool_error"] and all(e["request_id"] == "REQ-9" for e in ev) and ev[0]["permission"] == T.READ
