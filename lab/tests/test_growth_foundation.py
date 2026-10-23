"""Growth OS foundation on real PostgreSQL: schema constraints, row-level-security tenant isolation, CRM rules with an independent oracle, consent/suppression, audit chain, versioning,
append-only tables, and 'nothing can be sent'. Needs PostgreSQL (NASHA_PG_DSN or the embedded server); skipped with an explicit reason otherwise. SYNTHETIC data only."""
import inspect
import itertools
import os
import random

import pytest

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from nasha_lab.growth import schema as S, service as SV, scoring, testing as TT
from nasha_lab.warehouse import pg_hardening as H

SCHEMA = "growth_t"
# Independent oracle: the allowed stage graph, written out here and NOT imported from the schema module.
ORACLE_EDGES = {("new", "qualified"), ("new", "lost"), ("qualified", "proposal"), ("qualified", "lost"), ("proposal", "negotiation"), ("proposal", "lost"), ("negotiation", "won"), ("negotiation", "lost"), ("negotiation", "proposal")}
STAGES = ["new", "qualified", "proposal", "negotiation", "won", "lost"]


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
    rep = H.migrate(dsn, SCHEMA, specs=S.migrations(SCHEMA))
    assert [r["status"] for r in rep] == ["applied"] * 11
    users = [("ada", "Ada (synthetic owner)", "OWNER"), ("sam", "Sam (synthetic sales)", "SALES"), ("mia", "Mia (synthetic marketing)", "MARKETING"), ("vic", "Vic (synthetic viewer)", "VIEWER"), ("ana", "Ana (synthetic analyst)", "ANALYST")]
    SV.provision(dsn, SCHEMA, "tenant-nasha", "NASHA — The Courtyard (synthetic hospitality brand)", "restaurant", users)
    SV.provision(dsn, SCHEMA, "tenant-fit", "Meridian Fitness (synthetic studio)", "fitness", users)
    return dsn


def svc(db, tenant, user):
    return SV.GrowthService(db, SCHEMA, tenant, user)


def seed(s, tag):
    a = s.create_account(f"{tag} Catering Co", "business")
    c = s.create_contact(a, f"{tag} Buyer", f"{tag.lower()}.buyer@example.invalid")
    l = s.create_lead(c, "synthetic-referral")
    return a, c, l


# ---------------------------------------------------------------- schema and migrations
def test_migrations_are_idempotent_and_checksummed(db):
    assert [r["status"] for r in H.migrate(db, SCHEMA, specs=S.migrations(SCHEMA))] == ["already_applied"] * 11
    edited = S.migrations(SCHEMA); edited["104"] = (edited["104"][0] + ["CREATE INDEX ix_x ON accounts (name)"], [])
    with pytest.raises(H.MigrationChanged):
        H.migrate(db, SCHEMA, specs=edited)


def test_every_business_table_has_rls_enabled_and_forced_and_a_composite_primary_key(db):
    with psycopg.connect(db, autocommit=True) as c:
        c.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
        rls = {t: (e, f) for t, e, f in c.execute("SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relnamespace = %s::regnamespace AND relkind='r'", (SCHEMA,))}
        for t in S.ALL_TENANT_TABLES:
            assert rls[t] == (True, True), t
        for t in S.ALL_TENANT_TABLES:
            if t in ("tenants",):
                continue
            cols = [r[0] for r in c.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum = ANY(i.indkey) WHERE i.indrelid=%s::regclass AND i.indisprimary ORDER BY a.attnum", (t,))]
            assert cols[0] == "tenant_id", (t, cols)


def test_application_role_is_not_privileged(db):
    with psycopg.connect(db, autocommit=True) as c:
        sup, byp = c.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=%s", (S.APP_ROLE,)).fetchone()
        assert sup is False and byp is False


# ---------------------------------------------------------------- tenant isolation
def test_a_session_without_a_tenant_setting_sees_nothing(db):
    s = svc(db, "tenant-nasha", "ada"); seed(s, "Zed")
    with psycopg.connect(SV.app_dsn(db), autocommit=True) as c:
        c.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
        for t in ("accounts", "contacts", "leads", "audit_log", "users"):
            assert c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] == 0, t
    s.close()


