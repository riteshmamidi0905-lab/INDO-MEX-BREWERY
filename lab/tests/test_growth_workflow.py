"""Governed Growth OS lead-qualification workflow on real PostgreSQL and the real THE WEIR gateway: the happy path and every security, failure and recovery path required for Phase B.
Assertions about side effects are made against the DATABASE (leads, audit_log, activities), not the workflow's own return value. SYNTHETIC data only; the network is blocked."""
import asyncio
import dataclasses
import os
import socket
import uuid

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from nasha_lab.growth import schema as S, service as SV, workflow as WF
from nasha_lab.warehouse import pg_hardening as H

SCHEMA = "growth_wf"
GOOD = {"budget_confirmed": True, "decision_maker": True, "timeline_days": 20, "fit": 0.9, "engagement": 0.8}      # 25+20+20+18+12 = 95
WEAK = {"budget_confirmed": False, "decision_maker": False, "timeline_days": None, "fit": 0.2, "engagement": 0.1}   # 4+2 = 6
USERS = {"ada": ("Ada (synthetic owner)", "OWNER"), "omar": ("Omar (synthetic second owner)", "OWNER"), "sam": ("Sam (synthetic sales)", "SALES"), "mia": ("Mia (synthetic marketing)", "MARKETING"),
         "vic": ("Vic (synthetic viewer)", "VIEWER"), "ana": ("Ana (synthetic analyst)", "ANALYST")}


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


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
def world(dsn, tmp_path_factory):
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'); c.execute(f'CREATE SCHEMA "{SCHEMA}"')
    H.migrate(dsn, SCHEMA, specs=S.migrations(SCHEMA))
    root = tmp_path_factory.mktemp("gwf")
    return dsn, root


def make_env(world, tenant, clock=None, vertical="restaurant"):
    dsn, root = world
    return WF.provision_env(root / uuid.uuid4().hex[:6], dsn, SCHEMA, tenant, tenant, vertical, USERS, clock=clock)


def seed_lead(env, signals=GOOD, consent="opt_in", source="synthetic-referral", user="sam"):
    s = SV.GrowthService(env.dsn, SCHEMA, env.tenant_id, user)
    n = uuid.uuid4().hex[:8]
    a = s.create_account(f"Acct {n}"); c = s.create_contact(a, f"Person {n}", f"p{n}@example.invalid")
    if consent != "none":
        s.set_consent(c, consent)
    lead = s.create_lead(c, source, signals)
    s.close()
    return lead, c


def tok(wf, user):
    return wf.login(user, f"{wf.env.tenant_id}-{user}-dev-passcode")


def q(env, sql, params=()):
    with psycopg.connect(env.dsn, autocommit=True) as c:                        # privileged read for assertions (bypasses RLS on purpose)
        c.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
        cur = c.execute(sql, params)
        return cur.fetchall() if cur.description else []


