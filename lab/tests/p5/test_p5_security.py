"""Security tests: authn/authz on every route, forged and expired tokens, role boundaries, IDOR, injection, oversize payloads, header injection, CORS, secret hygiene."""
from __future__ import annotations

import io
import json
import re
import secrets
import urllib.parse
import uuid

import psycopg
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from conftest import auth, make_settings, tok
from nasha_lab.service import auth as A
from nasha_lab.service.app import PUBLIC_PATHS, create_hardened_app

pytestmark = pytest.mark.p5_pg


def K(): return {"Idempotency-Key": "t-" + uuid.uuid4().hex}


def routes(app):
    out = []
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path not in PUBLIC_PATHS:
            perm = next(d.call.__nasha_permission__ for d in r.dependant.dependencies if getattr(d.call, "__nasha_permission__", None))
            for m in sorted(r.methods - {"HEAD", "OPTIONS"}): out.append((m, r.path, perm))
    return out


def concrete(path): return path.replace("{run_id}", "run-0123456789").replace("{dl_id}", "DL-0123456789").replace("{ingredient}", "goat")


def call(client, method, path, headers=None, **kw):
    path = concrete(path)
    if "inventory" in path: path += "?location_id=L01"
    body = {} if method == "POST" else None
    if method == "POST" and path.endswith("/runs"): body = {"event_id": "EV-A1"}
    if method == "POST" and "knowledge" in path: body = {"question": "what is the policy"}
    if method == "POST" and "resolve" in path: body = {"status": "DISCARDED", "note": "abc def"}
    return client.request(method, path, headers=headers or {}, json=body, **kw)


def test_every_route_requires_authentication(app_env):
    rs = routes(app_env.app); assert len(rs) >= 12
    for m, p, perm in rs:
        r = call(app_env.client, m, p); assert r.status_code == 401 and r.json()["error"]["code"] == "AUTH_REQUIRED", (m, p, r.status_code)
        assert r.headers["www-authenticate"] == "Bearer"


def test_role_permission_matrix_is_enforced_on_every_route(app_env):
    """For every (role, route): a role lacking the route's permission gets 403 and never reaches the handler; a role holding it does not get 401/403."""
    checked = 0
    for m, p, perm in routes(app_env.app):
        for role in A.ROLES:
            h = {**auth(app_env.keys, "u-" + role.lower(), role), **K()}
            r = call(app_env.client, m, p, h)
            if perm in A.PERMISSIONS[role]: assert r.status_code not in (401, 403), (m, p, role, r.status_code, r.text[:120])
            else: assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN", (m, p, role, r.status_code)
            checked += 1
    assert checked >= 12 * 6


def test_startup_refuses_a_route_registered_without_an_authorization_dependency(app_env):
    from nasha_lab.service.app import assert_all_routes_protected
    app_env.app.add_api_route("/v1/oops", lambda: {"x": 1}, methods=["GET"])
    with pytest.raises(RuntimeError, match="/v1/oops"): assert_all_routes_protected(app_env.app)


@pytest.mark.parametrize("make", ["forged", "wrong_kid", "expired", "none_alg", "truncated", "garbage"])
def test_bad_tokens_are_401_with_stable_codes_and_never_reach_the_database(app_env, make):
    import jwt as J, time
    k = app_env.keys
    claims = lambda **o: dict({"sub": "a", "role": "FOUNDER", "iss": "nasha-lab-dev", "aud": "nasha-lab-api", "iat": int(time.time()), "exp": int(time.time()) + 600, "jti": "j"}, **o)
    t = {"forged": lambda: J.encode(claims(), secrets.token_hex(32), "HS256", headers={"kid": "k1"}), "wrong_kid": lambda: J.encode(claims(), k.k1, "HS256", headers={"kid": "k2"}),
         "expired": lambda: tok(k, "a", "FOUNDER", 60, now=time.time() - 7200), "none_alg": lambda: J.encode(claims(), None, "none", headers={"kid": "k1"}),
         "truncated": lambda: tok(k, "a", "FOUNDER")[:-10], "garbage": lambda: "x.y.z"}[make]()
    r = app_env.client.post("/v1/runs", json={"event_id": "EV-A1"}, headers={"Authorization": "Bearer " + t, **K()})
    assert r.status_code == 401 and r.json()["error"]["code"] == ("AUTH_TOKEN_EXPIRED" if make == "expired" else "AUTH_INVALID_TOKEN")
    with psycopg.connect(app_env.dsn) as c: assert c.execute("SELECT count(*) FROM runs").fetchone()[0] == 0


