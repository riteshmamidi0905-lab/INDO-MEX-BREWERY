"""Planners: the DETERMINISTIC planner (control/baseline) and the LLM planner share one interface, one state, one tool layer.

  collect(state, call, trace)  -> gather operational evidence through `call(evidence, gaps, tool, args, label)`; every call is validated,
                                  permission-checked, timed and traced by tools.execute, whoever proposed it
  decide(state)                -> a proposal dict: action, claims (each with evidence ids), uncertainties, optional draft/ticket, mutating actions

A planner never executes anything and never grants itself a permission.
"""
import json
import re

from . import knowledge as K, tools as T

PROMPT_VERSION = "p1"


def get(ev, tool):
    for k, v in ev.items():
        if v["tool"] == tool and v["ok"]: return k, v["data"]
    return None, None

def claim(text, *ids): return dict(text=text, evidence=[i for i in ids if i])

def deterministic_decide(state):
    """Deterministic planner: evidence -> proposal. Every claim carries evidence ids; the validator removes any that do not resolve."""
    fam, ev, a = state["family"], state["evidence"], state["assessment"]; p = state["event"]["payload"]; claims, unc, mut, nots = [], [], [], []
    D54 = "D-54" if "D-54" in a["policy_citations"] else None
    D81 = "D-81" if "D-81" in a["policy_citations"] else None
    cites = a["policy_citations"]
    if fam == "INVENTORY":
        un, note = get(ev, "get_supplier_notes_untrusted")
        if note is not None: unc.append(("UNTRUSTED supplier-portal note (unverified, not used as evidence): " + _safe(note["data"]["note"])) if note["ok"] else "UNTRUSTED supplier-portal note unusable: " + ", ".join(note["flags"]))
        ie, inv = get(ev, "query_inventory"); re_, risk = get(ev, "assess_inventory_risk"); pe, pos = get(ev, "get_open_purchase_orders"); se, sup = get(ev, "get_supplier_status")
        if not inv or not risk:
            return dict(action="ESCALATE_INSUFFICIENT_EVIDENCE", headline="INSUFFICIENT VERIFIED EVIDENCE: inventory data could not be retrieved", claims=[], uncertainties=["inventory or risk tools failed: " + ", ".join(f'{g["tool"]}:{g["code"]}' for g in a["gaps"])], citations=cites,
                        abstain=True, ticket=dict(kind="INVENTORY_RECOUNT", summary=f"Inventory evidence unavailable for {p['location_id']} {p['ingredient']}; a human must check the data sources."), mutating_actions=[], not_proposed=["any purchase recommendation"])
        claims.append(claim(f"Latest valid count {inv['last_count_qty']} {inv['unit']} on {inv['last_count_date']}; estimated on hand {inv['on_hand_estimate']}; average use {inv['avg_daily_usage_14d']}/day; cover {inv['days_of_cover']} days.", ie))
        if risk["lead_time_days"] is not None: claims.append(claim(f"Supplier {risk['supplier_id']} lead time is {risk['lead_time_days']} days; {risk['open_po_qty_arriving_in_time']} kg on open orders arrives within it." + (f" Needed through the lead time beyond usable stock: {risk['required_qty_through_lead_kg']} kg; the open orders {'cover' if risk['po_covers_shortage'] else 'do not cover'} it." if risk.get("po_coverage_rule") == "v2" else ""), re_, pe))
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

def _safe(s):
    """Untrusted (supplier-controlled) text is never echoed bare: it is capped, stripped of markup and wrapped as a quoted, marked span."""
    t = str(s)
    if K.INJECTION_RE.search(t): return "[withheld: possible instruction in data]"
    return "\u27e6untrusted: " + re.sub(r"[<>`$]", "", t)[:80] + "\u27e7"

def _policy_unc(a, D81):
    u = []
    if not a["policy_found"]: u.append("No authoritative NASHA policy was retrieved for this question: INSUFFICIENT VERIFIED EVIDENCE")
    elif D81 is None: u.append("D-81 (zero-dollar build) was not retrieved; spending authority is unconfirmed")
    return u



