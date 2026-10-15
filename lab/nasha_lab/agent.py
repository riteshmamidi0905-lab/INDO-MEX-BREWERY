"""LangGraph human-in-the-loop operations agent (SYNTHETIC / SIMULATED / NOT PRODUCTION DEPLOYED).

RECEIVE_EVENT -> CLASSIFY_EVENT -> COLLECT_OPERATIONAL_DATA -> RETRIEVE_POLICY -> ASSESS_EVIDENCE -> PROPOSE_ACTION
   -> HUMAN_REVIEW --approve--> EXECUTE_APPROVED -> FINALIZE
                   --reject---> FINALIZE
                   --edit-----> PROPOSE (validated edit) -> HUMAN_REVIEW
                   --more evidence--> COLLECT ...
The planner is DETERMINISTIC (rules over evidence), not a language model. That is a deliberate decision: the control flow, evidence
discipline, permissions and approval boundary are the engineering under test, and they are measurable without a paid model. A model can
replace `decide()` behind the same proposal schema (claims must still cite evidence ids; unsupported claims are dropped and counted).
"""
import json
import operator
import re
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from . import identity as ID, knowledge as K, planners as PL, tools as T
from .trace import Store

MAX_REVIEW_ROUNDS = 5
MAX_EVIDENCE_ROUNDS = 2


class S(TypedDict, total=False):
    run_id: str; request_id: str; event_id: str; event: dict; family: str; evidence: dict; gaps: list; policy: dict; assessment: dict
    tainted: list; proposal: dict; human: dict; review_rounds: int; evidence_rounds: int; status: str; final: dict; duplicate_of: str; executed: list


@dataclass
class Runtime:
    world: Any; kb: Any; store: Store; timeout_s: float = 2.0; planner: Any = None; authority: Any = None; gateway: Any = None


def validate_claims(claims, known_ids):
    """Every claim must resolve to at least one retrieved evidence id or authoritative citation; the rest are dropped and counted."""
    kept, dropped = [], 0
    for c in claims:
        c = dict(c, evidence=[e for e in c.get("evidence", []) if e in known_ids])
        if c["evidence"]: kept.append(c)
        else: dropped += 1
    return kept, dropped


ALLOWED_MUTATIONS = {"flag_record_for_review", "release_draft"}


def validate_mutations(pr, evidence, event, trace):
    """Defence in depth for ANY planner: a proposed mutation must use an allowed tool and target something that appears in trusted evidence
    or the event itself (no invented record keys); it still needs a signed human grant to run."""
    # ground ONLY in trusted results of calls that succeeded plus the event itself: the model's own tool arguments and error entries are not evidence
    blob = json.dumps({k: v.get("data") for k, v in evidence.items() if v.get("ok") and not v.get("injection_suspected") and v["tool"] != "get_supplier_notes_untrusted"}, default=str) + json.dumps(event, default=str)
    kept, rejected = [], []
    for a in pr.get("mutating_actions", []):
        tool, args = a.get("tool"), a.get("args", {})
        if tool not in ALLOWED_MUTATIONS: rejected.append((tool, "tool_not_allowed")); continue
        if tool == "flag_record_for_review" and not all(part in blob for part in str(args.get("key", "")).split(":")): rejected.append((tool, "target_not_in_evidence")); continue
        if tool == "release_draft" and args.get("draft_id") != pr.get("draft_id"): rejected.append((tool, "draft_not_from_this_run")); continue
        kept.append(a)
    for tool, why in rejected: trace.event("mutation_rejected", tool=tool, reason=why)
    pr["mutating_actions"] = kept
    return len(rejected)


