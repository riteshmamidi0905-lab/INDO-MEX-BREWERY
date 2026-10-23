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
         "lead.qualify": "qualified {entity} directly", "activity.log": "logged an activity on {entity}", "price.set": "set a price", "product.create": "added a product"}


def audit_summary(row, names, entity_names):
    """row: dict(actor, role, action, entity, entity_id, decision, detail). Sentence for the business view; the raw row stays available."""
    who = name(names, row["actor"]); ent = entity_names.get(row.get("entity_id"), "a record")
    d = row.get("detail") or {}
    if row["decision"] == "deny":
        return f"{who} ({str(row['role']).title()}) was refused: {row['action'].replace('.', ' ')}" + (f" ({d['why']})" if d.get("why") else "")
    tpl = AUDIT.get(row["action"])
    text = tpl.format(entity=ent, status=d.get("status", ""), score=d.get("score", ""), approved_by=name(names, d.get("approved_by"))) if tpl else row["action"].replace(".", " ")
    return f"{who} {text}"
