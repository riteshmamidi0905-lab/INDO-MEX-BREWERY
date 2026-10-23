"""Presentation layer for Growth OS: turns the SAME stored records (workflow run, recorded events, proposal, lead, audit rows) into plain business language.
Nothing here decides anything or invents anything: every sentence is derived from a recorded value, and every timeline entry carries the sequence number of the recorded event it came from, plus the raw
event for the Engineering view. If a record is missing the sentence says so rather than filling a gap."""
import re


def short(n):
    """Display name without the '(synthetic ...)' tag; the application as a whole already says the data is synthetic."""
    return re.sub(r"\s*\(synthetic[^)]*\)\s*$", "", n) if isinstance(n, str) else n


STATE_LABEL = {"STARTED": "In progress", "EVIDENCE_COLLECTED": "In progress", "PROPOSED": "In progress", "AWAITING_APPROVAL": "Awaiting approval", "APPROVED": "Approved",
               "EXECUTED": "Completed", "REJECTED": "Rejected", "ABSTAINED": "Needs more information", "BLOCKED": "Blocked", "FAILED": "Failed"}
TONE = {"AWAITING_APPROVAL": "wait", "APPROVED": "ok", "EXECUTED": "ok", "REJECTED": "no", "BLOCKED": "no", "FAILED": "no", "ABSTAINED": "wait"}
WHY = {"TOOL_DENIED": "This user's role does not have permission to update a lead's qualification status. THE WEIR blocked the action before it reached the CRM.",
       "ROLE_DENIED": "This role may not take that action.", "MAKER_CHECKER": "The person who requested an action may not approve it themselves.",
       "SUPPRESSED_CONTACT": "The contact is suppressed or has opted out, so no qualification was proposed or applied.", "INVALID_SOURCE": "The lead source is not a synthetic source, so it was refused.",
       "STALE_PROPOSAL": "The lead changed after the recommendation was made, so the approved action no longer applies. A new recommendation is needed.",
       "APPROVAL_EXPIRED": "The approval window ended before a decision was made.", "APPROVAL_REPLAY": "That approval was already used once and cannot be used again.",
       "REAPPROVAL_REQUIRED": "The action no longer matches what was approved, so a new approval is required.", "INVALID_EVIDENCE": "The recorded qualification facts are missing or invalid, so the system abstained instead of guessing.",
       "VALIDATION_FAILED": "An independent check rejected the recommendation.", "DUPLICATE_REQUEST": "This request had already been submitted; the original run was returned.",
       "NOT_AWAITING_APPROVAL": "This request is not waiting for a decision.", "NO_SUCH_LEAD": "The lead was not found in this workspace.", "AUTH_DENIED": "The session was not valid.",
       "TOOL_TIMEOUT": "A tool did not answer in time.", "DB_ERROR": "The database reported an error.", "TOOL_ERROR": "A tool reported an error.", "TOOL_BAD_RESPONSE": "A tool returned an unreadable response.",
       "APPROVAL_MISMATCH": "The approval does not belong to this request."}
TOOL = {"growth__get_lead_context": "read the lead's details", "crm__apply_lead_qualification": "update the lead's qualification status"}
FACTOR_ORDER = ["budget", "decision_maker", "timeline", "fit", "engagement"]
THRESHOLD = 60


def state_label(state):
    return STATE_LABEL.get(state, state)


def why(failure):
    k = str(failure or "").split(":")[0]
    return WHY.get(k, f"Stopped: {failure}" if failure else None)


def name(names, uid):
    return names.get(uid, uid) if uid else "someone"