def build_graph(rt: Runtime, checkpointer):
    w, kb, store = rt.world, rt.kb, rt.store

    def tr(state): return store.trace(state["run_id"], state.get("request_id", ""))

    def taint(evidence):
        """Values that appear ONLY in untrusted tool results (minus anything also present in trusted evidence)."""
        bad, good = set(), set()
        for e in evidence.values():
            if not e.get("ok") or e.get("data") is None: continue
            if e["tool"] == "get_supplier_notes_untrusted": bad.update(e["data"].get("tainted", []))
            else: T._flat(e["data"], good)
        return sorted(bad - good)

    def ctx(state, approval=None, evidence=None):
        return T.ToolContext(run_id=state["run_id"], request_id=state.get("request_id", ""), kb=kb, trace=tr(state), timeout_s=rt.timeout_s, approval=approval, authority=rt.authority,
                             gateway=rt.gateway, tainted=tuple(taint(evidence if evidence is not None else state.get("evidence", {}))))

    def call(state, evidence, gaps, tool, args, label=None):
        res = T.execute(w, tool, args, ctx(state, evidence=evidence))
        eid = f"E{len(evidence) + 1}:{label or tool}"
        entry = dict(tool=tool, ok=res["ok"], args=args)
        if res["ok"]:
            entry["data"] = res["data"]
            blob = json.dumps(res["data"], default=str)
            if K.INJECTION_RE.search(blob):
                entry["injection_suspected"] = True; gaps.append(dict(tool=tool, code="INJECTION_SUSPECTED_IN_TOOL_RESULT"))
                tr(state).event("injection_flagged", source=tool, where="tool_result")
        else:
            entry["error"] = res["error"]; gaps.append(dict(tool=tool, code=res["error"]["code"]))
        evidence[eid] = entry
        return eid, entry

    # ---------------------------------------------------------------- nodes
    def receive_event(state):
        t = tr(state); t.event("state", node="RECEIVE_EVENT", event_id=state["event_id"])
        row = w.q("SELECT * FROM operational_incidents WHERE event_id=?", state["event_id"])
        if not row:
            t.event("error", code="UNKNOWN_EVENT", event_id=state["event_id"]); return dict(status="FAILED_UNKNOWN_EVENT")
        prior = store.con.execute("SELECT run_id FROM agent_runs WHERE event_id=? AND run_id<>? AND status NOT IN ('FAILED','FAILED_UNKNOWN_EVENT') ORDER BY created LIMIT 1", (state["event_id"], state["run_id"])).fetchone()
        if prior:
            t.event("duplicate_event", duplicate_of=prior[0]); return dict(status="DUPLICATE_IGNORED", duplicate_of=prior[0])
        ev = dict(row[0]); ev["payload"] = json.loads(ev["payload"])
        pl = rt.planner
        t.event("run_meta", planner_type=pl.name, planner_version=getattr(pl, "version", ""), model=getattr(pl, "model", None), prompt_version=PL.PROMPT_VERSION if pl.name == "llm" else None,
                retriever_type=kb.default, embedding_model=getattr(kb, "embedding_model", None), knowledge_chunks=len(kb.chunks), tool_timeout_s=rt.timeout_s)
        return dict(event=ev, evidence={}, gaps=[], review_rounds=0, evidence_rounds=0, executed=[], status="RUNNING")

    def route_after_receive(state): return "classify_event" if state.get("event") else "finalize"

    def classify_event(state):
        fam = {"INVENTORY_EXCEPTION": "INVENTORY", "DQ_INCIDENT": "DATA_QUALITY", "POLICY_REVIEW": "POLICY"}.get(state["event"]["event_type"])
        tr(state).event("state", node="CLASSIFY_EVENT", family=fam)
        if not fam: return dict(status="FAILED_UNKNOWN_EVENT_TYPE")
        return dict(family=fam)

    def route_after_classify(state): return "collect" if state.get("family") else "finalize"

    def collect(state):
        t = tr(state); t.event("state", node="COLLECT_OPERATIONAL_DATA", family=state["family"], round=state["evidence_rounds"])
        ev, gaps = rt.planner.collect(state, lambda e, g, tool, args, label=None: call(state, e, g, tool, args, label), t)
        if state["evidence_rounds"] > 0:      # human asked for more: add labelled, NON-authoritative context (never used for claims)
            call(state, ev, gaps, "search_nasha_knowledge", dict(query="supplier ingredient inventory data quality policy", k=3, include_nonauthoritative=True), "context_only")
        return dict(evidence=ev, gaps=gaps)

    def retrieve_policy(state):
        t = tr(state); t.event("state", node="RETRIEVE_POLICY")
        qs = {"INVENTORY": ["What is the dietary policy for proteins such as goat, lamb and chicken and supplier specifications?", "What does the zero-dollar pre-capital build mean for purchasing and spending?"],
              "DATA_QUALITY": ["What is the procedure for handling corrupt or duplicate operational records and quarantine?"],
              "POLICY": ["What is the dietary policy on beef, pork and hidden derivatives such as stock, bouillon, shortening and natural flavors?"]}[state["family"]]
        pol, gaps = [], list(state["gaps"])
        for q in qs:
            res = T.execute(w, "get_current_policy", dict(question=q), ctx(state))
            if not res["ok"]:
                gaps.append(dict(tool="get_current_policy", code=res["error"]["code"])); pol.append(dict(question=q, error=res["error"])); continue
            d = res["data"]; pol.append(dict(question=q, **d))
            if d["injection_flagged"]:
                gaps.append(dict(tool="get_current_policy", code="INJECTION_SUSPECTED_IN_DOCUMENT")); t.event("injection_flagged", source="knowledge", chunks=d["injection_flagged"], where="retrieved_document")
            t.event("policy_retrieved", question=q, abstained=d["abstained"], citations=[(c["document_id"], c["effective_status"], c["verification_status"]) for c in d["citations"]], scores=[c.get("score") for c in d["citations"]], retriever=kb.default, gate_p=d.get("gate_p"), reason=d["reason"][:160])
        return dict(policy=dict(items=pol), gaps=gaps)

    def assess(state):
        t = tr(state); t.event("state", node="ASSESS_EVIDENCE")
        ev, gaps = state["evidence"], state["gaps"]
        cites = []
        for item in state["policy"]["items"]:
            for c in item.get("citations", []): cites.append(c["document_id"])
        cites = list(dict.fromkeys(cites))
        a = dict(policy_citations=cites, policy_found=bool(cites), gaps=gaps, injection=any("INJECTION" in g["code"] for g in gaps))
        t.event("assessment", policy_citations=cites, gap_codes=[f'{g["tool"]}:{g["code"]}' for g in gaps])
        return dict(assessment=a)

    def propose(state):
        t = tr(state); t.event("state", node="PROPOSE_ACTION")
        pr = rt.planner.decide(state, tr(state)); ev = state["evidence"]; known = set(ev) | set(state["assessment"]["policy_citations"])
        kept, dropped = validate_claims(pr.get("claims", []), known)
        pr["claims"] = kept; pr["unsupported_claims_removed"] = dropped
        pr["mutations_rejected"] = validate_mutations(pr, ev, state["event"], t)
        if dropped: t.event("unsupported_claims_removed", count=dropped)
        if pr.get("draft"):
            d = pr["draft"]; ev_ids = [e for e in d.pop("ev") if e]
            res = T.execute(w, "draft_purchase_recommendation", dict(d, evidence_ids=ev_ids or ["none"]), ctx(state))
            if res["ok"]:
                pr["draft_id"] = res["data"]["draft_id"]; pr["mutating_actions"] = [dict(tool="release_draft", args=dict(draft_id=pr["draft_id"]))]
            else:
                pr.update(action="ESCALATE_DRAFT_REJECTED", headline="The draft was rejected by tool validation", abstain=True); pr["uncertainties"].append(f"draft rejected: {res['error']['code']}: {res['error']['message'][:120]}"); pr["mutating_actions"] = []
        elif pr.get("ticket"):
            k = pr["ticket"]; res = T.execute(w, "draft_review_ticket", dict(kind=k["kind"], summary=k["summary"], evidence_ids=[e for e in k.get("ev", []) if e] or ["none"]), ctx(state))
            pr["draft_id"] = res["data"]["draft_id"] if res["ok"] else None
        pr["options"] = ["approve", "reject", "edit", "request_more_evidence"]
        t.event("proposal", action=pr["action"], abstain=pr.get("abstain", False), claims=len(pr["claims"]), uncertainties=pr["uncertainties"], draft_id=pr.get("draft_id"), mutating_actions=pr["mutating_actions"], not_proposed=pr.get("not_proposed", []))
        return dict(proposal=pr, status="AWAITING_HUMAN")

    def human_review(state):
        t = tr(state); t.event("state", node="HUMAN_REVIEW", round=state["review_rounds"])
        store.set_status(state["run_id"], "AWAITING_HUMAN")
        dec = interrupt(dict(run_id=state["run_id"], proposal=state["proposal"]))
        t.event("human_decision", decision=dec.get("decision"), reviewer=dec.get("reviewer", "unknown"), role=dec.get("role"), note=str(dec.get("note", ""))[:200], edits=dec.get("edits"))
        return dict(human=dec, review_rounds=state["review_rounds"] + 1, status="RUNNING")

    def route_review(state):
        d = (state["human"] or {}).get("decision")
        if d == "approve": return "execute"
        if d == "reject": return "finalize"
        if d == "edit": return "apply_edit" if state["review_rounds"] < MAX_REVIEW_ROUNDS else "finalize"
        if d == "request_more_evidence": return "more_evidence" if state["evidence_rounds"] < MAX_EVIDENCE_ROUNDS and state["review_rounds"] < MAX_REVIEW_ROUNDS else "finalize"
        tr(state).event("error", code="INVALID_DECISION", decision=str(d)[:40])
        return "human_review" if state["review_rounds"] < MAX_REVIEW_ROUNDS else "finalize"

    def apply_edit(state):
        t = tr(state); pr = json.loads(json.dumps(state["proposal"])); edits = state["human"].get("edits") or {}
        allowed = {"DRAFT_PURCHASE_RECOMMENDATION": {"qty_kg"}}.get(pr["action"], set())
        if not edits or set(edits) - allowed:
            t.event("error", code="EDIT_NOT_ALLOWED", allowed=sorted(allowed), got=sorted(edits)); pr["edit_error"] = f"edits limited to {sorted(allowed)}"
            return dict(proposal=pr)
        old = w.q("SELECT payload FROM drafts WHERE draft_id=?", pr["draft_id"])
        d = json.loads(old[0]["payload"]); d["qty_kg"] = edits["qty_kg"]
        res = T.execute(w, "draft_purchase_recommendation", d, ctx(state))
        if not res["ok"]:
            t.event("error", code="EDIT_REJECTED", detail=res["error"]); pr["edit_error"] = res["error"]["message"]; return dict(proposal=pr)
        pr["draft_id"] = res["data"]["draft_id"]; pr["mutating_actions"] = [dict(tool="release_draft", args=dict(draft_id=pr["draft_id"]))]; pr.pop("edit_error", None)
        t.event("proposal_edited", qty_kg=edits["qty_kg"], draft_id=pr["draft_id"])
        return dict(proposal=pr)

    def more_evidence(state):
        t = tr(state); t.event("state", node="REQUEST_MORE_EVIDENCE", round=state["evidence_rounds"] + 1)
        return dict(evidence_rounds=state["evidence_rounds"] + 1)

    def execute(state):
        t = tr(state); t.event("state", node="EXECUTE_APPROVED"); done = []
        grants = state["human"].get("grants") or []
        for i, act in enumerate(state["proposal"].get("mutating_actions", [])):
            appr = dict(grant=grants[i] if i < len(grants) else None)
            res = T.execute(w, act["tool"], act["args"], ctx(state, approval=appr))
            done.append(dict(tool=act["tool"], ok=res["ok"], error=res["error"], data=res["data"]))
        t.event("executed", actions=done)
        return dict(executed=done)

    def finalize(state):
        t = tr(state); st = state.get("status")
        d = (state.get("human") or {}).get("decision")
        if st in ("DUPLICATE_IGNORED", "FAILED_UNKNOWN_EVENT", "FAILED_UNKNOWN_EVENT_TYPE"): outcome = st
        elif d == "approve": outcome = "APPROVED_ABSTENTION_ACKNOWLEDGED" if state["proposal"].get("abstain") else "APPROVED_AND_EXECUTED_IN_SIMULATION"
        elif d == "reject": outcome = "REJECTED_BY_HUMAN_NO_ACTION"
        else: outcome = "ESCALATED_NO_DECISION"
        final = dict(outcome=outcome, executed=state.get("executed", []), draft_id=(state.get("proposal") or {}).get("draft_id"), duplicate_of=state.get("duplicate_of"),
                     external_actions_performed=0)
        t.event("final", **final)
        store.set_status(state["run_id"], outcome if outcome.startswith(("DUPLICATE", "FAILED")) else "COMPLETED", outcome, finished=True)
        return dict(final=final, status=outcome)

    g = StateGraph(S)
    for name, fn in [("receive_event", receive_event), ("classify_event", classify_event), ("collect", collect), ("retrieve_policy", retrieve_policy), ("assess", assess), ("propose", propose),
                     ("human_review", human_review), ("apply_edit", apply_edit), ("more_evidence", more_evidence), ("execute", execute), ("finalize", finalize)]:
        g.add_node(name, fn)
    g.add_edge(START, "receive_event")
    g.add_conditional_edges("receive_event", route_after_receive, {"classify_event": "classify_event", "finalize": "finalize"})
    g.add_conditional_edges("classify_event", route_after_classify, {"collect": "collect", "finalize": "finalize"})
    g.add_edge("collect", "retrieve_policy"); g.add_edge("retrieve_policy", "assess"); g.add_edge("assess", "propose"); g.add_edge("propose", "human_review")
    g.add_conditional_edges("human_review", route_review, {"execute": "execute", "finalize": "finalize", "apply_edit": "apply_edit", "more_evidence": "more_evidence", "human_review": "human_review"})
    g.add_edge("apply_edit", "human_review"); g.add_edge("more_evidence", "collect"); g.add_edge("execute", "finalize"); g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


