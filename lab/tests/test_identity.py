import pytest
from fastapi.testclient import TestClient
from nasha_lab import agent, api, eval_agent as EA, identity as ID, knowledge, tools as T, world as W


class Clock:
    def __init__(self): self.t = 1_000_000.0
    def __call__(self): return self.t


@pytest.fixture()
def strict():
    clock = Clock(); au = ID.Authority.dev(clock=clock)
    w = W.build_world(1)[0]
    svc = agent.AgentService(w, knowledge.default_kb(), authority=au)
    return svc, w, au, clock


def login(au, who): return au.login(who, ID.DEV_PASSCODES[who][1])


def test_login_requires_the_right_passcode(strict):
    svc, w, au, c = strict
    assert au.identify(login(au, "alice")) == ID.Identity("alice", "BUYER")
    for bad in [("alice", "wrong-passcode"), ("mallory", "alice-dev-passcode"), ("founder", "alice-dev-passcode")]:
        with pytest.raises(ID.AuthError) as e: au.login(*bad)
        assert e.value.code == "BAD_CREDENTIALS"


def test_no_session_means_no_decision_and_the_run_stays_waiting(strict):
    svc, w, au, c = strict; rid = svc.start("EV-A1", "t")["run"]["run_id"]
    with pytest.raises(ID.AuthError) as e: svc.resume(rid, dict(decision="approve"))
    assert e.value.code == "AUTH_REQUIRED" and svc.summary(rid)["awaiting_human"]
    assert w.q("SELECT status FROM drafts")[0]["status"] == "DRAFT_NOT_SUBMITTED"


def test_forged_tampered_and_wrong_kind_tokens_are_refused(strict):
    svc, w, au, c = strict; rid = svc.start("EV-A1", "t")["run"]["run_id"]; tok = login(au, "alice")
    body, sig = tok.split(".")
    for bad, code in [(body + "." + sig[:-2] + "xx", "BAD_SIGNATURE"), ("garbage", "MALFORMED_TOKEN"), (ID.Authority.dev().dev_session("founder"), "BAD_SIGNATURE")]:
        with pytest.raises(ID.AuthError) as e: svc.resume(rid, dict(decision="approve"), session=bad)
        assert e.value.code == code
    grant = au.issue_grant(ID.Identity("founder", "FOUNDER"), rid, [dict(tool="release_draft", args={}, args_hash="h")])
    with pytest.raises(ID.AuthError) as e: svc.resume(rid, dict(decision="approve"), session=grant)        # a grant is not a session
    assert e.value.code == "WRONG_TOKEN_KIND" and svc.summary(rid)["awaiting_human"]


def test_wrong_role_cannot_approve_and_nothing_executes(strict):
    svc, w, au, c = strict
    rid = svc.start("EV-C1", "t")["run"]["run_id"]                                  # D-54 policy event: founder-only
    for who in ("alice", "bob"):
        with pytest.raises(ID.AuthError) as e: svc.resume(rid, dict(decision="approve"), session=login(au, who))
        assert e.value.code == "ROLE_NOT_PERMITTED"
    assert svc.summary(rid)["awaiting_human"] and w.q("SELECT COUNT(*) n FROM review_queue")[0]["n"] == 0
    s = svc.resume(rid, dict(decision="approve"), session=login(au, "founder"))
    assert s["final"]["outcome"] == "APPROVED_AND_EXECUTED_IN_SIMULATION"


def test_roles_map_to_actions(strict):
    svc, w, au, c = strict
    a = svc.start("EV-A1", "t")["run"]["run_id"]          # release a purchase draft: BUYER or FOUNDER, not QUALITY_LEAD
    with pytest.raises(ID.AuthError): svc.resume(a, dict(decision="approve"), session=login(au, "bob"))
    assert svc.resume(a, dict(decision="approve"), session=login(au, "alice"))["final"]["outcome"] == "APPROVED_AND_EXECUTED_IN_SIMULATION"
    b = svc.start("EV-B1", "t")["run"]["run_id"]          # quarantine review: QUALITY_LEAD or FOUNDER
    assert svc.resume(b, dict(decision="approve"), session=login(au, "bob"))["final"]["executed"][0]["ok"]