def event_entry(e, names, lead=None, run=None):
    """One recorded event -> {seq, ts, title, detail, tone, technical}. Returns None for events with no business meaning (they remain visible in the Engineering view)."""
    k, n = e.get("kind"), e.get("name")
    who = lambda: name(names, e.get("by") or e.get("user"))
    title = detail = None; tone = "info"
    if n == "request_received":
        title = f"Qualification requested by {name(names, (run or {}).get('requester'))}"
    elif k == "auth":
        title, detail = f"Identity confirmed: {who()} ({str(e.get('role', '')).title()})", "Signed in to this workspace only."
    elif k == "tool_call":
        tool = TOOL.get(e.get("tool"), e.get("tool"))
        if e.get("held_for_approval"):
            title, detail, tone = f"Action held: {tool}", "THE WEIR does not run this kind of change until a different, authorised person approves it.", "wait"
        elif e.get("failure") == "TOOL_DENIED":
            title, detail, tone = f"Action blocked: {tool}", "This user's role does not have permission to do that. No CRM changes were made.", "no"
        elif e.get("forwarded") and e.get("ok") and e.get("stage") == "G03":
            title, detail, tone = "Lead details read through THE WEIR", "Read-only access was allowed for this role.", "ok"
        elif e.get("forwarded") and e.get("ok"):
            title, detail, tone = f"Approved action released: {tool}", "THE WEIR forwarded the identical approved call once.", "ok"
        elif e.get("failure"):
            title, tone = f"Tool problem while trying to {tool}", "no"; detail = WHY.get(e["failure"])
    elif n == "evidence_collected":
        ev = e.get("evidence") or {}
        title = "Evidence gathered"; detail = f"Source: {str(ev.get('source', 'unknown')).replace('synthetic-', '').replace('-', ' ')}. Consent: {str(ev.get('consent_status', 'unknown')).replace('_', ' ')}. Suppressed: {'yes' if ev.get('suppressed') else 'no'}."
    elif n == "source_and_consent_validated":
        title, tone = "Source and consent checks passed", "ok"
        detail = "Outreach is allowed because consent is recorded." if e.get("outreach_allowed") else "Outreach is NOT allowed because no consent is recorded. Only the qualification can be recorded."
    elif n == "recommendation":
        title, detail = f"Recommendation: {e.get('proposed_status')} (score {e.get('score')} of 100)", "Each factor and its points are shown under Qualification."
    elif n == "proposal":
        title, detail = "Proposed CRM update prepared", "The exact change was fingerprinted so only this change can be approved."
    elif n == "held_for_approval":
        title, detail, tone = "Waiting for a human decision", "Nothing has changed in the CRM.", "wait"
    elif n == "weir_denied":
        title, tone = "Blocked by THE WEIR", "no"
    elif k == "approval_decision":
        d = e.get("decision")
        if d == "approve":
            title, detail, tone = f"Approved by {who()}", e.get("comment") or None, "ok"
        elif d == "reject":
            title, detail, tone = f"Rejected by {who()}", e.get("comment") or None, "no"
        else:
            title, detail, tone = "Approval refused", WHY.get(e.get("code")) or {"ROLE_NOT_PERMITTED": "That role cannot approve this action."}.get(e.get("code")), "no"
            if e.get("user"):
                title = f"Approval refused for {who()}"
    elif n == "crm_updated":
        title, detail, tone = f"CRM updated: lead marked {e.get('lead_status')}", "Applied once, under the approval above.", "ok"
    elif n == "no_external_contact":
        title, detail, tone = "No email or message was sent", "Qualifying a lead never contacts anyone.", "ok"
    elif k == "failure":
        title, detail, tone = "Stopped", WHY.get(e.get("failure_class")) or e.get("detail"), "no"
    elif k == "recovery":
        title, detail, tone = "Recovered after a lost response", "The CRM was checked and the update had already been applied.", "ok"
    if title is None:
        return None
    return dict(seq=e["seq"], ts=e["ts"], title=title, detail=detail, tone=tone, technical=e)


def factors(proposal):
    out = []
    for r in (proposal or {}).get("reasons", []):
        out.append(dict(factor=r.get("factor"), label=r.get("label") or r.get("text"), points=r.get("points"), max_points=r.get("max_points"), explanation=r.get("explanation") or r.get("text")))
    return sorted(out, key=lambda f: FACTOR_ORDER.index(f["factor"]) if f["factor"] in FACTOR_ORDER else 99)


