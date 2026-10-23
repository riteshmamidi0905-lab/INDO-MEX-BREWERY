"""Growth OS workflow evaluation + mutation tests (real PostgreSQL, real THE WEIR gateway, SYNTHETIC data).

1. EVALUATION: a labelled set of synthetic leads whose expected qualification was computed BY HAND (an oracle independent of growth/scoring.py) is run through the whole governed workflow;
   the proposal, the CRM outcome and the audit record must match, and the safety cases must end in the expected block.
2. MUTATION: eight mutants each remove ONE control (authorization, tenant isolation, qualification threshold, suppression, consent, approval single-use, CRM state check, audit write).
   Every probe must PASS on the unmutated system and FAIL under its mutant; a surviving mutant would mean the tests do not test that control."""
import os
import uuid
from unittest import mock

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from nasha_lab.growth import qualification as Q, schema as S, scoring, service as SV, weir_growth as WG, workflow as WF
from nasha_lab.warehouse import pg_hardening as H

USERS = {"ada": ("Ada (synthetic owner)", "OWNER"), "omar": ("Omar (synthetic second owner)", "OWNER"), "sam": ("Sam (synthetic sales)", "SALES"), "vic": ("Vic (synthetic viewer)", "VIEWER")}


def sig(b, d, t, f, e):
    return {"budget_confirmed": b, "decision_maker": d, "timeline_days": t, "fit": f, "engagement": e}


# Hand-computed oracle: (signals, expected score, expected status). Points: budget 25, decision-maker 20, timeline <=30d 20 / <=90d 10, fit*20, engagement*15; qualify at >= 60.
ORACLE = [
    ("strong", sig(True, True, 20, 0.9, 0.8), 95, "qualified"),              # 25+20+20+18+12
    ("weak", sig(False, False, None, 0.2, 0.1), 6, "disqualified"),          # 0+0+0+4+2
    ("boundary-60", sig(True, True, 90, 0.25, 0.0), 60, "qualified"),        # 25+20+10+5+0
    ("just-below-58", sig(True, False, 10, 0.5, 0.2), 58, "disqualified"),   # 25+0+20+10+3
    ("no-decision-maker-45", sig(True, True, None, 0.0, 0.0), 45, "disqualified"),
]


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


class World:
    """One schema, two synthetic tenants, a workflow for each, and privileged helpers used only for assertions and for planting conditions."""

    def __init__(self, dsn, schema, root):
        self.dsn, self.schema = dsn, schema
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'); c.execute(f'CREATE SCHEMA "{schema}"')
        H.migrate(dsn, schema, specs=S.migrations(schema))
        self.envs = {t: WF.provision_env(root / f"{schema}-{t}", dsn, schema, t, t, "restaurant", USERS) for t in ("tenant-nasha", "tenant-meridian")}
        self.wf = {t: WF.GovernedLeadQualification(e) for t, e in self.envs.items()}

    def close(self):
        for w in self.wf.values():
            w.close()

    def tok(self, user, tenant="tenant-nasha"):
        w = self.wf[tenant]
        return w.login(user, f"{tenant}-{user}-dev-passcode")

    def sql(self, sql, params=()):
        with psycopg.connect(self.dsn, autocommit=True) as c:                    # privileged: bypasses RLS on purpose
            c.execute(f'SET search_path TO "{self.schema}", pg_catalog, public')
            cur = c.execute(sql, params)
            return cur.fetchall() if cur.description else []

    def lead(self, signals=None, consent="opt_in", tenant="tenant-nasha", suppress_directly=False):
        s = SV.GrowthService(self.dsn, self.schema, tenant, "sam")
        n = uuid.uuid4().hex[:8]
        a = s.create_account(f"Acct {n}"); email = f"p{n}@example.invalid"; c = s.create_contact(a, f"Person {n}", email)
        if consent != "none":
            s.set_consent(c, consent)
        lead = s.create_lead(c, "synthetic-referral", signals or sig(True, True, 20, 0.9, 0.8))
        s.close()
        if suppress_directly:                                                     # list updated independently of the consent flag
            self.sql("INSERT INTO suppression_list (tenant_id,email,reason) VALUES (%s,%s,'planted by test')", (tenant, email))
        return lead, c

    def status(self, lead):
        return self.sql("SELECT status FROM leads WHERE id=%s", (lead,))[0][0]

    def applied(self, lead):
        return self.sql("SELECT count(*) FROM audit_log WHERE action='lead.qualification_applied' AND decision='allow' AND entity_id=%s", (lead,))[0][0]


@pytest.fixture
def world(dsn, tmp_path):
    w = World(dsn, "growth_ev_" + uuid.uuid4().hex[:6], tmp_path)
    yield w
    w.close()


