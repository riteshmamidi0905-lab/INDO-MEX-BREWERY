"""Per-tenant procurement ledger (SQLite, hardened): proposals, DRAFT purchase orders, run state and a hash-chained audit trail.

Integrity is enforced by the database, not only by Python: foreign keys, CHECK constraints (a purchase order can ONLY be in state DRAFT_NOT_SENT: there is no value that
means "sent"), UNIQUE keys that make writes idempotent, and transactions (BEGIN IMMEDIATE) around every multi-row change. One ledger file per tenant: tenants never share it.
"""
import hashlib
import json
import sqlite3
import threading
import time

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
  corr_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, requester TEXT NOT NULL, role TEXT NOT NULL, location_id TEXT NOT NULL, ingredient_id TEXT,
  idem_key TEXT, state TEXT NOT NULL CHECK (state IN ('STARTED','EVIDENCE_COLLECTED','PROPOSED','AWAITING_APPROVAL','APPROVED','EXECUTED','ABSTAINED','BLOCKED','REJECTED','FAILED')),
  proposal_id TEXT, approval_id TEXT, failure TEXT, created REAL NOT NULL, updated REAL NOT NULL,
  UNIQUE (tenant_id, idem_key)
);
CREATE TABLE IF NOT EXISTS proposals (
  proposal_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, corr_id TEXT NOT NULL REFERENCES runs(corr_id), reco_id TEXT NOT NULL, ingredient_id TEXT NOT NULL, location_id TEXT NOT NULL,
  supplier_id TEXT NOT NULL, quote_id TEXT NOT NULL, qty REAL NOT NULL CHECK (qty > 0), unit TEXT NOT NULL, est_cost_usd REAL NOT NULL CHECK (est_cost_usd >= 0),
  price_class TEXT NOT NULL CHECK (price_class IN ('PLANNING_ASSUMPTION','SYNTHETIC_QUOTE','PUBLIC_REFERENCE','SUPPLIER_QUOTE')), inputs_hash TEXT NOT NULL,
  evidence_ids TEXT NOT NULL, explanation TEXT NOT NULL, state TEXT NOT NULL CHECK (state IN ('PROPOSED','APPROVED','REJECTED')), created REAL NOT NULL,
  UNIQUE (tenant_id, reco_id, inputs_hash)
);
CREATE TABLE IF NOT EXISTS po_drafts (
  po_id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL UNIQUE REFERENCES proposals(proposal_id), tenant_id TEXT NOT NULL, supplier_id TEXT NOT NULL, lines TEXT NOT NULL,
  est_cost_usd REAL NOT NULL CHECK (est_cost_usd >= 0), state TEXT NOT NULL CHECK (state = 'DRAFT_NOT_SENT'), approval_id TEXT NOT NULL, approved_by TEXT NOT NULL,
  idem_key TEXT NOT NULL UNIQUE, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, tenant_id TEXT NOT NULL, corr_id TEXT, actor TEXT NOT NULL, role TEXT, action TEXT NOT NULL, ref TEXT, detail TEXT,
  prev_hash TEXT NOT NULL, hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_runs_tenant_state ON runs(tenant_id, state);
CREATE INDEX IF NOT EXISTS ix_audit_corr ON audit(corr_id);
CREATE INDEX IF NOT EXISTS ix_proposals_corr ON proposals(corr_id);
"""


class LedgerError(Exception):
    def __init__(self, code, msg=""):
        super().__init__(f"{code}: {msg}" if msg else code)
        self.code = code


def _h(*p):
    return hashlib.sha256("|".join(map(str, p)).encode()).hexdigest()


class Ledger:
    def __init__(self, path, tenant_id, clock=time.time):
        self.path, self.tenant, self.clock = str(path), tenant_id, clock
        self.con = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)       # explicit transactions below
        self.lock = threading.RLock()
        self.con.executescript(SCHEMA)

    def close(self):
        self.con.close()

    # ----------------------------------------------------------------- transactions
    def _tx(self, fn):
        with self.lock:
            self.con.execute("BEGIN IMMEDIATE")
            try:
                out = fn()
                self.con.execute("COMMIT")
                return out
            except BaseException:
                self.con.execute("ROLLBACK")
                raise

    def _audit_in_tx(self, actor, role, action, corr_id=None, ref=None, detail=""):
        prev = (self.con.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone() or ("GENESIS",))[0]
        ts = self.clock()
        self.con.execute("INSERT INTO audit (ts,tenant_id,corr_id,actor,role,action,ref,detail,prev_hash,hash) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (ts, self.tenant, corr_id, actor, role, action, ref, detail, prev, _h(prev, ts, self.tenant, corr_id, actor, role, action, ref, detail)))

    def audit(self, actor, role, action, corr_id=None, ref=None, detail=""):
        return self._tx(lambda: self._audit_in_tx(actor, role, action, corr_id, ref, detail))

    def verify_audit(self):
        prev = "GENESIS"
        for seq, ts, ten, corr, actor, role, action, ref, detail, p, h in self.con.execute("SELECT seq,ts,tenant_id,corr_id,actor,role,action,ref,detail,prev_hash,hash FROM audit ORDER BY seq"):
            if p != prev or h != _h(p, ts, ten, corr, actor, role, action, ref, detail):
                return False, seq
            prev = h
        return True, None

    def audit_rows(self, corr_id=None):
        q = "SELECT seq, ts, actor, role, action, ref, detail FROM audit" + (" WHERE corr_id=?" if corr_id else "") + " ORDER BY seq"
        return [dict(zip(("seq", "ts", "actor", "role", "action", "ref", "detail"), r)) for r in self.con.execute(q, (corr_id,) if corr_id else ())]

    # ----------------------------------------------------------------- runs
    def start_run(self, corr_id, requester, role, location_id, ingredient_id, idem_key):
        """Idempotent on (tenant, idem_key): a retried request returns the ORIGINAL run instead of creating a second one."""
        def go():
            if idem_key:
                row = self.con.execute("SELECT corr_id FROM runs WHERE tenant_id=? AND idem_key=?", (self.tenant, idem_key)).fetchone()
                if row:
                    self._audit_in_tx(requester, role, "duplicate_request", row[0], idem_key, "returned the original run")
                    return row[0], True
            now = self.clock()
            self.con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (corr_id, self.tenant, requester, role, location_id, ingredient_id, idem_key, "STARTED", None, None, None, now, now))
            self._audit_in_tx(requester, role, "run_started", corr_id, idem_key or "", f"{location_id}/{ingredient_id}")
            return corr_id, False
        return self._tx(go)

    def set_state(self, corr_id, state, actor="system", role=None, **fields):
        def go():
            sets = ["state=?", "updated=?"] + [f"{k}=?" for k in fields]
            self.con.execute(f"UPDATE runs SET {', '.join(sets)} WHERE corr_id=? AND tenant_id=?", (state, self.clock(), *fields.values(), corr_id, self.tenant))
            self._audit_in_tx(actor, role, f"state:{state}", corr_id, fields.get("proposal_id") or fields.get("approval_id") or "", fields.get("failure") or "")
        self._tx(go)

    def run(self, corr_id):
        r = self.con.execute("SELECT corr_id, requester, role, location_id, ingredient_id, idem_key, state, proposal_id, approval_id, failure FROM runs WHERE corr_id=? AND tenant_id=?", (corr_id, self.tenant)).fetchone()
        return None if not r else dict(zip(("corr_id", "requester", "role", "location_id", "ingredient_id", "idem_key", "state", "proposal_id", "approval_id", "failure"), r))

    # ----------------------------------------------------------------- proposals
    def add_proposal(self, corr_id, p, explanation, evidence_ids, actor, role):
        def go():
            row = self.con.execute("SELECT proposal_id FROM proposals WHERE tenant_id=? AND reco_id=? AND inputs_hash=?", (self.tenant, p["reco_id"], p["inputs_hash"])).fetchone()
            if row:
                self._audit_in_tx(actor, role, "duplicate_proposal", corr_id, row[0], "same recommendation and inputs already proposed")
                return row[0]
            pid = "PR-" + _h(self.tenant, p["reco_id"], p["inputs_hash"])[:12]
            self.con.execute("INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (pid, self.tenant, corr_id, p["reco_id"], p["ingredient_id"], p["location_id"], p["supplier_id"], p["quote_id"], p["qty"], p["unit"],
                                                                                                p["est_cost_usd"], p["price_class"], p["inputs_hash"], json.dumps(sorted(evidence_ids)), json.dumps(explanation, sort_keys=True), "PROPOSED", self.clock()))
            self._audit_in_tx(actor, role, "proposal_created", corr_id, pid, f"{p['ingredient_id']} qty={p['qty']} supplier={p['supplier_id']}")
            return pid
        return self._tx(go)

    def set_proposal_state(self, proposal_id, state, actor, role, corr_id=None):
        def go():
            cur = self.con.execute("UPDATE proposals SET state=? WHERE proposal_id=? AND tenant_id=? AND state='PROPOSED'", (state, proposal_id, self.tenant))
            self._audit_in_tx(actor, role, f"proposal_{state.lower()}", corr_id, proposal_id, f"rows={cur.rowcount}")
            return cur.rowcount
        return self._tx(go)

    def proposal(self, proposal_id):
        r = self.con.execute("SELECT proposal_id, corr_id, reco_id, ingredient_id, location_id, supplier_id, quote_id, qty, unit, est_cost_usd, price_class, inputs_hash, evidence_ids, state FROM proposals WHERE proposal_id=? AND tenant_id=?",
                             (proposal_id, self.tenant)).fetchone()
        if not r:
            return None
        d = dict(zip(("proposal_id", "corr_id", "reco_id", "ingredient_id", "location_id", "supplier_id", "quote_id", "qty", "unit", "est_cost_usd", "price_class", "inputs_hash", "evidence_ids", "state"), r))
        d["evidence_ids"] = json.loads(d["evidence_ids"])
        return d

    # ----------------------------------------------------------------- purchase-order drafts
    def create_po_draft(self, proposal_id, approval_id, approved_by, idem_key, corr_id):
        """One transaction: insert the draft (UNIQUE per proposal and per idempotency key), mark the proposal APPROVED, audit. A duplicate returns the existing draft."""
        def go():
            row = self.con.execute("SELECT po_id FROM po_drafts WHERE proposal_id=? OR idem_key=?", (proposal_id, idem_key)).fetchone()
            if row:
                self._audit_in_tx("system", None, "duplicate_po_draft_suppressed", corr_id, row[0], "idempotent: existing draft returned")
                return row[0], True
            p = self.proposal(proposal_id)
            if p is None:
                raise LedgerError("NO_SUCH_PROPOSAL", proposal_id)
            if p["state"] != "PROPOSED":
                raise LedgerError("PROPOSAL_NOT_OPEN", p["state"])
            po = "PO-DRAFT-" + _h(self.tenant, proposal_id)[:10]
            self.con.execute("INSERT INTO po_drafts VALUES (?,?,?,?,?,?,?,?,?,?,?)", (po, proposal_id, self.tenant, p["supplier_id"], json.dumps([{"ingredient_id": p["ingredient_id"], "qty": p["qty"], "unit": p["unit"], "quote_id": p["quote_id"]}]),
                                                                                       p["est_cost_usd"], "DRAFT_NOT_SENT", approval_id, approved_by, idem_key, self.clock()))
            self.con.execute("UPDATE proposals SET state='APPROVED' WHERE proposal_id=?", (proposal_id,))
            self._audit_in_tx(approved_by, None, "po_draft_created", corr_id, po, f"approval={approval_id} state=DRAFT_NOT_SENT; NOT transmitted")
            return po, False
        return self._tx(go)

    def po_drafts(self):
        return self.con.execute("SELECT po_id, proposal_id, supplier_id, est_cost_usd, state, approved_by FROM po_drafts ORDER BY po_id").fetchall()
