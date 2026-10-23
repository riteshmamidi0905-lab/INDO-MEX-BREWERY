"""Database-enforced audit guarantee: a CRM mutation cannot COMMIT without an 'allow' audit row from the same transaction that names the changed row. Tested at the database (raw SQL as the
unprivileged application role), through the service (rollback, partial failure, concurrency) and over HTTP (duplicate requests). SYNTHETIC data only."""
import os
import threading
import uuid
from unittest import mock

import pytest

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, schema as S, service as SV, testing as TT, workflow as WF
from nasha_lab.warehouse import pg_hardening as H

SCHEMA = "growth_audit"
USERS = [("ada", "Ada", "OWNER"), ("sam", "Sam", "SALES")]
UW = {"ada": ("Ada", "OWNER"), "omar": ("Omar", "OWNER"), "sam": ("Sam", "SALES"), "mia": ("Mia", "MARKETING"), "vic": ("Vic", "VIEWER"), "ana": ("Ana", "ANALYST")}
GOOD = {"budget_confirmed": True, "decision_maker": True, "timeline_days": 20, "fit": 0.9, "engagement": 0.8}
Integrity = psycopg.errors.IntegrityConstraintViolation


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


@pytest.fixture(scope="module")
def db(dsn):
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'); c.execute(f'CREATE SCHEMA "{SCHEMA}"')
    H.migrate(dsn, SCHEMA, specs=S.migrations(SCHEMA))
    for t in ("tenant-a", "tenant-b"):
        SV.provision(dsn, SCHEMA, t, t, "hospitality", USERS)
    return dsn


def svc(db, tenant="tenant-a", user="ada"):
    return SV.GrowthService(db, SCHEMA, tenant, user)


def count(db, sql, params=()):
    with psycopg.connect(db, autocommit=True) as c:
        c.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
        return c.execute(sql, params).fetchone()[0]


def lead_fixture(s):
    a = s.create_account(f"Acct {uuid.uuid4().hex[:6]}"); n = uuid.uuid4().hex[:6]
    c = s.create_contact(a, "Person", f"p{n}@example.invalid"); s.set_consent(c, "opt_in")
    return a, c, s.create_lead(c, "synthetic-referral", GOOD)


# ---------------------------------------------------------------- the guard itself (raw SQL as the application role)
RAW = {  # table -> (insert sql, params-fn(s, acc))
    "accounts": ("INSERT INTO accounts (tenant_id,id,name,kind) VALUES ('tenant-a','{id}','Raw','business')", None),
    "products": ("INSERT INTO products (tenant_id,id,name,kind,unit_cost_cents) VALUES ('tenant-a','{id}','Raw P','dish',100)", None),
    "segments": ("INSERT INTO segments (tenant_id,id,name,kind,criteria,evidence_basis,confidence) VALUES ('tenant-a','{id}','Raw S','icp','{{}}','synthetic_assumption',0.5)", None),
    "suppression_list": ("INSERT INTO suppression_list (tenant_id,email,reason) VALUES ('tenant-a','{id}','raw')", None),
}


@pytest.mark.parametrize("table", sorted(RAW))
def test_raw_insert_into_each_guarded_table_without_audit_evidence_is_refused_and_leaves_nothing(db, table):
    s = svc(db)
    rid = f"raw-{uuid.uuid4().hex[:6]}" if table != "suppression_list" else f"{uuid.uuid4().hex[:6]}@example.invalid"
    with pytest.raises(Integrity, match="no audit evidence"):
        s.con.execute(RAW[table][0].format(id=rid))
    key = "email" if table == "suppression_list" else "id"
    assert count(db, f"SELECT count(*) FROM {table} WHERE {key}=%s", (rid,)) == 0
    with TT.audited(s, table, rid):                                              # the same statement WITH evidence from the same transaction commits
        s.con.execute(RAW[table][0].format(id=rid))
    assert count(db, f"SELECT count(*) FROM {table} WHERE {key}=%s", (rid,)) == 1
    s.close()


def test_raw_updates_of_leads_opportunities_and_contacts_without_evidence_are_refused(db):
    s = svc(db); a, c, lead = lead_fixture(s)
    for sql, params in (("UPDATE leads SET score=1 WHERE id=%s", (lead,)), ("UPDATE contacts SET job_title='x' WHERE id=%s", (c,)), ("UPDATE accounts SET name='hijacked' WHERE id=%s", (a,))):
        with pytest.raises(Integrity, match="no audit evidence"):
            s.con.execute(sql, params)
    assert count(db, "SELECT count(*) FROM accounts WHERE name='hijacked'") == 0 and count(db, "SELECT score FROM leads WHERE id=%s", (lead,)) is None
    s.close()


