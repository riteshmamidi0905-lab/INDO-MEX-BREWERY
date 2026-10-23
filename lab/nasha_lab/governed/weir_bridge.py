"""THE WEIR wiring for the governed workflow: a per-role policy (default deny), the warehouse read upstream, and the procurement write upstream.

Layers, each of which would stop an unauthorised purchase on its own:
  1. identity   - the requester must hold a valid session of THIS tenant's authority, with a role allowed to start a procurement run (tenant authority = tenant boundary).
  2. THE WEIR   - the per-role policy lists the tools that role may call at all; anything else is denied before any upstream runs. The procurement write tool has effect=write under
                  gate_write=approve, so even an allowed role's call is HELD until a human approves that exact call (bound to the call hash, the session, a TTL, single use).
  3. upstream   - the procurement upstream re-validates the call against the ledger and the warehouse (proposal exists and is open, arguments identical, recommendation still current,
                  quote exists, quantity/amount caps) and writes only through the ledger, whose schema cannot represent a sent order.
"""
import inspect
import json
import re
import sqlite3
from typing import Any

from ..warehouse.ops_ai import TOOLS, OpsAI, Principal
from ..warehouse.ops_ai_weir import OpsAIUpstream
from .agent import MAX_PO_USD, MAX_QTY_FACTOR
from .ledger import Ledger, LedgerError

PROC_TOOL = "procurement__create_draft_purchase_order"
READ_ROLES = {"BUYER": "analyst", "QUALITY_LEAD": "analyst", "FOUNDER": "exec"}         # governed-workflow role -> Ops AI role
PROCUREMENT_ROLES = {"BUYER", "FOUNDER"}                                                  # roles whose policy contains the procurement write tool
INITIATE_ROLES = {"BUYER", "FOUNDER", "QUALITY_LEAD"}


def policy_for(role, ttl=900):
    """Default-deny policy for one role. Tools not listed do not exist for that role."""
    tools: dict[str, Any] = {}
    for n in TOOLS:
        if n == "supplier_notes":
            tools[f"warehouse__{n}"] = {"effect": "read", "result": {"conf": "internal", "integ": "untrusted"}}      # supplier-written text: untrusted integrity
        else:
            tools[f"warehouse__{n}"] = {"effect": "read", "result": {"conf": "internal"}}
    upstreams = {"warehouse": {"command": ["python", "-c", "pass"]}}
    if role in PROCUREMENT_ROLES:
        tools[PROC_TOOL] = {"effect": "write", "target": {"proposal_id": "other"}, "content": ["note"]}
        upstreams["procurement"] = {"command": ["python", "-c", "pass"]}
    return {"policy": {"name": f"nasha-governed-{role.lower()}", "internal_domains": ["corp.example"], "approval_ttl_seconds": ttl},
            "rules": {"gate_write": "approve", "gate_egress": "deny", "flow_conf_secret": "deny", "untrusted_read": "approve", "dest_untrusted": "approve"},
            "upstreams": upstreams, "tools": tools}


def ops_principal(identity, tenant_sites=None):
    return Principal(identity.id, READ_ROLES.get(identity.role, "analyst"))