# ---------------------------------------------------------------- evaluation against the hand oracle
@pytest.mark.parametrize("name,signals,score,status", ORACLE, ids=[o[0] for o in ORACLE])
def test_workflow_proposal_and_crm_outcome_match_the_hand_computed_oracle(world, name, signals, score, status):
    lead, _ = world.lead(signals)
    wf = world.wf["tenant-nasha"]
    r = wf.run(world.tok("sam"), lead)
    assert r["status"] == "AWAITING_APPROVAL" and (r["recommendation"]["score"], r["recommendation"]["proposed_status"]) == (score, status)
    assert world.status(lead) == "new" and world.applied(lead) == 0
    d = wf.decide(r["corr_id"], world.tok("ada"), True)
    assert d["status"] == "EXECUTED" and world.status(lead) == status
    assert world.sql("SELECT score FROM leads WHERE id=%s", (lead,))[0][0] == score and world.applied(lead) == 1
    assert SV.GrowthService(world.dsn, world.schema, "tenant-nasha", "ada").verify_audit()[0] is True


# ---------------------------------------------------------------- probes: True means "the control holds"
def p_authorization(w):
    wf = w.wf["tenant-nasha"]
    lead, _ = w.lead()
    r = wf.run(w.tok("vic"), lead)                                                # a VIEWER may not start a qualification, and must never cause a CRM update
    if r["status"] == "AWAITING_APPROVAL":
        wf.decide(r["corr_id"], w.tok("ada"), True)
    return r["status"] != "EXECUTED" and w.applied(lead) == 0 and w.status(lead) == "new"


def p_tenant_isolation(w):
    other, _ = w.lead(tenant="tenant-meridian")
    s = SV.GrowthService(w.dsn, w.schema, "tenant-nasha", "sam")
    try:
        return s.get_lead_context(other) is None
    finally:
        s.close()


def p_qualification_threshold(w):
    ok = True
    for _, signals, score, status in ORACLE:
        lead, _ = w.lead(signals)
        rec = w.wf["tenant-nasha"].run(w.tok("sam"), lead).get("recommendation")
        ok &= bool(rec) and (rec["score"], rec["proposed_status"]) == (score, status)
    return ok


def p_suppression(w):
    lead, _ = w.lead(suppress_directly=True)
    r = w.wf["tenant-nasha"].run(w.tok("sam"), lead)
    return r.get("failure") == "SUPPRESSED_CONTACT" and not w.wf["tenant-nasha"].weir.list_approvals()


def p_consent(w):
    lead, _ = w.lead(consent="none")
    r = w.wf["tenant-nasha"].run(w.tok("sam"), lead)
    return r["recommendation"]["outreach_allowed"] is False


def p_approval_replay(w):
    import asyncio
    wf = w.wf["tenant-nasha"]
    lead, _ = w.lead()
    r = wf.run(w.tok("sam"), lead)
    if wf.decide(r["corr_id"], w.tok("ada"), True)["status"] != "EXECUTED":
        return False
    run = wf.store.run(r["corr_id"])
    gw, _crm = wf._gateway(WF.ID.Identity(run["requester"], run["role"]))
    out = wf.loop.run_until_complete(gw.call_tool_detailed(gw.open_session(r["corr_id"]), WG.CRM_TOOL, wf._args(run)))     # the identical call, again
    return out.forwarded is False and w.applied(lead) == 1


def p_crm_state(w):                                                               # the CRM write itself refuses a stale version and a converted lead
    lead, _ = w.lead()
    s = SV.GrowthService(w.dsn, w.schema, "tenant-nasha", "sam")
    try:
        w.sql("UPDATE leads SET source='synthetic-event-fair' WHERE id=%s", (lead,))     # version bump after the proposal
        try:
            s.apply_qualification(lead, "qualified", 95, 1, "wf-x", "appr-x", "ada"); return False
        except SV.Blocked:
            pass
        w.sql("UPDATE leads SET status='converted' WHERE id=%s", (lead,))
        try:
            s.apply_qualification(lead, "qualified", 95, 2, "wf-y", "appr-y", "ada"); return False
        except (SV.Blocked, psycopg.Error):
            pass
        return w.status(lead) == "converted" and w.applied(lead) == 0
    finally:
        s.close()


def p_audit(w):
    wf = w.wf["tenant-nasha"]
    lead, _ = w.lead()
    r = wf.run(w.tok("sam"), lead)
    wf.decide(r["corr_id"], w.tok("ada"), True)
    rows = w.sql("SELECT detail FROM audit_log WHERE action='lead.qualification_applied' AND decision='allow' AND entity_id=%s", (lead,))
    s = SV.GrowthService(w.dsn, w.schema, "tenant-nasha", "ada")
    try:
        return len(rows) == 1 and rows[0][0].get("approved_by") == "ada" and rows[0][0].get("approval") == r["approval_id"] and s.verify_audit()[0] is True
    finally:
        s.close()