class AgentService:
    """Start / inspect / resume runs. One thread id per run; state survives a process restart when a SQLite checkpoint file is used."""
    def __init__(self, world, kb, store=None, checkpoint_path=None, timeout_s=2.0, planner=None, authority=None, gateway=None):
        self.store = store or Store()
        self.cp = SqliteSaver(sqlite3.connect(checkpoint_path, check_same_thread=False)) if checkpoint_path else InMemorySaver()
        self.rt = Runtime(world, kb, self.store, timeout_s, planner or PL.DeterministicPlanner(), authority or ID.Authority.dev(), gateway)
        self.graph = build_graph(self.rt, self.cp)
        self.lock = threading.RLock()

    def _cfg(self, run_id): return {"configurable": {"thread_id": run_id}}

    def summary(self, run_id):
        run = self.store.run(run_id)
        if not run: return None
        st = self.graph.get_state(self._cfg(run_id))
        pending = None
        for tsk in st.tasks:
            for i in tsk.interrupts: pending = i.value
        vals = st.values or {}
        return dict(run=run, awaiting_human=bool(pending), proposal=(pending or {}).get("proposal") or vals.get("proposal"), final=vals.get("final"), status=run["status"])

    def start(self, event_id, request_id=""):
        with self.lock:
            run_id = self.store.create_run(event_id, request_id)
            self.graph.invoke({"run_id": run_id, "request_id": request_id, "event_id": event_id}, self._cfg(run_id))
        return self.summary(run_id)

    def dev_session(self, reviewer_id="founder"):
        return self.rt.authority.dev_session(reviewer_id)

    def resume(self, run_id, decision: dict, session=None):
        """Resume a run at the human-review interrupt. The reviewer is identified from the session token (never from free text);
        an approval mints a signed grant bound to this run and to the exact tool + arguments of the proposal being approved."""
        with self.lock:
            s = self.summary(run_id)
            if s is None: raise KeyError(run_id)
            if not s["awaiting_human"]: raise RuntimeError(f"run {run_id} is not awaiting a human decision (status {s['status']})")
            who = self.rt.authority.identify(session)                     # AuthError propagates; the run stays awaiting
            decision = dict(decision, reviewer=who.id, role=who.role)
            if decision.get("decision") == "approve":
                acts = []
                for a in s["proposal"].get("mutating_actions", []):
                    clean = T.TOOLS[a["tool"]].input_model.model_validate(a["args"]).model_dump()
                    acts.append(dict(tool=a["tool"], args=clean, args_hash=T.args_hash(a["tool"], clean)))
                grant = self.rt.authority.issue_grant(who, run_id, acts)   # ROLE_NOT_PERMITTED propagates; nothing executes
                decision["grants"] = [grant] * len(acts)
            self.graph.invoke(Command(resume=decision), self._cfg(run_id))
        return self.summary(run_id)