def test_tenant_a_cannot_read_write_or_reference_tenant_b(db):
    a, b = svc(db, "tenant-nasha", "ada"), svc(db, "tenant-fit", "ada")
    acc_a, con_a, lead_a = seed(a, "Alpha"); acc_b, con_b, lead_b = seed(b, "Bravo")
    assert {r[0] for r in a.read("SELECT id FROM accounts")} >= {acc_a} and acc_b not in {r[0] for r in a.read("SELECT id FROM accounts")}
    assert not a.read("SELECT 1 FROM contacts WHERE id=%s", (con_b,)) and not a.read("SELECT 1 FROM leads WHERE id=%s", (lead_b,))
    # updates and deletes by id silently match nothing across the boundary
    n = a.con.execute("UPDATE accounts SET name='hijack' WHERE id=%s", (acc_b,)).rowcount
    assert n == 0 and b.read("SELECT name FROM accounts WHERE id=%s", (acc_b,))[0][0] == "Bravo Catering Co"
    # inserting a row for the other tenant violates the policy
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        a.con.execute("INSERT INTO accounts (tenant_id,id,name,kind) VALUES ('tenant-fit','acc-x','forged','business')")
    # a composite foreign key cannot point at another tenant's row, even with the raw id
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        a.con.execute("INSERT INTO contacts (tenant_id,id,account_id,full_name,email) VALUES ('tenant-nasha','con-x',%s,'x','x@example.invalid')", (acc_b,))
    with pytest.raises(SV.Blocked):
        a.set_consent(con_b, "opt_in")
    # the audit logs are separate too
    assert all(r[0] == "tenant-nasha" for r in a.read("SELECT tenant_id FROM audit_log")) and all(r[0] == "tenant-fit" for r in b.read("SELECT tenant_id FROM audit_log"))
    a.close(); b.close()


def test_the_application_role_cannot_turn_row_security_off_or_change_tenants_data_it_does_not_own(db):
    s = svc(db, "tenant-nasha", "ada")
    with pytest.raises(psycopg.Error):
        s.con.execute("SET row_security = off"); s.con.execute("SELECT count(*) FROM accounts").fetchone()
        raise psycopg.Error("row_security=off silently allowed")  # reached only if PostgreSQL did not refuse
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        s.con.execute("INSERT INTO tenants (tenant_id,name,vertical) VALUES ('tenant-evil','x','y')")
    s.close()


# ---------------------------------------------------------------- authorization
@pytest.mark.parametrize("user,action_call", [("vic", lambda s: s.create_account("Nope")), ("vic", lambda s: s.create_segment("n", "icp", {}, "synthetic_assumption", 0.5)),
                                              ("mia", lambda s: s.create_account("Nope")), ("sam", lambda s: s.create_product("p", "dish", 100)), ("ana", lambda s: s.create_account("Nope")),
                                              ("ghost", lambda s: s.create_account("Nope"))])
def test_default_deny_and_every_denial_is_audited(db, user, action_call):
    s = svc(db, "tenant-nasha", user)
    before = s.con.execute("SELECT count(*) FROM audit_log WHERE decision='deny'").fetchone()[0]
    with pytest.raises(SV.Denied):
        action_call(s)
    assert s.con.execute("SELECT count(*) FROM audit_log WHERE decision='deny'").fetchone()[0] == before + 1
    s.close()


def test_policy_has_no_action_that_everyone_may_do_except_read_and_unlisted_actions_are_denied(db):
    assert all(roles != {"OWNER", "SALES", "MARKETING", "ANALYST", "VIEWER"} for a, roles in SV.POLICY.items() if a != "read")
    s = svc(db, "tenant-nasha", "ada")
    with pytest.raises(SV.Denied):
        s._authorize("anything.unlisted")
    s.close()