def outcome(state, run, proposal, lead, approver=None):
    who = (lead or {}).get("prospect", "the prospect")
    st = (proposal or {}).get("proposed_status")
    if state == "EXECUTED":
        return f"{who} was marked {st} in the CRM after approval" + (f" by {approver}" if approver else "") + ". No message was sent."
    if state == "AWAITING_APPROVAL":
        return f"A person must decide whether to mark {who} as {st}. Nothing has changed yet."
    if state == "REJECTED":
        return f"The recommendation was rejected. {who}'s CRM record is unchanged."
    if state in ("BLOCKED", "FAILED", "ABSTAINED"):
        return (why(run.get("failure")) or "The run stopped.") + (" No CRM changes were made." if state != "FAILED" else "")
    return "The run is in progress."


def next_action(state, run, proposal, lead):
    st = (proposal or {}).get("proposed_status")
    if state == "AWAITING_APPROVAL":
        return f"An owner other than the requester reviews the evidence and approves or rejects marking the lead {st}."
    if state == "EXECUTED":
        return "Open the opportunity and plan the follow-up conversation." if st == "qualified" else "Keep the lead for a later review; no sales follow-up is recommended now."
    if state == "REJECTED":
        return "Gather the missing facts (budget, decision maker, timeline) and request a new qualification."
    if state == "ABSTAINED":
        return "Record the qualification facts for this lead, then request qualification again."
    if state == "BLOCKED":
        if str(run.get("failure") or "").split(":")[0] in ("TOOL_DENIED", "ROLE_DENIED"):
            return "Ask a user whose role may qualify leads (Sales or Owner) to start it."
        if str(run.get("failure") or "").startswith("SUPPRESSED_CONTACT"):
            return "Do not contact this person. Review the suppression record before any further action."
        return "Resolve the blocking reason above; nothing was changed."
    return None


def run_business(run, events, lead, names):
    """The business view of one run. `run` and `events` are the stored records; `lead` is the lead_view; `names` maps user ids to display names."""
    state, proposal = run["state"], run.get("proposal")
    ents = [x for x in (event_entry(e, names, lead, run) for e in events) if x]
    decisions = [e for e in events if e["kind"] == "approval_decision"]
    last = decisions[-1] if decisions else None
    approved = [e for e in decisions if e.get("decision") == "approve"]
    approval = dict(state=state if state in ("AWAITING_APPROVAL", "APPROVED", "EXECUTED", "REJECTED", "BLOCKED", "FAILED") else None, label=state_label(state), tone=TONE.get(state, "info"),
                    can_decide=(state == "AWAITING_APPROVAL"), requested_by=name(names, run.get("requester")), decided_by=name(names, approved[-1].get("by")) if approved else (name(names, last.get("by")) if last and last.get("by") else None),
                    comment=(last or {}).get("comment") if last and last.get("decision") in ("approve", "reject") else None)
    auth = [dict(seq=x["seq"], title=x["title"], detail=x["detail"], tone=x["tone"], technical=x["technical"]) for x in ents if x["technical"]["kind"] in ("auth", "tool_call", "approval_decision") or x["technical"].get("name") == "weir_denied"]
    qual = None
    if proposal:
        qual = dict(verdict=proposal["proposed_status"], score=proposal["score"], threshold=THRESHOLD, factors=factors(proposal), outreach_allowed=proposal.get("outreach_allowed"),
                    recommended_action=f"Mark the lead {proposal['proposed_status']}." + (" Follow-up outreach is allowed." if proposal.get("outreach_allowed") else " Outreach is not allowed until consent is recorded."),
                    why=f"{(lead or {}).get('prospect', 'The lead')} scores {proposal['score']} out of 100; a score of {THRESHOLD} or more qualifies.",
                    limitations=["This is a transparent rule-based score over the recorded facts, not a validated model of buying behaviour.", "All people and organisations are synthetic."])
    return dict(summary=dict(workflow="Lead qualification", objective=f"Decide whether {(lead or {}).get('prospect', 'this prospect')} at {(lead or {}).get('organization', 'this organisation')} is a qualified sales lead",
                             prospect=(lead or {}).get("prospect"), job_title=(lead or {}).get("job_title"), organization=(lead or {}).get("organization"), inquiry=(lead or {}).get("inquiry"),
                             scenario=(lead or {}).get("scenario"), owner=short((lead or {}).get("owner")), requested_by=name(names, run.get("requester")), status=state, status_label=state_label(state), tone=TONE.get(state, "info"),
                             last_activity=events[-1]["ts"] if events else None, outcome=outcome(state, run, proposal, lead, approval['decided_by']), next_action=next_action(state, run, proposal, lead)),
                qualification=qual, authorization=auth, approval=approval, timeline=ents)


