"""Deterministic agent evaluation: happy paths, human-decision paths and failure injection. OFFLINE, SYNTHETIC, same-author."""
import json
import statistics
import sys
import time

from . import agent, identity as ID, knowledge as K, tools as T, world as W

SECS = {"query_inventory", "assess_inventory_risk", "get_open_purchase_orders", "get_supplier_status", "list_quality_findings", "get_current_policy"}
NEEDED = {  # event family -> tools that must be called
    "INVENTORY": {"query_inventory", "assess_inventory_risk", "get_open_purchase_orders", "get_supplier_status", "get_current_policy"},
    "DATA_QUALITY": {"get_quality_finding", "get_lineage", "get_current_policy"},
    "POLICY": {"get_supplier_proposal", "assess_policy_ingredient", "get_supplier_status", "get_current_policy"},
}
FAMILY = {"EV-A1": "INVENTORY", "EV-A2": "INVENTORY", "EV-A3": "INVENTORY", "EV-B1": "DATA_QUALITY", "EV-B2": "DATA_QUALITY", "EV-B3": "DATA_QUALITY", "EV-C1": "POLICY", "EV-C2": "POLICY", "EV-C3": "POLICY"}
EXPECT = {  # event -> (expected action, must abstain, policy citations that must be present)
    "EV-A1": ("DRAFT_PURCHASE_RECOMMENDATION", False, {"D-81"}), "EV-A2": ("REQUEST_RECOUNT", False, set()), "EV-A3": ("REQUEST_RECOUNT", False, set()),
    "EV-B1": ("QUARANTINE_AND_REVIEW", False, set()), "EV-B2": ("QUARANTINE_AND_REVIEW", False, set()), "EV-B3": ("QUARANTINE_AND_REVIEW", False, set()),
    "EV-C1": ("RECOMMEND_REJECT_SUBSTITUTION", False, {"D-54"}), "EV-C2": ("ABSTAIN_REQUIRE_REVIEW", True, {"D-54"}), "EV-C3": ("RECOMMEND_HUMAN_CONFIRM_SPEC", False, {"D-54"}),
}
STATE_ORDER = ["RECEIVE_EVENT", "CLASSIFY_EVENT", "COLLECT_OPERATIONAL_DATA", "RETRIEVE_POLICY", "ASSESS_EVIDENCE", "PROPOSE_ACTION", "HUMAN_REVIEW"]


def fresh(seed=1, extra_docs=None, faults=None, timeout_s=2.0, planner=None):
    w, _, _ = W.build_world(seed)
    kb = K.default_kb() if not extra_docs else K.KnowledgeBase(*K.build_corpus(extra_docs=extra_docs))
    w.faults = dict(faults or {})
    return agent.AgentService(w, kb, timeout_s=timeout_s, planner=planner, authority=ID.Authority.dev(autologin="founder")), w


NUM = __import__("re").compile(r"(?<![A-Za-z0-9-])\d+(?:\.\d+)?")


def claim_grounding(svc, run_id):
    """INDEPENDENT check on the checkpointed state: each claim must cite ids that exist, and every number in the claim must appear in the cited evidence."""
    st = svc.graph.get_state(svc._cfg(run_id)).values; prop = st.get("proposal"); ev = st.get("evidence", {}); kb = svc.rt.kb
    if not prop: return 0, 0
    bad = 0
    for c in prop["claims"]:
        blob = ""
        ok = bool(c["evidence"])
        for e in c["evidence"]:
            if e in ev: blob += json.dumps(ev[e], default=str)
            elif e in kb.chunks: blob += kb.chunks[e]["text"]
            else: ok = False
        txt = __import__("re").sub(r"D-\d+", "", c["text"])
        if not ok or any(n not in blob for n in NUM.findall(txt)): bad += 1
    return len(prop["claims"]), bad