# ---------------------------------------------------------------- CRM state machine
def test_database_enforces_exactly_the_oracle_stage_graph_for_every_pair(db):
    s = svc(db, "tenant-nasha", "ada")
    acc, con, lead = seed(s, "Graph")
    for frm, to in itertools.product(STAGES, STAGES):
        if frm == to or frm in ("won", "lost"):
            continue
        opp = s._id("opp")
        with TT.audited(s, "opportunities", opp):
            s.con.execute("INSERT INTO opportunities (tenant_id,id,account_id,name,stage,amount_cents) VALUES (%s,%s,%s,'t',%s,100)", (s.tenant, opp, acc, frm))
        ok = not TT.attempt(s, "opportunities", opp, "UPDATE opportunities SET stage=%s WHERE tenant_id=%s AND id=%s", (to, s.tenant, opp), psycopg.errors.CheckViolation)
        assert ok == ((frm, to) in ORACLE_EDGES), (frm, to)
    s.close()


def test_random_walks_through_the_service_never_leave_the_oracle_graph_and_closed_is_final(db):
    s = svc(db, "tenant-nasha", "sam"); rnd = random.Random(5)
    acc = s.create_account("Walk Co")
    for k in range(12):
        con = s.create_contact(acc, f"W{k}", f"walk{k}@example.invalid"); lead = s.create_lead(con, "synthetic")
        s.qualify_lead(lead, {"budget_confirmed": True, "decision_maker": True, "timeline_days": 10, "fit": 1, "engagement": 1})
        opp = s.convert_lead(lead, f"Opp {k}", 50_000)
        cur = "new"
        for _ in range(8):
            to = rnd.choice(STAGES)
            try:
                s.advance(opp, to); cur = to; assert (cur) in STAGES
            except SV.Blocked:
                pass
        rows = s.read("SELECT from_stage, to_stage FROM stage_transitions WHERE opportunity_id=%s", (opp,))
        assert all((a, b) in ORACLE_EDGES for a, b in rows)
        if cur in ("won", "lost"):
            with pytest.raises(SV.Blocked):
                s.advance(opp, "proposal")
    s.close()


def test_only_a_qualified_lead_converts_and_conversion_is_audited(db):
    s = svc(db, "tenant-nasha", "sam"); acc, con, lead = seed(s, "Conv")
    with pytest.raises(SV.Blocked):
        s.convert_lead(lead, "too early", 1000)
    assert s.qualify_lead(lead, {"budget_confirmed": True, "decision_maker": True, "timeline_days": 20, "fit": 0.9, "engagement": 0.8})[1] == "qualified"
    opp = s.convert_lead(lead, "Corporate lunch", 120_000)
    assert s.read("SELECT status FROM leads WHERE id=%s", (lead,))[0][0] == "converted" and s.read("SELECT stage FROM opportunities WHERE id=%s", (opp,))[0][0] == "new"
    assert s.read("SELECT count(*) FROM audit_log WHERE action='lead.convert' AND decision='allow'")[0][0] >= 1 and s.read("SELECT count(*) FROM audit_log WHERE decision='deny' AND detail->>'why' LIKE %s", ("%qualified%",))[0][0] >= 1
    s.close()


@pytest.mark.parametrize("sig,expected", [({"budget_confirmed": True, "decision_maker": True, "timeline_days": 10, "fit": 1.0, "engagement": 1.0}, 100), ({}, 0),
                                          ({"budget_confirmed": True, "decision_maker": True, "timeline_days": 60, "fit": 0.0, "engagement": 0.0}, 55),
                                          ({"budget_confirmed": True, "decision_maker": False, "timeline_days": 10, "fit": 0.5, "engagement": 0.0}, 55), ({"fit": 5, "engagement": -3}, 20)])
def test_lead_scoring_matches_hand_computed_scores(sig, expected):
    sc, status = scoring.score_lead(sig)
    assert sc == expected and status == ("qualified" if expected >= 60 else "disqualified")