def test_reviewer_identity_and_role_are_recorded_in_the_trace(strict):
    svc, w, au, c = strict; rid = svc.start("EV-B2", "t")["run"]["run_id"]; svc.resume(rid, dict(decision="approve", reviewer="spoofed-name"), session=login(au, "bob"))
    ev = svc.store.events(rid); d = next(e for e in ev if e["kind"] == "human_decision"); v = next(e for e in ev if e["kind"] == "approval_verified")
    assert d["reviewer"] == "bob" and d["role"] == "QUALITY_LEAD" and v["reviewer"] == "bob"          # free text cannot override the token


def test_expired_session_and_expired_grant(strict):
    svc, w, au, c = strict; rid = svc.start("EV-A1", "t")["run"]["run_id"]; tok = login(au, "alice")
    c.t += au.session_ttl + 1
    with pytest.raises(ID.AuthError) as e: svc.resume(rid, dict(decision="approve"), session=tok)
    assert e.value.code == "EXPIRED"
    who = ID.Identity("alice", "BUYER"); args = dict(draft_id="DR-00000000"); h = T.args_hash("release_draft", args)
    g = au.issue_grant(who, rid, [dict(tool="release_draft", args=args, args_hash=h)])
    c.t += au.grant_ttl + 1
    assert au.verify_grant(g, rid, "release_draft", args, h) == (False, "EXPIRED", None)


def test_grant_replay_wrong_run_changed_arguments_and_wrong_tool(strict):
    svc, w, au, c = strict; who = ID.Identity("founder", "FOUNDER"); args = dict(table="orders", key="O000001", reason="human review requested")
    h = T.args_hash("flag_record_for_review", args)
    g = au.issue_grant(who, "run-1", [dict(tool="flag_record_for_review", args=args, args_hash=h)])
    assert au.verify_grant(g, "run-2", "flag_record_for_review", args, h)[1] == "WRONG_RUN"
    changed = dict(args, key="O999999")
    assert au.verify_grant(g, "run-1", "flag_record_for_review", changed, T.args_hash("flag_record_for_review", changed))[1] == "ARGUMENTS_OR_TOOL_NOT_APPROVED"
    assert au.verify_grant(g, "run-1", "release_draft", args, h)[1] == "ARGUMENTS_OR_TOOL_NOT_APPROVED"
    assert au.verify_grant(g, "run-1", "flag_record_for_review", args, h)[0] is True
    assert au.verify_grant(g, "run-1", "flag_record_for_review", args, h)[1] == "REPLAYED"


def test_grant_cannot_be_issued_for_a_role_that_may_not_approve(strict):
    svc, w, au, c = strict; args = dict(table="supplier_proposals", key="P-01", reason="policy review requested")
    with pytest.raises(ID.AuthError) as e: au.issue_grant(ID.Identity("alice", "BUYER"), "r", [dict(tool="flag_record_for_review", args=args, args_hash="h")])
    assert e.value.code == "ROLE_NOT_PERMITTED"


# ------------------------------------------------------------------ HTTP
@pytest.fixture()
def http(strict):
    svc, w, au, c = strict
    return TestClient(api.create_app(service=svc)), au


def bearer(http_au, who):
    client, au = http_au
    t = client.post("/auth/session", json={"reviewer_id": who, "passcode": ID.DEV_PASSCODES[who][1]}).json()["token"]
    return {"Authorization": "Bearer " + t}


def test_http_auth_flow(http):
    client, au = http
    assert client.post("/auth/session", json={"reviewer_id": "alice", "passcode": "nope-nope"}).status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=bearer(http, "alice")).json() == {"reviewer_id": "alice", "role": "BUYER"}
    rid = client.post("/agent/runs", json={"event_id": "EV-C1"}).json()["run"]["run_id"]
    assert client.post(f"/agent/runs/{rid}/approve", json={}).status_code == 401
    r = client.post(f"/agent/runs/{rid}/approve", json={}, headers=bearer(http, "alice")); assert r.status_code == 403 and r.json()["error"]["code"] == "ROLE_NOT_PERMITTED"
    assert client.get(f"/agent/runs/{rid}").json()["awaiting_human"]
    ok = client.post(f"/agent/runs/{rid}/approve", json={"note": "ok"}, headers=bearer(http, "founder")); assert ok.status_code == 200 and ok.json()["final"]["executed"][0]["ok"]
    assert client.post(f"/agent/runs/{rid}/approve", json={}, headers=bearer(http, "founder")).status_code == 409