class DeterministicPlanner:
    """CONTROL planner: fixed evidence checklist per event family, rules over evidence. No model."""
    name, version, model = "deterministic", "d1", None

    def collect(self, state, call, trace):
        ev, gaps = {}, []; p = state["event"]["payload"]
        if state["family"] == "INVENTORY":
            loc, ing = p["location_id"], p["ingredient"]
            call(ev, gaps, "query_inventory", dict(location_id=loc, ingredient=ing))
            call(ev, gaps, "assess_inventory_risk", dict(location_id=loc, ingredient=ing))
            call(ev, gaps, "get_open_purchase_orders", dict(ingredient=ing))
            se, sd = call(ev, gaps, "get_supplier_status", dict(ingredient=ing))
            if sd["ok"] and sd["data"]["suppliers"]: call(ev, gaps, "get_supplier_notes_untrusted", dict(supplier_id=sd["data"]["suppliers"][0]["supplier_id"]))
            eid, e = call(ev, gaps, "list_quality_findings", dict(rule="unit_mismatch", limit=100))
            if e["ok"]:
                rel = [f for f in e["data"]["findings"] if f["key"].startswith(loc + ":") and f["key"].endswith(":" + ing)]
                ev[eid]["relevant"] = rel
        elif state["family"] == "DATA_QUALITY":
            eid, e = call(ev, gaps, "get_quality_finding", dict(finding_id=p["finding_id"]) if p.get("finding_id") else dict(finding_id=1_000_000))
            if e["ok"]:
                f = e["data"]; call(ev, gaps, "get_lineage", dict(table=f["table"], key=f["key"]))
        elif state["family"] == "POLICY":
            eid, e = call(ev, gaps, "get_supplier_proposal", dict(proposal_id=p["proposal_id"]))
            if e["ok"]:
                d = e["data"]
                call(ev, gaps, "assess_policy_ingredient", dict(ingredient_text=d["ingredient_text"], declared_source=d["declared_source"], spec_sheet_status=d["spec_sheet_status"]))
                call(ev, gaps, "get_supplier_status", dict(supplier_id=d["supplier_id"]))
        return ev, gaps

    def decide(self, state, trace=None):
        return deterministic_decide(state)


def action_envelope(state):
    """Deterministic GUARDRAIL: the set of actions that the tool evidence permits, whoever the planner is. It never picks an action; it only
    forbids actions that are LESS conservative than the evidence allows (e.g. 'cleared' when the screening tool said the source is not established)."""
    fam, ev, a = state["family"], state["evidence"], state["assessment"]
    ESC = "ESCALATE_INSUFFICIENT_EVIDENCE"
    if fam == "INVENTORY":
        _, inv = get(ev, "query_inventory"); _, risk = get(ev, "assess_inventory_risk"); _, sup = get(ev, "get_supplier_status")
        if not inv or not risk: return {ESC}
        bad = list(inv["data_flags"]) + ([] if risk["count_variance_ratio"] is None or 0.4 <= risk["count_variance_ratio"] <= 2 else ["COUNT_VARIANCE"])
        if bad: return {"REQUEST_RECOUNT", ESC}
        if risk["shortfall_before_lead_time"]:
            if not sup: return {ESC}
            if not [s for s in sup["suppliers"] if s["status"] == "ACTIVE"]: return {"ESCALATE_SUPPLIER_UNAVAILABLE", ESC}
            return {"DRAFT_PURCHASE_RECOMMENDATION", ESC, "REQUEST_RECOUNT"}
        return {"NO_ACTION", "REQUEST_RECOUNT", ESC} if not [g for g in a["gaps"] if "INJECTION" not in g["code"]] else {"REQUEST_RECOUNT", ESC}
    if fam == "DATA_QUALITY":
        _, f = get(ev, "get_quality_finding")
        return {"QUARANTINE_AND_REVIEW", ESC} if f else {ESC}
    _, asm = get(ev, "assess_policy_ingredient")
    if not asm or not a["policy_citations"]: return {"ABSTAIN_REQUIRE_REVIEW"}
    return {"PROHIBITED": {"RECOMMEND_REJECT_SUBSTITUTION", "ABSTAIN_REQUIRE_REVIEW"}, "CLEARED_PENDING_HUMAN": {"RECOMMEND_HUMAN_CONFIRM_SPEC", "ABSTAIN_REQUIRE_REVIEW"},
            "REQUIRES_REVIEW": {"ABSTAIN_REQUIRE_REVIEW"}, "NO_POLICY_SIGNAL": {"ABSTAIN_REQUIRE_REVIEW", "RECOMMEND_HUMAN_CONFIRM_SPEC"}}[asm["verdict"]]