# ---------------------------------------------------------------- mutants
def lax_context(self, lead_id):                                                  # mutant: no tenant filter in the query ...
    self._authorize("read")
    r = self.con.execute("SELECT l.id, l.status, l.score, l.source, l.signals, l.version, c.id, c.email, c.consent_status, false, a.id, a.name "
                         "FROM leads l JOIN contacts c ON c.id=l.contact_id JOIN accounts a ON a.id=c.account_id WHERE l.id=%s", (lead_id,)).fetchone()
    return None if not r else dict(lead_id=r[0], status=r[1], score=r[2], source=r[3], signals=r[4], lead_version=r[5], contact_id=r[6], consent_status=r[8], suppressed=False, account_id=r[10], account_name=r[11])


def ignore_suppression(orig):
    def f(self, lead_id):
        ctx = orig(self, lead_id)
        return None if ctx is None else dict(ctx, suppressed=False)
    return f


def always_outreach(orig):
    def f(ctx):
        return dict(orig(ctx), outreach_allowed=True)
    return f


def lax_consume(self, session_id, call_hash):                                    # mutant: approval is never marked consumed
    row = self._db.execute("SELECT id FROM approvals WHERE session_id=? AND call_hash=? AND state IN ('approved','consumed') ORDER BY created LIMIT 1", (session_id, call_hash)).fetchone()
    return str(row[0]) if row else None


def lax_apply(self, lead_id, status, score, expected_version, run_id, approval_id, approved_by):     # mutant: no version / converted check
    self.con.execute("UPDATE leads SET status=%s, score=%s, qualified_by_run=%s WHERE tenant_id=%s AND id=%s", (status, score, run_id, self.tenant, lead_id))
    self._audit("lead.qualification_applied", "leads", lead_id, "allow", {"run": run_id, "approval": approval_id, "approved_by": approved_by, "status": status, "score": score})
    return lead_id


def drop_qualification_audit(orig):
    def f(self, action, entity, entity_id, decision, detail=None):
        return None if action == "lead.qualification_applied" else orig(self, action, entity, entity_id, decision, detail)
    return f


