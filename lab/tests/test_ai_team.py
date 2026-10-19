from nasha_lab.ai_team import ROLES, BY_NAME

def test_twelve_distinct_roles_and_no_agent_sprawl():
    assert len(ROLES) == len(BY_NAME) == 12
    assert sum(r.kind == "LangGraph workflow" for r in ROLES) == 1
    assert all(r.purpose and r.inputs and r.outputs and r.sources and r.metrics for r in ROLES)

def test_dependency_graph_is_closed_and_acyclic():
    def visit(name, stack, done):
        assert name not in stack, "cyclic role dependencies"
        if name in done:
            return
        for dep in BY_NAME[name].depends_on:
            assert dep in BY_NAME
            visit(dep, stack | {name}, done)
        done.add(name)
    done = set()
    for name in BY_NAME:
        visit(name, set(), done)

def test_protected_roles_require_human_authorization():
    for name in ("MERIDIAN", "SPARK", "NEXUS"):
        r = BY_NAME[name]
        assert "Human" in r.human_approval or "human" in r.human_approval or "Founder" in r.human_approval
        assert "THE WEIR" in r.failure

def test_roles_do_not_claim_unimplemented_tools():
    for name in ("ECHO", "SPARK"):
        assert BY_NAME[name].kind in ("planned evidence service", "proposal service")
        assert not BY_NAME[name].tools
