"""Contract tests: OpenAPI snapshot, a response-schema check for every route, the stable error-code table, and the single error envelope."""
from __future__ import annotations

import json
import os
import re
import uuid

from fastapi.routing import APIRoute

from conftest import auth
from nasha_lab.service import errors as E, schemas as S
from nasha_lab.service.app import PUBLIC_PATHS

SNAP = os.path.join(os.path.dirname(__file__), "snapshots")
UPDATE = os.environ.get("P5_UPDATE_SNAPSHOTS") == "1"


def snapshot(name, obj):
    p = os.path.join(SNAP, name)
    if UPDATE: open(p, "w", encoding="utf-8").write(json.dumps(obj, indent=1, sort_keys=True) + "\n")
    return json.load(open(p, encoding="utf-8"))


def K(): return {"Idempotency-Key": "t-" + uuid.uuid4().hex}


def test_error_code_table_is_stable():
    """A code, its status, failure class or retry advice cannot change without updating the snapshot (an API-visible change)."""
    assert E.error_table_snapshot() == snapshot("error_codes.json", E.error_table_snapshot())


def test_every_code_used_in_source_is_registered():
    root = os.path.join(os.path.dirname(__file__), "..", "..", "nasha_lab", "service"); used = set()
    for f in os.listdir(root):
        if f.endswith(".py"): used |= set(re.findall(r'ApiError\(\s*"([A-Z_]+)"', open(os.path.join(root, f), encoding="utf-8").read()))
    from nasha_lab.service.gateway import TOOL_ERROR_MAP
    used |= set(TOOL_ERROR_MAP.values())
    assert used - set(E.ERROR_TABLE) == set(), used - set(E.ERROR_TABLE)
    assert len(used) >= 25


def normalise(doc):
    """The HTTP contract without generator-specific detail: pydantic/FastAPI versions differ in how they spell constants, nullable types and defaults (this snapshot failed in CI
    under a different pydantic version), so compare what a client depends on: routes, methods, parameters, request/response schema names and status codes, security, and each schema's
    property names, required set and references."""
    def ref(x): return x.get("$ref", "").rsplit("/", 1)[-1] if isinstance(x, dict) else ""
    def refs(x):
        if isinstance(x, dict): return sorted({ref(x)} - {""} | {r for v in x.values() for r in refs(v)})
        if isinstance(x, list): return sorted({r for v in x for r in refs(v)})
        return []
    out = {"paths": {}, "schemas": {}, "security": sorted(doc["components"].get("securitySchemes", {}))}
    for path, ops in sorted(doc["paths"].items()):
        for m, op in sorted(ops.items()):
            out["paths"][f"{m.upper()} {path}"] = {"operationId": op["operationId"], "tags": op.get("tags"), "security": bool(op.get("security")), "parameters": sorted(f"{p['in']}:{p['name']}:{p.get('required', False)}" for p in op.get("parameters", [])),
                                                    "request": refs(op.get("requestBody", {})), "responses": {c: {"refs": refs(r), "types": sorted(r.get("content", {}))} for c, r in sorted(op["responses"].items())}}
    for name, sch in sorted(doc["components"]["schemas"].items()):
        out["schemas"][name] = {"properties": sorted(sch.get("properties", {})), "required": sorted(sch.get("required", [])), "refs": refs(sch.get("properties", {})), "extra_forbidden": sch.get("additionalProperties") is False}
    return out


def test_openapi_document_matches_the_committed_snapshot(app_env):
    doc = normalise(app_env.client.get("/openapi.json").json())
    assert doc == snapshot("openapi.json", doc), "the HTTP contract changed: review the diff, then regenerate with P5_UPDATE_SNAPSHOTS=1"


def test_openapi_declares_security_error_envelopes_and_labels(app_env):
    doc = app_env.client.get("/openapi.json").json(); assert "SYNTHETIC DATA" in doc["info"]["description"] and "NOT PRODUCTION DEPLOYED" in doc["info"]["description"]
    for path, ops in doc["paths"].items():
        for method, op in ops.items():
            if path in PUBLIC_PATHS: continue
            assert op.get("security"), (method, path)
            assert "401" in op["responses"] or "422" in op["responses"], (method, path)
            for code, resp in op["responses"].items():
                if code.startswith(("4", "5")): assert resp["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorEnvelope"), (method, path, code)
    assert "HTTPBearer" in doc["components"]["securitySchemes"]


def test_every_route_is_documented_and_every_documented_route_exists(app_env):
    doc = app_env.client.get("/openapi.json").json()["paths"]
    mine = {(m.lower(), r.path) for r in app_env.app.routes if isinstance(r, APIRoute) for m in r.methods if m not in ("HEAD", "OPTIONS")}
    documented = {(m, p) for p, ops in doc.items() for m in ops}
    assert mine == documented


