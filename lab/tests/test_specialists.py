import pytest
from nasha_lab.specialists import invoke
from nasha_lab.ai_team import BY_NAME

CASES = {
 "ATLAS":{"objective":"seasonal menu","evidence":["synthetic demand scenario"]},
 "BREWMASTER":{"style":"hefeweizen","batch_liters":20,"ingredient_requirements":{"wheat":10}},
 "FORGE":{"dish":"mango habanero gobi","ingredients":["cauliflower","mango"],"estimated_cost":4.2},
 "SENTINEL":{"on_hand":2,"reorder_point":10},
 "MERIDIAN":{"supplier_quotes":[{"supplier_id":"synthetic-b","price":20},{"supplier_id":"synthetic-a","price":19}]},
 "PULSE":{"units":10,"unit_price":12,"unit_cost":7},
 "ECHO":{"synthetic_feedback":["great food","slow service","fine"]},
 "SPARK":{"insight":"synthetic sentiment","campaign_goal":"awareness"},
 "NEXUS":{"handoffs":[{"role":"SENTINEL"},{"role":"PULSE"}]},
 "GUARDIAN":{"ingredients":["chicken","rice"],"evidence":["D-54"]},
 "SCRIBE":{"question":"hefeweizen wheat","documents":[{"id":"bjcp-synthetic","text":"hefeweizen wheat style"}]},
 "LUMEN":{"checks":[True,True,True]},
}

@pytest.mark.parametrize("role",sorted(CASES))
def test_every_role_executes_independent_contract(role):
    r=invoke(role,CASES[role])
    assert r.role==role and r.status=="OK" and r.evaluation["valid"]
    assert r.sources == BY_NAME[role].sources
    assert r.output and r.evaluation["contract"]=="deterministic_v1"
    assert invoke(role,CASES[role])==r

@pytest.mark.parametrize("role",sorted(CASES))
def test_every_role_rejects_missing_evidence(role):
    r=invoke(role,{})
    assert r.status=="REQUIRES_REVIEW"
    assert not r.evaluation["valid"]

def test_no_beef_or_pork_in_menu_and_guardian():
    assert invoke("FORGE",{"dish":"taco","ingredients":["beef"],"estimated_cost":5}).status=="REQUIRES_REVIEW"
    assert invoke("GUARDIAN",{"ingredients":["pork"],"evidence":["D-54"]}).output["dietary_pass"] is False

def test_procurement_is_never_automatically_executed():
    r=invoke("MERIDIAN",CASES["MERIDIAN"])
    assert r.requires_approval and r.output["status"]=="DRAFT_ONLY"
    assert r.output["requires_weir"]

def test_customer_feedback_is_explicitly_synthetic():
    r=invoke("ECHO",CASES["ECHO"])
    assert r.output["data"]=="SYNTHETIC" and r.output["sample_count"]==3

def test_evaluation_does_not_hide_failure():
    assert invoke("LUMEN",{"checks":[True,False]}).output["status"]=="FAIL"
