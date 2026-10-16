"""Unit tests (no database): configuration, secrets handling, tokens and permissions, rate limiter, metrics, log redaction, trace context, error table."""
from __future__ import annotations

import io
import json
import logging
import os
import secrets
import time

import jwt
import pytest

from nasha_lab.service import auth as A, errors as E, obs
from nasha_lab.service.config import ConfigError, load_settings
from nasha_lab.service.ratelimit import TokenBucketLimiter


def env(**kw):
    base = {"NASHA_SVC_DATABASE_URL": "postgresql://svc:" + secrets.token_hex(8) + "@db.invalid:5432/app", "NASHA_SVC_JWT_KEYS": json.dumps({"k1": secrets.token_hex(32)}), "NASHA_SVC_JWT_ACTIVE_KID": "k1"}
    base.update({"NASHA_SVC_" + k.upper(): v for k, v in kw.items()}); return base


# --------------------------------------------------------------------------------------------- configuration
def test_valid_config_loads_with_defaults_and_typed_values():
    s = load_settings(env(db_pool_max="7", rate_ip_capacity="12.5", require_db_at_start="true"))
    assert s.db_pool_max == 7 and s.rate_ip_capacity == 12.5 and s.require_db_at_start is True and s.env == "dev" and s.cors_origins == []


def test_repr_str_dump_and_safe_dict_never_contain_secret_values():
    e = env(); s = load_settings(e); pw = e["NASHA_SVC_DATABASE_URL"].split(":")[2].split("@")[0]; key = list(json.loads(e["NASHA_SVC_JWT_KEYS"]).values())[0]
    for text in (repr(s), str(s), s.model_dump_json(), json.dumps(s.safe_dict()), repr(s.jwt_keys), str(s.database_url)):
        assert pw not in text and key not in text
    assert s.database_url.get_secret_value().endswith("/app")        # the value is reachable only through the explicit accessor


@pytest.mark.parametrize("bad,needle", [
    ({"database_url": "mysql://u:p@h/db"}, "DATABASE_URL"), ({"db_pool_max": "0"}, "DB_POOL_MAX"), ({"db_pool_min": "9", "db_pool_max": "3"}, "db_pool_min"),
    ({"rate_ip_capacity": "-1"}, "RATE_IP_CAPACITY"), ({"jwt_active_kid": "nope"}, "jwt_active_kid"), ({"env": "production"}, "ENV"), ({"cors_origins": '["*"]'}, "wildcards"),
    ({"tool_timeout_s": "20", "run_deadline_s": "10"}, "tool_timeout_s"), ({"max_body_bytes": "10"}, "MAX_BODY_BYTES"), ({"log_level": "TRACE"}, "LOG_LEVEL"),
    ({"env": "staging", "dev_token_issuer": "true"}, "dev_token_issuer"), ({"env": "staging", "docs_enabled": "true"}, "docs_enabled"),
])
def test_bad_config_fails_fast_with_a_clear_value_free_message(bad, needle):
    base = env(); e = dict(base, **{"NASHA_SVC_" + k.upper(): v for k, v in bad.items()})
    with pytest.raises(ConfigError) as x: load_settings(e)
    assert needle in str(x.value)
    secret_bits = [base["NASHA_SVC_DATABASE_URL"].split(":")[2].split("@")[0], list(json.loads(base["NASHA_SVC_JWT_KEYS"]).values())[0]]
    assert not any(b in str(x.value) for b in secret_bits)


def test_missing_required_settings_are_all_reported_together():
    with pytest.raises(ConfigError) as x: load_settings({})
    m = str(x.value); assert "DATABASE_URL" in m and "JWT_KEYS" in m and "JWT_ACTIVE_KID" in m


def test_weak_or_placeholder_signing_keys_are_refused_without_echoing_them():
    for weak in ("zq9", "changeme" * 6, "password-password-password-password-x"):
        e = env(); e["NASHA_SVC_JWT_KEYS"] = json.dumps({"k1": weak})
        with pytest.raises(ConfigError) as x: load_settings(e)
        assert weak not in str(x.value) and "k1" in str(x.value)


def test_unknown_setting_is_rejected_a_typo_in_a_security_setting_must_not_be_ignored():
    with pytest.raises(ConfigError, match="NASHA_SVC_JWT_ISUER: unknown setting"): load_settings(env(jwt_isuer="x"))


