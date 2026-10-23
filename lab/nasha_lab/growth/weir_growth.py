"""THE WEIR wiring for Growth OS. Reuses the SAME gateway and approval store as the procurement workflow: a per-role default-deny policy, a read upstream, and one write upstream
(`crm__apply_lead_qualification`, effect=write, gate_write=approve, so every call is HELD until a different, authorised person approves that exact call: bound to the call hash, the session,
a TTL and single use). No separate authorization framework exists here; the service layer's role policy and the database's row-level security are additional layers beneath it."""
import inspect
import json

from .service import Blocked, Denied, GrowthService
from . import qualification as Q

CRM_TOOL = "crm__apply_lead_qualification"
READ_TOOL = "growth__get_lead_context"
INITIATE_ROLES = {"SALES", "OWNER"}                  # roles whose policy contains the write tool
READ_ROLES = {"SALES", "OWNER", "ANALYST", "MARKETING"}


def policy_for(role, ttl=900):
    tools, upstreams = {}, {}
    if role in READ_ROLES:
        tools[READ_TOOL] = {"effect": "read", "result": {"conf": "internal"}}
        upstreams["growth"] = {"command": ["python", "-c", "pass"]}
    if role in INITIATE_ROLES:
        tools[CRM_TOOL] = {"effect": "write", "target": {"proposal_id": "other"}, "content": ["note"]}
        upstreams["crm"] = {"command": ["python", "-c", "pass"]}
    return {"policy": {"name": f"growth-os-{role.lower()}", "internal_domains": ["corp.example"], "approval_ttl_seconds": ttl},
            "rules": {"gate_write": "approve", "gate_egress": "deny", "flow_conf_secret": "deny", "untrusted_read": "approve", "dest_untrusted": "approve"}, "upstreams": upstreams, "tools": tools}


def _ok(obj):
    return {"content": [{"type": "text", "text": json.dumps(obj, default=str)}], "isError": False}


def _err(code, detail=""):
    return {"content": [{"type": "text", "text": json.dumps({"error": code, "detail": detail})}], "isError": True}


class GrowthReadUpstream:
    name = "growth"

    def __init__(self, svc: GrowthService, fault=None):
        self.svc, self.fault, self.calls = svc, fault, 0

    async def start(self):
        return None

    async def close(self):
        return None

    async def list_tools(self):
        return [{"name": "get_lead_context", "description": "Read one lead, its contact's consent/suppression status and recorded signals (this tenant only).", "inputSchema": {"type": "object", "additionalProperties": True}}]

    async def call_tool(self, name, arguments, timeout):
        self.calls += 1
        if self.fault:
            r = self.fault(self, name, arguments)
            r = await r if inspect.isawaitable(r) else r
            if r is not None:
                return r
        if name != "get_lead_context":
            return _err("UNKNOWN_TOOL")
        lead_id = arguments.get("lead_id")
        if not isinstance(lead_id, str) or not lead_id:
            return _err("BAD_ARGUMENT", "lead_id")
        try:
            ctx = self.svc.get_lead_context(lead_id)
        except Denied as e:
            return _err("DENIED", str(e))
        return _ok({"rows": [ctx] if ctx else [], "provenance": {"tenant": self.svc.tenant, "synthetic": True}})


class CrmUpstream:
    """The only write path for qualification. The approval context is set by the orchestrator, never by the arguments, and the upstream re-validates everything against the stored proposal."""
    name = "crm"

    def __init__(self, svc: GrowthService, store, fault=None):
        self.svc, self.store, self.fault, self.calls, self.context, self.after_fault = svc, store, fault, 0, None, None

    async def start(self):
        return None

    async def close(self):
        return None

    async def list_tools(self):
        return [{"name": "apply_lead_qualification", "description": "Apply an approved qualification to a lead. Updates the CRM record only; sends nothing.", "inputSchema": {"type": "object", "additionalProperties": True}}]

    async def call_tool(self, name, arguments, timeout):
        self.calls += 1
        if self.fault:
            r = self.fault(self, name, arguments)
            r = await r if inspect.isawaitable(r) else r
            if r is not None:
                return r
        if name != "apply_lead_qualification":
            return _err("UNKNOWN_TOOL")
        ctx = self.context
        if not ctx or not ctx.get("approval_id") or not ctx.get("approved_by"):
            return _err("NO_APPROVAL_CONTEXT", "the write was not reached through the approval path")
        a = arguments
        for k in ("proposal_id", "lead_id", "status", "score", "expected_lead_version", "evidence_hash"):
            if k not in a:
                return _err("MISSING_ARGUMENT", k)
        run = self.store.run(ctx["corr_id"])
        if run is None or run["proposal"] is None:
            return _err("NO_SUCH_PROPOSAL")
        p = run["proposal"]
        if run["state"] not in ("APPROVED",):
            return _err("PROPOSAL_NOT_OPEN", run["state"])
        if a["proposal_id"] != ctx["corr_id"] or a["lead_id"] != p["lead_id"] or a["status"] != p["proposed_status"] or a["score"] != p["score"] or a["expected_lead_version"] != p["expected_lead_version"] or a["evidence_hash"] != run["proposal_hash"]:
            return _err("PROPOSAL_MISMATCH")
        live = self.svc.get_lead_context(p["lead_id"])
        if live is None:
            return _err("NO_SUCH_LEAD")
        if live["suppressed"] or live["consent_status"] == "opt_out":
            return _err("SUPPRESSED_CONTACT")
        already = self.svc.qualified_by(p["lead_id"]) == ctx["corr_id"]
        if not already:
            if live["lead_version"] != p["expected_lead_version"]:
                return _err("STALE_PROPOSAL", "the lead changed since the proposal")
            problems = Q.validate_recommendation(p, dict(live, lead_version=p["expected_lead_version"]))
            if problems:
                return _err("VALIDATION_FAILED", problems[0])
        try:
            self.svc.apply_qualification(p["lead_id"], p["proposed_status"], p["score"], p["expected_lead_version"], ctx["corr_id"], ctx["approval_id"], ctx["approved_by"])
        except Blocked as e:
            return _err("BLOCKED", str(e))
        except Denied as e:
            return _err("DENIED", str(e))
        if self.after_fault:
            r = self.after_fault(self, p["lead_id"])
            r = await r if inspect.isawaitable(r) else r
            if r is not None:
                return r
        return _ok({"lead_id": p["lead_id"], "status": p["proposed_status"], "applied": True, "emails_sent": 0})