RLS_OFF = "; ".join(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY; ALTER TABLE {t} DISABLE ROW LEVEL SECURITY" for t in ("leads", "contacts", "accounts"))

def drop_validator(orig):
    return lambda rec, ctx: []


def viewer_everywhere():
    import contextlib
    st = contextlib.ExitStack()
    st.enter_context(mock.patch.object(WG, "INITIATE_ROLES", WG.INITIATE_ROLES | {"VIEWER"}))
    st.enter_context(mock.patch.object(WG, "READ_ROLES", WG.READ_ROLES | {"VIEWER"}))
    st.enter_context(mock.patch.dict(SV.POLICY, {"lead.qualify": SV.POLICY["lead.qualify"] | {"VIEWER"}}))
    return st


def threshold_and_validator():
    import contextlib
    st = contextlib.ExitStack()
    st.enter_context(mock.patch.object(scoring, "QUALIFY_AT", 40))
    st.enter_context(mock.patch.object(Q, "validate_recommendation", drop_validator(Q.validate_recommendation)))
    return st


MUTANTS = [  # (name, probe, privileged SQL, patch factory)
    ("authorization bypass: VIEWER allowed at THE WEIR and in the service", p_authorization, None, viewer_everywhere),
    ("tenant leakage: RLS off and tenant filter removed", p_tenant_isolation, RLS_OFF, lambda: mock.patch.object(SV.GrowthService, "get_lead_context", lax_context)),
    ("incorrect lead qualification: threshold lowered and independent validator removed", p_qualification_threshold, None, threshold_and_validator),
    ("suppression bypass: suppression list ignored", p_suppression, None, lambda: mock.patch.object(SV.GrowthService, "get_lead_context", ignore_suppression(SV.GrowthService.get_lead_context))),
    ("consent bypass: outreach always allowed", p_consent, None, lambda: mock.patch.object(Q, "recommend", always_outreach(Q.recommend))),
    ("approval replay: approvals never consumed", p_approval_replay, None, lambda: mock.patch.object(WF.WeirStore, "consume_approval", lax_consume)),
    ("incorrect CRM transition: stale/converted check removed", p_crm_state, None, lambda: mock.patch.object(SV.GrowthService, "apply_qualification", lax_apply)),
    ("missing audit records: qualification not audited", p_audit, None, lambda: mock.patch.object(SV.GrowthService, "_audit", drop_qualification_audit(SV.GrowthService._audit))),
]
PROBES = [m[1] for m in MUTANTS]


@pytest.mark.parametrize("probe", PROBES, ids=[p.__name__ for p in PROBES])
def test_every_probe_passes_on_the_unmutated_system(dsn, tmp_path, probe):
    w = World(dsn, "growth_ev0_" + uuid.uuid4().hex[:6], tmp_path)
    try:
        assert probe(w) is True, probe.__name__
    finally:
        w.close()


@pytest.mark.parametrize("name,probe,sql,patch", MUTANTS, ids=[m[0].split(":")[0] for m in MUTANTS])
def test_each_mutant_is_detected_by_its_probe(dsn, tmp_path, name, probe, sql, patch):
    w = World(dsn, "growth_evm_" + uuid.uuid4().hex[:6], tmp_path)
    try:
        if sql:
            for st in sql.split("; "):
                w.sql(st)
        with patch():
            held = probe(w)
        assert held is False, f"mutant survived: {name}"
    finally:
        w.close()


# ---------------------------------------------------------------- defence in depth: a single removed layer is still stopped by the next one
def test_a_viewer_allowed_by_THE_WEIR_alone_is_still_stopped_by_the_service_policy(dsn, tmp_path):
    w = World(dsn, "growth_evl_" + uuid.uuid4().hex[:6], tmp_path)
    try:
        with mock.patch.object(WG, "INITIATE_ROLES", WG.INITIATE_ROLES | {"VIEWER"}), mock.patch.object(WG, "READ_ROLES", WG.READ_ROLES | {"VIEWER"}):
            assert p_authorization(w) is True
    finally:
        w.close()


def test_a_wrong_threshold_alone_is_caught_by_the_independent_validator(dsn, tmp_path):
    w = World(dsn, "growth_evl_" + uuid.uuid4().hex[:6], tmp_path)
    try:
        lead, _ = w.lead(sig(True, False, 10, 0.5, 0.2))                         # true score 58 -> disqualified; the mutant would say qualified
        with mock.patch.object(scoring, "QUALIFY_AT", 40):
            r = w.wf["tenant-nasha"].run(w.tok("sam"), lead)
        assert r["failure"] == "VALIDATION_FAILED" and not w.wf["tenant-nasha"].weir.list_approvals() and w.applied(lead) == 0
    finally:
        w.close()


def test_a_stale_proposal_is_stopped_before_the_write_even_if_the_service_check_is_removed(dsn, tmp_path):
    w = World(dsn, "growth_evl_" + uuid.uuid4().hex[:6], tmp_path)
    try:
        wf = w.wf["tenant-nasha"]
        lead, _ = w.lead()
        r = wf.run(w.tok("sam"), lead)
        w.sql("UPDATE leads SET source='synthetic-event-fair' WHERE id=%s", (lead,))
        with mock.patch.object(SV.GrowthService, "apply_qualification", lax_apply):
            d = wf.decide(r["corr_id"], w.tok("ada"), True)
        assert d["failure"] == "STALE_PROPOSAL" and w.status(lead) == "new" and w.applied(lead) == 0
    finally:
        w.close()


def test_a_replayed_approval_creates_nothing_new_even_if_THE_WEIR_never_consumes_approvals(dsn, tmp_path):
    w = World(dsn, "growth_evl_" + uuid.uuid4().hex[:6], tmp_path)
    try:
        wf = w.wf["tenant-nasha"]
        lead, _ = w.lead()
        r = wf.run(w.tok("sam"), lead)
        with mock.patch.object(WF.WeirStore, "consume_approval", lax_consume):
            assert wf.decide(r["corr_id"], w.tok("ada"), True)["status"] == "EXECUTED"
            again = wf.decide(r["corr_id"], w.tok("ada"), True)                      # workflow state machine stops it
            direct = wf.execute_approved(r["corr_id"])                                # so does the state check on direct execution
        assert again["failure"] == "APPROVAL_REPLAY" and direct["failure"] == "NOT_AWAITING_APPROVAL" and w.applied(lead) == 1
    finally:
        w.close()


def test_a_wrongly_permissive_consent_flag_does_not_make_the_workflow_able_to_send_anything(dsn, tmp_path):
    w = World(dsn, "growth_evl_" + uuid.uuid4().hex[:6], tmp_path)
    try:
        lead, contact = w.lead(consent="none")
        with mock.patch.object(Q, "recommend", always_outreach(Q.recommend)):
            r = w.wf["tenant-nasha"].run(w.tok("sam"), lead)
            w.wf["tenant-nasha"].decide(r["corr_id"], w.tok("ada"), True)
        assert w.sql("SELECT count(*) FROM activities WHERE contact_id=%s", (contact,))[0][0] == 0      # the flag is advisory; the draft gate (service) is the enforcement
        s = SV.GrowthService(w.dsn, w.schema, "tenant-nasha", "sam")
        with pytest.raises(SV.Blocked):
            s.draft_outreach(contact, "hello")
        s.close()
    finally:
        w.close()
