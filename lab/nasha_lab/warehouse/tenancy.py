"""Second-customer deployment: a tenant gateway in front of per-tenant warehouses (SYNTHETIC data).

Isolation model (what is and is not isolated):
  * one warehouse database file per tenant, opened read-only; no connection, cache or table is shared between tenants;
  * one audit database per tenant, plus a gateway audit for decisions made before a tenant is chosen (unknown tenant, grant denied, override attempts);
  * a principal's tenant must be GRANTED to that user (default deny); arguments may never name a tenant/warehouse: such calls are refused and logged;
  * NOT isolated: the same Python process and code (a bug in shared code could cross tenants), and the in-process principal object is trusted input
    (a real deployment needs an identity provider). This is a design demonstration over synthetic data, not a security certification.
"""
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import db as wdb
from .ops_ai import OpsAI, Principal

GATEWAY_AUDIT = """CREATE TABLE IF NOT EXISTS tenant_gateway_audit (call_id TEXT PRIMARY KEY, ts TEXT, user TEXT, claimed_tenant TEXT, tool TEXT, decision TEXT, code TEXT)"""
FORBIDDEN_ARGS = {"tenant", "tenant_id", "warehouse", "db", "path", "dsn", "schema"}


@dataclass(frozen=True)
class TenantPrincipal:
    user: str
    role: str
    tenant: str
    site: Optional[str] = None


class TenantGateway:
    def __init__(self, registry: dict, grants: dict, audit_dir):
        """registry: {tenant_id: warehouse_path}; grants: {user: {tenant_id, ...}}; audit_dir: directory for audit databases."""
        self.registry, self.grants = dict(registry), {u: set(t) for u, t in grants.items()}
        self.dir = Path(audit_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._ai = {}
        self.gw = sqlite3.connect(str(self.dir / "_gateway.db"))
        self.gw.execute(GATEWAY_AUDIT)

    def close(self):
        for a in self._ai.values():
            a.close()
        self.gw.close()

    def _tenant_ai(self, tenant):
        if tenant not in self._ai:
            self._ai[tenant] = OpsAI(self.registry[tenant], self.dir / f"{tenant}.audit.db")
        return self._ai[tenant]

    def _deny(self, who, tool, code, msg):
        self.gw.execute("INSERT INTO tenant_gateway_audit VALUES (?,?,?,?,?,?,?)", (uuid.uuid4().hex[:12], wdb.now(), who.user, who.tenant, tool, "deny", code))
        self.gw.commit()
        return {"ok": False, "code": code, "error": msg}

    def call(self, who: TenantPrincipal, tool: str, args: Optional[dict] = None) -> dict:
        args = dict(args or {})
        if who.tenant not in self.registry:
            return self._deny(who, tool, "unknown_tenant", "no such tenant")
        if who.tenant not in self.grants.get(who.user, set()):
            return self._deny(who, tool, "tenant_not_granted", f"{who.user} has no grant for {who.tenant}")
        if FORBIDDEN_ARGS & {k.lower() for k in args}:
            return self._deny(who, tool, "tenant_override", "arguments may not select a tenant or data source")
        r = self._tenant_ai(who.tenant).call(Principal(who.user, who.role, who.site), tool, args)
        r["tenant"] = who.tenant
        return r

    def ask(self, who: TenantPrincipal, question: str) -> dict:
        if who.tenant not in self.registry or who.tenant not in self.grants.get(who.user, set()):
            return self.call(who, "list_months")      # reuses the same denial path and audit
        r = self._tenant_ai(who.tenant).ask(Principal(who.user, who.role, who.site), question)
        r["tenant"] = who.tenant
        return r

    def metrics(self):
        out = {t: self._tenant_ai(t).metrics() for t in self.registry}
        out["_gateway"] = dict(self.gw.execute("SELECT code, count(*) FROM tenant_gateway_audit GROUP BY code").fetchall())
        return out
