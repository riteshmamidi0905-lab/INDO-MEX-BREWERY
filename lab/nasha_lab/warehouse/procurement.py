"""Procurement recommendations -> human approval -> DRAFT purchase order. Nothing here ever places an order.

An AI/system principal may PROPOSE (store a recommendation with its inputs hash and rationale). Only a human approver role may approve or reject; the approver must
differ from the proposer; approval needs a comment; an approved recommendation yields a DRAFT_NOT_SENT purchase-order draft, which is a record, not a transmission to
a supplier. Every transition is appended to a SHA-256 hash chain, so any later edit of history is detectable.
Behind THE WEIR the write tool `procurement__propose_purchase_order` has effect=write under rule gate_write=approve: the gateway holds the call until a human resolves it.
"""
import hashlib
import json
import sqlite3
import time

HUMAN_ROLES = {"founder", "head_chef", "finance", "procurement_manager"}
PROPOSER_ROLES = {"agent", "system", "analyst"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS reco (reco_id TEXT PRIMARY KEY, payload TEXT, inputs_hash TEXT, proposed_by TEXT, status TEXT, decided_by TEXT, decision_comment TEXT);
CREATE TABLE IF NOT EXISTS po_draft (po_id TEXT PRIMARY KEY, reco_id TEXT, supplier_id TEXT, lines TEXT, est_cost_usd REAL, state TEXT, price_class TEXT);
CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, role TEXT, action TEXT, reco_id TEXT, detail TEXT, prev_hash TEXT, hash TEXT);
"""


class ProcurementError(Exception):
    pass


def _h(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


class ProcurementStore:
    def __init__(self, path=":memory:"):
        self.con = sqlite3.connect(str(path))
        self.con.executescript(SCHEMA)

    def _log(self, actor, role, action, reco_id, detail=""):
        prev = (self.con.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone() or ("GENESIS",))[0]
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.con.execute("INSERT INTO audit (ts,actor,role,action,reco_id,detail,prev_hash,hash) VALUES (?,?,?,?,?,?,?,?)", (ts, actor, role, action, reco_id, detail, prev, _h(prev, ts, actor, role, action, reco_id, detail)))
        self.con.commit()

    def verify_audit(self):
        prev = "GENESIS"
        for seq, ts, actor, role, action, rid, detail, p, h in self.con.execute("SELECT seq,ts,actor,role,action,reco_id,detail,prev_hash,hash FROM audit ORDER BY seq"):
            if p != prev or h != _h(p, ts, actor, role, action, rid, detail):
                return False, seq
            prev = h
        return True, None

    def propose(self, reco: dict, actor: str, role: str):
        """reco: dict with reco_id, supplier_id, ingredient_id, location_id, order_qty, unit, est_cost_usd, price_class, inputs_hash, rationale."""
        if role not in PROPOSER_ROLES | HUMAN_ROLES:
            raise ProcurementError(f"role '{role}' may not propose")
        if reco.get("price_class") not in ("SYNTHETIC_QUOTE", "PLANNING_ASSUMPTION", "SUPPLIER_QUOTE", "PUBLIC_REFERENCE"):
            raise ProcurementError("recommendation must carry a price class")
        if self.con.execute("SELECT 1 FROM reco WHERE reco_id=?", (reco["reco_id"],)).fetchone():
            return reco["reco_id"]                                               # idempotent
        self.con.execute("INSERT INTO reco VALUES (?,?,?,?,?,?,?)", (reco["reco_id"], json.dumps(reco, sort_keys=True, default=str), reco["inputs_hash"], actor, "PROPOSED", None, None))
        self.con.commit()
        self._log(actor, role, "propose", reco["reco_id"], f"inputs={reco['inputs_hash']}")
        return reco["reco_id"]

    def _get(self, reco_id):
        r = self.con.execute("SELECT payload, proposed_by, status FROM reco WHERE reco_id=?", (reco_id,)).fetchone()
        if not r:
            raise ProcurementError(f"no such recommendation {reco_id}")
        return json.loads(r[0]), r[1], r[2]

    def approve(self, reco_id, approver, role, comment):
        payload, proposer, status = self._get(reco_id)
        if role not in HUMAN_ROLES:
            raise ProcurementError(f"role '{role}' may not approve: only a human approver ({sorted(HUMAN_ROLES)})")
        if approver == proposer:
            raise ProcurementError("maker-checker: approver must differ from proposer")
        if not comment or not comment.strip():
            raise ProcurementError("an approval needs a comment")
        if status != "PROPOSED":
            raise ProcurementError(f"only a PROPOSED recommendation can be approved (is {status})")
        self.con.execute("UPDATE reco SET status='APPROVED', decided_by=?, decision_comment=? WHERE reco_id=?", (approver, comment.strip(), reco_id))
        po_id = "PO-DRAFT-" + _h(reco_id)[:10]
        self.con.execute("INSERT INTO po_draft VALUES (?,?,?,?,?,?,?)", (po_id, reco_id, payload["supplier_id"], json.dumps([{"ingredient_id": payload["ingredient_id"], "qty": payload["order_qty"], "unit": payload["unit"]}]),
                                                                            payload["est_cost_usd"], "DRAFT_NOT_SENT", payload["price_class"]))
        self.con.commit()
        self._log(approver, role, "approve", reco_id, comment.strip())
        return po_id

    def reject(self, reco_id, actor, role, comment):
        _, _, status = self._get(reco_id)
        if role not in HUMAN_ROLES:
            raise ProcurementError("only a human approver may reject")
        if status != "PROPOSED":
            raise ProcurementError(f"only a PROPOSED recommendation can be rejected (is {status})")
        self.con.execute("UPDATE reco SET status='REJECTED', decided_by=?, decision_comment=? WHERE reco_id=?", (actor, comment, reco_id))
        self.con.commit()
        self._log(actor, role, "reject", reco_id, comment)

    def status(self, reco_id):
        return self._get(reco_id)[2]

    def po_drafts(self):
        return self.con.execute("SELECT po_id, reco_id, supplier_id, est_cost_usd, state, price_class FROM po_draft ORDER BY po_id").fetchall()


def load_recos(wh_path, limit=None, location_id=None):
    """Read PROPOSED recommendations out of the scenario table as dicts."""
    con = sqlite3.connect(f"file:{wh_path}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(scn_procurement_reco)")]
    q = "SELECT * FROM scn_procurement_reco" + (" WHERE location_id=?" if location_id else "") + " ORDER BY est_cost_usd DESC, reco_id" + (f" LIMIT {int(limit)}" if limit else "")
    rows = [dict(zip(cols, r)) for r in con.execute(q, (location_id,) if location_id else ())]
    con.close()
    return rows


class ProcurementUpstream:
    """mcp_weir Upstream: exposes ONE write tool. The gateway policy marks it effect=write with gate_write=approve, so it is forwarded only after human approval;
    even then the tool only stores a PROPOSAL (status PROPOSED) - approval of the purchase itself is a separate human step in the store."""
    name = "procurement"

    def __init__(self, store: ProcurementStore, recos: dict, actor="ops-ai-agent", role="agent"):
        self.store, self.recos, self.actor, self.role, self.calls = store, recos, actor, role, 0

    async def start(self):
        return None

    async def close(self):
        return None

    async def list_tools(self):
        return [{"name": "propose_purchase_order", "description": "Store a reorder PROPOSAL for human review (does not order).", "inputSchema": {"type": "object", "additionalProperties": True}}]

    async def call_tool(self, name, arguments, timeout):
        self.calls += 1
        try:
            if name != "propose_purchase_order":
                raise ProcurementError("unknown tool")
            reco = self.recos[arguments["reco_id"]]
            rid = self.store.propose(reco, self.actor, self.role)
            return {"content": [{"type": "text", "text": json.dumps({"reco_id": rid, "status": self.store.status(rid)})}], "isError": False}
        except (ProcurementError, KeyError) as e:
            return {"content": [{"type": "text", "text": f"denied: {e}"}], "isError": True}


def weir_policy_with_procurement(base):
    """Extend the Ops AI WEIR policy with the procurement write tool (gate_write=approve already applies to effect=write)."""
    base["tools"]["procurement__propose_purchase_order"] = {"effect": "write", "target": {"reco_id": "other"}, "content": ["note"]}
    base["upstreams"]["procurement"] = {"command": ["python", "-c", "pass"]}
    return base
