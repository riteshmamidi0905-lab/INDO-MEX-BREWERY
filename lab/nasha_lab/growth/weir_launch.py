"""THE WEIR wiring for the launch workspace: the SAME gateway and approval store as Growth OS lead qualification and the procurement lab. A per-role default-deny policy, one read upstream (supplier data for a project)
and one write upstream (`procure__record_recommendation`, effect=write, gate_write=approve): every call is HELD until a different, authorised person approves that exact call (bound to call hash and session, with a time limit
and single use). No second authorization framework exists here."""
import inspect
import json

from .service import Blocked, Denied, GrowthService
from . import launch as L, procurement as PRC

WRITE_TOOL = "procure__record_recommendation"
READ_TOOL = "launch__get_supplier_data"
INITIATE_ROLES = {"OWNER", "ANALYST"}
READ_ROLES = {"OWNER", "ANALYST", "SALES", "MARKETING"}


def policy_for(role, ttl=900):
    tools, upstreams = {}, {}
    if role in READ_ROLES:
        tools[READ_TOOL] = {"effect": "read", "result": {"conf": "internal"}}; upstreams["launch"] = {"command": ["python", "-c", "pass"]}
    if role in INITIATE_ROLES:
        tools[WRITE_TOOL] = {"effect": "write", "target": {"proposal_id": "other"}, "content": ["note"]}; upstreams["procure"] = {"command": ["python", "-c", "pass"]}
    return {"policy": {"name": f"launch-{role.lower()}", "internal_domains": ["corp.example"], "approval_ttl_seconds": ttl},
            "rules": {"gate_write": "approve", "gate_egress": "deny", "flow_conf_secret": "deny", "untrusted_read": "approve", "dest_untrusted": "approve"}, "upstreams": upstreams, "tools": tools}


def _ok(obj):
    return {"content": [{"type": "text", "text": json.dumps(obj, default=str)}], "isError": False}


def _err(code, detail=""):
    return {"content": [{"type": "text", "text": json.dumps({"error": code, "detail": detail})}], "isError": True}


class _Upstream:
    def __init__(self, fault=None):
        self.fault, self.calls = fault, 0

    async def start(self):
        return None

    async def close(self):
        return None

    async def _fault(self, name, arguments):
        if self.fault:
            r = self.fault(self, name, arguments)
            return await r if inspect.isawaitable(r) else r
        return None


class LaunchReadUpstream(_Upstream):
    name = "launch"

    def __init__(self, svc: GrowthService, as_of, fault=None):
        super().__init__(fault); self.svc, self.as_of = svc, as_of

    async def list_tools(self):
        return [{"name": "get_supplier_data", "description": "Read one launch project, its financial scenario and this tenant's supplier records (this tenant only).", "inputSchema": {"type": "object", "additionalProperties": True}}]

    async def call_tool(self, name, arguments, timeout):
        self.calls += 1
        r = await self._fault(name, arguments)
        if r is not None:
            return r
        if name != "get_supplier_data":
            return _err("UNKNOWN_TOOL")
        pid = arguments.get("project_id")
        if not isinstance(pid, str) or not pid:
            return _err("BAD_ARGUMENT", "project_id")
        try:
            ov = self.svc.project_overview(pid)
            if ov is None:
                return _ok({"project": None})
            pc = self.svc.procurement_context(pid)
            return _ok({"project": dict(id=ov["id"], name=ov["name"], industry=ov["industry"], location=ov["location"], stage=ov["stage"]), "scenario": pc["scenario"], "requirements": pc["requirements"], "use_recipes": pc["use_recipes"],
                        "directory": self.svc.supplier_directory(self.as_of, pid), "provenance": {"tenant": self.svc.tenant, "synthetic": True}})
        except Denied as e:
            return _err("DENIED", str(e))
        except ValueError as e:
            return _err("NO_SCENARIO", str(e))


class ProcureUpstream(_Upstream):
    """The only write path. The approval context comes from the orchestrator, never from the arguments; everything is re-validated against the stored proposal and re-derived from CURRENT data."""
    name = "procure"

    def __init__(self, svc: GrowthService, store, as_of, fault=None):
        super().__init__(fault); self.svc, self.store, self.as_of, self.context = svc, store, as_of, None

    async def list_tools(self):
        return [{"name": "record_recommendation", "description": "Record an approved procurement recommendation. Records only; places no order and contacts no supplier.", "inputSchema": {"type": "object", "additionalProperties": True}}]

    async def call_tool(self, name, arguments, timeout):
        self.calls += 1
        r = await self._fault(name, arguments)
        if r is not None:
            return r
        if name != "record_recommendation":
            return _err("UNKNOWN_TOOL")
        ctx = self.context
        if not ctx or not ctx.get("approval_id") or not ctx.get("approved_by"):
            return _err("NO_APPROVAL_CONTEXT", "the write was not reached through the approval path")
        for k in ("proposal_id", "project_id", "proposal_hash", "period_weeks"):
            if k not in arguments:
                return _err("MISSING_ARGUMENT", k)
        run = self.store.run(ctx["corr_id"])
        if run is None or run["items"] is None:
            return _err("NO_SUCH_PROPOSAL")
        if run["state"] != "APPROVED":
            return _err("PROPOSAL_NOT_OPEN", run["state"])
        if arguments["proposal_id"] != ctx["corr_id"] or arguments["project_id"] != run["project_id"] or arguments["proposal_hash"] != run["proposal_hash"]:
            return _err("PROPOSAL_MISMATCH")
        # re-derive from CURRENT data: quotes that expired or changed since the proposal make it stale
        try:
            pc = self.svc.procurement_context(run["project_id"])
            plan = PRC.plan(self.svc.supplier_directory(self.as_of, run["project_id"]), pc["scenario"], int(arguments["period_weeks"]), self.as_of, pc["requirements"], pc["use_recipes"])
        except (ValueError, Denied) as e:
            return _err("STALE_PROPOSAL", str(e))
        if PRC.digest(plan) != run["proposal_hash"]:
            return _err("STALE_PROPOSAL", "supplier quotes or the financial scenario changed since the recommendation was made")
        try:
            self.svc.record_procurement(ctx["corr_id"], ctx["approval_id"], ctx["approved_by"])
        except Blocked as e:
            return _err("BLOCKED", str(e))
        except Denied as e:
            return _err("DENIED", str(e))
        return _ok({"recorded": True, "run_id": ctx["corr_id"], "orders_placed": 0, "suppliers_contacted": 0})
