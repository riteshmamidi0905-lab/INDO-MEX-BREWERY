"""Instrumented scenario runner: one synthetic scenario -> one OpsService run -> telemetry record + trace events.
SYNTHETIC / SIMULATED / OFFLINE. Re-uses the lab's scenario generator and world builder; pins the frozen Block 3 corpus like every other evaluation entry point."""
import json
from dataclasses import dataclass, field
from typing import Any

from .. import agent, identity as ID, knowledge as K, planners as PL, scenarios as S, scripted_models as SM, llm_planner as LP
K.use_version("block3")                           # same pin as eval_planners / eval_failures
from .. import untrusted_mcp as UM
from ..trace import Store
from ..trust import UNTRUSTED, Gateway
from . import telemetry as TM
from .faultlib import FaultableKB, FaultyClient, FlakyConnection
from .resilience import ResilientKB


class FakeClock:
    """Manually advanced clock for approval-expiry experiments."""
    def __init__(self, t=1_800_000_000.0): self.t = t
    def __call__(self): return self.t
    def advance(self, s): self.t += s


PLANNERS = {"deterministic": lambda client=None: PL.DeterministicPlanner(), "rule-model": lambda client=None: LP.LLMPlanner(client or SM.rule_model()),
            "worst-case": lambda client=None: LP.LLMPlanner(client or SM.worst_case_model()), "parrot": lambda client=None: LP.LLMPlanner(client or SM.parrot_model()),
            "parrot+guardrail": lambda client=None: LP.LLMPlanner(client or SM.parrot_model(), guardrail=True), "taint-copier": lambda client=None: LP.LLMPlanner(client or SM.taint_model())}
_KBS = {}


def shared_kb(extra_docs=None):
    from ..eval_planners import kb_for
    return kb_for(extra_docs or [])


@dataclass
class Env:
    sc: Any; world: Any; svc: Any; ops: Any; eid: str; planner: Any; kb: Any; clock: FakeClock; authority: Any
    client: Any = None; flaky: Any = None; handles: dict = field(default_factory=dict)


def make_env(sc, planner="deterministic", *, timeout_s=None, stack=None, registry=None, logger=None, versions=None, kb_wrap=None, client_mode=None, client_kw=None,
             flaky_db=False, session_mode=False, approval_ttl_s=900.0, session_ttl=900, resilient_kb=False, extra_faults=None, portal=None, faults=None, extra_docs=None, authority_rules=None):
    w = S.fresh_world(1, getattr(sc, "menu_version", "v1"), getattr(sc, "po_coverage", "v1")); payload = sc.setup(w)
    etype = {"INVENTORY": "INVENTORY_EXCEPTION", "DATA_QUALITY": "DQ_INCIDENT", "POLICY": "POLICY_REVIEW"}[sc.event_family]
    eid = S.add_event(w, etype, payload); w.con.commit(); w.faults = dict(sc.faults if faults is None else faults)
    clock = FakeClock()
    client = None
    if planner in ("rule-model", "worst-case", "parrot", "parrot+guardrail", "taint-copier") and client_mode:
        base = {"rule-model": SM.rule_model, "worst-case": SM.worst_case_model, "parrot": SM.parrot_model, "parrot+guardrail": SM.parrot_model, "taint-copier": SM.taint_model}[planner]()
        client = FaultyClient(base, mode=client_mode, **(client_kw or {})); pl = PLANNERS[planner](client)
    else: pl = PLANNERS[planner]()
    kb = shared_kb(sc.extra_docs if extra_docs is None else extra_docs)
    if kb_wrap == "faultable": kb = FaultableKB(kb)
    if resilient_kb: kb = ResilientKB(kb, sleep=lambda s: None)
    if authority_rules == "v2":
        from ..knowledge_authority import AuthorityKB
        kb = AuthorityKB(kb, "v2")
    flaky = None
    if flaky_db: flaky = FlakyConnection(w.con); w.con = flaky
    tmo = timeout_s if timeout_s is not None else (0.05 if "slow" in w.faults.values() else 2.0)
    gw = Gateway({"portal": (UM.build(portal or sc.portal), UNTRUSTED)})
    authority = ID.Authority.dev(autologin=None if session_mode else "founder", clock=clock, session_ttl=session_ttl)
    svc = agent.AgentService(w, kb, store=Store(), timeout_s=tmo, planner=pl, authority=authority, gateway=gw)
    ops = TM.OpsService(svc, stack=stack or TM.ExecStack(), registry=registry, logger=logger, versions=versions, clock=clock, approval_ttl_s=approval_ttl_s)
    return Env(sc, w, svc, ops, eid, pl, kb, clock, authority, client=client, flaky=flaky)


def drive(env, decisions=None, session=None):
    """Start the run and apply the scenario's human decisions. Returns (run_id, summary). AuthError from a decision propagates to the caller."""
    s = env.ops.start(env.eid, "ops-" + env.sc.id)
    rid = (s.get("run") or {}).get("run_id")
    if rid is None: return None, s
    for d in (env.sc.decisions if decisions is None else decisions):
        if d["decision"] == "REPLAY": env.ops.start(env.eid, "ops-replay"); continue
        if not env.ops.summary(rid)["awaiting_human"]: break
        env.ops.resume(rid, d, session)
    return rid, env.ops.summary(rid)


def run_scenario(sc, planner="deterministic", **kw):
    """Convenience: run to completion and return (record, events, env)."""
    env = make_env(sc, planner, **kw)
    rid, summ = drive(env)
    return (env.ops.record(rid) if rid else None), (env.svc.store.events(rid) if rid else []), env


def clean_pool():
    """CLEAN control pool: scenarios with no fault, no injected document, an honest portal and no attack label, split-labelled."""
    dev, held, adv = S.build(); held_b = S.build_b()
    ok = lambda sc: not sc.faults and not sc.extra_docs and sc.portal == "ok" and not sc.attack
    return dict(dev=[s for s in dev if ok(s)], heldout=[s for s in held if ok(s)], heldoutB=[s for s in held_b if ok(s)])
