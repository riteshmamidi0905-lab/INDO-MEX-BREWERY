"""Pytest plugin that re-installs the PRE-FIX audit write (lock, read and insert as separate autocommit statements) WITHOUT touching the source tree. Used only by
tools/audit_concurrency_incident.py to reproduce the incident: `python -m pytest -p legacy_audit_plugin` with tools/ on PYTHONPATH. Never imported by the application."""
from psycopg.types.json import Jsonb

from nasha_lab.growth import service as SV


def legacy_audit(self, action, entity, entity_id, decision, detail=None):
    detail = detail or {}
    self.con.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("audit:" + self.tenant,))
    last = self.con.execute("SELECT seq, hash FROM audit_log WHERE tenant_id=%s ORDER BY seq DESC LIMIT 1", (self.tenant,)).fetchone()
    seq, prev = (last[0] + 1, last[1]) if last else (1, "genesis")
    h = SV._hash(prev, self.tenant, seq, self.user, self.role or "NONE", action, entity, entity_id, decision, detail)
    self.con.execute("INSERT INTO audit_log (tenant_id, seq, actor, role, action, entity, entity_id, decision, detail, prev_hash, hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (self.tenant, seq, self.user, self.role or "NONE", action, entity, entity_id, decision, Jsonb(detail), prev, h))


SV.GrowthService._audit = legacy_audit
