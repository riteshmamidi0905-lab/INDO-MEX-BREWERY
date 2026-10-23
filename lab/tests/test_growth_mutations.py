"""Mutation tests for the Growth OS controls: each mutant removes ONE protection (a database constraint, RLS, a trigger, a policy entry, a service rule); the matching probe must then report that
the protection no longer holds. A mutant the probes cannot see would mean the tests are not testing the control. Also checks that every probe passes on the unmutated system."""
import os
from unittest import mock

import pytest

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from nasha_lab.growth import schema as S, service as SV, testing as TT
from nasha_lab.warehouse import pg_hardening as H

USERS = [("ada", "Ada", "OWNER"), ("sam", "Sam", "SALES"), ("vic", "Vic", "VIEWER")]


@pytest.fixture(scope="module")
def dsn(tmp_path_factory):
    if os.environ.get("NASHA_PG_DSN"):
        yield os.environ["NASHA_PG_DSN"]; return
    try:
        import pixeltable_pgserver as pg
        srv = pg.get_server(str(tmp_path_factory.mktemp("pgdata")), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    yield srv.get_uri(); srv.cleanup()


def build(dsn, schema):
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'); c.execute(f'CREATE SCHEMA "{schema}"')
    H.migrate(dsn, schema, specs=S.migrations(schema))
    for t in ("ta", "tb"):
        SV.provision(dsn, schema, f"tenant-{t}", t, "x", USERS)


def admin(dsn, schema, sql):
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'SET search_path TO "{schema}", pg_catalog, public'); c.execute(sql)


# ---- probes: True means "the protection holds"
def p_rls(dsn, sc):
    a, b = SV.GrowthService(dsn, sc, "tenant-ta", "ada"), SV.GrowthService(dsn, sc, "tenant-tb", "ada")
    acc = b.create_account("B only")
    seen = a.con.execute("SELECT count(*) FROM accounts WHERE id=%s", (acc,)).fetchone()[0]
    a.close(); b.close(); return seen == 0


def p_cross_fk(dsn, sc):
    a, b = SV.GrowthService(dsn, sc, "tenant-ta", "ada"), SV.GrowthService(dsn, sc, "tenant-tb", "ada")
    acc_b = b.create_account("B acct")
    ok = TT.attempt(a, "contacts", "c1", "INSERT INTO contacts (tenant_id,id,account_id,full_name,email) VALUES ('tenant-ta','c1',%s,'x','x@example.invalid')", (acc_b,), (psycopg.errors.ForeignKeyViolation, psycopg.errors.InsufficientPrivilege))
    a.close(); b.close(); return ok


def p_stage(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "ada")
    acc = s.create_account("S")
    with TT.audited(s, "opportunities", "o1"):
        s.con.execute("INSERT INTO opportunities (tenant_id,id,account_id,name,amount_cents) VALUES ('tenant-ta','o1',%s,'o',1)", (acc,))
    ok = TT.attempt(s, "opportunities", "o1", "UPDATE opportunities SET stage='won' WHERE id='o1'", (), psycopg.errors.CheckViolation)          # new -> won is not allowed
    s.close(); return ok


def p_policy(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "vic")
    try:
        s.create_account("viewer made this"); ok = False
    except SV.Denied:
        ok = True
    s.close(); return ok


def _contact(s):
    a = s.create_account("C"); return s.create_contact(a, "P", "p@example.invalid")


def p_consent(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "sam"); c = _contact(s)
    try:
        s.draft_outreach(c, "hi"); ok = False
    except SV.Blocked:
        ok = True
    s.close(); return ok


def p_suppression(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "sam"); c = _contact(s); s.set_consent(c, "opt_in"); s.suppress("p@example.invalid", "stop")
    try:
        s.draft_outreach(c, "hi"); ok = False
    except SV.Blocked:
        ok = True
    s.close(); return ok


def p_deny_audited(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "vic")
    try:
        s.create_account("x")
    except SV.Denied:
        pass
    n = s.con.execute("SELECT count(*) FROM audit_log WHERE decision='deny'").fetchone()[0]
    s.close(); return n >= 1


def p_no_sent_state(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "ada"); camp = s.create_campaign("c")
    ok = TT.attempt(s, "campaigns", camp, "UPDATE campaigns SET status='sent' WHERE id=%s", (camp,), psycopg.errors.CheckViolation)
    s.close(); return ok


