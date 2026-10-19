"""NASHA AI role registry. Planning metadata, not twelve deployed LLM agents.

SYNTHETIC BUSINESS SCENARIOS ONLY. THE WEIR is independent security enforcement.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Role:
    name: str
    purpose: str
    kind: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    tools: tuple[str, ...]
    sources: tuple[str, ...]
    permissions: tuple[str, ...]
    depends_on: tuple[str, ...]
    metrics: tuple[str, ...]
    human_approval: str
    failure: str
    color: str
    symbol: str

def role(name, purpose, kind, inputs, outputs, tools, sources, permissions, depends, metrics, approval, color, symbol):
    return Role(name, purpose, kind, tuple(inputs), tuple(outputs), tuple(tools), tuple(sources),
                tuple(permissions), tuple(depends), tuple(metrics), approval,
                "Abstain on missing evidence; record error; no protected action without THE WEIR approval.",
                color, symbol)

ROLES = (
    role("ATLAS","Business strategy","orchestrated analyst",["scenario"],["decision brief"],["knowledge_search"],["versioned research"],["READ"],["PULSE","SCRIBE"],["citation coverage"],"Founder signs off decisions","#CBA46A","compass"),
    role("BREWMASTER","Brewing intelligence","deterministic service",["beer brief"],["test batch plan"],["knowledge_search"],["BJCP references"],["READ"],["SCRIBE"],["style compliance"],"Founder approves brewing plan","#D9A441","grain"),
    role("FORGE","Product and menu","deterministic service",["recipe brief"],["pairing proposal"],["menu_lookup"],["versioned menu"],["READ"],["BREWMASTER","GUARDIAN"],["dietary policy violations"],"Founder approves menu change","#C56E48","flame"),
    role("SENTINEL","Inventory intelligence","deterministic service",["inventory event"],["risk assessment"],["query_inventory","assess_inventory_risk"],["synthetic inventory"],["READ","ANALYZE"],[],["anomaly precision","recall"],"Human review for uncertain records","#438F83","shield"),
    role("MERIDIAN","Procurement","supervised workflow",["risk assessment"],["draft recommendation"],["draft_purchase_recommendation"],["synthetic suppliers"],["READ","DRAFT"],["SENTINEL"],["recommendation validity"],"THE WEIR plus authorized human before protected action","#A58AB5","route"),
    role("PULSE","Business analytics","deterministic service",["synthetic metrics"],["scenario analysis"],["validated_metrics"],["synthetic operations"],["READ"],[],["metric reproducibility"],"Founder approval for decisions","#4D91BA","pulse"),
    role("ECHO","Customer intelligence","planned evidence service",["synthetic feedback"],["labelled insights"],[],["synthetic feedback corpus"],["READ"],[],["sentiment F1"],"Human review before external use","#BC82A6","wave"),
    role("SPARK","Marketing and brand","proposal service",["approved insights"],["campaign draft"],[],["NASHA brand guidelines"],["READ","DRAFT"],["ECHO","GUARDIAN"],["claim substantiation"],"Founder approves publication; no automatic publishing","#E8A95E","spark"),
    role("NEXUS","Operations coordinator","LangGraph workflow",["incident"],["reviewable proposal"],["query_inventory","search_nasha_knowledge"],["synthetic operations","policy"],["READ","ANALYZE","DRAFT"],["SENTINEL","MERIDIAN","GUARDIAN"],["task completion"],"Human interrupt and THE WEIR for protected tools","#8C9CB2","nodes"),
    role("GUARDIAN","Quality and compliance","deterministic service",["proposal"],["policy verdict"],["assess_policy_ingredient"],["D-54 policy","verified documents"],["READ","ANALYZE"],["SCRIBE"],["policy violations"],"No self-authorization; THE WEIR independently enforces","#709D7B","check"),
    role("SCRIBE","Knowledge and research","retrieval service",["research question"],["cited evidence"],["search_nasha_knowledge"],["versioned knowledge"],["READ"],[],["retrieval MRR","citation validity"],"Human verifies external claims","#91A7B4","book"),
    role("LUMEN","AI evaluation and reliability","deterministic service",["run evidence"],["release assessment"],["release_gate"],["versioned evaluations"],["READ"],["NEXUS","SCRIBE"],["test pass rate","regression count"],"Human reviews release; no auto deployment","#C1A4DB","prism"),
)
BY_NAME = {r.name: r for r in ROLES}
assert len(BY_NAME) == 12