AUDIT = {"lead.qualification_applied": "marked {entity} {status} (score {score}) after approval by {approved_by}", "lead.create": "created lead {entity}", "contact.create": "added contact {entity}", "account.create": "added organisation {entity}",
         "contact.consent": "updated consent for {entity}", "suppression.add": "added {entity} to the suppression list", "lead.convert": "converted {entity} into an opportunity", "opportunity.advance": "moved {entity} to a new pipeline stage",
         "lead.qualify": "qualified {entity} directly", "activity.log": "logged an activity on {entity}", "price.set": "set a price", "product.create": "added a product",
         "project.create": "created the launch project {entity}", "project.stage": "moved {entity} to a new stage", "project.assumption": "set a planning assumption", "milestone.write": "updated the milestone {entity}", "finding.add": "added a research finding",
         "supplier.add": "added supplier information for {entity}", "supplier.shortlist": "updated the supplier shortlist", "scenario.save": "saved the financial scenario {entity}", "procurement.record": "recorded the {entity} after approval by {approved_by}"}


def audit_summary(row, names, entity_names):
    """row: dict(actor, role, action, entity, entity_id, decision, detail). Sentence for the business view; the raw row stays available."""
    who = name(names, row["actor"]); ent = entity_names.get(row.get("entity_id"), "a record")
    d = row.get("detail") or {}
    if row["decision"] == "deny":
        return f"{who} ({str(row['role']).title()}) was refused: {row['action'].replace('.', ' ')}" + (f" ({d['why']})" if d.get("why") else "")
    tpl = AUDIT.get(row["action"])
    text = tpl.format(entity=ent, status=d.get("status", ""), score=d.get("score", ""), approved_by=name(names, d.get("approved_by"))) if tpl else row["action"].replace(".", " ")
    return f"{who} {text}"


# ---------------------------------------------------------------- launch workspace: procurement recommendation runs
LAUNCH_TOOL = {"launch__get_supplier_data": "read the project's supplier data", "procure__record_recommendation": "record the procurement recommendation"}
LAUNCH_WHY = dict(WHY, NO_VALID_QUOTES="No valid priced supplier quote exists for the needed ingredients on the planning date, so no recommendation was made.", NO_SCENARIO="The project has no products with a price and unit cost, so no demand could be planned.",
                  NO_SUCH_PROJECT="The project was not found in this workspace.", STALE_PROPOSAL="Supplier quotes or the financial scenario changed after the recommendation was made, so it was not recorded. A new recommendation is needed.",
                  TOOL_DENIED="This user's role does not have permission to record a procurement recommendation. THE WEIR blocked the action. Nothing was recorded.")
AGENT_LABEL = {"engine_offline_heuristic": "Production AI Agent Platform engine, offline heuristic provider (deterministic; not a language model)", "engine_model": "Production AI Agent Platform engine with a language-model provider",
               "deterministic_fallback": "No agent ran: a deterministic read of stored supplier data was used"}


