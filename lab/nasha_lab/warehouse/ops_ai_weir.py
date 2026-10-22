"""Ops AI warehouse tools behind THE WEIR (the real mcp_weir Gateway) — SYNTHETIC data.

Layering (defence in depth): THE WEIR decides first (policy per tool, labels, egress/approval rules, tamper-evident audit chain); only a call it
FORWARDS reaches the Ops AI upstream, which applies its own default-deny role/site gate and writes its own audit row. Neither layer trusts the other.
Warehouse results are labelled `internal` in the WEIR policy, so an agent that read warehouse data cannot publish it through an egress tool.

The two audits are joined by `call_hash`: sha256 of WEIR's canonical {"tool": "warehouse__<name>", "args": ...}, which the upstream recomputes
from exactly what it was given, so a WEIR event and an Ops AI audit row for the same call can be matched without any shared secret.
Requires the separate THE WEIR package (mcp_weir, weir_testbed); this module imports nothing from it at import time so the lab works without it.
"""
import hashlib
import json
import sqlite3
from typing import Any

from .ops_ai import TOOLS, OpsAI, Principal

SERVER = "warehouse"


def _canonical(obj):                       # must equal mcp_weir.store.canonical
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def call_hash(tool_full_name, args):
    return hashlib.sha256(_canonical({"tool": tool_full_name, "args": args}).encode()).hexdigest()


class OpsAIUpstream:
    """Implements mcp_weir's Upstream protocol for the Ops AI tools, bound to ONE principal (one gateway per principal)."""

    def __init__(self, ops: OpsAI, who: Principal):
        self.name, self.ops, self.who, self.calls = SERVER, ops, who, 0
        ops.audit.execute("CREATE TABLE IF NOT EXISTS ops_ai_weir_link (call_id TEXT PRIMARY KEY, call_hash TEXT)")

    async def start(self):
        return None

    async def close(self):
        return None

    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "inputSchema": {"type": "object", "additionalProperties": True}} for t in TOOLS.values()]

    async def call_tool(self, name: str, arguments: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls += 1
        r = self.ops.call(self.who, name, arguments)
        self.ops.audit.execute("INSERT OR REPLACE INTO ops_ai_weir_link VALUES (?,?)", (r["call_id"], call_hash(f"{SERVER}__{name}", arguments)))
        self.ops.audit.commit()
        if not r["ok"]:
            return {"content": [{"type": "text", "text": f"denied: {r['code']}"}], "isError": True}
        return {"content": [{"type": "text", "text": json.dumps({"rows": r["rows"], "provenance": r["provenance"]}, default=str)}], "isError": False}


def policy(read_label="internal"):
    tools = {f"{SERVER}__{n}": {"effect": "read", "result": {"conf": read_label}} for n in TOOLS}
    tools["notes__save_note"] = {"effect": "write", "target": {"title": "other"}, "content": ["body"]}
    tools["notes__publish_note"] = {"effect": "egress", "content": ["title", "body"]}
    return {"policy": {"name": "nasha-ops-ai-warehouse", "internal_domains": ["corp.example"], "approval_ttl_seconds": 30},
            "rules": {"gate_write": "approve", "gate_egress": "deny", "flow_conf_secret": "deny", "untrusted_read": "approve"},
            "upstreams": {SERVER: {"command": ["python", "-c", "pass"]}, "notes": {"command": ["python", "-m", "weir_testbed.servers", "notes"]}},
            "tools": tools}


def joined_audit(weir_store, session_id, ops: OpsAI):
    """Match every WEIR call decision of a session to the Ops AI audit row it caused (or None when WEIR blocked it before the upstream)."""
    rows = {h[:16]: cid for cid, h in ops.audit.execute("SELECT call_id, call_hash FROM ops_ai_weir_link")}      # WEIR stores a 16-hex prefix of the hash in its events
    out = []
    for ev in weir_store.events(session_id):
        if ev["kind"] == "call.decision":
            p = ev["payload"] if isinstance(ev["payload"], dict) else json.loads(ev["payload"])
            h = (p.get("call_hash") or "")[:16]
            out.append({"weir_call_id": p.get("call"), "tool": p.get("tool"), "verdict": p.get("verdict") or p.get("decision"), "ops_call_id": rows.get(h)})
    return out