def test_malformed_json_setting_does_not_echo_its_value():
    e = env(); e["NASHA_SVC_JWT_KEYS"] = '{"k1": "' + secrets.token_hex(20)
    with pytest.raises(ConfigError) as x: load_settings(e)
    assert "valid JSON" in str(x.value) and e["NASHA_SVC_JWT_KEYS"][8:20] not in str(x.value)


def test_secrets_can_be_read_from_files(tmp_path):
    kf, df = tmp_path / "keys", tmp_path / "dsn"; k = secrets.token_hex(32); kf.write_text(json.dumps({"k9": k}) + "\n"); df.write_text("postgresql://u:" + secrets.token_hex(6) + "@h/d\n")
    s = load_settings({"NASHA_SVC_JWT_KEYS_FILE": str(kf), "NASHA_SVC_DATABASE_URL_FILE": str(df), "NASHA_SVC_JWT_ACTIVE_KID": "k9"})
    assert s.signing_keys() == {"k9": k}
    with pytest.raises(ConfigError, match="cannot read the secret file"): load_settings({"NASHA_SVC_JWT_KEYS_FILE": str(tmp_path / "missing"), "NASHA_SVC_DATABASE_URL": "postgresql://u:p@h/d", "NASHA_SVC_JWT_ACTIVE_KID": "k9"})


def test_environment_value_wins_over_file(tmp_path):
    f = tmp_path / "k"; f.write_text(json.dumps({"kf": secrets.token_hex(32)}))
    e = env(); e["NASHA_SVC_JWT_KEYS_FILE"] = str(f)
    assert list(load_settings(e).jwt_keys) == ["k1"]


def test_cli_check_config_masks_secrets_and_bad_config_exits_78(monkeypatch, capsys):
    from nasha_lab.service.__main__ import main
    e = env()
    for k, v in e.items(): monkeypatch.setenv(k, v)
    assert main(["check-config"]) == 0
    out = capsys.readouterr().out; assert "***" in out and list(json.loads(e["NASHA_SVC_JWT_KEYS"]).values())[0] not in out
    monkeypatch.setenv("NASHA_SVC_DB_POOL_MAX", "0"); assert main(["check-config"]) == 78
    monkeypatch.setenv("NASHA_SVC_DB_POOL_MAX", "5"); monkeypatch.setenv("NASHA_SVC_ENV", "staging"); assert main(["mint-token", "--sub", "x", "--role", "READER"]) == 2


def test_serve_factory_exits_78_on_bad_config(monkeypatch):
    from nasha_lab.service import serve
    for k in list(os.environ):
        if k.startswith("NASHA_SVC_"): monkeypatch.delenv(k)
    with pytest.raises(SystemExit) as x: serve.app()
    assert x.value.code == 78


# --------------------------------------------------------------------------------------------- tokens
KEYS = {"k1": secrets.token_hex(32), "k2": secrets.token_hex(32)}
def svc(**kw): return A.TokenService(KEYS, "k1", "iss", "aud", **kw)


def test_valid_token_round_trips_with_kid_and_role():
    p = svc().verify(svc().issue("alice", "BUYER"))
    assert (p.sub, p.role, p.kid) == ("alice", "BUYER", "k1") and p.can("runs:decide") and not p.can("metrics:read")


def test_expired_token_is_distinguished_from_invalid():
    with pytest.raises(E.ApiError) as x: svc().verify(svc().issue("alice", "BUYER", 60, now=time.time() - 7200))
    assert x.value.code == "AUTH_TOKEN_EXPIRED"


