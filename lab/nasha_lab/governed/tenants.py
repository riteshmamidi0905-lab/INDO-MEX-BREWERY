"""Synthetic enterprise TENANTS for the governed workflow (D-89).

Each tenant has its OWN: warehouse database (orders, inventory, recipes/BOM, finance, suppliers/quotes), procurement ledger (proposals, PO drafts, run state, audit chain),
THE WEIR approval store, run-trace store, agent memory, private documents, and identity authority (its own signing secret and reviewers). Nothing is shared at the data layer,
so there is no cross-tenant join to get wrong. What is NOT isolated: one Python process and one code base (a bug in shared code could still cross tenants), the shared
reference recipe files used to seed each tenant's scenario tables, and the shared policy knowledge base (public NASHA decisions). See docs/GOVERNED-SECURITY.md.
"""
import hashlib
import secrets
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .. import enterprise_sim as es, identity as ID, knowledge as K
from ..recipes import suppliers
from ..warehouse import pipeline, scenario

DEFAULT_ROLES = {"buyer": "BUYER", "buyer2": "BUYER", "quality": "QUALITY_LEAD", "founder": "FOUNDER", "viewer": "VIEWER"}


def make_authority(tenant_id, people, clock=None, secret=None, **kw):
    """people: {reviewer_id: (role, passcode)}. A tenant's authority has its OWN random secret: another tenant's tokens fail signature verification."""
    rv = {}
    for rid, (role, pc) in people.items():
        salt = secrets.token_hex(8)
        rv[rid] = (role, ID.Authority._hash(pc, salt), salt)
    extra = {"clock": clock} if clock else {}
    return ID.Authority(rv, secret=secret or secrets.token_bytes(32), **extra, **kw)


class AgentMemory:
    """Per-tenant agent memory: short summaries of earlier runs, written and read only through the tenant's own database file."""
    def __init__(self, path, tenant_id):
        self.tenant, self.con = tenant_id, sqlite3.connect(str(path), check_same_thread=False)
        self.con.execute("CREATE TABLE IF NOT EXISTS memory (tenant_id TEXT NOT NULL, corr_id TEXT, key TEXT NOT NULL, value TEXT NOT NULL, ts REAL)")
        self.con.commit()

    def remember(self, corr_id, key, value, ts=0.0):
        self.con.execute("INSERT INTO memory VALUES (?,?,?,?,?)", (self.tenant, corr_id, key, value, ts)); self.con.commit()

    def recall(self, key):
        return [dict(corr_id=c, key=k, value=v) for c, k, v in self.con.execute("SELECT corr_id, key, value FROM memory WHERE tenant_id=? AND key=? ORDER BY rowid", (self.tenant, key))]

    def all(self):
        return [r[0] for r in self.con.execute("SELECT value FROM memory WHERE tenant_id=?", (self.tenant,))]


class TenantKnowledge:
    """Private tenant documents behind a BM25 index. Results carry the tenant id and document id (provenance)."""
    def __init__(self, tenant_id, docs):
        self.tenant, self.chunks = tenant_id, []
        for title, text in sorted(docs.items()):
            for i, (heading, part) in enumerate(K.chunk_markdown(text, title)):
                self.chunks.append(dict(chunk_id=f"{tenant_id}:{hashlib.sha256(title.encode()).hexdigest()[:6]}:{i}", document_id=f"{tenant_id}/{title}", title=title, heading=heading, text=part))
        self.index = K.BM25(self.chunks) if self.chunks else None
        self.by_id = {c["chunk_id"]: c for c in self.chunks}

    def search(self, query, k=3):
        if not self.index:
            return []
        return [dict(chunk_id=cid, score=round(s, 4), document_id=self.by_id[cid]["document_id"], tenant=self.tenant, text=self.by_id[cid]["text"][:400]) for cid, s in self.index.search(query, k)]


@dataclass
class TenantEnv:
    tenant_id: str
    root: Path
    cfg: object
    authority: object
    people: dict
    docs: dict
    warehouse: Path = None
    ledger_path: Path = None
    weir_db: Path = None
    trace_db: Path = None
    memory_db: Path = None
    quotes: dict = field(default_factory=dict)

    def memory(self):
        return AgentMemory(self.memory_db, self.tenant_id)

    def knowledge(self):
        return TenantKnowledge(self.tenant_id, self.docs)


def provision(root, tenant_id, cfg, quote_seed=87, people=None, docs=None, drop_supplier_quotes_for=(), supplier_notes=None, clock=None, scn_seed=7, auth_ttl=900):
    """Create a tenant end to end: generate synthetic orders -> warehouse pipeline -> recipe/inventory/forecast scenario -> per-tenant stores. SYNTHETIC."""
    root = Path(root) / tenant_id
    root.mkdir(parents=True, exist_ok=True)
    es.generate(cfg, root / "src")
    pipeline.run(root / "src", root / "warehouse.db")
    q = suppliers.generate(seed=quote_seed)
    if drop_supplier_quotes_for:                                       # missing supplier data: remove every quote for these ingredients
        q["quotes"] = [x for x in q["quotes"] if x["ingredient_id"] not in set(drop_supplier_quotes_for)]
    scenario.build(root / "warehouse.db", seed=scn_seed, quotes=q, supplier_notes=supplier_notes)
    people = people or {f"{tenant_id}-{k}": (role, f"{tenant_id}-{k}-dev-passcode") for k, role in DEFAULT_ROLES.items()}
    docs = docs if docs is not None else {"Receiving SOP": f"# Receiving SOP ({tenant_id})\nTenant-private: deliveries are checked against the purchase order by the {tenant_id} receiving lead."}
    return TenantEnv(tenant_id=tenant_id, root=root, cfg=cfg, authority=make_authority(tenant_id, people, clock=clock, grant_ttl=auth_ttl, session_ttl=auth_ttl), people=people, docs=docs, warehouse=root / "warehouse.db",
                     ledger_path=root / "ledger.db", weir_db=root / "weir.db", trace_db=root / "trace.db", memory_db=root / "memory.db", quotes=q)


def default_pair(root, clock=None):
    """Two different synthetic enterprises (different seed, size, site mix, supplier quotes, people and private documents)."""
    a = provision(root, "tenant-a", es.SimConfig(name="tenant-a", menu="current", seed=11, months=10, fast_casual=3, beer_gardens=1, target_orders=20_000, loyalty_profiles=2_000, employees=60, open_at_start=3),
                  quote_seed=87, docs={"Receiving SOP": "# Receiving SOP (tenant-a)\nAlpha Courtyard private: negotiated chicken floor price is CONFIDENTIAL-ALPHA-4411.",
                                       "Supplier terms": "# Supplier terms\nAlpha terms net 30 with Synthetic Supplier 01."}, clock=clock)
    b = provision(root, "tenant-b", es.SimConfig(name="tenant-b", menu="current", seed=23, months=9, fast_casual=2, beer_gardens=2, target_orders=16_000, loyalty_profiles=1_500, employees=45, open_at_start=2),
                  quote_seed=131, docs={"Receiving SOP": "# Receiving SOP (tenant-b)\nBravo Brewhouse private: paneer rebate agreement CONFIDENTIAL-BRAVO-9027."}, clock=clock)
    return a, b