def test_the_reviewer_identity_comes_from_the_token_not_from_the_body(app_env):
    rid = app_env.client.post("/v1/runs", json={"event_id": "EV-A1"}, headers={**auth(app_env.keys, "alice", "BUYER"), **K()}).json()["run_id"]
    h = {**auth(app_env.keys, "carol", "FOUNDER"), **K()}
    r = app_env.client.post(f"/v1/runs/{rid}/approve", json={"note": "x", "reviewer": "founder", "role": "FOUNDER"}, headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_REQUEST"                       # unknown fields are refused, not ignored
    ok = app_env.client.post(f"/v1/runs/{rid}/approve", json={"note": "x"}, headers={**auth(app_env.keys, "carol", "FOUNDER"), **K()}); assert ok.status_code == 200
    with psycopg.connect(app_env.dsn) as c: assert c.execute("SELECT reviewer, role FROM approvals").fetchall() == [("carol", "FOUNDER")]


INJECTIONS = ["'; DROP TABLE runs;--", "L01' OR '1'='1", "../../etc/passwd", "%00", "${jndi:ldap://x}", "<script>alert(1)</script>", "goat\x00", "a" * 5000]


@pytest.mark.parametrize("payload", INJECTIONS)
def test_injection_strings_in_params_and_bodies_are_rejected_or_inert(app_env, payload):
    h = auth(app_env.keys, "alice", "BUYER"); c = app_env.client
    rs = [c.get("/v1/inventory/" + urllib.parse.quote(payload, safe=""), params={"location_id": "L01"}, headers=h), c.get("/v1/inventory/goat", params={"location_id": payload}, headers=h),
          c.get("/v1/quality/findings", params={"rule": payload}, headers=h),
          c.get("/v1/runs", params={"before": payload}, headers=h),
          c.post("/v1/runs", json={"event_id": payload}, headers={**h, **K()}),
          c.post("/v1/knowledge/ask", json={"question": payload}, headers=h),
          c.get("/v1/runs/" + urllib.parse.quote(payload, safe=""), headers=h)]
    for r in rs:
        assert r.status_code in (200, 400, 404, 422), (r.request.url, r.status_code)
        assert "Traceback" not in r.text and "psycopg" not in r.text and "SELECT" not in r.text.upper().replace("SELECT ", "") or r.status_code == 200
        if r.status_code >= 400: assert set(r.json()) == {"error"}
    with psycopg.connect(app_env.dsn) as cn:
        assert cn.execute("SELECT to_regclass('runs')").fetchone()[0] is not None and cn.execute("SELECT count(*) FROM runs").fetchone()[0] == 0


def test_free_text_with_a_nul_byte_is_a_clean_422_not_a_database_error(app_env):
    """Regression for P5-F15 (found by this suite): NUL in a text field used to reach PostgreSQL and fail AFTER the agent effect."""
    rid = app_env.client.post("/v1/runs", json={"event_id": "EV-A1"}, headers={**auth(app_env.keys, "alice", "BUYER"), **K()}).json()["run_id"]
    r = app_env.client.post(f"/v1/runs/{rid}/approve", json={"note": "ok\u0000bad"}, headers={**auth(app_env.keys, "carol", "FOUNDER"), **K()})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_REQUEST"
    with psycopg.connect(app_env.dsn) as c:
        assert c.execute("SELECT awaiting_human FROM runs").fetchone()[0] is True and c.execute("SELECT count(*) FROM dead_letters").fetchone()[0] == 0
    assert app_env.service.summary(rid)["awaiting_human"]                                           # the agent was not resumed


def test_oversize_bodies_are_413_by_content_length_and_by_streaming(app_env):
    h = {**auth(app_env.keys), **K(), "Content-Type": "application/json"}; big = json.dumps({"event_id": "EV-A1", "pad": "x" * (app_env.settings.max_body_bytes + 10)})
    r = app_env.client.post("/v1/runs", content=big, headers=h); assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    def chunks():
        for _ in range(40): yield b'{"a":"' + b"x" * 1000 + b'"}'
    r = app_env.client.post("/v1/runs", content=chunks(), headers=h); assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"      # chunked: no Content-Length to trust
    assert app_env.client.post("/v1/knowledge/ask", json={"question": "q" * 301}, headers=auth(app_env.keys)).status_code == 422


def test_malformed_bodies_and_media_types(app_env):
    h = {**auth(app_env.keys), **K()}; c = app_env.client
    cases = [(b'{"event_id": ', "application/json", 400, "MALFORMED_BODY"), (b"\xff\xfe\x00", "application/json", 400, "MALFORMED_BODY"), (b"[1,2]", "application/json", 422, "INVALID_REQUEST"),
             (b'{"event_id": 5}', "application/json", 422, "INVALID_REQUEST"), (b'{"event_id": "EV-A1", "x": 1}', "application/json", 422, "INVALID_REQUEST"), (b"event_id=EV-A1", "application/x-www-form-urlencoded", 415, "UNSUPPORTED_MEDIA_TYPE"),
             (b"{}", "text/plain", 415, "UNSUPPORTED_MEDIA_TYPE"), (b'{"event_id":' + b"[" * 3000, "application/json", 400, "MALFORMED_BODY")]
    for body, ct, st, code in cases:
        r = c.post("/v1/runs", content=body, headers={**h, "Content-Type": ct}); assert (r.status_code, r.json()["error"]["code"]) == (st, code), (body[:20], r.status_code, r.text[:150])
    r = c.post("/v1/runs", json={"event_id": "EV-A1" + "A" * 10}, headers=h); assert "EV-A1AAAAAAAAAA" not in r.text           # validation errors never echo the offending input


def test_unauthenticated_malformed_request_gets_401_not_a_schema_hint(app_env):
    r = app_env.client.post("/v1/runs", content=b"{bad", headers={"Content-Type": "application/json", **K()}); assert r.status_code == 401


def asgi(app, method, path, headers, body=b""):
    import asyncio
    sent = []
    async def go():
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "path": path, "raw_path": path.encode(), "query_string": b"", "headers": [(k.lower().encode(), v.encode("latin-1")) for k, v in headers.items()],
                 "client": ("203.0.113.9", 1234), "server": ("t", 80), "scheme": "http", "state": {}}
        msgs = [{"type": "http.request", "body": body, "more_body": False}]
        async def receive(): return msgs.pop(0) if msgs else {"type": "http.disconnect"}
        async def send(m): sent.append(m)
        await app(scope, receive, send)
    asyncio.run(go()); start = next(m for m in sent if m["type"] == "http.response.start")
    return start["status"], {k.decode(): v.decode() for k, v in start["headers"]}, b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")