@pytest.mark.parametrize("make", [
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, secrets.token_hex(32), algorithm="HS256", headers={"kid": "k1"}),   # forged: wrong key
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k2"}),   # right key, wrong kid
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "unknown"}),
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256"),                              # no kid
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS512", headers={"kid": "k1"}),    # algorithm switch
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, None, algorithm="none", headers={"kid": "k1"}),             # alg none
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "other", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k1"}),  # wrong issuer
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "other", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k1"}),  # wrong audience
    lambda s: jwt.encode({"sub": "a", "role": "ROOT", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k1"}),      # unknown role
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k1"}),                                  # no exp
    lambda s: jwt.encode({"sub": "a", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 10**7, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k1"}), # lifetime too long
    lambda s: jwt.encode({"sub": "a b;--", "role": "BUYER", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k1"}),  # bad subject
    lambda s: s.issue("a", "BUYER")[:-3] + "AAA",                                                                                                                                                                  # tampered signature
    lambda s: "not-a-jwt", lambda s: "", lambda s: "a.b.c",
])
def test_forged_or_malformed_tokens_are_all_rejected_as_invalid(make):
    s = svc(max_ttl_s=3600)
    with pytest.raises(E.ApiError) as x: s.verify(make(s))
    assert x.value.code == "AUTH_INVALID_TOKEN" and "k1" not in x.value.message


def test_key_rotation_old_tokens_valid_until_the_old_kid_is_removed():
    old = svc().issue("alice", "BUYER")                                   # signed with k1
    rotated = A.TokenService(KEYS, "k2", "iss", "aud")                    # k2 active, k1 still verifies
    assert rotated.verify(old).kid == "k1" and rotated.verify(rotated.issue("alice", "BUYER")).kid == "k2"
    retired = A.TokenService({"k2": KEYS["k2"]}, "k2", "iss", "aud")      # k1 removed
    with pytest.raises(E.ApiError): retired.verify(old)


def test_bearer_header_parsing_is_strict():
    assert A.parse_bearer("Bearer abc") == "abc" and A.parse_bearer("bearer abc") == "abc"
    for bad in ("Basic abc", "Bearer", "Bearer a b", "abc"):
        with pytest.raises(E.ApiError) as x: A.parse_bearer(bad)
        assert x.value.code == "AUTH_INVALID_TOKEN"
    with pytest.raises(E.ApiError) as x: A.parse_bearer(None)
    assert x.value.code == "AUTH_REQUIRED"


def test_permissions_are_explicit_least_privilege_and_deny_by_default():
    assert not A.Principal("x", "NOBODY", "k", "j").can("tools:read")
    for role, perms in A.PERMISSIONS.items():
        assert perms <= A.ALL_PERMISSIONS
    for role in ("READER", "OPERATOR", "AUDITOR"): assert not A.PERMISSIONS[role] & {"runs:decide", "runs:create"} or role == "OPERATOR" and False
    assert "runs:decide" not in A.PERMISSIONS["OPERATOR"] and "runs:decide" not in A.PERMISSIONS["AUDITOR"] and "runs:decide" not in A.PERMISSIONS["READER"]
    assert {r for r, p in A.PERMISSIONS.items() if "metrics:read" in p} == {"OPERATOR"}
    assert {r for r, p in A.PERMISSIONS.items() if "runs:decide" in p} == set(A.REVIEWER_ROLES)
    assert {r for r, p in A.PERMISSIONS.items() if "deadletters:resolve" in p} == {"OPERATOR"}


def test_a_token_cannot_carry_a_permission_claim_only_a_role_maps_to_permissions():
    t = jwt.encode({"sub": "a", "role": "READER", "permissions": ["runs:decide"], "scope": "admin", "iss": "iss", "aud": "aud", "iat": int(time.time()), "exp": int(time.time()) + 60, "jti": "j"}, KEYS["k1"], algorithm="HS256", headers={"kid": "k1"})
    p = svc().verify(t); assert not p.can("runs:decide") and p.role == "READER"


# --------------------------------------------------------------------------------------------- rate limiter
def test_token_bucket_refills_and_reports_retry_after():
    now = [0.0]; lim = TokenBucketLimiter(3, 1.0, clock=lambda: now[0])
    assert [lim.take("a")[0] for _ in range(4)] == [True, True, True, False]
    ok, wait = lim.take("a"); assert not ok and 0.9 < wait <= 1.0
    now[0] += 1.0; assert lim.take("a")[0] and not lim.take("a")[0]
    assert lim.take("b")[0]                                              # independent keys


def test_rate_limiter_table_is_bounded():
    lim = TokenBucketLimiter(5, 1.0, max_keys=100)
    for i in range(1000): lim.take(f"ip{i}")
    assert lim.size() == 100 and lim.evictions == 900


# --------------------------------------------------------------------------------------------- observability
def test_prometheus_text_is_well_formed_with_buckets_and_escaped_labels():
    m = obs.Metrics(); m.inc("t_total", help="h", route='/a"b\\c'); m.set("g", 2.5, help="g"); m.observe("lat", 0.03, help="l", route="/x"); m.observe("lat", 20, help="l", route="/x")
    t = m.render()
    assert '# TYPE t_total counter' in t and r't_total{route="/a\"b\\c"} 1' in t and 'g 2.5' in t
    assert 'lat_bucket{route="/x",le="0.05"} 1' in t and 'lat_bucket{route="/x",le="+Inf"} 2' in t and 'lat_count{route="/x"} 2' in t and "lat_sum" in t


def test_metrics_memory_is_bounded_by_labels_not_by_request_count():
    m = obs.Metrics()
    for i in range(20000): m.observe("lat", i / 1000, route="/x")
    assert len(m.hists["lat"][(("route", "/x"),)]) == len(obs.BUCKETS) + 2


def test_log_redaction_scrubs_tokens_jwts_connection_urls_and_assignments():
    buf = io.StringIO(); log = obs.configure_logging("DEBUG", buf)
    jwt_like = "eyJ" + "a" * 20 + "." + "b" * 20 + "." + "c" * 20; pw = secrets.token_hex(6)
    obs.emit(log, logging.INFO, f"auth Bearer {jwt_like} dsn postgresql://svc:{pw}@db/x password={pw} api_key: {pw}", request_id="req-1", detail=f"token={pw}", secret_field=pw, principal="abc")
    line = buf.getvalue()
    assert jwt_like not in line and pw not in line and "secret_field" not in line and "req-1" in line and json.loads(line)["synthetic"] is True


def test_log_exception_records_type_only():
    buf = io.StringIO(); log = obs.configure_logging("INFO", buf); pw = secrets.token_hex(6)
    try: raise ValueError(f"boom {pw}")
    except ValueError: log.error("failed", exc_info=True)
    assert pw not in buf.getvalue() and json.loads(buf.getvalue())["exc_type"] == "ValueError"


def test_principal_hash_is_keyed_stable_and_not_the_id():
    h1, h2 = obs.Hasher(b"salt-one"), obs.Hasher(b"salt-two")
    assert h1("alice") == h1("alice") and h1("alice") != h2("alice") and "alice" not in h1("alice") and len(h1("alice")) == 12


def test_traceparent_parsing_and_span_nesting_with_bounded_ring():
    assert obs.parse_traceparent("00-" + "a" * 32 + "-" + "b" * 16 + "-01") == ("a" * 32, "b" * 16)
    for bad in ("", "00-" + "0" * 32 + "-" + "b" * 16 + "-01", "xx", "00-short-b-01", None): assert obs.parse_traceparent(bad) is None
    t = obs.Tracer(obs.configure_logging("ERROR", io.StringIO()), obs.BoundedJsonLogger(maxlen=5))
    tid, sid, parent = t.start("00-" + "a" * 32 + "-" + "b" * 16 + "-01"); assert tid == "a" * 32 and parent == "b" * 16
    with t.span("outer"):
        with t.span("inner"): pass
    inner, outer = list(t.ring.lines)[-2:]
    assert inner["name"] == "inner" and inner["parent"] == outer["span_id"] and outer["parent"] == sid and inner["trace_id"] == tid
    for _ in range(50):
        with t.span("x"): pass
    assert len(t.ring.lines) == 5


# --------------------------------------------------------------------------------------------- error table
def test_error_table_maps_to_failure_policy_classes_and_valid_retry_advice():
    from nasha_lab.ops.failure_policy import FAILURE_CLASSES
    for code, spec in E.ERROR_TABLE.items():
        assert spec.failure_class in FAILURE_CLASSES, code
        assert spec.client_retry in ("never", "after_retry_after", "same_idempotency_key", "reconcile_first", "after_human_review"), code
        assert 400 <= spec.status <= 599
    assert E.envelope("RATE_LIMITED", "m", "req-1", retry_after_s=1.5)["error"]["retry_after_s"] == 1.5
    with pytest.raises(KeyError): E.ApiError("NOT_A_CODE", "x")


def test_ambiguous_timeouts_are_never_advised_as_blind_retries():
    for code in ("DEADLINE_EXCEEDED", "DB_TIMEOUT", "DECISION_AMBIGUOUS"):
        assert E.ERROR_TABLE[code].failure_class == "TIMEOUT_AMBIGUOUS" and E.ERROR_TABLE[code].client_retry in ("same_idempotency_key", "after_human_review")
