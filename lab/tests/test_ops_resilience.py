"""P2: timeouts, retries/backoff with idempotency (GAP-01), retriever fallback (GAP-04), rate limiting (GAP-10). SYNTHETIC / OFFLINE."""
import pytest
from fastapi.testclient import TestClient
from nasha_lab import agent, api, eval_agent as EA, knowledge as K, tools as T
from nasha_lab.ops import faultlib as FL, resilience as RS, runner as R, telemetry as TM


def test_backoff_is_bounded_exponential_with_jitter_and_deterministic():
    p = RS.RetryPolicy(max_attempts=4, base_ms=10, factor=2, max_ms=30, jitter=0.25, seed=3)
    s = p.schedule(); assert s == p.schedule() and len(s) == 3
    for n, d in enumerate(s, 1):
        nominal = min(30, 10 * 2 ** (n - 1)); assert nominal * 0.75 <= d <= nominal * 1.25
    assert s[2] <= 30 * 1.25                       # capped


def test_call_with_retry_stops_at_max_attempts_and_sleeps_between():
    calls, slept = [], []
    r, attempts, sleeps, opened = RS.call_with_retry(lambda: calls.append(1) or "bad", RS.RetryPolicy(max_attempts=3), is_failure=lambda x: "TIMEOUT", sleep=slept.append)
    assert attempts == 3 and len(calls) == 3 and len(slept) == 2 and not opened


def test_non_retryable_codes_are_not_retried():
    r, attempts, sleeps, _ = RS.call_with_retry(lambda: "bad", RS.RetryPolicy(max_attempts=3), is_failure=lambda x: "NOT_FOUND", sleep=lambda s: None)
    assert attempts == 1


def test_circuit_breaker_opens_half_opens_and_closes():
    t = [0.0]; b = RS.CircuitBreaker(threshold=2, reset_s=10, clock=lambda: t[0])
    assert b.allow("k"); b.record("k", False); assert b.allow("k"); b.record("k", False)
    assert b.state("k") == "OPEN" and not b.allow("k")
    t[0] = 11; assert b.state("k") == "HALF_OPEN" and b.allow("k") and not b.allow("k")      # exactly one probe
    b.record("k", False); assert b.state("k") == "OPEN"                                         # failed probe re-opens
    t[0] = 25; assert b.allow("k"); b.record("k", True); assert b.state("k") == "CLOSED"


@pytest.fixture(scope="module")
def pool(): return R.clean_pool()


def _inv_with_tool(pool):
    for sc in pool["heldout"]:
        if sc.event_family == "INVENTORY" and "query_inventory" in sc.expected["required"]: return sc


def test_transient_tool_timeout_is_absorbed_by_retry_but_still_alerted(pool):
    from nasha_lab.ops import alerts as A
    sc = _inv_with_tool(pool); ca = R.run_scenario(sc)[0]["action"]
    plan = FL.FaultPlan(transient={"query_inventory": dict(fail_first=1, code="TIMEOUT")})
    env = R.make_env(sc, stack=TM.ExecStack(faults=plan, retry=RS.RetryPolicy(max_attempts=3, base_ms=1, max_ms=2))); rid, s = R.drive(env, decisions=[]); rec = env.ops.record(rid)
    assert rec["action"] == ca and rec["tool_retries"] == 1
    assert any(a["cls"] == "TOOL_TIMEOUT" for a in A.AlertEvaluator().scan_events(env.svc.store.events(rid), rid))
    env2 = R.make_env(sc, stack=TM.ExecStack(faults=FL.FaultPlan(transient={"query_inventory": dict(fail_first=1, code="TIMEOUT")}))); rid2, _ = R.drive(env2, decisions=[])
    assert env2.ops.record(rid2)["action"].startswith("ESCALATE")        # without retry the same fault escalates


def test_persistent_failure_is_bounded_and_trips_the_breaker(pool):
    sc = _inv_with_tool(pool); br = RS.CircuitBreaker(threshold=3, reset_s=999); st = TM.ExecStack(retry=RS.RetryPolicy(max_attempts=2, base_ms=1, max_ms=2), breaker=br)
    seen = []
    for k in range(4):
        env = R.make_env(sc, stack=st, faults={**dict(sc.faults), "query_inventory": "error"}); rid, _ = R.drive(env, decisions=[])
        seen += [x for x in st.samples if x["run_id"] == rid and x["tool"] == "query_inventory"]
    assert all(x["attempts"] <= 2 for x in seen) and any(x["circuit_open"] for x in seen) and seen[-1]["code"] == "CIRCUIT_OPEN"


def _draft_sc(pool):
    return next(s for s in pool["heldout"] if s.event_family == "INVENTORY" and "DRAFT_PURCHASE_RECOMMENDATION" in s.expected["action"])


