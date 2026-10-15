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

from . import knowledge as K, tools as T
from .trace import Store

MAX_REVIEW_ROUNDS = 5
MAX_EVIDENCE_ROUNDS = 2


class S(TypedDict, total=False):
    run_id: str; request_id: str; event_id: str; event: dict; family: str; evidence: dict; gaps: list; policy: dict; assessment: dict
    proposal: dict; human: dict; review_rounds: int; evidence_rounds: int; status: str; final: dict; duplicate_of: str; executed: list


@dataclass
class Runtime:
    world: Any; kb: Any; store: Store; timeout_s: float = 2.0; approvals: Optional[dict] = None


def validate_claims(claims, known_ids):
    """Every claim must resolve to at least one retrieved evidence id or authoritative citation; the rest are dropped and counted."""
    kept, dropped = [], 0
    for c in claims:
        c = dict(c, evidence=[e for e in c.get("evidence", []) if e in known_ids])
        if c["evidence"]: kept.append(c)
        else: dropped += 1
    return kept, dropped


def build_graph(rt: Runtime, checkpointer):
    w, kb, store = rt.world, rt.kb, rt.store

    def tr(state): return store.trace(state["run_id"], state.get("request_id", ""))

    def ctx(state, approval=None):
        return T.ToolContext(run_id=state["run_id"], request_id=state.get("request_id", ""), kb=kb, trace=tr(state), timeout_s=rt.timeout_s, approval=approval)

    def call(state, evidence, gaps, tool, args, label=None):
        res = T.execute(w, tool, args, ctx(state))
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
        ev, gaps = {}, []; p = state["event"]["payload"]
        if state["family"] == "INVENTORY":
            loc, ing = p["location_id"], p["ingredient"]
            call(state, ev, gaps, "query_inventory", dict(location_id=loc, ingredient=ing))
            call(state, ev, gaps, "assess_inventory_risk", dict(location_id=loc, ingredient=ing))
            call(state, ev, gaps, "get_open_purchase_orders", dict(ingredient=ing))
            call(state, ev, gaps, "get_supplier_status", dict(ingredient=ing))
            eid, e = call(state, ev, gaps, "list_quality_findings", dict(rule="unit_mismatch", limit=100))
            if e["ok"]:
                rel = [f for f in e["data"]["findings"] if f["key"].startswith(loc + ":") and f["key"].endswith(":" + ing)]
                ev[eid]["relevant"] = rel
        elif state["family"] == "DATA_QUALITY":
            eid, e = call(state, ev, gaps, "get_quality_finding", dict(finding_id=p["finding_id"]) if p.get("finding_id") else dict(finding_id=1_000_000))
            if e["ok"]:
                f = e["data"]; call(state, ev, gaps, "get_lineage", dict(table=f["table"], key=f["key"]))
        elif state["family"] == "POLICY":
            eid, e = call(state, ev, gaps, "get_supplier_proposal", dict(proposal_id=p["proposal_id"]))
            if e["ok"]:
                d = e["data"]
                call(state, ev, gaps, "assess_policy_ingredient", dict(ingredient_text=d["ingredient_text"], declared_source=d["declared_source"], spec_sheet_status=d["spec_sheet_status"]))
                call(state, ev, gaps, "get_supplier_status", dict(supplier_id=d["supplier_id"]))
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
            t.event("policy_retrieved", question=q, abstained=d["abstained"], citations=[(c["document_id"], c["effective_status"], c["verification_status"]) for c in d["citations"]], reason=d["reason"][:160])
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

    def get(ev, tool):
        for k, v in ev.items():
            if v["tool"] == tool and v["ok"]: return k, v["data"]
        return None, None

    def claim(text, *ids): return dict(text=text, evidence=[i for i in ids if i])

    def decide(state):
        """Deterministic planner: evidence -> proposal. Every claim carries evidence ids; the validator removes any that do not resolve."""
        fam, ev, a = state["family"], state["evidence"], state["assessment"]; p = state["event"]["payload"]; claims, unc, mut, nots = [], [], [], []
        D54 = "D-54" if "D-54" in a["policy_citations"] else None
        D81 = "D-81" if "D-81" in a["policy_citations"] else None
        cites = a["policy_citations"]
        if fam == "INVENTORY":
            ie, inv = get(ev, "query_inventory"); re_, risk = get(ev, "assess_inventory_risk"); pe, pos = get(ev, "get_open_purchase_orders"); se, sup = get(ev, "get_supplier_status")
            if not inv or not risk:
                return dict(action="ESCALATE_INSUFFICIENT_EVIDENCE", headline="INSUFFICIENT VERIFIED EVIDENCE: inventory data could not be retrieved", claims=[], uncertainties=["inventory or risk tools failed: " + ", ".join(f'{g["tool"]}:{g["code"]}' for g in a["gaps"])], citations=cites,
                            abstain=True, ticket=dict(kind="INVENTORY_RECOUNT", summary=f"Inventory evidence unavailable for {p['location_id']} {p['ingredient']}; a human must check the data sources."), mutating_actions=[], not_proposed=["any purchase recommendation"])
            claims.append(claim(f"Latest valid count {inv['last_count_qty']} {inv['unit']} on {inv['last_count_date']}; estimated on hand {inv['on_hand_estimate']}; average use {inv['avg_daily_usage_14d']}/day; cover {inv['days_of_cover']} days.", ie))
            if risk["lead_time_days"] is not None: claims.append(claim(f"Supplier {risk['supplier_id']} lead time is {risk['lead_time_days']} days; {risk['open_po_qty_arriving_in_time']} kg on open orders arrives within it.", re_, pe))
            bad = [f for f in inv["data_flags"]]
            if risk["count_variance_ratio"] is not None and (risk["count_variance_ratio"] > 2 or risk["count_variance_ratio"] < .4): bad.append("COUNT_VARIANCE")
            qk = None
            if bad:
                unc.append("count data is unreliable: " + ", ".join(bad))
                if inv["newer_counts_quarantined"]: claims.append(claim(f"Newer count(s) were quarantined by the data-quality layer: {', '.join(inv['newer_counts_quarantined'])}.", ie))
                key = f"{p['location_id']}:{inv['last_count_date']}:{p['ingredient']}" if inv["last_count_date"] else f"{p['location_id']}:{state['event']['detected_at']}:{p['ingredient']}"
                nots += ["a purchase recommendation based on an unreliable count", "any inventory adjustment before a recount"]
                return dict(action="REQUEST_RECOUNT", headline=f"Recount {p['ingredient']} at {p['location_id']} before any purchase decision", claims=claims, uncertainties=unc + _policy_unc(a, D81), citations=cites, abstain=False,
                            ticket=dict(kind="INVENTORY_RECOUNT", summary=f"Count for {p['location_id']} {p['ingredient']} is unreliable ({', '.join(bad)}); request a physical recount.", ev=[ie, re_]),
                            mutating_actions=[dict(tool="flag_record_for_review", args=dict(table="inventory_counts", key=key, reason=f"Recount requested: {', '.join(bad)}"))], not_proposed=nots)
            if risk["shortfall_before_lead_time"] and not sup:      # regression (found by failure injection): a failed supplier lookup must never degrade to NO_ACTION
                claims.append(claim(f"Cover {risk['days_of_cover']} days is below the {risk['lead_time_days']}-day lead time, but supplier status could not be confirmed.", re_))
                return dict(action="ESCALATE_INSUFFICIENT_EVIDENCE", headline="INSUFFICIENT VERIFIED EVIDENCE: cover is short but the supplier could not be confirmed", claims=claims,
                            uncertainties=unc + ["supplier status unavailable: " + ", ".join(f'{g["tool"]}:{g["code"]}' for g in a["gaps"])], citations=cites, abstain=True,
                            ticket=dict(kind="INVENTORY_RECOUNT", summary=f"Short cover for {p['ingredient']} at {p['location_id']} and supplier status unavailable; a human must confirm sourcing.", ev=[ie, re_]), mutating_actions=[], not_proposed=["any purchase recommendation without a confirmed ACTIVE supplier"])
            if risk["shortfall_before_lead_time"] and sup:
                active = [s for s in sup["suppliers"] if s["status"] == "ACTIVE"]
                if not active:
                    claims.append(claim("Every supplier of this ingredient is not ACTIVE.", se))
                    return dict(action="ESCALATE_SUPPLIER_UNAVAILABLE", headline="Cover is short but no active supplier exists", claims=claims, uncertainties=unc + ["alternative supplier not identified in the data"], citations=cites, abstain=False,
                                ticket=dict(kind="INVENTORY_RECOUNT", summary="Short cover and no ACTIVE supplier; a human must decide sourcing.", ev=[ie, se]), mutating_actions=[], not_proposed=["any purchase recommendation"])
                unc += _policy_unc(a, D81)
                if D54 is None and p["ingredient"] in ("goat", "chicken thigh", "paneer", "cheese"): unc.append("D-54 was not retrieved; supplier compliance for this protein is not confirmed here")
                else: claims.append(claim("D-54 lists goat, lamb, chicken, seafood and vegetarian proteins as the primary protein architecture; the order is not a prohibited protein.", D54))
                if D81: claims.append(claim("D-81 sets a zero-dollar pre-capital build; any real purchase needs explicit founder authority.", D81))
                return dict(action="DRAFT_PURCHASE_RECOMMENDATION", headline=f"Draft a {risk['recommended_qty_kg']} kg {p['ingredient']} recommendation for {risk['supplier_id']} (not an order)", claims=claims, uncertainties=unc, citations=cites, abstain=False,
                            draft=dict(location_id=p["location_id"], ingredient=p["ingredient"], qty_kg=risk["recommended_qty_kg"], supplier_id=risk["supplier_id"], rationale=f"Cover {risk['days_of_cover']} d below lead time {risk['lead_time_days']} d; no open order arrives in time.", ev=[ie, re_, pe, se]),
                            mutating_actions=[], not_proposed=["placing a purchase order", "contacting the supplier"])
            if a["gaps"] and any(g["code"] != "INJECTION_SUSPECTED_IN_DOCUMENT" for g in a["gaps"]):      # never report "no action" on partial evidence
                return dict(action="ESCALATE_INSUFFICIENT_EVIDENCE", headline="INSUFFICIENT VERIFIED EVIDENCE: some checks failed, so no-action cannot be concluded", claims=claims,
                            uncertainties=unc + ["failed checks: " + ", ".join(f'{g["tool"]}:{g["code"]}' for g in a["gaps"])], citations=cites, abstain=True, ticket=dict(kind="INVENTORY_RECOUNT", summary="Partial evidence; a human must review.", ev=[ie]), mutating_actions=[], not_proposed=["concluding no action"])
            return dict(action="NO_ACTION", headline="No exception confirmed from current evidence", claims=claims, uncertainties=unc, citations=cites, abstain=False, mutating_actions=[], not_proposed=[])
        if fam == "DATA_QUALITY":
            fe, f = get(ev, "get_quality_finding"); le, lin = get(ev, "get_lineage")
            if not f:
                return dict(action="ESCALATE_INSUFFICIENT_EVIDENCE", headline="INSUFFICIENT VERIFIED EVIDENCE: the finding could not be retrieved", claims=[], uncertainties=["finding lookup failed: " + ", ".join(f'{g["tool"]}:{g["code"]}' for g in a["gaps"])], citations=cites, abstain=True,
                            ticket=dict(kind="QUALITY_REVIEW", summary="Quality finding unavailable; a human must inspect the pipeline."), mutating_actions=[], not_proposed=["any correction"])
            claims.append(claim(f"Finding {f['rule']} on {f['table']} key {f['key']} (severity {f['severity']}): {f['detail'][:80]}", fe))
            if lin:
                claims.append(claim(f"Quarantined: {lin['quarantined']} ({', '.join(lin['reasons']) or 'no quarantine reason'}); original record still in the modeled layer: {lin['in_modeled_layer']}; {len(lin['affected_records'])} related record(s).", le))
            else: unc.append("lineage could not be retrieved; affected records unknown")
            if not a["policy_found"]: unc.append("No authoritative NASHA procedure for corrupt-record handling was found in the knowledge base: INSUFFICIENT VERIFIED EVIDENCE. The conservative default below is a DESIGN ASSUMPTION (keep quarantined, review, never auto-correct).")
            return dict(action="QUARANTINE_AND_REVIEW", headline=f"Keep {f['key']} quarantined and put it in the human review queue", claims=claims, uncertainties=unc, citations=cites, abstain=False,
                        ticket=dict(kind="QUALITY_REVIEW", summary=f"{f['rule']} on {f['key']}; review and decide; no automatic correction.", ev=[fe, le]),
                        mutating_actions=[dict(tool="flag_record_for_review", args=dict(table=f["table"], key=f["key"], reason=f"{f['rule']} found by the quality layer; human review requested"))],
                        not_proposed=["deleting or rewriting the raw record", "merging orders automatically", "restating revenue"])
        # POLICY
        pe, prop = get(ev, "get_supplier_proposal"); ae, asm = get(ev, "assess_policy_ingredient")
        if not prop or not asm or not cites:
            return dict(action="ABSTAIN_REQUIRE_REVIEW", headline="INSUFFICIENT VERIFIED EVIDENCE: cannot assess the proposal against the dietary policy", claims=[claim(f"Proposal text: {_safe(prop['ingredient_text'])}", pe)] if prop else [],
                        uncertainties=["policy source or proposal data missing: " + ", ".join(f'{g["tool"]}:{g["code"]}' for g in a["gaps"]) if a["gaps"] else "authoritative dietary policy not retrieved"], citations=cites, abstain=True,
                        ticket=dict(kind="POLICY_REVIEW", summary=f"Proposal {p['proposal_id']} cannot be assessed; a human must review against D-54.", ev=[pe]),
                        mutating_actions=[dict(tool="flag_record_for_review", args=dict(table="supplier_proposals", key=p["proposal_id"], reason="Cannot assess against D-54; human review"))], not_proposed=["approving or rejecting the substitution on inference"])
        claims.append(claim(f"Proposal {prop['proposal_id']}: {_safe(prop['ingredient_text'])}; declared source {_safe(prop['declared_source'])}; spec sheet {prop['spec_sheet_status']}.", pe))
        claims.append(claim(f"Screening verdict {asm['verdict']}: {'; '.join(asm['basis'])}", ae))
        if D54: claims.append(claim("D-54 (founder, binding): beef-free and pork-free, applies to stocks, broths, fats and supplier assumptions; this is not a halal claim.", D54))
        v = asm["verdict"]
        flag = dict(tool="flag_record_for_review", args=dict(table="supplier_proposals", key=p["proposal_id"], reason=f"D-54 screening verdict {v}; human decision required"))
        if v == "PROHIBITED":
            return dict(action="RECOMMEND_REJECT_SUBSTITUTION", headline=f"Recommend rejecting {prop['proposal_id']}: it names a prohibited ingredient (D-54)", claims=claims, uncertainties=["a human must confirm the rejection; the supplier is not contacted"], citations=cites, abstain=False,
                        ticket=dict(kind="POLICY_REVIEW", summary=f"{prop['proposal_id']} names a D-54 prohibited ingredient.", ev=[pe, ae]), mutating_actions=[flag], not_proposed=["contacting the supplier", "approving any substitute"])
        if v == "CLEARED_PENDING_HUMAN":
            return dict(action="RECOMMEND_HUMAN_CONFIRM_SPEC", headline=f"Supplier statement for {prop['proposal_id']} names a permitted source; a human must confirm the document", claims=claims, uncertainties=["the statement itself has not been verified; this agent cannot verify documents", "no approval is implied"], citations=cites, abstain=False,
                        ticket=dict(kind="POLICY_REVIEW", summary=f"{prop['proposal_id']}: confirm the supplier statement before any approval.", ev=[pe, ae]), mutating_actions=[flag], not_proposed=["treating the substitution as approved"])
        return dict(action="ABSTAIN_REQUIRE_REVIEW", headline=f"INSUFFICIENT VERIFIED EVIDENCE for {prop['proposal_id']}: do not infer that it is allowed or prohibited", claims=claims,
                    uncertainties=["animal source not established; a written supplier statement is required (hidden-derivative checklist)", "the agent cannot contact the supplier"], citations=cites, abstain=True,
                    ticket=dict(kind="POLICY_REVIEW", summary=f"{prop['proposal_id']}: source unspecified, spec sheet {prop['spec_sheet_status']}; request a written statement through a human.", ev=[pe, ae]), mutating_actions=[flag],
                    not_proposed=["approving", "rejecting on inference", "contacting the supplier"])

    def _safe(s): return "[withheld: possible instruction in data]" if K.INJECTION_RE.search(str(s)) else str(s)[:120]

    def _policy_unc(a, D81):
        u = []
        if not a["policy_found"]: u.append("No authoritative NASHA policy was retrieved for this question: INSUFFICIENT VERIFIED EVIDENCE")
        elif D81 is None: u.append("D-81 (zero-dollar build) was not retrieved; spending authority is unconfirmed")
        return u

    def propose(state):
        t = tr(state); t.event("state", node="PROPOSE_ACTION")
        pr = decide(state); ev = state["evidence"]; known = set(ev) | set(state["assessment"]["policy_citations"])
        kept, dropped = validate_claims(pr.get("claims", []), known)
        pr["claims"] = kept; pr["unsupported_claims_removed"] = dropped
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
        t.event("human_decision", decision=dec.get("decision"), reviewer=dec.get("reviewer", "unknown"), note=str(dec.get("note", ""))[:200], edits=dec.get("edits"))
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
        for act in state["proposal"].get("mutating_actions", []):
            appr = dict(run_id=state["run_id"], tool=act["tool"], args_hash=T.args_hash(act["tool"], T.TOOLS[act["tool"]].input_model.model_validate(act["args"]).model_dump()), by=state["human"].get("reviewer", "unknown"))
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
    def __init__(self, world, kb, store=None, checkpoint_path=None, timeout_s=2.0):
        self.store = store or Store()
        self.cp = SqliteSaver(sqlite3.connect(checkpoint_path, check_same_thread=False)) if checkpoint_path else InMemorySaver()
        self.rt = Runtime(world, kb, self.store, timeout_s)
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

    def resume(self, run_id, decision: dict):
        with self.lock:
            s = self.summary(run_id)
            if s is None: raise KeyError(run_id)
            if not s["awaiting_human"]: raise RuntimeError(f"run {run_id} is not awaiting a human decision (status {s['status']})")
            self.graph.invoke(Command(resume=decision), self._cfg(run_id))
        return self.summary(run_id)