def p_synthetic_email(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "ada"); a = s.create_account("E")
    ok = TT.attempt(s, "contacts", "ce", "INSERT INTO contacts (tenant_id,id,account_id,full_name,email) VALUES ('tenant-ta','ce',%s,'r','real@gmail.com')", (a,), psycopg.errors.CheckViolation)
    s.close(); return ok


def p_append_only(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "ada"); s.create_account("A")
    try:
        s.con.execute("DELETE FROM audit_log"); ok = False
    except psycopg.errors.InsufficientPrivilege:
        ok = True
    s.close(); return ok


def p_audit_guard(dsn, sc):
    s = SV.GrowthService(dsn, sc, "tenant-ta", "ada")
    try:
        s.con.execute("INSERT INTO accounts (tenant_id,id,name,kind) VALUES ('tenant-ta','raw-unaudited','Raw','business')"); ok = False        # a CRM row with no audit evidence must not commit
    except psycopg.errors.IntegrityConstraintViolation:
        ok = True
    s.close(); return ok


PROBES = [p_rls, p_cross_fk, p_stage, p_policy, p_consent, p_suppression, p_deny_audited, p_no_sent_state, p_synthetic_email, p_append_only, p_audit_guard]


def lax_draft(self, contact_id, body):                          # mutant: outreach with no consent/suppression checks (still audited like every write: the audit guard is a separate control)
    def go():
        aid = self._id("act")
        self.con.execute("INSERT INTO activities (tenant_id,id,contact_id,kind,body,actor) VALUES (%s,%s,%s,'email_draft',%s,%s)", (self.tenant, aid, contact_id, body, self.user))
        return aid
    return self._write("outreach.draft", "activities", go)


def no_deny_audit(orig):
    def f(self, action, entity, entity_id, decision, detail=None):
        return None if decision == "deny" else orig(self, action, entity, entity_id, decision, detail)
    return f


MUTANTS = [  # (name, probe that must fail, db sql or None, python patch context or None)
    ("RLS disabled on accounts", p_rls, "ALTER TABLE accounts NO FORCE ROW LEVEL SECURITY; ALTER TABLE accounts DISABLE ROW LEVEL SECURITY", None),
    ("cross-tenant foreign key dropped", p_cross_fk, "ALTER TABLE contacts DROP CONSTRAINT contacts_tenant_id_account_id_fkey; ALTER TABLE contacts DISABLE ROW LEVEL SECURITY", None),
    ("stage-rule trigger dropped", p_stage, "DROP TRIGGER opp_stage_rules ON opportunities", None),
    ("viewer may create accounts", p_policy, None, lambda: mock.patch.dict(SV.POLICY, {"account.create": {"OWNER", "SALES", "VIEWER"}})),
    ("consent check removed", p_consent, None, lambda: mock.patch.object(SV.GrowthService, "draft_outreach", lax_draft)),
    ("suppression check removed", p_suppression, None, lambda: mock.patch.object(SV.GrowthService, "draft_outreach", lax_draft)),
    ("denials no longer audited", p_deny_audited, None, lambda: mock.patch.object(SV.GrowthService, "_audit", no_deny_audit(SV.GrowthService._audit))),
    ("campaign gains a 'sent' state", p_no_sent_state, "ALTER TABLE campaigns DROP CONSTRAINT campaigns_status_check", None),
    ("real email addresses allowed", p_synthetic_email, "ALTER TABLE contacts DROP CONSTRAINT contacts_email_check", None),
    ("audit log becomes deletable", p_append_only, f"GRANT DELETE ON audit_log TO {S.APP_ROLE}", None),
    ("audit guard dropped from accounts", p_audit_guard, "DROP TRIGGER crm_audit_guard ON accounts", None)]


def test_every_probe_passes_on_the_unmutated_system(dsn):
    for p in PROBES:
        build(dsn, "growth_m0")                      # a fresh schema per probe: probes create their own rows
        assert p(dsn, "growth_m0"), p.__name__


@pytest.mark.parametrize("name,probe,sql,patch", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_each_mutant_is_detected_by_its_probe(dsn, name, probe, sql, patch):
    sc = "growth_m_" + str(abs(hash(name)) % 10**6)
    build(dsn, sc)
    if sql:
        for st in sql.split("; "):
            admin(dsn, sc, st)
    if patch:
        with patch():
            held = probe(dsn, sc)
    else:
        held = probe(dsn, sc)
    assert held is False, f"mutant survived: {name}"