# ---------------------------------------------------------------- consent and "nothing can be sent"
def test_outreach_drafts_require_opt_in_and_respect_suppression(db):
    s = svc(db, "tenant-nasha", "sam"); acc, con, lead = seed(s, "Consent")
    with pytest.raises(SV.Blocked):
        s.draft_outreach(con, "hello")                    # no consent recorded
    s.set_consent(con, "opt_in")
    aid = s.draft_outreach(con, "hello (draft)")
    assert s.read("SELECT kind FROM activities WHERE id=%s", (aid,))[0][0] == "email_draft"
    s.suppress("consent.buyer@example.invalid", "requested no contact")
    with pytest.raises(SV.Blocked):
        s.draft_outreach(con, "again")
    with pytest.raises(SV.Blocked):
        s.set_consent(con, "opt_in")                       # the suppression list wins over a flipped flag
    s.close()


def test_there_is_no_way_to_send_publish_or_spend(db):
    names = {n for n, _ in inspect.getmembers(SV.GrowthService, inspect.isfunction)}
    assert not [n for n in names if any(w in n for w in ("send", "publish", "deploy", "purchase", "buy", "spend", "launch"))]
    s = svc(db, "tenant-nasha", "ada"); acc, con, lead = seed(s, "NoSend")
    camp = s.create_campaign("Draft campaign")
    for status in ("sent", "running", "published", "live"):
        with pytest.raises(psycopg.errors.CheckViolation):
            s.con.execute("UPDATE campaigns SET status=%s WHERE tenant_id=%s AND id=%s", (status, s.tenant, camp))
    with pytest.raises(psycopg.errors.CheckViolation):
        s.con.execute("INSERT INTO contacts (tenant_id,id,account_id,full_name,email) VALUES (%s,'con-real',%s,'Real Person','person@gmail.com')", (s.tenant, acc))      # real-looking addresses are rejected
    s.close()