def crm_updates(env, lead):
    return q(env, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='lead.qualification_applied' AND decision='allow' AND entity_id=%s", (env.tenant_id, lead))[0][0]


@pytest.fixture
def wf_pair(world):
    clock = Clock()
    env = make_env(world, "tenant-nasha", clock)
    wf = WF.GovernedLeadQualification(env, clock=clock)
    yield env, wf, clock
    wf.close()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    real = socket.socket.connect
    def guard(self, addr):
        if self.family != socket.AF_UNIX:
            raise AssertionError(f"network access attempted: {addr}")
        return real(self, addr)
    monkeypatch.setattr(socket.socket, "connect", guard)


# ---------------------------------------------------------------- the happy path
def test_end_to_end_lead_qualification_with_human_approval_updates_the_crm_and_contacts_no_one(wf_pair):
    env, wf, _ = wf_pair
    lead, contact = seed_lead(env)
    r = wf.run(tok(wf, "sam"), lead, idempotency_key="k-happy", request_id="req-1")
    assert r["status"] == "AWAITING_APPROVAL" and r["recommendation"]["proposed_status"] == "qualified" and r["recommendation"]["score"] == 95
    assert q(env, "SELECT status FROM leads WHERE id=%s", (lead,))[0][0] == "new" and crm_updates(env, lead) == 0, "nothing may change before the human decides"
    d = wf.decide(r["corr_id"], tok(wf, "ada"), True, "reviewed the evidence")
    assert d["status"] == "EXECUTED" and d["side_effects"] == dict(crm_updates=1, emails_sent=0, external_contacts=0)
    assert q(env, "SELECT status, score, qualified_by_run FROM leads WHERE id=%s", (lead,))[0] == ("qualified", 95, r["corr_id"])
    a = q(env, "SELECT actor, detail FROM audit_log WHERE tenant_id=%s AND action='lead.qualification_applied' AND entity_id=%s", (env.tenant_id, lead))
    assert len(a) == 1 and a[0][0] == "sam" and a[0][1]["approved_by"] == "ada" and a[0][1]["approval"] == r["approval_id"] and a[0][1]["run"] == r["corr_id"]
    stages = [e.get("name") for e in wf.trace(r["corr_id"]) if e["kind"] == "stage"]
    assert stages == ["request_received", "evidence_collected", "source_and_consent_validated", "recommendation", "proposal", "held_for_approval", "crm_updated", "no_external_contact"]
    assert q(env, "SELECT count(*) FROM activities WHERE contact_id=%s", (contact,))[0][0] == 0, "no email draft or message of any kind"
    assert wf.status(r["corr_id"])["state"] == "EXECUTED"


def test_rejection_leaves_the_crm_untouched_and_is_final(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    r = wf.run(tok(wf, "sam"), lead)
    d = wf.decide(r["corr_id"], tok(wf, "ada"), False, "not convinced")
    assert d["status"] == "REJECTED" and crm_updates(env, lead) == 0 and q(env, "SELECT status FROM leads WHERE id=%s", (lead,))[0][0] == "new"
    assert wf.decide(r["corr_id"], tok(wf, "ada"), True)["failure"] == "NOT_AWAITING_APPROVAL" and crm_updates(env, lead) == 0
    with pytest.raises(psycopg.errors.CheckViolation):
        q(env, "UPDATE workflow_runs SET state='STARTED' WHERE id=%s", (r["corr_id"],))             # a finished run cannot be reopened, even by SQL


def test_a_weak_lead_is_recommended_disqualified_with_evidence_for_every_reason(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env, WEAK)
    r = wf.run(tok(wf, "sam"), lead)
    rec = r["recommendation"]
    assert rec["proposed_status"] == "disqualified" and rec["score"] == 6 and all(x["evidence"] in rec["evidence"] for x in rec["reasons"])
    assert "not a validated model" in rec["notice"]


# ---------------------------------------------------------------- authorization is enforced by THE WEIR
def test_roles_without_the_write_tool_are_denied_by_the_weir_and_viewer_is_denied_earlier(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    for user, cls in (("mia", "TOOL_DENIED"), ("ana", "TOOL_DENIED"), ("vic", "ROLE_DENIED")):
        r = wf.run(tok(wf, user), lead)
        assert r["status"] in ("BLOCKED", "DENIED") and r["failure"] == cls, (user, r)
        assert crm_updates(env, lead) == 0
    ev = wf.trace(wf.run(tok(wf, "mia"), lead)["corr_id"])
    assert any(e["kind"] == "tool_call" and e.get("tool") == "crm__apply_lead_qualification" and e.get("failure") == "TOOL_DENIED" for e in ev), "the denial must come from the gateway call"


def test_the_write_never_runs_without_the_approval_path_and_an_unlisted_tool_is_blocked_before_any_upstream(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    ident = wf.env.authority.identify(tok(wf, "sam"))
    gw, crm = wf._gateway(ident)
    sess = gw.open_session("direct-attempt")
    out = wf.loop.run_until_complete(gw.call_tool_detailed(sess, "crm__delete_lead", {"lead_id": lead}))
    assert not out.forwarded and not out.approval_id
    calls = crm.calls
    res = wf.loop.run_until_complete(crm.call_tool("apply_lead_qualification", dict(proposal_id="x", lead_id=lead, status="qualified", score=95, expected_lead_version=1, evidence_hash="h"), 1))
    assert res["isError"] and "NO_APPROVAL_CONTEXT" in res["content"][0]["text"] and crm_updates(env, lead) == 0 and crm.calls == calls + 1


def test_direct_crm_writes_by_unauthorised_roles_are_denied_and_audited(world, wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    for user in ("vic", "mia", "ana"):
        s = SV.GrowthService(env.dsn, SCHEMA, env.tenant_id, user)
        with pytest.raises(SV.Denied):
            s.apply_qualification(lead, "qualified", 95, 1, "r", "a", "x")
        s.close()
    assert q(env, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='lead.qualify' AND decision='deny'", (env.tenant_id,))[0][0] >= 3 and crm_updates(env, lead) == 0


# ---------------------------------------------------------------- cross-tenant
def test_cross_tenant_sessions_leads_runs_and_approvals_do_not_cross(world):
    ea, eb = make_env(world, "tenant-nasha"), make_env(world, "tenant-fit", vertical="fitness")
    wa, wb = WF.GovernedLeadQualification(ea), WF.GovernedLeadQualification(eb)
    try:
        lead_a, _ = seed_lead(ea); lead_b, _ = seed_lead(eb)
        assert wa.run(tok(wb, "sam"), lead_a)["failure"] == "AUTH_DENIED", "tenant B's session must fail tenant A's signature check"
        assert wa.run(tok(wa, "sam"), lead_b)["failure"] == "NO_SUCH_LEAD", "tenant A cannot even see that tenant B's lead exists"
        ra = wa.run(tok(wa, "sam"), lead_a)
        assert wb.decide(ra["corr_id"], tok(wb, "ada"), True)["failure"] == "NOT_AWAITING_APPROVAL", "tenant B cannot decide tenant A's run"
        assert wb.status(ra["corr_id"]) is None and wb.trace(ra["corr_id"]) == []
        assert wa.decide(ra["corr_id"], tok(wb, "ada"), True)["failure"] == "AUTH_DENIED" and crm_updates(ea, lead_a) == 0
        assert wb.weir.list_approvals() == [] and len(wa.weir.list_approvals()) == 1
        wa.decide(ra["corr_id"], tok(wa, "ada"), True)
        assert crm_updates(ea, lead_a) == 1 and crm_updates(eb, lead_b) == 0 and q(eb, "SELECT status FROM leads WHERE id=%s", (lead_b,))[0][0] == "new"
    finally:
        wa.close(); wb.close()


def test_workflow_state_and_events_are_isolated_by_row_level_security(world):
    ea, eb = make_env(world, "tenant-nasha"), make_env(world, "tenant-fit", vertical="fitness")
    wa, wb = WF.GovernedLeadQualification(ea), WF.GovernedLeadQualification(eb)
    try:
        la, _ = seed_lead(ea); lb, _ = seed_lead(eb)
        ra, rb = wa.run(tok(wa, "sam"), la), wb.run(tok(wb, "sam"), lb)
        assert wa.store.run(rb["corr_id"]) is None and wb.store.run(ra["corr_id"]) is None
        assert wa.store.con.execute("SELECT count(*) FROM workflow_events WHERE run_id=%s", (rb["corr_id"],)).fetchone()[0] == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            wa.store.con.execute("INSERT INTO workflow_runs (tenant_id,id,workflow,requester,role,lead_id,state) VALUES ('tenant-fit','wf-forged','x','sam','SALES',%s,'STARTED')", (lb,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            wa.store.con.execute("DELETE FROM workflow_events")
    finally:
        wa.close(); wb.close()


# ---------------------------------------------------------------- consent, suppression, source, evidence
def test_a_suppressed_contact_is_blocked_before_any_proposal_exists(wf_pair):
    env, wf, _ = wf_pair
    lead, contact = seed_lead(env)
    email = q(env, "SELECT email FROM contacts WHERE id=%s", (contact,))[0][0]
    s = SV.GrowthService(env.dsn, SCHEMA, env.tenant_id, "sam"); s.suppress(email, "asked to stop"); s.close()
    r = wf.run(tok(wf, "sam"), lead)
    assert r["failure"] == "SUPPRESSED_CONTACT" and r["status"] == "BLOCKED" and wf.status(r["corr_id"])["proposal"] is None and not wf.weir.list_approvals() and crm_updates(env, lead) == 0


def test_suppression_after_the_proposal_blocks_the_execution(wf_pair):
    env, wf, _ = wf_pair
    lead, contact = seed_lead(env)
    r = wf.run(tok(wf, "sam"), lead)
    email = q(env, "SELECT email FROM contacts WHERE id=%s", (contact,))[0][0]
    s = SV.GrowthService(env.dsn, SCHEMA, env.tenant_id, "sam"); s.suppress(email, "asked to stop after the proposal"); s.close()
    d = wf.decide(r["corr_id"], tok(wf, "ada"), True)
    assert d["failure"] == "SUPPRESSED_CONTACT" and crm_updates(env, lead) == 0


def test_missing_consent_still_qualifies_but_marks_outreach_not_allowed_and_creates_no_message(wf_pair):
    env, wf, _ = wf_pair
    lead, contact = seed_lead(env, consent="none")
    r = wf.run(tok(wf, "sam"), lead)
    assert r["status"] == "AWAITING_APPROVAL" and r["recommendation"]["outreach_allowed"] is False
    wf.decide(r["corr_id"], tok(wf, "ada"), True)
    assert q(env, "SELECT count(*) FROM activities WHERE contact_id=%s", (contact,))[0][0] == 0
    lead2, c2 = seed_lead(env, consent="opt_in")
    assert wf.run(tok(wf, "sam"), lead2)["recommendation"]["outreach_allowed"] is True


def test_an_invalid_source_is_rejected_by_the_database_and_by_the_workflow(world, dsn=None):
    d, root = world
    with psycopg.connect(d, autocommit=True) as c:
        c.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
        env = make_env(world, "tenant-src")
        s = SV.GrowthService(d, SCHEMA, "tenant-src", "sam")
        a = s.create_account("Src Co"); con = s.create_contact(a, "S", "s@example.invalid")
        with pytest.raises(psycopg.errors.CheckViolation):
            s.create_lead(con, "scraped-linkedin", GOOD)                                      # layer 1: the schema refuses a non-synthetic source
        c.execute("ALTER TABLE leads DROP CONSTRAINT leads_source_synthetic")                 # layer 2 (defence in depth): remove it and the workflow still refuses
        lead = s.create_lead(con, "scraped-linkedin", GOOD)
        wf = WF.GovernedLeadQualification(env)
        try:
            r = wf.run(tok(wf, "sam"), lead)
            assert r["failure"] == "INVALID_SOURCE" and not wf.weir.list_approvals() and wf.status(r["corr_id"])["proposal"] is None
        finally:
            wf.close(); s.close()
        c.execute("ALTER TABLE leads ADD CONSTRAINT leads_source_synthetic CHECK (source LIKE 'synthetic%') NOT VALID")


@pytest.mark.parametrize("signals", [None, {}, {**GOOD, "fit": 7}, {**GOOD, "budget_confirmed": "yes"}, {**GOOD, "timeline_days": -3}, {**GOOD, "surprise": 1}, {**GOOD, "decision_maker": None}])
def test_invalid_or_missing_qualification_evidence_abstains_and_requests_no_approval(wf_pair, signals):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env, signals)
    r = wf.run(tok(wf, "sam"), lead)
    assert r["status"] == "ABSTAINED" and r["failure"] == "INVALID_EVIDENCE" and r["problems"] and not wf.weir.list_approvals() and crm_updates(env, lead) == 0


# ---------------------------------------------------------------- approvals: maker-checker, expiry, replay, tampering, duplicates
def test_maker_checker_and_role_rules_for_the_approver(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    r = wf.run(tok(wf, "ada"), lead)                                   # an OWNER requests...
    assert wf.decide(r["corr_id"], tok(wf, "ada"), True)["failure"] == "MAKER_CHECKER"
    for user in ("sam", "mia", "vic", "ana"):
        assert wf.decide(r["corr_id"], tok(wf, user), True)["failure"] == "ROLE_DENIED"
    assert crm_updates(env, lead) == 0
    assert wf.decide(r["corr_id"], tok(wf, "omar"), True)["status"] == "EXECUTED" and crm_updates(env, lead) == 1


def test_an_approval_that_expires_before_the_decision_is_refused(wf_pair):
    env, wf, clock = wf_pair
    lead, _ = seed_lead(env)
    r = wf.run(tok(wf, "sam"), lead)
    clock.advance(901)
    ses = tok(wf, "ada")                                               # a fresh session (the old ones also expire with the clock)
    d = wf.decide(r["corr_id"], ses, True)
    assert d["failure"] == "APPROVAL_EXPIRED" and d["status"] == "EXPIRED" and crm_updates(env, lead) == 0


def test_an_approval_that_expires_between_approval_and_execution_forces_reapproval(wf_pair):
    env, wf, clock = wf_pair
    lead, _ = seed_lead(env)
    r = wf.run(tok(wf, "sam"), lead)
    d = wf.decide(r["corr_id"], tok(wf, "ada"), True, execute=False)
    assert d["status"] == "APPROVED_NOT_EXECUTED"
    clock.advance(901)
    e = wf.execute_approved(r["corr_id"])
    assert e["failure"] == "REAPPROVAL_REQUIRED" and e["approval_id"] != r["approval_id"] and crm_updates(env, lead) == 0
    assert wf.status(r["corr_id"])["state"] == "AWAITING_APPROVAL"


def test_a_replayed_approval_creates_nothing_new(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    r = wf.run(tok(wf, "sam"), lead)
    assert wf.decide(r["corr_id"], tok(wf, "ada"), True)["status"] == "EXECUTED"
    for _ in range(3):
        assert wf.decide(r["corr_id"], tok(wf, "omar"), True)["failure"] == "APPROVAL_REPLAY"
    assert wf.execute_approved(r["corr_id"])["status"] == "DENIED" and crm_updates(env, lead) == 1


def test_a_proposal_modified_after_approval_is_not_applied(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env, WEAK)
    r = wf.run(tok(wf, "sam"), lead)
    wf.decide(r["corr_id"], tok(wf, "ada"), True, execute=False)
    run = wf.status(r["corr_id"]); p = dict(run["proposal"], proposed_status="qualified", score=95)
    import json
    q(env, "UPDATE workflow_runs SET proposal=%s::jsonb WHERE id=%s", (json.dumps(p), r["corr_id"]))     # tamper: flip the recommendation after the human approved the original
    e = wf.execute_approved(r["corr_id"])
    assert e["failure"] == "REAPPROVAL_REQUIRED" and crm_updates(env, lead) == 0 and q(env, "SELECT status FROM leads WHERE id=%s", (lead,))[0][0] == "new"


def test_a_lead_changed_after_the_proposal_makes_it_stale(wf_pair):
    env, wf, _ = wf_pair
    lead, contact = seed_lead(env)
    r = wf.run(tok(wf, "sam"), lead)
    s = SV.GrowthService(env.dsn, SCHEMA, env.tenant_id, "sam"); s.set_consent(contact, "opt_in"); s.close()
    q(env, "UPDATE leads SET source='synthetic-event-fair' WHERE tenant_id=%s AND id=%s", (env.tenant_id, lead))      # any change bumps the lead version
    d = wf.decide(r["corr_id"], tok(wf, "ada"), True)
    assert d["failure"] == "STALE_PROPOSAL" and crm_updates(env, lead) == 0


def test_duplicate_requests_return_the_original_run_without_new_effects(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    r1 = wf.run(tok(wf, "sam"), lead, idempotency_key="same-key")
    r2 = wf.run(tok(wf, "sam"), lead, idempotency_key="same-key")
    assert r2["status"] == "DUPLICATE" and r2["duplicate_of"] == r1["corr_id"]
    assert q(env, "SELECT count(*) FROM workflow_runs WHERE lead_id=%s", (lead,))[0][0] == 1 and len(wf.weir.list_approvals()) == 1


# ---------------------------------------------------------------- tool, database and partial failures
def _slow(self, name, args):
    async def go():
        await asyncio.sleep(0.5)
    return go()


def test_a_read_tool_timeout_fails_safe(world):
    env = make_env(world, "tenant-nasha")
    wf = WF.GovernedLeadQualification(env, fault=_slow, tool_timeout=0.05)
    try:
        lead, _ = seed_lead(env)
        r = wf.run(tok(wf, "sam"), lead)
        assert r["failure"] == "TOOL_TIMEOUT" and wf.status(r["corr_id"])["proposal"] is None and crm_updates(env, lead) == 0
    finally:
        wf.close()


@pytest.mark.parametrize("fault,cls", [(lambda self, n, a: {"content": [{"type": "text", "text": "not json at all"}], "isError": False}, "TOOL_BAD_RESPONSE"),
                                       (lambda self, n, a: {"content": [{"type": "text", "text": '{"error":"boom"}'}], "isError": True}, "TOOL_ERROR"),
                                       (lambda self, n, a: (_ for _ in ()).throw(psycopg.OperationalError("db down")), "TOOL_ERROR")])
def test_invalid_read_responses_and_database_failures_while_reading_never_become_evidence(world, fault, cls):
    env = make_env(world, "tenant-nasha")
    wf = WF.GovernedLeadQualification(env, fault=fault)
    try:
        lead, _ = seed_lead(env)
        r = wf.run(tok(wf, "sam"), lead)
        assert r["failure"] == cls and r["status"] in ("FAILED", "BLOCKED") and wf.status(r["corr_id"])["proposal"] is None and crm_updates(env, lead) == 0
    finally:
        wf.close()


def test_a_database_failure_during_the_crm_write_applies_nothing_and_recovery_needs_a_new_approval(world):
    env = make_env(world, "tenant-nasha")
    boom = {"on": True}
    def crm_fault(self, name, args):
        if boom["on"]:
            raise psycopg.OperationalError("connection lost during write")
    wf = WF.GovernedLeadQualification(env, crm_fault=crm_fault)
    try:
        lead, _ = seed_lead(env)
        r = wf.run(tok(wf, "sam"), lead)
        d = wf.decide(r["corr_id"], tok(wf, "ada"), True)
        assert d["status"] == "FAILED" and d["failure"] == "TOOL_ERROR" and crm_updates(env, lead) == 0 and wf.status(r["corr_id"])["state"] == "FAILED"
        assert wf.decide(r["corr_id"], tok(wf, "ada"), True)["failure"] == "NOT_AWAITING_APPROVAL", "the consumed approval cannot be reused"
    finally:
        wf.close()


def test_a_crash_after_the_crm_write_is_reconciled_against_the_crm_not_repeated(world):
    env = make_env(world, "tenant-nasha")
    wf = WF.GovernedLeadQualification(env)
    try:
        lead, _ = seed_lead(env)
        gw, crm = wf._gateway(wf.env.authority.identify(tok(wf, "sam")))
        crm.after_fault = lambda self, lead_id: {"content": [{"type": "text", "text": "connection reset after commit"}], "isError": True}      # the write committed, the response was lost
        r = wf.run(tok(wf, "sam"), lead)
        d = wf.decide(r["corr_id"], tok(wf, "ada"), True)
        assert d["status"] == "EXECUTED" and d.get("recovered_from") and crm_updates(env, lead) == 1
        assert any(e["kind"] == "recovery" for e in wf.trace(r["corr_id"]))
    finally:
        wf.close()


def test_every_step_is_traced_audited_and_secrets_never_appear(wf_pair):
    env, wf, _ = wf_pair
    lead, _ = seed_lead(env)
    ses = tok(wf, "sam")
    r = wf.run(ses, lead, request_id="req-trace")
    wf.decide(r["corr_id"], tok(wf, "ada"), True)
    ev = wf.trace(r["corr_id"])
    assert [e["seq"] for e in ev] == list(range(1, len(ev) + 1)) and any(e["kind"] == "approval_decision" for e in ev)
    blob = str(ev) + str(q(env, "SELECT detail FROM audit_log WHERE tenant_id=%s", (env.tenant_id,)))
    assert "dev-passcode" not in blob and ses not in blob
    ok = SV.GrowthService(env.dsn, SCHEMA, env.tenant_id, "ada").verify_audit()
    assert ok[0] is True
