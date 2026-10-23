"""Growth OS HTTP API contract and security tests over real PostgreSQL, the real THE WEIR gateway and two synthetic tenants (NASHA and Meridian Fitness). SYNTHETIC data only."""
import os
import re
import uuid

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from nasha_lab.growth import api as GA, schema as S, workflow as WF
from nasha_lab.warehouse import pg_hardening as H

SCHEMA = "growth_api"
USERS = {"ada": ("Ada (synthetic owner)", "OWNER"), "omar": ("Omar (synthetic owner 2)", "OWNER"), "sam": ("Sam (synthetic sales)", "SALES"), "mia": ("Mia (synthetic marketing)", "MARKETING"),
         "vic": ("Vic (synthetic viewer)", "VIEWER"), "ana": ("Ana (synthetic analyst)", "ANALYST")}
GOOD = {"budget_confirmed": True, "decision_maker": True, "timeline_days": 20, "fit": 0.9, "engagement": 0.8}


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
def api(dsn, tmp_path_factory):
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'); c.execute(f'CREATE SCHEMA "{SCHEMA}"')
    H.migrate(dsn, SCHEMA, specs=S.migrations(SCHEMA))
    root = tmp_path_factory.mktemp("gapi")
    envs = {"tenant-nasha": WF.provision_env(root, dsn, SCHEMA, "tenant-nasha", "NASHA (synthetic)", "restaurant", USERS),
            "tenant-fit": WF.provision_env(root, dsn, SCHEMA, "tenant-fit", "Meridian Fitness (synthetic)", "fitness", USERS)}
    return TestClient(GA.create_growth_app(envs)), envs


def hdr(envs, tenant, user, **extra):
    env = envs[tenant]
    return {"Authorization": "Bearer " + env.authority.login(user, f"{tenant}-{user}-dev-passcode"), **extra}


def mk_lead(c, envs, tenant="tenant-nasha", signals=GOOD, consent="opt_in"):
    h = hdr(envs, tenant, "sam"); n = uuid.uuid4().hex[:8]
    a = c.post(f"/v1/tenants/{tenant}/accounts", json={"name": f"Acct {n}"}, headers=h).json()["id"]
    con = c.post(f"/v1/tenants/{tenant}/contacts", json={"account_id": a, "full_name": f"P {n}", "email": f"p{n}@example.invalid"}, headers=h).json()["id"]
    if consent != "none":
        assert c.put(f"/v1/tenants/{tenant}/contacts/{con}/consent", json={"status": consent}, headers=h).status_code == 200
    body = {"contact_id": con, "source": "synthetic-referral"}
    if signals is not None:
        body["signals"] = signals
    r = c.post(f"/v1/tenants/{tenant}/leads", json=body, headers=h)
    assert r.status_code == 201, r.text
    return a, con, r.json()["id"]