def test_idempotent_retry_does_not_duplicate_an_ambiguously_failed_draft(pool):
    sc = _draft_sc(pool); counts = {}
    for arm, kw in {"naive": dict(naive_draft_retry=True), "reconcile": dict(reconcile_drafts=True)}.items():
        env = R.make_env(sc, stack=TM.ExecStack(faults=FL.FaultPlan(commit_then_timeout={"draft_purchase_recommendation"}), retry=RS.RetryPolicy(max_attempts=3, base_ms=1, max_ms=2), **kw))
        rid, _ = R.drive(env, decisions=[]); counts[arm] = (env.world.q("SELECT COUNT(*) n FROM drafts WHERE kind='PURCHASE_RECOMMENDATION'")[0]["n"], env.ops.record(rid)["action"])
    assert counts["naive"][0] == 2, "the hazard is real: a naive retry duplicates the draft"
    assert counts["reconcile"] == (1, "DRAFT_PURCHASE_RECOMMENDATION")


def test_retriever_down_falls_back_to_lexical_and_still_cites_authoritative_sources():
    kb = K.default_kb("block3"); f = FL.FaultableKB(kb, fault="down"); r = RS.ResilientKB(f, sleep=lambda s: None)
    q = "What is the dietary policy on beef, pork and hidden derivatives such as stock, bouillon, shortening and natural flavors?"
    with pytest.raises(RuntimeError): f.ask(q)
    a = r.ask(q); assert not a["abstained"] and a["citations"] and a["retriever_fallback"] == "bm25" and r.mode == "fallback"
    assert all(c["effective_status"] in ("CURRENT", "FROZEN", "PROVISIONAL", "SUPPORTING") for c in a["citations"]) and r.events[0]["kind"] == "retriever_fallback"
    f.fault = None; b = RS.ResilientKB(f, sleep=lambda s: None).ask(q); assert "retriever_fallback" not in b


def test_fallback_keeps_the_agent_decision_for_a_policy_event(pool):
    from nasha_lab.ops import alerts as A
    sc = next(s for s in pool["heldout"] if s.event_family == "POLICY"); ca = R.run_scenario(sc)[0]["action"]
    env = R.make_env(sc, kb_wrap="faultable", resilient_kb=True); env.kb._kb.fault = "down"; rid, _ = R.drive(env, decisions=[]); rec = env.ops.record(rid)
    assert rec["retrieval"]["fallback"] >= 1 and (rec["action"] == ca or rec["action"].startswith("ABSTAIN"))
    assert any(a["rule_id"] == "AR-22" for a in A.AlertEvaluator().scan_run(rec))


def test_without_fallback_retrieval_failure_is_detected_and_fails_closed(pool):
    from nasha_lab.ops import alerts as A
    sc = next(s for s in pool["heldout"] if s.event_family == "POLICY")
    env = R.make_env(sc, kb_wrap="faultable"); env.kb.fault = "down"; rid, _ = R.drive(env, decisions=[]); rec = env.ops.record(rid)
    assert rec["retrieval"]["miss"] >= 1 and rec["action"].startswith(("ABSTAIN", "ESCALATE"))
    assert "RETRIEVAL_UNAVAILABLE" in {a["cls"] for a in A.AlertEvaluator().scan_events(env.svc.store.events(rid), rid)}


# ------------------------------------------------------------------ GAP-10
def test_token_bucket_refills_with_the_clock():
    t = [0.0]; rl = RS.RateLimiter(capacity=2, refill_per_s=1.0, clock=lambda: t[0])
    assert rl.take("a")[0] and rl.take("a")[0]; ok, wait = rl.take("a"); assert not ok and wait == pytest.approx(1.0)
    assert rl.take("b")[0]                       # separate key
    t[0] = 1.0; assert rl.take("a")[0]


def test_api_rate_limit_returns_429_with_error_envelope_and_exempts_probes():
    svc, w = EA.fresh(); t = [0.0]; app = RS.with_rate_limit(api.create_app(service=svc), RS.RateLimiter(capacity=3, refill_per_s=0.5, clock=lambda: t[0]))
    c = TestClient(app)
    codes = [c.get("/events", headers={"X-Client-Id": "u1"}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    r = c.get("/events", headers={"X-Client-Id": "u1"}); assert r.json()["error"]["code"] == "RATE_LIMITED" and int(r.headers["retry-after"]) >= 1
    assert c.get("/events", headers={"X-Client-Id": "u2"}).status_code == 200            # another client is unaffected
    assert all(c.get("/health", headers={"X-Client-Id": "u1"}).status_code == 200 for _ in range(10))
    t[0] = 10.0; assert c.get("/events", headers={"X-Client-Id": "u1"}).status_code == 200