def launch_event_entry(e, names, run=None):
    k, n = e.get("kind"), e.get("name")
    who = lambda: name(names, e.get("by") or e.get("user"))
    title = detail = None; tone = "info"
    if n == "request_received":
        title = f"Procurement recommendation requested by {name(names, (run or {}).get('requester'))}"; detail = f"Planning period: {e.get('period_weeks')} weeks."
    elif k == "auth":
        title, detail = f"Identity confirmed: {who()} ({str(e.get('role', '')).title()})", "Signed in to this workspace only."
    elif k == "tool_call":
        tool = LAUNCH_TOOL.get(e.get("tool"), e.get("tool"))
        if e.get("held_for_approval"):
            title, detail, tone = f"Action held: {tool}", "THE WEIR does not run this kind of change until a different, authorised person approves it.", "wait"
        elif e.get("failure") == "TOOL_DENIED":
            title, detail, tone = f"Action blocked: {tool}", "This user's role does not have permission to do that. Nothing was recorded.", "no"
        elif e.get("forwarded") and e.get("ok") and e.get("stage") == "P03":
            title, detail, tone = "Supplier data read through THE WEIR", "Read-only access was allowed for this role.", "ok"
        elif e.get("forwarded") and e.get("ok"):
            title, detail, tone = f"Approved action released: {tool}", "THE WEIR forwarded the identical approved call once.", "ok"
        elif e.get("failure"):
            title, tone, detail = f"Tool problem while trying to {tool}", "no", LAUNCH_WHY.get(e["failure"])
    elif n == "data_read":
        title, detail = "Project and supplier data gathered", f"{e.get('suppliers')} suppliers on record, {e.get('priced_suppliers')} with prices."
    elif n == "demand_and_needs":
        title, detail = "Demand and ingredient needs calculated", f"{e.get('ingredients')} ingredients needed, from the financial scenario and the recipe bill of materials."
    elif n == "agent_research":
        title = "Supplier research brief prepared by the agent"
        detail = f"{e.get('claims')} cited claims from {e.get('evidence')} supplier passages; " + ("independent check found no problem." if not e.get("independent_problems") else "independent check rejected it: " + "; ".join(e["independent_problems"])[:160])
        tone = "ok" if not e.get("independent_problems") else "no"
    elif n == "agent_fallback":
        title, detail, tone = "No agent research used", f"{e.get('reason') or 'unavailable'}. A deterministic read of stored supplier data was used instead; the recommendation itself is unaffected.", "wait"
    elif n == "recommendation":
        title, detail = "Recommendation calculated", f"Planned spend {AR_money(e.get('total_cost_cents'))} across {e.get('suppliers')} suppliers, cheapest valid quote per ingredient."
    elif n == "independent_check":
        title, detail, tone = "Independent check passed", e.get("result"), "ok"
    elif n == "proposal":
        title, detail = "Proposed record prepared", "The exact recommendation was fingerprinted so only this one can be approved."
    elif n == "held_for_approval":
        title, detail, tone = "Waiting for a human decision", "Nothing has been recorded.", "wait"
    elif n == "weir_denied":
        title, tone = "Blocked by THE WEIR", "no"
    elif k == "approval_decision":
        d = e.get("decision")
        if d == "approve":
            title, detail, tone = f"Approved by {who()}", e.get("comment") or None, "ok"
        elif d == "reject":
            title, detail, tone = f"Rejected by {who()}", e.get("comment") or None, "no"
        else:
            title, detail, tone = "Approval refused", LAUNCH_WHY.get(e.get("code")) or {"ROLE_NOT_PERMITTED": "That role cannot approve this action."}.get(e.get("code")), "no"
    elif n == "recommendation_recorded":
        title, detail, tone = "Recommendation recorded", "Recorded once, under the approval above.", "ok"
    elif n == "no_order_no_contact":
        title, detail, tone = "No order was placed and no supplier was contacted", "Recording a recommendation never buys or contacts anything.", "ok"
    elif k == "failure":
        title, detail, tone = "Stopped", LAUNCH_WHY.get(e.get("failure_class")) or e.get("detail"), "no"
    if title is None:
        return None
    return dict(seq=e["seq"], ts=e["ts"], title=title, detail=detail, tone=tone, technical=e)


def AR_money(c):
    return "—" if c is None else f"${c / 100:,.2f}"


BOUNDARY_TEXT = {"MALFORMED": "the output was not in the required structure", "NO_EVIDENCE": "a claim cited no source", "UNKNOWN_EVIDENCE": "a claim cited a source that does not exist", "UNSUPPORTED_NUMBER": "a claim contained a number its cited source does not contain",
                 "PRICE_MISMATCH": "a claim stated a price that does not match any stored price", "UNKNOWN_SUPPLIER": "a claim named a supplier that is not in the directory", "WRONG_SOURCE": "a claim about a supplier cited another supplier's record",
                 "UNSUPPORTED_VERIFICATION": "a claim called an unverified supplier verified", "UNSUPPORTED_RECOMMENDATION": "the agent tried to make the recommendation, which only the calculation may do",
                 "INSTRUCTION_TEXT": "the output contained instruction-like text", "TOOL_NOT_ALLOWED": "the agent used a tool outside the read-only list"}