class ProcurementUpstream:
    """The only write path: create a DRAFT purchase order. Context (approval id, approver, correlation id) is set by the orchestrator, never by the agent's arguments."""
    name = "procurement"

    def __init__(self, ledger: Ledger, warehouse_path, tenant_id, fault=None):
        self.ledger, self.wh, self.tenant, self.fault, self.calls = ledger, str(warehouse_path), tenant_id, fault, 0
        self.context = None                                                # {approval_id, approved_by, corr_id}
        self.after_fault = None                                            # test hook: awaited AFTER a successful write (simulates a lost response / crash after commit)

    async def start(self):
        return None

    async def close(self):
        return None

    async def list_tools(self):
        return [{"name": "create_draft_purchase_order", "description": "Create a DRAFT purchase order from an approved proposal. Never transmits.", "inputSchema": {"type": "object", "additionalProperties": True}}]

    def _reject(self, code, msg=""):
        return {"content": [{"type": "text", "text": json.dumps({"error": code, "detail": msg})}], "isError": True}

    async def call_tool(self, name, arguments, timeout):
        self.calls += 1
        if self.fault:                                                      # fault injection hook for failure-path tests: returns a result or raises
            injected = self.fault(self, name, arguments)
            if inspect.isawaitable(injected):
                injected = await injected
            if injected is not None:
                return injected
        if name != "create_draft_purchase_order":
            return self._reject("UNKNOWN_TOOL")
        ctx = self.context
        if not ctx or not ctx.get("approval_id") or not ctx.get("approved_by"):
            return self._reject("NO_APPROVAL_CONTEXT", "the write was not reached through the approval path")
        a = arguments
        for k in ("proposal_id", "reco_id", "inputs_hash", "qty", "est_cost_usd", "supplier_id", "quote_id", "idempotency_key"):
            if k not in a:
                return self._reject("MISSING_ARGUMENT", k)
        p = self.ledger.proposal(a["proposal_id"])
        if p is None:
            return self._reject("NO_SUCH_PROPOSAL")
        if p["state"] != "PROPOSED":
            if p["state"] == "APPROVED":
                po, _ = self.ledger.create_po_draft(a["proposal_id"], ctx["approval_id"], ctx["approved_by"], a["idempotency_key"], ctx["corr_id"])
                return {"content": [{"type": "text", "text": json.dumps({"po_id": po, "state": "DRAFT_NOT_SENT", "duplicate": True})}], "isError": False}
            return self._reject("PROPOSAL_NOT_OPEN", p["state"])
        for k_a, k_p in (("reco_id", "reco_id"), ("inputs_hash", "inputs_hash"), ("supplier_id", "supplier_id"), ("quote_id", "quote_id")):
            if a[k_a] != p[k_p]:
                return self._reject("PROPOSAL_MISMATCH", k_a)
        if abs(float(a["qty"]) - p["qty"]) > 1e-9:
            return self._reject("PROPOSAL_MISMATCH", "qty")
        if abs(float(a["est_cost_usd"]) - p["est_cost_usd"]) > 1e-9:
            return self._reject("PROPOSAL_MISMATCH", "est_cost_usd")
        if not p["evidence_ids"]:
            return self._reject("MISSING_EVIDENCE")
        con = sqlite3.connect(f"file:{self.wh}?mode=ro", uri=True)
        try:
            reco = con.execute("SELECT order_qty, est_cost_usd, inputs_hash, status FROM scn_procurement_reco WHERE reco_id=?", (p["reco_id"],)).fetchone()
            quote = con.execute("SELECT valid_from, valid_to, price_class FROM scn_supplier_quote WHERE quote_id=? AND supplier_id=? AND ingredient_id=?", (p["quote_id"], p["supplier_id"], p["ingredient_id"])).fetchone()
            sup = con.execute("SELECT 1 FROM scn_supplier WHERE supplier_id=?", (p["supplier_id"],)).fetchone()
        finally:
            con.close()
        if reco is None or reco[2] != p["inputs_hash"] or reco[3] != "PROPOSED":
            return self._reject("STALE_PROPOSAL", "the recommendation changed or no longer exists")
        if not sup or quote is None:
            return self._reject("SUPPLIER_DATA_MISSING")
        if p["qty"] > reco[0] * MAX_QTY_FACTOR + 1e-9:
            return self._reject("UNSAFE_QUANTITY")
        if abs(p["est_cost_usd"] - reco[1] * p["qty"] / max(reco[0], 1e-9)) > 0.02:       # the amount must still be what the recommendation implies for this quantity (a tampered cost is not approvable)
            return self._reject("PROPOSAL_MISMATCH", "est_cost_usd_vs_recommendation")
        if p["est_cost_usd"] > MAX_PO_USD:
            return self._reject("UNSAFE_AMOUNT")
        try:
            po, dup = self.ledger.create_po_draft(p["proposal_id"], ctx["approval_id"], ctx["approved_by"], a["idempotency_key"], ctx["corr_id"])
        except LedgerError as e:
            return self._reject(e.code)
        except sqlite3.Error as e:
            return self._reject("DATABASE_ERROR", type(e).__name__)
        if self.after_fault:
            r = self.after_fault(self, po)
            if inspect.isawaitable(r):
                r = await r
            if r is not None:
                return r
        return {"content": [{"type": "text", "text": json.dumps({"po_id": po, "state": "DRAFT_NOT_SENT", "duplicate": dup})}], "isError": False}


def make_upstreams(env, ops: OpsAI, who: Principal, ledger: Ledger, role: str, fault=None, warehouse_wrapper=None):
    """Upstreams for ONE role's gateway. The procurement upstream exists only for roles whose policy contains the write tool."""
    wh = OpsAIUpstream(ops, who)
    if warehouse_wrapper:
        wh = warehouse_wrapper(wh)
    ups = {"warehouse": wh}
    proc = None
    if role in PROCUREMENT_ROLES:
        proc = ProcurementUpstream(ledger, env.warehouse, env.tenant_id, fault=fault)
        ups["procurement"] = proc
    return ups, proc