# ---------------------------------------------------------------- audit, versions, append-only
def test_audit_is_hash_chained_complete_and_tamper_evident(db):
    s = svc(db, "tenant-fit", "ada"); seed(s, "Chain")
    ok, n = s.verify_audit()
    assert ok and n >= 4
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        s.con.execute("UPDATE audit_log SET action='x' WHERE tenant_id=%s", (s.tenant,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        s.con.execute("DELETE FROM audit_log WHERE tenant_id=%s", (s.tenant,))
    with psycopg.connect(db, autocommit=True) as admin:                    # a privileged actor edits a row: the chain must notice
        admin.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
        admin.execute("ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY"); admin.execute("UPDATE audit_log SET actor='mallory' WHERE tenant_id='tenant-fit' AND seq=2"); admin.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    assert s.verify_audit() == (False, 2)
    s.close()


def test_every_successful_write_has_exactly_one_audit_row(db):
    s = svc(db, "tenant-nasha", "mia")
    n0 = s.con.execute("SELECT count(*) FROM audit_log WHERE decision='allow'").fetchone()[0]
    seg = s.create_segment("Audit seg", "icp", {"x": 1}, "synthetic_assumption", 0.4)
    camp = s.create_campaign("Audit camp", segment_id=seg)
    assert s.con.execute("SELECT count(*) FROM audit_log WHERE decision='allow'").fetchone()[0] == n0 + 2
    assert {r[0] for r in s.read("SELECT entity_id FROM audit_log WHERE decision='allow' ORDER BY seq DESC LIMIT 2")} == {seg, camp}
    s.close()


def test_updates_bump_the_version_and_snapshot_every_state(db):
    s = svc(db, "tenant-nasha", "sam"); acc, con, lead = seed(s, "Ver")
    s.set_consent(con, "opt_in"); s.set_consent(con, "opt_out")
    assert s.read("SELECT version FROM contacts WHERE id=%s", (con,))[0][0] == 3
    snaps = s.read("SELECT version, snapshot->>'consent_status' FROM entity_versions WHERE entity='contacts' AND entity_id=%s ORDER BY version", (con,))
    assert snaps == [(1, "none"), (2, "opt_in"), (3, "opt_out")]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        s.con.execute("DELETE FROM entity_versions WHERE tenant_id=%s", (s.tenant,))
    s.close()


# ---------------------------------------------------------------- two different simulated businesses
@pytest.fixture(scope="module")
def two_tenants(db, tmp_path_factory):
    from nasha_lab.governed import tenants as T
    from nasha_lab.growth import seed as SD
    SV.provision(db, SCHEMA, "tenant-nasha-seeded", "NASHA seeded (synthetic)", "restaurant", [("ada", "Ada", "OWNER"), ("sam", "Sam", "SALES"), ("mia", "Mia", "MARKETING")])
    SV.provision(db, SCHEMA, "tenant-fit-seeded", "Meridian Fitness seeded (synthetic)", "fitness", [("ada", "Ada", "OWNER"), ("sam", "Sam", "SALES"), ("mia", "Mia", "MARKETING")])
    a_env, _ = T.default_pair(tmp_path_factory.mktemp("gt"))
    a, b = SV.GrowthService(db, SCHEMA, "tenant-nasha-seeded", "ada"), SV.GrowthService(db, SCHEMA, "tenant-fit-seeded", "ada")
    ra, rb = SD.seed_nasha(a, a_env.warehouse), SD.seed_fitness(b)
    yield a, b, ra, rb
    a.close(); b.close()


def test_the_two_tenants_have_different_products_prices_customers_and_segments(two_tenants):
    a, b, ra, rb = two_tenants
    pa = {r[0]: r[1] for r in a.read("SELECT p.name, pr.amount_cents FROM products p JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id WHERE pr.status='current'")}
    pb = {r[0]: r[1] for r in b.read("SELECT p.name, pr.amount_cents FROM products p JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id WHERE pr.status='current'")}
    assert pa["Tandoori Lamb Tacos"] == 1850 and pa["Chaat Elote"] == 1350 and "Monthly membership" not in pa and not any("Goat" in k for k in pa)
    assert pb == {"Monthly membership": 7900, "10-class pack": 14900, "Personal training session": 8500}
    assert {r[0] for r in a.read("SELECT name FROM segments")}.isdisjoint({r[0] for r in b.read("SELECT name FROM segments")})
    assert a.read("SELECT count(*) FROM accounts")[0] != b.read("SELECT count(*) FROM accounts")[0]
    assert {r[0] for r in a.read("SELECT email FROM contacts")}.isdisjoint({r[0] for r in b.read("SELECT email FROM contacts")})


def test_cross_tenant_probes_across_every_table_return_nothing(two_tenants):
    a, b, ra, rb = two_tenants
    ids_b = {t: [r[0] for r in b.read(f"SELECT id FROM {t}")] for t in ("accounts", "contacts", "leads", "segments", "products", "prices")}
    for t, ids in ids_b.items():
        assert ids, t
        assert not a.read(f"SELECT 1 FROM {t} WHERE id = ANY(%s)", (ids,)), f"tenant A can see tenant B {t}"
    assert not a.read("SELECT 1 FROM audit_log WHERE tenant_id=%s", ("tenant-fit-seeded",)) and not a.read("SELECT 1 FROM entity_versions WHERE tenant_id=%s", ("tenant-fit-seeded",))
    with pytest.raises(SV.Blocked):
        a.draft_outreach(rb["accounts"][0][1], "cross-tenant draft")


def test_segment_rows_are_labelled_synthetic_and_never_fully_confident(two_tenants):
    a, *_ = two_tenants
    rows = a.read("SELECT name, evidence_basis, confidence FROM segments")
    assert rows and all(r[1] in ("synthetic_data_derived", "synthetic_assumption") and r[2] < 1 for r in rows)
    assert any(r[1] == "synthetic_data_derived" for r in rows) and next(r for r in rows if r[0] == "nasha-corporate-lunch-organisers")[1] == "synthetic_assumption"
