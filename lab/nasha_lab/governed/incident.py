"""Incident investigation over ONE correlation id (D-89). Answers, from recorded data only: who asked, which tenant, what the agent attempted, which tools ran, what evidence was retrieved,
which policy applied, why an action was blocked, and whether any side effect occurred. Reads the run trace, the ledger (audit chain, proposals, drafts) and THE WEIR approval store.
The report never contains session tokens, passcodes or signing secrets (verified by test); identities are the synthetic reviewer ids."""
import json

from . import weir_bridge as WB


def investigate(wf, corr_id):
    run = wf.ledger.run(corr_id)
    tr = wf.trace.run(corr_id)
    events = wf.trace.events(corr_id)
    if run is None and tr is None:
        return {"corr_id": corr_id, "tenant": wf.env.tenant_id, "found": False, "answer": "No such correlation id in this tenant's stores."}
    who = (run or {})
    tools = [dict(stage=e.get("stage"), tool=e.get("tool"), forwarded=e.get("forwarded"), held_for_approval=bool(e.get("held_for_approval")), weir_codes=e.get("codes"), failure=e.get("failure"), ms=e.get("ms")) for e in events if e["kind"] == "tool_call"]
    retrieval = next((e for e in events if e["kind"] == "stage" and e.get("name") == "retrieval_complete"), None)
    evidence = [dict(id=x["id"], ok=x["ok"], trust=x["trust"], injection_flagged=x["injection"], source=(x.get("provenance") or {}).get("source") or (x.get("provenance") or {}).get("synthetic")) for x in (retrieval or {}).get("evidence", [])]
    explanation = next((e for e in events if e["kind"] == "stage" and e.get("name") == "explanation"), None)
    failures = [dict(failure_class=e.get("failure_class"), detail=e.get("detail")) for e in events if e["kind"] == "failure"]
    auth = [dict(decision=e.get("decision"), code=e.get("code"), role=e.get("role")) for e in events if e["kind"] in ("auth", "approval_decision")]
    role = who.get("role")
    policy = WB.policy_for(role) if role else None
    approvals = [dict(id=a.id, state=wf.weir.latest_approval_state(a.session_id, a.call_hash) or a.state, tool=a.tool, resolved_by=a.resolved_by, rules=a.rules, expires=a.expires) for a in wf.weir.list_approvals() if a.session_id == corr_id]
    pos = [dict(po_id=r[0], state=r[4], supplier=r[2], est_cost_usd=r[3]) for r in wf.ledger.con.execute(
        "SELECT po_id, proposal_id, supplier_id, est_cost_usd, state FROM po_drafts WHERE proposal_id IN (SELECT proposal_id FROM proposals WHERE corr_id=?)", (corr_id,))]
    blocked_by = None
    for t in tools:
        if t["tool"] == WB.PROC_TOOL and t["forwarded"] is False and not t["held_for_approval"]:
            blocked_by = dict(layer="THE WEIR", reason="the procurement write tool is not in this role's policy (default deny)", role=role, policy_tools_for_role=sorted(policy["tools"]) if policy else None, codes=t["weir_codes"])
    if blocked_by is None and failures:
        blocked_by = dict(layer="workflow", reason=failures[-1]["failure_class"], detail=failures[-1]["detail"])
    ok_chain, bad_seq = wf.ledger.verify_audit()
    side = dict(purchase_orders_created=len(pos), draft_orders=pos, external_transmissions=0, ledger_audit_chain_valid=ok_chain, weir_chain_valid=wf.weir.verify_chain()[0])
    rep = {"corr_id": corr_id, "tenant": wf.env.tenant_id, "found": True,
           "who": dict(requester=who.get("requester"), role=role),
           "attempted": dict(location_id=who.get("location_id"), ingredient_id=who.get("ingredient_id"), proposal_id=who.get("proposal_id"), final_state=who.get("state"), failure=who.get("failure")),
           "tools_called": tools, "evidence_retrieved": evidence, "agent_explanation": dict(planner=(explanation or {}).get("planner"), claims_kept=(explanation or {}).get("claims_kept"), claims_dropped=(explanation or {}).get("claims_dropped"),
                                                                                              final_action=(explanation or {}).get("final_action"), violations=(explanation or {}).get("violations")),
           "authorization": dict(events=auth, policy_rules=(policy or {}).get("rules"), approvals=approvals), "why_blocked": blocked_by, "failures": failures, "side_effects": side,
           "audit_rows": [dict(action=a["action"], role=a["role"], ref=a["ref"]) for a in wf.ledger.audit_rows(corr_id)]}
    rep["answers"] = _answers(rep)
    return rep


def _answers(r):
    side, why = r["side_effects"], r["why_blocked"]
    return {"Who initiated the request?": f"{r['who']['requester']} ({r['who']['role']})", "Which tenant?": r["tenant"],
            "What did the agent attempt?": f"{r['attempted']['ingredient_id']} at {r['attempted']['location_id']}; final state {r['attempted']['final_state']}",
            "Which tools were called?": [f"{t['tool']} ({'held' if t['held_for_approval'] else 'forwarded' if t['forwarded'] else 'blocked'})" for t in r["tools_called"] if t["tool"]],
            "What evidence was retrieved?": [f"{e['id']} [{e['trust']}{', injection flagged' if e['injection_flagged'] else ''}]" for e in r["evidence_retrieved"]],
            "Which policy applied?": (why or {}).get("policy_tools_for_role") and f"per-role WEIR policy for {r['who']['role']}" or f"per-role WEIR policy for {r['who']['role']} (gate_write=approve)",
            "Why was the action blocked?": why or "not blocked (completed or awaiting approval)",
            "Did any side effect occur?": f"{side['purchase_orders_created']} draft purchase order(s); 0 external transmissions; audit chain valid: {side['ledger_audit_chain_valid']}"}


def render_markdown(r):
    if not r["found"]:
        return f"# Incident {r['corr_id']}\n\n{r['answer']}\n"
    out = [f"# Incident report `{r['corr_id']}` · tenant `{r['tenant']}`", ""]
    for q, a in r["answers"].items():
        out += [f"**{q}**", "", (a if isinstance(a, str) else "\n".join(f"- {x}" for x in a) if isinstance(a, list) else f"`{json.dumps(a, default=str)}`"), ""]
    out += ["## Audit rows", ""] + [f"- {x['action']} · {x['role'] or '-'} · {x['ref'] or ''}" for x in r["audit_rows"]]
    return "\n".join(out) + "\n"