def test_success_responses_validate_against_their_declared_models(app_env):
    c, k = app_env.client, app_env.keys; ops, alice, carol = auth(k, "ops", "OPERATOR"), auth(k, "alice", "BUYER"), auth(k, "carol", "FOUNDER")
    run = c.post("/v1/runs", json={"event_id": "EV-A1"}, headers={**alice, **K()}); rid = run.json()["run_id"]
    cases = [(c.get("/healthz"), S.Live, 200), (c.get("/readyz"), S.Ready, 200), (run, S.RunView, 201), (c.get(f"/v1/runs/{rid}", headers=alice), S.RunView, 200), (c.get("/v1/runs", headers=alice), S.RunList, 200),
             (c.get("/v1/events", headers=alice), S.EventList, 200), (c.get("/v1/inventory/goat?location_id=L01", headers=alice), S.ToolData, 200), (c.get("/v1/quality/findings", headers=alice), S.ToolData, 200),
             (c.post("/v1/knowledge/ask", json={"question": "dairy alternatives policy"}, headers=alice), S.ToolData, 200), (c.get("/v1/dead-letters", headers=ops), S.DeadLetterList, 200),
             (c.get("/v1/audit", headers=ops), S.AuditList, 200), (c.post(f"/v1/runs/{rid}/approve", json={"note": "ok"}, headers={**carol, **K()}), S.RunView, 200)]
    for r, model, status in cases:
        assert r.status_code == status, (r.request.url, r.status_code, r.text[:200]); model.model_validate(r.json())
    assert c.get("/metrics", headers=ops).headers["content-type"].startswith("text/plain")
    run2 = c.post("/v1/runs", json={"event_id": "EV-A2"}, headers={**alice, **K()}); assert run2.status_code == 201
    r = c.post(f"/v1/runs/{run2.json()['run_id']}/reject", json={}, headers={**carol, **K()}); S.RunView.model_validate(r.json())


def test_every_error_response_is_the_one_envelope_with_a_registered_code(app_env):
    c, k = app_env.client, app_env.keys; alice = auth(k, "alice", "BUYER"); seen = set()
    reqs = [c.get("/nope"), c.delete("/healthz"), c.get("/v1/events"), c.get("/v1/events", headers={"Authorization": "Bearer x.y.z"}), c.get("/metrics", headers=alice), c.get("/v1/runs/run-0000000000", headers=alice),
            c.get("/v1/runs/BAD", headers=alice), c.post("/v1/runs", json={}, headers={**alice, **K()}), c.post("/v1/runs", json={"event_id": "EV-A1"}, headers=alice), c.post("/v1/runs", content=b"{", headers={**alice, **K(), "Content-Type": "application/json"}),
            c.post("/v1/runs", json={"event_id": "EV-Z99"}, headers={**alice, **K()}), c.get("/v1/inventory/nonexistent?location_id=L01", headers=alice), c.get("/v1/inventory/goat", headers=alice),
            c.post("/v1/runs/run-0000000000/approve", json={}, headers={**alice, **K()}), c.post("/v1/runs", content=b"x", headers={**alice, **K(), "Content-Type": "text/plain"})]
    for r in reqs:
        b = r.json(); assert set(b) == {"error"}, (r.request.url, b); S.ErrorEnvelope.model_validate(b); e = b["error"]
        assert e["code"] in E.ERROR_TABLE and r.status_code == E.ERROR_TABLE[e["code"]].status, e
        assert e["request_id"] == r.headers["x-request-id"] and e["failure_class"] == E.ERROR_TABLE[e["code"]].failure_class
        seen.add(e["code"])
    assert len(seen) >= 10, seen


def test_retry_after_header_matches_the_envelope(migrated_db, keys, svc, tmp_path):
    from fastapi.testclient import TestClient
    from conftest import make_settings
    from nasha_lab.service.app import create_hardened_app
    s = make_settings(migrated_db, keys, str(tmp_path), rate_ip_capacity=2, rate_ip_refill_per_s=0.5)
    with TestClient(create_hardened_app(s, service=svc)) as c:
        rs = [c.get("/v1/events") for _ in range(4)]
    r = next(x for x in rs if x.status_code == 429); e = r.json()["error"]
    assert e["code"] == "RATE_LIMITED" and int(r.headers["retry-after"]) >= 1 and e["retry_after_s"] > 0 and e["client_retry"] == "after_retry_after"


def test_request_and_trace_ids_are_propagated(app_env):
    tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
    r = app_env.client.get("/v1/events", headers={**auth(app_env.keys), "X-Request-ID": "client-req-0001", "traceparent": tp})
    assert r.headers["x-request-id"] == "client-req-0001" and r.headers["traceparent"].split("-")[1] == "a" * 32 and r.headers["traceparent"].split("-")[2] != "b" * 16
    e = app_env.client.get("/v1/events", headers={"X-Request-ID": "client-req-0002"}).json()["error"]; assert e["request_id"] == "client-req-0002"
