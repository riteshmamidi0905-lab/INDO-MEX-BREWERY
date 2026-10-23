"""Growth OS service layer: tenant-scoped CRM, segmentation, pricing and offers on PostgreSQL, with role-based authorization, consent/suppression rules and a per-tenant hash-chained audit log.
One GrowthService = one authenticated actor in one tenant. It connects as the non-privileged application role, sets `app.tenant_id` for the session, and every write is authorized, audited and
versioned. There is deliberately NO send / publish / purchase method: outbound communication, publishing and ad spend are not implemented (and the schema has no state for them)."""
import hashlib
import json
import uuid

import psycopg
from psycopg.types.json import Jsonb

from . import schema as S

# default-deny action -> roles. An action missing here is denied for everyone.
POLICY = {
    "account.create": {"OWNER", "SALES"}, "contact.create": {"OWNER", "SALES"}, "contact.consent": {"OWNER", "SALES", "MARKETING"}, "suppression.add": {"OWNER", "SALES", "MARKETING"},
    "lead.create": {"OWNER", "SALES", "MARKETING"}, "lead.qualify": {"OWNER", "SALES"}, "lead.convert": {"OWNER", "SALES"}, "opportunity.advance": {"OWNER", "SALES"}, "activity.log": {"OWNER", "SALES", "MARKETING"},
    "segment.create": {"OWNER", "MARKETING", "ANALYST"}, "product.create": {"OWNER"}, "price.scenario": {"OWNER", "ANALYST"}, "price.set_current": {"OWNER"}, "offer.create": {"OWNER", "MARKETING"},
    "campaign.create": {"OWNER", "MARKETING"}, "content.draft": {"OWNER", "MARKETING"}, "outreach.draft": {"OWNER", "SALES", "MARKETING"},
    "read": {"OWNER", "SALES", "MARKETING", "ANALYST", "VIEWER"},
}


class Denied(Exception):
    def __init__(self, action, why):
        super().__init__(f"{action} denied: {why}"); self.action, self.why = action, why


class Blocked(Exception):
    """A business rule refused the action (for example outreach to a suppressed contact)."""


def _hash(prev, tenant, seq, actor, role, action, entity, entity_id, decision, detail):
    return hashlib.sha256(json.dumps([prev, tenant, seq, actor, role, action, entity, entity_id, decision, detail], sort_keys=True, default=str).encode()).hexdigest()