# ---------------------------------------------------------------- contract
def test_openapi_contract_has_only_tenant_scoped_v1_operations_and_nothing_that_sends_or_debugs(api):
    c, _ = api
    spec = c.get("/openapi.json").json()
    paths = spec["paths"]
    assert all(p == "/v1/health" or p.startswith("/v1/tenants/{tenant}/") for p in paths)
    words = ("debug", "admin", "sql", "dump", "export", "send", "publish", "deploy", "purchase", "email", "launch", "exec")
    assert not [p for p in paths if any(w in p.lower() for w in words)]
    ops = sorted(f"{m.upper()} {p}" for p, v in paths.items() for m in v)
    expected = ["GET /v1/health", "POST /v1/tenants/{tenant}/session", "GET /v1/tenants/{tenant}/me", "POST /v1/tenants/{tenant}/accounts", "GET /v1/tenants/{tenant}/accounts", "GET /v1/tenants/{tenant}/accounts/{account_id}", "POST /v1/tenants/{tenant}/contacts",
                "GET /v1/tenants/{tenant}/contacts", "PUT /v1/tenants/{tenant}/contacts/{contact_id}/consent", "POST /v1/tenants/{tenant}/leads", "GET /v1/tenants/{tenant}/leads", "GET /v1/tenants/{tenant}/leads/{lead_id}",
                "POST /v1/tenants/{tenant}/leads/{lead_id}/convert", "GET /v1/tenants/{tenant}/opportunities", "POST /v1/tenants/{tenant}/opportunities/{opp_id}/stage", "GET /v1/tenants/{tenant}/pipeline",
                "POST /v1/tenants/{tenant}/activities", "GET /v1/tenants/{tenant}/activities", "GET /v1/tenants/{tenant}/products", "POST /v1/tenants/{tenant}/products/{product_id}/prices", "POST /v1/tenants/{tenant}/pricing/scenarios",
                "POST /v1/tenants/{tenant}/workflows/lead-qualification", "GET /v1/tenants/{tenant}/workflows/runs", "GET /v1/tenants/{tenant}/workflows/runs/{corr_id}", "POST /v1/tenants/{tenant}/workflows/runs/{corr_id}/decision",
                "GET /v1/tenants/{tenant}/approvals", "GET /v1/tenants/{tenant}/audit", "GET /v1/tenants/{tenant}/audit/verify", "GET /v1/tenants/{tenant}/dashboard", "GET /v1/tenants/{tenant}/provenance",
                "GET /v1/tenants/{tenant}/projects", "POST /v1/tenants/{tenant}/projects", "GET /v1/tenants/{tenant}/projects/{project_id}", "PUT /v1/tenants/{tenant}/projects/{project_id}/assumptions/{key}",
                "POST /v1/tenants/{tenant}/projects/{project_id}/milestones", "PUT /v1/tenants/{tenant}/milestones/{milestone_id}/status", "POST /v1/tenants/{tenant}/projects/{project_id}/findings", "GET /v1/tenants/{tenant}/suppliers",
                "POST /v1/tenants/{tenant}/suppliers", "POST /v1/tenants/{tenant}/suppliers/{supplier_id}/products", "PUT /v1/tenants/{tenant}/projects/{project_id}/suppliers/{supplier_id}", "POST /v1/tenants/{tenant}/projects/{project_id}/scenarios/preview",
                "POST /v1/tenants/{tenant}/projects/{project_id}/scenarios/compare", "POST /v1/tenants/{tenant}/projects/{project_id}/scenarios", "GET /v1/tenants/{tenant}/projects/{project_id}/scenarios/{scenario_id}",
                "POST /v1/tenants/{tenant}/projects/{project_id}/procurement", "GET /v1/tenants/{tenant}/procurement/runs", "GET /v1/tenants/{tenant}/procurement/runs/{run_id}", "POST /v1/tenants/{tenant}/procurement/runs/{run_id}/decision"]
    assert ops == sorted(expected), set(ops) ^ set(expected)
    for p in paths.values():
        for op in p.values():
            if "requestBody" in op:
                ref = op["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
                assert spec["components"]["schemas"][ref].get("additionalProperties") is False, f"{ref} must reject unknown fields"


def test_every_error_uses_one_envelope_with_the_request_id_and_never_leaks_internals(api):
    c, envs = api
    for r in (c.get("/v1/tenants/tenant-nasha/accounts"), c.get("/v1/tenants/nope/accounts"), c.post("/v1/tenants/tenant-nasha/accounts", json={}, headers=hdr(envs, "tenant-nasha", "ada")),
              c.get("/v1/tenants/tenant-nasha/accounts/acc-deadbeef00", headers=hdr(envs, "tenant-nasha", "ada")), c.get("/nothing-here")):
        b = r.json()
        assert set(b) == {"error"} and set(b["error"]) == {"code", "message", "request_id"} and b["error"]["request_id"] == r.headers["X-Request-Id"]
        assert not re.search(r"Traceback|psycopg|postgres|/home/|\.py|SELECT |tenant_id", r.text)
    assert c.get("/v1/health", headers={"X-Request-Id": "trace-abc-123"}).headers["X-Request-Id"] == "trace-abc-123"
    assert c.get("/v1/health", headers={"X-Request-Id": "bad id!!"}).headers["X-Request-Id"] != "bad id!!"


# ---------------------------------------------------------------- authentication, tenant context
def test_unknown_tenants_and_bad_sessions_are_indistinguishable_and_cross_tenant_tokens_fail(api):
    c, envs = api
    a = hdr(envs, "tenant-nasha", "ada")
    r_unknown = c.get("/v1/tenants/tenant-ghost/accounts", headers=a)
    r_badtoken = c.get("/v1/tenants/tenant-nasha/accounts", headers={"Authorization": "Bearer abc.def"})
    r_cross = c.get("/v1/tenants/tenant-fit/accounts", headers=a)
    assert r_unknown.status_code == r_badtoken.status_code == r_cross.status_code == 401
    strip = lambda r: {**r.json()["error"], "request_id": ""}
    assert strip(r_unknown) == strip(r_badtoken) == strip(r_cross), "no existence oracle"


def test_tenant_context_cannot_be_changed_by_untrusted_parameters(api):
    c, envs = api
    h = hdr(envs, "tenant-nasha", "sam", **{"X-Tenant-Id": "tenant-fit", "X-Tenant": "tenant-fit"})
    assert c.get("/v1/tenants/tenant-nasha/me?tenant=tenant-fit&tenant_id=tenant-fit", headers=h).json() == {"tenant": "tenant-nasha", "user": "sam", "role": "SALES", "display_name": "Sam", "tenant_name": "NASHA (synthetic)"}
    r = c.post("/v1/tenants/tenant-nasha/accounts", json={"name": "Forged", "tenant_id": "tenant-fit"}, headers=h)
    assert r.status_code == 422, "an unknown body field such as tenant_id is rejected, not ignored"
    r = c.post("/v1/tenants/tenant-nasha/accounts?tenant_id=tenant-fit", json={"name": "Param Forged"}, headers=h)
    assert r.status_code == 201
    assert not [a for a in c.get("/v1/tenants/tenant-fit/accounts", headers=hdr(envs, "tenant-fit", "sam")).json()["items"] if a["name"] == "Param Forged"]


def test_cross_tenant_reads_by_id_find_nothing_and_cross_tenant_references_are_refused(api):
    c, envs = api
    a_acc, a_con, a_lead = mk_lead(c, envs); b_acc, b_con, b_lead = mk_lead(c, envs, "tenant-fit")
    hb = hdr(envs, "tenant-fit", "sam"); ha = hdr(envs, "tenant-nasha", "sam")
    assert c.get(f"/v1/tenants/tenant-fit/accounts/{a_acc}", headers=hb).status_code == 404
    assert c.get(f"/v1/tenants/tenant-fit/leads/{a_lead}", headers=hb).status_code == 404
    assert c.post("/v1/tenants/tenant-nasha/contacts", json={"account_id": b_acc, "full_name": "X", "email": "x@example.invalid"}, headers=ha).status_code == 422
    assert c.post("/v1/tenants/tenant-nasha/workflows/lead-qualification", json={"lead_id": b_lead}, headers=ha).status_code == 404
    assert b_acc not in {i["id"] for i in c.get("/v1/tenants/tenant-nasha/accounts?limit=50", headers=ha).json()["items"]}


# ---------------------------------------------------------------- authorization at the API
@pytest.mark.parametrize("user,method,path,body,status", [
    ("vic", "post", "/accounts", {"name": "x"}, 403), ("mia", "post", "/accounts", {"name": "x"}, 403), ("ana", "post", "/leads", {"contact_id": "con-aaaaaaaa", "source": "synthetic"}, 403),
    ("vic", "get", "/accounts", None, 200), ("mia", "post", "/workflows/lead-qualification", {"lead_id": "lead-aaaaaaaa"}, 404), ("sam", "post", "/products/prod-aaaaaaaa/prices", {"amount_cents": 100, "status": "current", "basis": "x y z"}, 403)])
def test_role_policy_is_enforced_by_default_deny(api, user, method, path, body, status):
    c, envs = api
    r = getattr(c, method)(f"/v1/tenants/tenant-nasha{path}", headers=hdr(envs, "tenant-nasha", user), **({"json": body} if body is not None else {}))
    assert r.status_code == status, r.text


# ---------------------------------------------------------------- validation, idempotency, pagination
@pytest.mark.parametrize("body", [{"name": ""}, {"name": "x" * 500}, {"name": "ok", "kind": "galaxy"}, {"name": "ok", "extra": 1}, {"name": 5}, {}])
def test_input_validation_rejects_malformed_account_bodies(api, body):
    c, envs = api
    assert c.post("/v1/tenants/tenant-nasha/accounts", json=body, headers=hdr(envs, "tenant-nasha", "ada")).status_code == 422


def test_contacts_must_be_synthetic_and_leads_need_synthetic_sources_and_valid_signals(api):
    c, envs = api
    h = hdr(envs, "tenant-nasha", "sam")
    acc = c.post("/v1/tenants/tenant-nasha/accounts", json={"name": f"V {uuid.uuid4().hex[:6]}"}, headers=h).json()["id"]
    assert c.post("/v1/tenants/tenant-nasha/contacts", json={"account_id": acc, "full_name": "R", "email": "real.person@gmail.com"}, headers=h).status_code == 422
    con = c.post("/v1/tenants/tenant-nasha/contacts", json={"account_id": acc, "full_name": "R", "email": f"{uuid.uuid4().hex[:6]}@example.invalid"}, headers=h).json()["id"]
    assert c.post("/v1/tenants/tenant-nasha/leads", json={"contact_id": con, "source": "scraped-linkedin"}, headers=h).status_code == 422
    assert c.post("/v1/tenants/tenant-nasha/leads", json={"contact_id": con, "source": "synthetic-x", "signals": {**GOOD, "fit": 3}}, headers=h).status_code == 422


def test_idempotency_key_replays_the_original_response_and_rejects_a_different_body(api):
    c, envs = api
    h = hdr(envs, "tenant-nasha", "sam", **{"Idempotency-Key": "idem-key-0001"})
    n = uuid.uuid4().hex[:6]
    r1 = c.post("/v1/tenants/tenant-nasha/accounts", json={"name": f"Idem {n}"}, headers=h)
    r2 = c.post("/v1/tenants/tenant-nasha/accounts", json={"name": f"Idem {n}"}, headers=h)
    assert r1.status_code == r2.status_code == 201 and r1.json() == r2.json() and r2.headers["Idempotent-Replay"] == "true"
    assert len([a for a in c.get("/v1/tenants/tenant-nasha/accounts?limit=50", headers=h).json()["items"] if a["name"] == f"Idem {n}"]) == 1
    assert c.post("/v1/tenants/tenant-nasha/accounts", json={"name": "A different body"}, headers=h).status_code == 409
    assert c.post("/v1/tenants/tenant-nasha/accounts", json={"name": "x"}, headers={**h, "Idempotency-Key": "short"}).status_code == 422


def test_the_same_idempotency_key_in_another_tenant_is_independent(api):
    c, envs = api
    k = {"Idempotency-Key": "shared-key-9999"}
    r1 = c.post("/v1/tenants/tenant-nasha/accounts", json={"name": f"Shared {uuid.uuid4().hex[:5]}"}, headers=hdr(envs, "tenant-nasha", "sam", **k))
    r2 = c.post("/v1/tenants/tenant-fit/accounts", json={"name": f"Shared {uuid.uuid4().hex[:5]}"}, headers=hdr(envs, "tenant-fit", "sam", **k))
    assert r1.status_code == r2.status_code == 201 and r1.json()["id"] != r2.json()["id"] and "Idempotent-Replay" not in r2.headers


def test_pagination_is_capped_ordered_and_complete(api):
    c, envs = api
    h = hdr(envs, "tenant-fit", "sam")
    for i in range(7):
        c.post("/v1/tenants/tenant-fit/accounts", json={"name": f"Page {uuid.uuid4().hex[:6]}"}, headers=h)
    assert c.get("/v1/tenants/tenant-fit/accounts?limit=51", headers=h).status_code == 422 and c.get("/v1/tenants/tenant-fit/accounts?limit=0", headers=h).status_code == 422
    assert c.get("/v1/tenants/tenant-fit/accounts?cursor=abc", headers=h).status_code == 422
    seen, cur = [], None
    while True:
        r = c.get("/v1/tenants/tenant-fit/accounts?limit=3" + (f"&cursor={cur}" if cur else ""), headers=h).json()
        seen += [i["id"] for i in r["items"]]; cur = r["next_cursor"]
        if not cur:
            break
    assert len(seen) == len(set(seen)) >= 7


# ---------------------------------------------------------------- pipeline and pricing
def test_pipeline_transitions_are_validated_by_the_backend(api):
    c, envs = api
    h = hdr(envs, "tenant-nasha", "sam")
    a, con, lead = mk_lead(c, envs)
    ql = c.post("/v1/tenants/tenant-nasha/workflows/lead-qualification", json={"lead_id": lead}, headers=h).json()
    assert c.post(f"/v1/tenants/tenant-nasha/workflows/runs/{ql['corr_id']}/decision", json={"approve": True}, headers=hdr(envs, "tenant-nasha", "ada")).status_code == 200
    opp = c.post(f"/v1/tenants/tenant-nasha/leads/{lead}/convert", json={"opportunity_name": "Team lunch", "amount_cents": 250000}, headers=h).json()["id"]
    bad = c.post(f"/v1/tenants/tenant-nasha/opportunities/{opp}/stage", json={"to_stage": "won"}, headers=h)
    assert bad.status_code == 409 and "illegal stage transition" in bad.json()["error"]["message"]
    assert c.post(f"/v1/tenants/tenant-nasha/opportunities/{opp}/stage", json={"to_stage": "qualified"}, headers=h).status_code == 200
    assert c.post(f"/v1/tenants/tenant-nasha/opportunities/{opp}/stage", json={"to_stage": "qualified"}, headers=h).status_code == 409
    assert c.post(f"/v1/tenants/tenant-nasha/opportunities/{opp}/stage", json={"to_stage": "galaxy"}, headers=h).status_code == 422
    p = c.get("/v1/tenants/tenant-nasha/pipeline", headers=h).json()
    assert {s["stage"]: s["next"] for s in p["stages"]}["qualified"] == ["lost", "proposal"] and sum(s["count"] for s in p["stages"]) >= 1


def _product(c, envs, tenant, name, cost, price, user="ada"):
    from nasha_lab.growth import service as SV
    s = SV.GrowthService(envs[tenant].dsn, SCHEMA, tenant, user)
    pid = s.create_product(f"{name} {uuid.uuid4().hex[:4]}", "dish", cost); s.set_price(pid, price, __import__("datetime").date(2026, 10, 23), "current", "synthetic"); s.close()
    return pid


def test_pricing_scenarios_use_the_pricing_engine_label_their_assumptions_and_are_role_gated(api):
    c, envs = api
    pid = _product(c, envs, "tenant-nasha", "Tandoori Lamb Tacos", 555, 1850)
    body = {"product_id": pid, "base_units": 200, "fixed_costs_cents": 100000, "assumed_elasticity": -1.5, "scenarios": [{"label": "base"}, {"label": "10% off", "discount_pct": 10}, {"label": "lamb +20%", "cost_shock": 0.2}]}
    r = c.post("/v1/tenants/tenant-nasha/pricing/scenarios", json=body, headers=hdr(envs, "tenant-nasha", "ana"))
    assert r.status_code == 200
    j = r.json(); base, off, inf = j["scenarios"]
    assert abs(base["margin"] - (1850 - 555) / 1850) < 1e-9 and abs(off["price_cents"] - 1665) < 1e-9 and abs(inf["cost_cents"] - 666) < 1e-9
    assert abs(off["gross_profit_at_base_units_cents"] - (1665 - 555) * 200) < 1e-6 and abs(base["breakeven_units"] - 100000 / 1295) < 1e-9
    assert any("planning assumptions" in a for a in j["assumptions"]) and "assumed" in j["sensitivity"]["assumption"]
    assert c.post("/v1/tenants/tenant-nasha/pricing/scenarios", json=body, headers=hdr(envs, "tenant-nasha", "sam")).status_code == 403
    assert c.post("/v1/tenants/tenant-nasha/pricing/scenarios", json={**body, "product_id": "prod-ffffffff00"}, headers=hdr(envs, "tenant-nasha", "ada")).status_code == 404
    other = _product(c, envs, "tenant-fit", "Monthly membership", 1800, 7900)
    assert c.post("/v1/tenants/tenant-nasha/pricing/scenarios", json={**body, "product_id": other}, headers=hdr(envs, "tenant-nasha", "ada")).status_code == 404, "another tenant's product is invisible"
    prods = c.get("/v1/tenants/tenant-nasha/products", headers=hdr(envs, "tenant-nasha", "vic")).json()["items"]
    lamb = next(p for p in prods if p["id"] == pid)
    assert abs(lamb["margin"] - (1850 - 555) / 1850) < 1e-9


# ---------------------------------------------------------------- the governed workflow over HTTP
def test_lead_qualification_over_http_denied_held_approved_updated_and_audited(api):
    c, envs = api
    a, con, lead = mk_lead(c, envs)
    sam, ada, mia = (hdr(envs, "tenant-nasha", u) for u in ("sam", "ada", "mia"))
    base = "/v1/tenants/tenant-nasha"
    assert c.post(f"{base}/workflows/lead-qualification", json={"lead_id": lead}, headers=mia).status_code == 403, "THE WEIR denies a role without the write tool"
    r = c.post(f"{base}/workflows/lead-qualification", json={"lead_id": lead}, headers={**sam, "Idempotency-Key": "qual-key-0001"})
    assert r.status_code == 202 and r.json()["status"] == "AWAITING_APPROVAL" and r.json()["recommendation"]["score"] == 95
    run = r.json()["corr_id"]
    assert c.post(f"{base}/workflows/lead-qualification", json={"lead_id": lead}, headers={**sam, "Idempotency-Key": "qual-key-0001"}).status_code == 200
    pend = c.get(f"{base}/approvals?state=pending", headers=ada).json()["items"]
    assert run in {p["run_id"] for p in pend}
    assert c.get(f"{base}/leads/{lead}", headers=ada).json()["status"] == "new"
    assert c.post(f"{base}/workflows/runs/{run}/decision", json={"approve": True}, headers=sam).status_code == 403          # maker-checker / role
    d = c.post(f"{base}/workflows/runs/{run}/decision", json={"approve": True, "comment": "ok"}, headers=ada)
    assert d.status_code == 200 and d.json()["status"] == "EXECUTED" and d.json()["side_effects"]["emails_sent"] == 0
    assert c.post(f"{base}/workflows/runs/{run}/decision", json={"approve": True}, headers=ada).status_code == 409, "replay"
    assert c.get(f"{base}/leads/{lead}", headers=ada).json()["status"] == "qualified"
    det = c.get(f"{base}/workflows/runs/{run}", headers=sam).json()
    assert det["state"] == "EXECUTED" and [e.get("name") for e in det["events"] if e["kind"] == "stage"][-2:] == ["crm_updated", "no_external_contact"]
    hist = c.get(f"{base}/approvals?state=history", headers=ada).json()["items"]
    assert any(h["run_id"] == run and h["detail"]["decision"] == "approve" for h in hist)
    aud = c.get(f"{base}/audit?limit=50", headers=ada).json()["items"]
    assert any(a["action"] == "lead.qualification_applied" and a["entity_id"] == lead and a["detail"]["approved_by"] == "ada" for a in aud)
    assert c.get(f"{base}/audit/verify", headers=ada).json()["chain_valid"] is True
    other = hdr(envs, "tenant-fit", "ada")
    assert c.get(f"/v1/tenants/tenant-fit/workflows/runs/{run}", headers=other).status_code == 404 and c.post(f"/v1/tenants/tenant-fit/workflows/runs/{run}/decision", json={"approve": True}, headers=other).status_code == 404


def test_dashboard_numbers_match_the_database_and_are_tenant_scoped(api):
    c, envs = api
    h = hdr(envs, "tenant-nasha", "ada")
    d = c.get("/v1/tenants/tenant-nasha/dashboard", headers=h).json()
    assert d["synthetic"] is True and d["lead_total"] == sum(d["leads"].values()) and d["approvals_pending"] == d["qualification_runs"].get("AWAITING_APPROVAL", 0)
    items = c.get("/v1/tenants/tenant-nasha/leads?limit=50", headers=h).json()
    assert d["lead_total"] >= len(items["items"]) and all(e["run_id"].startswith("wf-") for e in d["recent_events"])
    db = c.get("/v1/tenants/tenant-fit/dashboard", headers=hdr(envs, "tenant-fit", "ada")).json()
    assert db["lead_total"] != d["lead_total"] or db["recent_events"] != d["recent_events"]


def test_login_issues_a_tenant_bound_session_and_fails_identically_for_unknown_tenants_and_bad_passcodes(api):
    c, envs = api
    ok = c.post("/v1/tenants/tenant-nasha/session", json={"user": "sam", "passcode": "tenant-nasha-sam-dev-passcode"})
    assert ok.status_code == 200 and ok.json()["role"] == "SALES" and c.get("/v1/tenants/tenant-nasha/me", headers={"Authorization": "Bearer " + ok.json()["token"]}).status_code == 200
    assert c.get("/v1/tenants/tenant-fit/me", headers={"Authorization": "Bearer " + ok.json()["token"]}).status_code == 401
    bad = [c.post("/v1/tenants/tenant-nasha/session", json={"user": "sam", "passcode": "wrong"}), c.post("/v1/tenants/tenant-ghost/session", json={"user": "sam", "passcode": "x"}),
           c.post("/v1/tenants/tenant-nasha/session", json={"user": "nobody", "passcode": "x"})]
    assert {r.status_code for r in bad} == {401} and len({r.json()["error"]["message"] for r in bad}) == 1 and "token" not in bad[0].text
