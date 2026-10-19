import pytest
from nasha_lab.ai_workflows import WORKFLOWS, plan

@pytest.mark.parametrize("name", sorted(WORKFLOWS))
def test_workflow_is_structured_and_nonexecuting(name):
    p = plan(name)
    assert p["scenario"] == "SYNTHETIC"
    assert p["execution"] == "PLAN_ONLY"
    assert p["external_actions"] == 0
    assert p["protected_execution"] == "THE_WEIR_REQUIRED"
    assert p["human_approval"] == "REQUIRED_BEFORE_PROTECTED_ACTION"
    assert len(p["steps"]) >= 5
    for i, step in enumerate(p["steps"]):
        assert step["step"] == i + 1
        assert step["status"] == "NOT_EXECUTED"
        assert step["depends_on"] == ((i,) if i else ())

def test_rejects_unknown_or_non_synthetic_workflows():
    with pytest.raises(ValueError):
        plan("send_real_purchase_order")
    with pytest.raises(ValueError):
        plan("seasonal_beer", synthetic=False)

def test_workflow_security_and_policy_roles():
    assert "GUARDIAN" in [x["role"] for x in plan("seasonal_beer")["steps"]]
    assert "GUARDIAN" in [x["role"] for x in plan("customer_marketing")["steps"]]
    assert "MERIDIAN" in [x["role"] for x in plan("inventory_procurement")["steps"]]