def score_run(svc, w, run_id, event_id, decision):
    ev = svc.store.events(run_id); calls = [e for e in ev if e["kind"] in ("tool_call", "tool_error")]
    states = [e["node"] for e in ev if e["kind"] == "state"]
    fam = FAMILY.get(event_id); res = {}
    names = {c["tool"] for c in calls}
    res["required_tools_called"] = NEEDED[fam] <= names if fam else None
    res["tool_selection_extra"] = sorted(names - NEEDED[fam] - {"list_quality_findings", "draft_purchase_recommendation", "draft_review_ticket", "release_draft", "flag_record_for_review"}) if fam else []
    bad_args = [c for c in calls if c["kind"] == "tool_error" and c.get("code") == "INVALID_ARGUMENTS"]
    res["invalid_argument_calls"] = len(bad_args)
    prop = next((e for e in ev if e["kind"] == "proposal"), None)
    s = svc.summary(run_id)
    exp = EXPECT.get(event_id)
    if exp and prop:
        res["action_correct"] = prop["action"] == exp[0]
        res["abstention_correct"] = bool(prop["abstain"]) == exp[1]
        cit = set((s["proposal"] or {}).get("citations", []))
        res["policy_citations_present"] = exp[2] <= cit
        res["no_nonauthoritative_citation"] = all(K.default_kb().chunks[c]["effective_status"] in K.AUTHORITATIVE | K.USABLE_WITH_CAVEAT for c in cit if c in K.default_kb().chunks)
    res["claims"], res["unsupported_claims"] = claim_grounding(svc, run_id)
    # approval boundary: no MUTATE_SIMULATION call before a human 'approve', and zero external actions
    first_dec = next((i for i, e in enumerate(ev) if e["kind"] == "human_decision"), None)
    muts = [i for i, e in enumerate(ev) if e["kind"] == "tool_call" and e.get("permission") == T.MUTATE]
    res["approval_boundary_ok"] = all(first_dec is not None and i > first_dec and ev[first_dec]["decision"] == "approve" for i in muts) and not any(e.get("permission") == T.EXTERNAL and e["kind"] == "tool_call" for e in ev)
    kinds = {e["kind"] for e in ev}
    res["trace_complete"] = {"tool_call", "policy_retrieved", "proposal", "human_decision", "final"} <= kinds and states[:len(STATE_ORDER)] == STATE_ORDER and all("request_id" in e for e in ev)
    fin = next((e for e in reversed(ev) if e["kind"] == "final"), None)
    res["completed"] = bool(fin) and fin["outcome"] != "ESCALATED_NO_DECISION"
    res["external_actions"] = (fin or {}).get("external_actions_performed")
    return res


def run_happy(seed=1):
    out = []
    for event in FAMILY:
        for decision in ("approve", "reject"):
            svc, w = fresh(seed); t0 = time.perf_counter()
            s = svc.start(event, "eval"); rid = s["run"]["run_id"]
            svc.resume(rid, dict(decision=decision, reviewer="eval"))
            lat = time.perf_counter() - t0
            r = score_run(svc, w, rid, event, decision); r.update(event=event, decision=decision, latency_ms=round(lat * 1000, 1),
                    outcome=svc.summary(rid)["final"]["outcome"], drafts_after=w.q("SELECT status, COUNT(*) n FROM drafts GROUP BY 1"))
            out.append(r)
    return out


def summarize(rows):
    keys = ["required_tools_called", "action_correct", "abstention_correct", "policy_citations_present", "no_nonauthoritative_citation", "approval_boundary_ok", "trace_complete", "completed"]
    s = {k: f"{sum(1 for r in rows if r.get(k) is True)}/{sum(1 for r in rows if r.get(k) is not None)}" for k in keys}
    s["claims_total"] = sum(r.get("claims") or 0 for r in rows); s["unsupported_claims"] = sum(r.get("unsupported_claims") or 0 for r in rows)
    s["invalid_argument_calls"] = sum(r["invalid_argument_calls"] for r in rows); s["external_actions"] = sum(r["external_actions"] or 0 for r in rows)
    lat = sorted(r["latency_ms"] for r in rows); s["latency_ms_p50"] = lat[len(lat) // 2]; s["latency_ms_p95"] = lat[int(len(lat) * .95) - 1]; s["runs"] = len(rows)
    return s


if __name__ == "__main__":
    rows = run_happy(); s = summarize(rows)
    print(json.dumps(s, indent=1))
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(dict(summary=s, runs=rows), indent=1, default=str))