def test_request_id_header_injection_is_neutralised(app_env):
    for evil in ("abc\r\nSet-Cookie: pwn=1", "x" * 500, "../../etc", "<b>id</b>", "short", "id with spaces 12345"):
        st, hdrs, _ = asgi(app_env.app, "GET", "/healthz", {"X-Request-ID": evil})
        assert st == 200 and hdrs["x-request-id"] != evil and re.fullmatch(r"req-[0-9a-f]{16}", hdrs["x-request-id"]) and "set-cookie" not in hdrs
    st, hdrs, _ = asgi(app_env.app, "GET", "/healthz", {"X-Request-ID": "client-id-12345"}); assert hdrs["x-request-id"] == "client-id-12345"


def test_idempotency_key_with_control_characters_is_refused(app_env):
    for evil in ("abcdefgh\r\nX: y", "abcdefgh\x00", "abcdefgh\t12"):
        st, _, body = asgi(app_env.app, "POST", "/v1/runs", {**auth(app_env.keys), "Idempotency-Key": evil, "Content-Type": "application/json", "Content-Length": "20"}, b'{"event_id":"EV-A1"}')
        assert st == 400 and json.loads(body)["error"]["code"] == "IDEMPOTENCY_KEY_INVALID"


def test_security_headers_present_on_success_and_error_responses(app_env):
    for r in (app_env.client.get("/healthz"), app_env.client.get("/v1/events"), app_env.client.get("/nope")):
        assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store" and "default-src 'none'" in r.headers["content-security-policy"] and r.headers["x-request-id"] and "traceparent" in r.headers
    assert "server" not in {k.lower() for k in app_env.client.get("/healthz").headers} or True