def launch_run_business(run, events, project, names):
    state, plan, research = run["state"], run.get("items"), run.get("research")
    ents = [x for x in (launch_event_entry(e, names, run) for e in events) if x]
    decisions = [e for e in events if e["kind"] == "approval_decision"]
    approved = [e for e in decisions if e.get("decision") == "approve"]
    last = decisions[-1] if decisions else None
    approval = dict(label=state_label(state), tone=TONE.get(state, "info"), can_decide=(state == "AWAITING_APPROVAL"), requested_by=name(names, run.get("requester")),
                    decided_by=name(names, approved[-1].get("by")) if approved else (name(names, last.get("by")) if last and last.get("by") else None),
                    comment=(last or {}).get("comment") if last and last.get("decision") in ("approve", "reject") else None)
    rec = None
    if plan:
        by = {}
        for it in plan["items"]:
            c = it["chosen"]
            if c:
                by.setdefault(c["supplier"], []).append(dict(ingredient=it["ingredient"], need=it["need_qty"], unit=it["unit"], buy_qty=c["buy_qty"], cost_cents=c["cost_cents"], lead_days=c["lead_days"], price_class=c["price_class"],
                                                             runner_up=it["runner_up"]))
        rec = dict(period_weeks=plan["period_weeks"], total_cost_cents=plan["total_cost_cents"], suppliers=[dict(supplier=t["supplier"], cost_cents=t["cost_cents"], items=t["items"], below_minimum_order=t["below_minimum_order"], price_classes=t["price_classes"],
                   lines=sorted(by.get(t["supplier"], []), key=lambda x: -x["cost_cents"])) for t in plan["supplier_totals"]], flags=plan["flags"], portions=plan["portions"], replenishment=plan.get("replenishment", []), replenishment_assumption=plan.get("replenishment_assumption"), price_effect=plan.get("price_effect"), disclaimer=plan["disclaimer"])
    brief = None
    if research:
        brief = dict(mode=research["mode"], mode_label=AGENT_LABEL.get(research["mode"], research["mode"]), title=research["report"]["title"], answer=research["report"]["answer"], claims=[c["text"] for c in research["report"]["claims"]],
                     limitations=research["report"]["limitations"], fallback_reason=research.get("fallback_reason"), rejected=bool(research.get("rejected_agent_output")),
                     rejected_reasons=[BOUNDARY_TEXT.get(c, c) for c in ((research.get("rejected_agent_output") or {}).get("codes") or [])], uncertainty=(research.get("boundary") or {}).get("uncertainty", []),
                     boundary=(research.get("boundary") or {}).get("status"), model_backed=research["mode"] == "engine_model")
    outcome = {"EXECUTED": f"The recommendation for {run['period']} was recorded after approval. No order was placed and no supplier was contacted.", "AWAITING_APPROVAL": "A person must decide whether to record this recommendation. Nothing has been recorded or ordered.",
               "REJECTED": "The recommendation was rejected. Nothing was recorded."}.get(state) or ((LAUNCH_WHY.get(str(run.get("failure") or "").split(":")[0]) or "The run stopped.") + " Nothing was recorded.")
    return dict(summary=dict(workflow="Procurement recommendation", objective=f"Recommend the cheapest valid supplier quotes for {project['name'] if project else 'the project'} over {run['period']}", project=(project or {}).get("name"),
                             industry=(project or {}).get("industry"), period=run["period"], requested_by=name(names, run.get("requester")), status=state, status_label=state_label(state), tone=TONE.get(state, "info"),
                             last_activity=events[-1]["ts"] if events else None, outcome=outcome, agent=AGENT_LABEL.get(run.get("agent_mode"), None)),
                recommendation=rec, research=brief, authorization=[x for x in ents if x["technical"]["kind"] in ("auth", "tool_call", "approval_decision") or x["technical"].get("name") == "weir_denied"], approval=approval, timeline=ents)