def test_evidence_must_name_the_changed_row_be_an_allow_and_come_from_the_same_transaction_and_tenant(db):
    s = svc(db); a, c, lead = lead_fixture(s); other = svc(db, "tenant-b")
    stmt = ("UPDATE leads SET score=5 WHERE id=%s", (lead,))
    with pytest.raises(Integrity):                                               # evidence for a different row
        with s.con.transaction():
            s.con.execute(*stmt); s._audit("x", "leads", "lead-other", "allow")
    with pytest.raises(Integrity):                                               # evidence for a different entity type
        with s.con.transaction():
            s.con.execute(*stmt); s._audit("x", "accounts", lead, "allow")
    with pytest.raises(Integrity):                                               # a DENY record is not evidence of an allowed change
        with s.con.transaction():
            s.con.execute(*stmt); s._audit("x", "leads", lead, "deny")
    s._audit("x", "leads", lead, "allow")                                         # evidence from an EARLIER transaction does not carry over
    with pytest.raises(Integrity):
        s.con.execute(*stmt)
    with pytest.raises(Integrity):                                               # evidence written by the other tenant does not count (and cannot be written into this one)
        with s.con.transaction():
            s.con.execute(*stmt); other._audit("x", "leads", lead, "allow")
    assert count(db, "SELECT score FROM leads WHERE id=%s", (lead,)) is None
    s.close(); other.close()


def test_the_transaction_id_on_an_audit_row_is_stamped_by_the_database_and_a_hand_written_row_is_detectable(db):
    SV.provision(db, SCHEMA, "tenant-forge", "tenant-forge", "hospitality", USERS)                      # own tenant: this test deliberately breaks its chain
    s = svc(db, "tenant-forge"); a, c, lead = lead_fixture(s)
    with s.con.transaction():
        s.con.execute("UPDATE leads SET score=7 WHERE id=%s", (lead,))
        s.con.execute("INSERT INTO audit_log (tenant_id, seq, actor, role, action, entity, entity_id, decision, detail, prev_hash, hash, txid) VALUES ('tenant-forge', 999999, 'ada', 'OWNER', 'forged', 'leads', %s, 'allow', '{}', 'x', 'x', 1)", (lead,))
        stamped = s.con.execute("SELECT txid, txid_current() FROM audit_log WHERE seq=999999").fetchone()
    assert stamped[0] == stamped[1] != 1, "the supplied txid was overwritten with the real transaction id: evidence cannot point at another transaction"
    ok, bad = s.verify_audit()
    assert ok is False and bad is not None, "a hand-written audit row cannot hide: it names the actor and breaks the hash chain, which verification reports"
    s.close()


def test_the_application_role_cannot_disable_the_guard(db):
    s = svc(db)
    for sql in ("ALTER TABLE leads DISABLE TRIGGER crm_audit_guard", "DROP TRIGGER crm_audit_guard ON leads", "SET session_replication_role = replica", "ALTER TABLE audit_log DISABLE TRIGGER audit_log_stamp"):
        with pytest.raises((psycopg.errors.InsufficientPrivilege, psycopg.errors.UndefinedObject)):
            s.con.execute(sql)
    s.close()