def provision(admin_dsn, schema, tenant_id, name, vertical, users):
    """Privileged setup (not reachable from the application role): create the tenant row and its users."""
    with psycopg.connect(admin_dsn, autocommit=True) as c:
        c.execute(f'SET search_path TO "{schema}", pg_catalog, public')
        c.execute("INSERT INTO tenants (tenant_id, name, vertical) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (tenant_id, name, vertical))
        c.execute("SELECT set_config('app.tenant_id', %s, false)", (tenant_id,))      # superusers bypass RLS, but keep the setting explicit for readers
        for uid, display, role in users:
            c.execute("INSERT INTO users (tenant_id, id, display_name, role) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", (tenant_id, uid, display, role))


def app_dsn(admin_dsn):
    """The same server, connecting as the unprivileged application role (local trust auth in the embedded test server; a real deployment would use a password or certificate)."""
    if "user=" in admin_dsn:
        return admin_dsn
    return admin_dsn.replace("postgresql://postgres:", f"postgresql://{S.APP_ROLE}:", 1)


class GrowthService:
    def __init__(self, dsn, schema, tenant_id, user_id):
        self.tenant, self.user, self.schema = tenant_id, user_id, schema
        self.con = psycopg.connect(app_dsn(dsn), autocommit=True)
        self.con.execute(f'SET search_path TO "{schema}", pg_catalog, public')
        self.con.execute("SELECT set_config('app.tenant_id', %s, false)", (tenant_id,))
        row = self.con.execute("SELECT role FROM users WHERE tenant_id=%s AND id=%s", (tenant_id, user_id)).fetchone()
        self.role = row[0] if row else None

    def close(self):
        self.con.close()

    # ------------------------------------------------------------ plumbing
    def _audit(self, action, entity, entity_id, decision, detail=None):
        detail = detail or {}
        self.con.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("audit:" + self.tenant,))          # one writer extends a tenant's chain at a time (released at commit/rollback)
        last = self.con.execute("SELECT seq, hash FROM audit_log WHERE tenant_id=%s ORDER BY seq DESC LIMIT 1", (self.tenant,)).fetchone()
        seq, prev = (last[0] + 1, last[1]) if last else (1, "genesis")
        h = _hash(prev, self.tenant, seq, self.user, self.role or "NONE", action, entity, entity_id, decision, detail)
        self.con.execute("INSERT INTO audit_log (tenant_id, seq, actor, role, action, entity, entity_id, decision, detail, prev_hash, hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                         (self.tenant, seq, self.user, self.role or "NONE", action, entity, entity_id, decision, Jsonb(detail), prev, h))

    def _authorize(self, action, entity=None, entity_id=None):
        if self.role is None:
            self._audit(action, entity, entity_id, "deny", {"why": "unknown user"}); raise Denied(action, "unknown user for this tenant")
        if self.role not in POLICY.get(action, set()):
            self._audit(action, entity, entity_id, "deny", {"why": "role not permitted"}); raise Denied(action, f"role {self.role} may not do this")

    def _write(self, action, entity, fn):
        """Authorize, run the write and its audit row in ONE transaction (all or nothing)."""
        self._authorize(action, entity)
        try:
            with self.con.transaction():
                entity_id = fn()
                also = None
                if isinstance(entity_id, tuple):               # a write that touches more than one row names the others, so each carries evidence
                    entity_id, also = entity_id
                self._audit(action, entity, entity_id, "allow", {"also": also} if also else None)
        except Blocked as e:                       # the write rolled back; the refusal itself is still on the record
            self._audit(action, entity, None, "deny", {"why": str(e)})
            raise
        return entity_id

    def _id(self, prefix):
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    def read(self, sql, params=()):
        self._authorize("read")
        return self.con.execute(sql, params).fetchall()

    # ------------------------------------------------------------ CRM
    def create_account(self, name, kind="business", segment_id=None):
        i = self._id("acc")
        return self._write("account.create", "accounts", lambda: self.con.execute("INSERT INTO accounts (tenant_id,id,name,kind,segment_id,created_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, name, kind, segment_id, self.user)).fetchone()[0])

    def create_contact(self, account_id, full_name, email, job_title=None):
        i = self._id("con")
        return self._write("contact.create", "contacts", lambda: self.con.execute("INSERT INTO contacts (tenant_id,id,account_id,full_name,email,job_title,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, account_id, full_name, email, job_title, self.user)).fetchone()[0])

    def set_consent(self, contact_id, status):
        def go():
            if status == "opt_in" and self.con.execute("SELECT 1 FROM suppression_list s JOIN contacts c ON c.tenant_id=s.tenant_id AND c.email=s.email WHERE c.tenant_id=%s AND c.id=%s", (self.tenant, contact_id)).fetchone():
                raise Blocked("contact is on the suppression list; consent cannot be flipped back")
            n = self.con.execute("UPDATE contacts SET consent_status=%s WHERE tenant_id=%s AND id=%s RETURNING id", (status, self.tenant, contact_id)).fetchone()
            if not n:
                raise Blocked("no such contact in this tenant")
            return contact_id
        return self._write("contact.consent", "contacts", go)

    def suppress(self, email, reason):
        def go():
            self.con.execute("INSERT INTO suppression_list (tenant_id,email,reason) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (self.tenant, email, reason))
            ids = [r[0] for r in self.con.execute("UPDATE contacts SET consent_status='opt_out' WHERE tenant_id=%s AND email=%s RETURNING id", (self.tenant, email)).fetchall()]
            return email, [f"contacts:{i}" for i in ids]
        return self._write("suppression.add", "suppression_list", go)

    def create_lead(self, contact_id, source, signals=None, inquiry=None, assigned_to=None, scenario=None, inquiry_received=None):
        i = self._id("lead")
        return self._write("lead.create", "leads", lambda: self.con.execute("INSERT INTO leads (tenant_id,id,contact_id,source,signals,inquiry,assigned_to,scenario,inquiry_received,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                                                                           (self.tenant, i, contact_id, source, Jsonb(signals) if signals is not None else None, inquiry, assigned_to, scenario, inquiry_received, self.user)).fetchone()[0])

    LEAD_VIEW = ("SELECT l.id, l.status, l.score, l.source, l.version, l.inquiry, l.scenario, l.inquiry_received, l.created_at, c.id, c.full_name, c.job_title, c.consent_status, "
                 "EXISTS (SELECT 1 FROM suppression_list s WHERE s.tenant_id=c.tenant_id AND s.email=c.email), a.id, a.name, a.kind, u.id, u.display_name "
                 "FROM leads l JOIN contacts c ON c.tenant_id=l.tenant_id AND c.id=l.contact_id JOIN accounts a ON a.tenant_id=c.tenant_id AND a.id=c.account_id LEFT JOIN users u ON u.tenant_id=l.tenant_id AND u.id=l.assigned_to")
    LEAD_VIEW_KEYS = ("lead_id", "status", "score", "source", "version", "inquiry", "scenario", "inquiry_received", "created_at", "contact_id", "prospect", "job_title", "consent_status", "suppressed", "account_id", "organization", "organization_kind", "owner_id", "owner")

    def lead_view(self, lead_id):
        """Presentation record for one lead (names, organisation, inquiry, owner) in this tenant only. Read-only; the workflow never uses it for decisions."""
        self._authorize("read")
        r = self.con.execute(self.LEAD_VIEW + " WHERE l.tenant_id=%s AND l.id=%s", (self.tenant, lead_id)).fetchone()
        return dict(zip(self.LEAD_VIEW_KEYS, r)) if r else None

    def get_lead_context(self, lead_id):
        """Everything the qualification workflow may look at for one lead, in this tenant only: the lead, its contact's consent and suppression status, and the recorded signals."""
        self._authorize("read")
        r = self.con.execute("SELECT l.id, l.status, l.score, l.source, l.signals, l.version, c.id, c.email, c.consent_status, EXISTS (SELECT 1 FROM suppression_list s WHERE s.tenant_id=c.tenant_id AND s.email=c.email), a.id, a.name "
                             "FROM leads l JOIN contacts c ON c.tenant_id=l.tenant_id AND c.id=l.contact_id JOIN accounts a ON a.tenant_id=c.tenant_id AND a.id=c.account_id WHERE l.tenant_id=%s AND l.id=%s", (self.tenant, lead_id)).fetchone()
        if not r:
            return None
        return dict(lead_id=r[0], status=r[1], score=r[2], source=r[3], signals=r[4], lead_version=r[5], contact_id=r[6], consent_status=r[8], suppressed=bool(r[9]), account_id=r[10], account_name=r[11])

    def qualified_by(self, lead_id):
        self._authorize("read")
        r = self.con.execute("SELECT qualified_by_run FROM leads WHERE tenant_id=%s AND id=%s", (self.tenant, lead_id)).fetchone()
        return r[0] if r else None

    def apply_qualification(self, lead_id, status, score, expected_version, run_id, approval_id, approved_by):
        """The CRM update a human approved: authorized as lead.qualify, optimistic on the lead version, idempotent per run, recorded in the append-only audit with the approval that allowed it."""
        if status not in ("qualified", "disqualified"):
            raise Blocked("qualification status must be qualified or disqualified")
        def go():
            cur = self.con.execute("SELECT status, version, qualified_by_run FROM leads WHERE tenant_id=%s AND id=%s FOR UPDATE", (self.tenant, lead_id)).fetchone()
            if not cur:
                raise Blocked("no such lead in this tenant")
            if cur[2] == run_id:
                return lead_id                                              # this run already applied it (idempotent)
            if cur[1] != expected_version:
                raise Blocked("lead changed since the proposal was made")
            if cur[0] == "converted":
                raise Blocked("lead already converted")
            self.con.execute("UPDATE leads SET status=%s, score=%s, qualified_by_run=%s WHERE tenant_id=%s AND id=%s", (status, score, run_id, self.tenant, lead_id))
            self._audit("lead.qualification_applied", "leads", lead_id, "allow", {"run": run_id, "approval": approval_id, "approved_by": approved_by, "status": status, "score": score})
            return lead_id
        self._authorize("lead.qualify", "leads", lead_id)
        try:
            with self.con.transaction():
                go()
        except Blocked as e:
            self._audit("lead.qualification_applied", "leads", lead_id, "deny", {"why": str(e), "run": run_id})
            raise
        return lead_id

    def qualify_lead(self, lead_id, signals):
        """Rule-based lead score (documented in growth/scoring.py); a person reviews it. Sets qualified / disqualified."""
        from .scoring import score_lead
        sc, status = score_lead(signals)
        def go():
            r = self.con.execute("UPDATE leads SET score=%s, status=%s WHERE tenant_id=%s AND id=%s AND status IN ('new','qualified','disqualified') RETURNING id", (sc, status, self.tenant, lead_id)).fetchone()
            if not r:
                raise Blocked("lead not found or already converted")
            return lead_id
        self._write("lead.qualify", "leads", go)
        return sc, status

    def convert_lead(self, lead_id, opportunity_name, amount_cents, expected_close=None):
        def go():
            row = self.con.execute("SELECT l.status, c.account_id FROM leads l JOIN contacts c ON c.tenant_id=l.tenant_id AND c.id=l.contact_id WHERE l.tenant_id=%s AND l.id=%s FOR UPDATE OF l", (self.tenant, lead_id)).fetchone()
            if not row or row[0] != "qualified":
                raise Blocked("only a qualified lead can be converted")
            oid = self._id("opp")
            self.con.execute("INSERT INTO opportunities (tenant_id,id,account_id,lead_id,name,amount_cents,expected_close,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (self.tenant, oid, row[1], lead_id, opportunity_name, amount_cents, expected_close, self.user))
            self.con.execute("UPDATE leads SET status='converted' WHERE tenant_id=%s AND id=%s", (self.tenant, lead_id))
            return oid, [f"leads:{lead_id}"]
        return self._write("lead.convert", "opportunities", go)

    def advance(self, opportunity_id, to_stage):
        def go():
            cur = self.con.execute("SELECT stage FROM opportunities WHERE tenant_id=%s AND id=%s FOR UPDATE", (self.tenant, opportunity_id)).fetchone()
            if not cur:
                raise Blocked("no such opportunity in this tenant")
            if cur[0] == to_stage:
                raise Blocked("opportunity is already in that stage")
            try:
                self.con.execute("UPDATE opportunities SET stage=%s WHERE tenant_id=%s AND id=%s", (to_stage, self.tenant, opportunity_id))
            except psycopg.errors.CheckViolation as e:
                raise Blocked(str(e).splitlines()[0]) from e
            self.con.execute("INSERT INTO stage_transitions (tenant_id,id,opportunity_id,from_stage,to_stage,actor) VALUES (%s,%s,%s,%s,%s,%s)", (self.tenant, self._id("tr"), opportunity_id, cur[0], to_stage, self.user))
            return opportunity_id
        return self._write("opportunity.advance", "opportunities", go)

    def log_activity(self, kind, body, opportunity_id=None, contact_id=None):
        i = self._id("act")
        return self._write("activity.log", "activities", lambda: self.con.execute("INSERT INTO activities (tenant_id,id,opportunity_id,contact_id,kind,body,actor) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, opportunity_id, contact_id, kind, body, self.user)).fetchone()[0])

    def draft_outreach(self, contact_id, body):
        """Create an email DRAFT activity. Refused unless the contact has opted in and is not suppressed. Nothing is ever sent: there is no send path."""
        def go():
            row = self.con.execute("SELECT c.email, c.consent_status, EXISTS (SELECT 1 FROM suppression_list s WHERE s.tenant_id=c.tenant_id AND s.email=c.email) FROM contacts c WHERE c.tenant_id=%s AND c.id=%s", (self.tenant, contact_id)).fetchone()
            if not row:
                raise Blocked("no such contact in this tenant")
            if row[2] or row[1] == "opt_out":
                raise Blocked("contact is suppressed or has opted out")
            if row[1] != "opt_in":
                raise Blocked("no recorded consent: outreach drafts require opt_in")
            aid = self._id("act")
            self.con.execute("INSERT INTO activities (tenant_id,id,contact_id,kind,body,actor) VALUES (%s,%s,%s,'email_draft',%s,%s)", (self.tenant, aid, contact_id, body, self.user))
            return aid
        return self._write("outreach.draft", "activities", go)

    # ------------------------------------------------------------ segments, products, pricing, offers, campaigns
    def create_segment(self, name, kind, criteria, basis, confidence, est_value_cents=None):
        i = self._id("seg")
        return self._write("segment.create", "segments", lambda: self.con.execute("INSERT INTO segments (tenant_id,id,name,kind,criteria,evidence_basis,confidence,est_value_cents,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, name, kind, Jsonb(criteria), basis, confidence, est_value_cents, self.user)).fetchone()[0])

    def create_product(self, name, kind, unit_cost_cents, cost_basis="synthetic_assumption"):
        i = self._id("prod")
        return self._write("product.create", "products", lambda: self.con.execute("INSERT INTO products (tenant_id,id,name,kind,unit_cost_cents,cost_basis,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, name, kind, unit_cost_cents, cost_basis, self.user)).fetchone()[0])

    def set_price(self, product_id, amount_cents, valid_from, status, basis):
        action = "price.set_current" if status == "current" else "price.scenario"
        i = self._id("price")
        return self._write(action, "prices", lambda: self.con.execute("INSERT INTO prices (tenant_id,id,product_id,amount_cents,valid_from,status,basis,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, product_id, amount_cents, valid_from, status, basis, self.user)).fetchone()[0])

    def create_offer(self, name, product_id, discount_pct, starts, ends):
        i = self._id("offer")
        return self._write("offer.create", "offers", lambda: self.con.execute("INSERT INTO offers (tenant_id,id,name,product_id,discount_pct,starts,ends,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, name, product_id, discount_pct, starts, ends, self.user)).fetchone()[0])

    def create_campaign(self, name, offer_id=None, segment_id=None):
        i = self._id("camp")
        return self._write("campaign.create", "campaigns", lambda: self.con.execute("INSERT INTO campaigns (tenant_id,id,name,offer_id,segment_id,created_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, name, offer_id, segment_id, self.user)).fetchone()[0])

    # ------------------------------------------------------------ audit
    def verify_audit(self):
        rows = self.con.execute("SELECT seq, actor, role, action, entity, entity_id, decision, detail, prev_hash, hash FROM audit_log WHERE tenant_id=%s ORDER BY seq", (self.tenant,)).fetchall()
        prev = "genesis"
        for seq, actor, role, action, entity, entity_id, decision, detail, ph, h in rows:
            if ph != prev or h != _hash(prev, self.tenant, seq, actor, role, action, entity, entity_id, decision, detail):
                return False, seq
            prev = h
        return True, len(rows)