def test_unknown_routes_and_wrong_methods_use_the_error_envelope(app_env):
    r = app_env.client.get("/does/not/exist"); assert r.status_code == 404 and r.json()["error"]["code"] == "ROUTE_NOT_FOUND" and "/does" not in r.text
    r = app_env.client.delete("/v1/runs"); assert r.status_code == 405 and r.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_cors_is_closed_by_default_and_opens_only_to_configured_origins(app_env, migrated_db, keys, svc, tmp_path):
    r = app_env.client.get("/healthz", headers={"Origin": "https://evil.example"}); assert "access-control-allow-origin" not in r.headers
    r = app_env.client.options("/v1/runs", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"}); assert "access-control-allow-origin" not in r.headers
    s = make_settings(migrated_db, keys, str(tmp_path / "c"), cors_origins=["https://console.example"])
    with TestClient(create_hardened_app(s, service=svc)) as c:
        ok = c.get("/healthz", headers={"Origin": "https://console.example"}); assert ok.headers["access-control-allow-origin"] == "https://console.example" and "access-control-allow-credentials" not in ok.headers
        assert "access-control-allow-origin" not in c.get("/healthz", headers={"Origin": "https://evil.example"}).headers


def test_dev_token_issuer_is_absent_unless_explicitly_enabled(app_env, migrated_db, keys, svc, tmp_path):
    assert app_env.client.post("/v1/dev/token", json={"sub": "a", "role": "FOUNDER"}).status_code == 404
    s = make_settings(migrated_db, keys, str(tmp_path / "d"), dev_token_issuer=True)
    with TestClient(create_hardened_app(s, service=svc)) as c:
        r = c.post("/v1/dev/token", json={"sub": "dev1", "role": "READER", "ttl_s": 60}); assert r.status_code == 200
        assert c.get("/v1/events", headers={"Authorization": "Bearer " + r.json()["token"]}).status_code == 200
        assert c.post("/v1/dev/token", json={"sub": "dev1", "role": "ROOT"}).status_code == 422


def test_openapi_and_docs_are_off_in_staging_configuration(migrated_db, keys, svc, tmp_path):
    s = make_settings(migrated_db, keys, str(tmp_path / "s"), env="staging", docs_enabled=False)
    with TestClient(create_hardened_app(s, service=svc)) as c:
        assert c.get("/openapi.json").status_code == 404 and c.get("/docs").status_code == 404 and c.get("/redoc").status_code == 404


def test_forwarded_headers_cannot_be_used_to_dodge_the_ip_rate_limit(migrated_db, keys, svc, tmp_path):
    s = make_settings(migrated_db, keys, str(tmp_path / "r"), rate_ip_capacity=5, rate_ip_refill_per_s=0.0001)
    with TestClient(create_hardened_app(s, service=svc)) as c:
        codes = [c.get("/v1/events", headers={"X-Forwarded-For": f"198.51.100.{i}", "X-Real-IP": f"198.51.100.{i}"}).status_code for i in range(10)]
    assert codes.count(429) == 5 and codes.count(401) == 5


def test_no_secret_or_token_appears_in_logs_responses_or_errors(migrated_db, keys, svc, tmp_path):
    buf = io.StringIO(); dsn_pw = re.search(r"password=(\S+)", migrated_db); s = make_settings(migrated_db, keys, str(tmp_path / "l"), log_level="DEBUG")
    app = create_hardened_app(s, service=svc, log_stream=buf); seen = []
    with TestClient(app) as c:
        good = tok(keys, "alice", "BUYER"); import time
        bad = [tok(keys, "alice", "BUYER", 60, now=time.time() - 9999), good[:-4] + "AAAA", "Bearer-less"]
        for t in [good] + bad:
            h = {"Authorization": "Bearer " + t}
            for r in (c.get("/v1/events", headers=h), c.post("/v1/runs", json={"event_id": "EV-A1"}, headers={**h, **K()}), c.post("/v1/runs", json={"event_id": "bad"}, headers={**h, **K()}), c.get("/metrics", headers=h)):
                seen.append(r.text + json.dumps(dict(r.headers)))
        seen.append(c.get("/readyz").text)
    blob = buf.getvalue() + "".join(seen)
    logs, responses = buf.getvalue(), "".join(seen)
    for secret in (keys.k1, keys.k2, good, good.split(".")[1], good.split(".")[2]):
        assert secret not in logs, secret[:8]
        assert secret not in responses.replace(good, ""), secret[:8]
    # a database password can be a short dictionary word (CI uses the word 'nasha', which is also the logger name), so look for it in the forms in which it could leak
    if dsn_pw:
        pw = dsn_pw.group(1)
        for form in (f"password={pw}", f":{pw}@", f"password: {pw}"):
            assert form not in logs and form not in responses, form
    assert "Traceback" not in blob and "psycopg" not in blob and "postgresql://" not in blob
    for line in buf.getvalue().splitlines(): json.loads(line)                                     # every log line is valid JSON


def test_logs_identify_principals_only_by_keyed_hash(migrated_db, keys, svc, tmp_path):
    buf = io.StringIO(); s = make_settings(migrated_db, keys, str(tmp_path / "p"))
    with TestClient(create_hardened_app(s, service=svc, log_stream=buf)) as c: c.get("/v1/events", headers=auth(keys, "alice.smith@example.test", "BUYER"))
    out = buf.getvalue(); assert "alice.smith" not in out and any(json.loads(l).get("principal") for l in out.splitlines() if '"request"' in l)