def test_audit_remains_append_only_and_hash_chained(db):
    s = svc(db); lead_fixture(s)
    for sql in ("UPDATE audit_log SET actor='x'", "DELETE FROM audit_log"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            s.con.execute(sql)
    ok, n = s.verify_audit()
    assert ok is True and n > 0
    s.close()


# ---------------------------------------------------------------- rollback, partial failure
def test_a_failure_after_the_mutation_but_before_the_audit_row_rolls_the_mutation_back(db):
    s = svc(db)
    before = count(db, "SELECT count(*) FROM accounts WHERE tenant_id='tenant-a'")
    with mock.patch.object(SV.GrowthService, "_audit", side_effect=RuntimeError("audit store down")):
        with pytest.raises(RuntimeError):
            s.create_account("Never persisted")
    assert count(db, "SELECT count(*) FROM accounts WHERE tenant_id='tenant-a'") == before and count(db, "SELECT count(*) FROM accounts WHERE name='Never persisted'") == 0
    s.close()


def test_a_multi_row_write_that_fails_halfway_leaves_no_partial_state(db):
    s = svc(db); a, c, lead = lead_fixture(s); s.qualify_lead(lead, GOOD)
    orig = s.con.execute
    class Boom:
        def __init__(self, con): self.con = con
        def __getattr__(self, k): return getattr(self.con, k)
        def execute(self, sql, *a, **k):
            if sql.startswith("UPDATE leads SET status='converted'"):
                raise psycopg.errors.OperationalError("simulated database failure mid-write")
            return self.con.execute(sql, *a, **k)
    real = s.con; s.con = Boom(real)
    with pytest.raises(psycopg.errors.OperationalError):
        s.convert_lead(lead, "Half done", 1000)
    s.con = real
    assert count(db, "SELECT count(*) FROM opportunities WHERE name='Half done'") == 0 and count(db, "SELECT status FROM leads WHERE id=%s", (lead,)) is not None
    assert s.get_lead_context(lead)["status"] == "qualified", "the lead is unchanged and can still be converted"
    s.convert_lead(lead, "Done properly", 1000)
    s.close()


def test_multi_row_writes_name_every_row_they_touch_and_lose_the_evidence_if_they_do_not(db):
    s = svc(db); a, c, lead = lead_fixture(s); s.qualify_lead(lead, GOOD)
    s.convert_lead(lead, "Opp", 500)
    row = count(db, "SELECT detail->'also' FROM audit_log WHERE action='lead.convert' AND detail->'also' ? %s ORDER BY seq DESC LIMIT 1", (f"leads:{lead}",))
    assert row == [f"leads:{lead}"]
    a2, c2, lead2 = lead_fixture(s); s.qualify_lead(lead2, GOOD)
    orig = SV.GrowthService._audit
    def drop_also(self, action, entity, entity_id, decision, detail=None):
        return orig(self, action, entity, entity_id, decision, None)
    with mock.patch.object(SV.GrowthService, "_audit", drop_also):
        with pytest.raises(Integrity, match="no audit evidence"):
            s.convert_lead(lead2, "Opp2", 500)                                    # the lead UPDATE is not covered by an audit row naming it
    assert s.get_lead_context(lead2)["status"] == "qualified"
    s.close()


def test_suppression_names_the_contacts_it_opts_out(db):
    s = svc(db); a, c, lead = lead_fixture(s)
    email = count(db, "SELECT email FROM contacts WHERE id=%s", (c,))
    s.suppress(email, "asked to stop")
    assert s.get_lead_context(lead)["suppressed"] is True and count(db, "SELECT consent_status FROM contacts WHERE id=%s", (c,)) == "opt_out"
    s.close()


# ---------------------------------------------------------------- concurrency and duplicates
def test_concurrent_writers_in_one_tenant_all_commit_with_a_valid_unbroken_chain(db):
    errs, N = [], 8
    def work(i):
        try:
            s = svc(db, "tenant-a", "ada")
            for k in range(3):
                s.create_account(f"Concurrent {i}-{k}-{uuid.uuid4().hex[:4]}")
            s.close()
        except Exception as e:  # noqa: BLE001
            errs.append(repr(e))
    ts = [threading.Thread(target=work, args=(i,)) for i in range(N)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert not errs, errs[:2]
    s = svc(db); ok, n = s.verify_audit(); s.close()
    assert ok is True
    assert count(db, "SELECT count(*) FROM accounts WHERE name LIKE 'Concurrent %%'") == N * 3 == count(db, "SELECT count(*) FROM audit_log WHERE action='account.create' AND entity_id IN (SELECT id FROM accounts WHERE name LIKE 'Concurrent %%')")


def test_two_concurrent_conversions_of_the_same_lead_produce_exactly_one_opportunity(db):
    s0 = svc(db); a, c, lead = lead_fixture(s0); s0.qualify_lead(lead, GOOD); s0.close()
    res = []
    def conv(i):
        s = svc(db, "tenant-a", "sam" if i % 2 else "ada")
        try:
            res.append(("ok", s.convert_lead(lead, f"Race {i}", 100)))
        except SV.Blocked as e:
            res.append(("blocked", str(e)))
        finally:
            s.close()
    ts = [threading.Thread(target=conv, args=(i,)) for i in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert [r[0] for r in res].count("ok") == 1 and count(db, "SELECT count(*) FROM opportunities WHERE lead_id=%s", (lead,)) == 1


@pytest.fixture(scope="module")
def api(db, tmp_path_factory):
    root = tmp_path_factory.mktemp("gaud")
    envs = {t: WF.provision_env(root, db, SCHEMA, t, t, "hospitality", UW) for t in ("tenant-a", "tenant-b")}
    return TestClient(GA.create_growth_app(envs)), envs


def hdr(envs, tenant, user, **x):
    return {"Authorization": "Bearer " + envs[tenant].authority.login(user, f"{tenant}-{user}-dev-passcode"), **x}


def test_a_duplicate_http_request_creates_one_record_and_one_audit_row(api, db):
    c, envs = api
    name = f"Dup {uuid.uuid4().hex[:6]}"
    h = hdr(envs, "tenant-a", "sam", **{"Idempotency-Key": "dup-key-" + uuid.uuid4().hex[:8]})
    r1 = c.post("/v1/tenants/tenant-a/accounts", json={"name": name}, headers=h); r2 = c.post("/v1/tenants/tenant-a/accounts", json={"name": name}, headers=h)
    assert r1.status_code == 201 and r2.status_code == 201 and r1.json() == r2.json()
    assert count(db, "SELECT count(*) FROM accounts WHERE name=%s", (name,)) == 1
    assert count(db, "SELECT count(*) FROM audit_log WHERE action='account.create' AND entity_id=%s", (r1.json()["id"],)) == 1
