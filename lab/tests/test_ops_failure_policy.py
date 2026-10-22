"""Explicit failure/retry policy (Milestone 1). SYNTHETIC / OFFLINE."""
import itertools
import os
import random

import pytest
from nasha_lab import llm_planner as LP, tools as T
from nasha_lab.ops import failure_policy as FP, faultlib as FL, runner as R
from nasha_lab.ops.util import RESULTS_DIR, load_json

P = FP.load_policy()


def test_every_registered_tool_is_classified_and_matches_the_registry():
    assert set(P.cfg["tools"]) == set(T.TOOLS), "tools in failure-policy.json differ from the registry"
    for n, spec in T.TOOLS.items():
        e = P.cfg["tools"][n]
        assert e["class"] in FP.OP_CLASSES and e["permission"] == spec.permission and P.tool(n).classified
        assert e["side_effects"] == (spec.permission not in (T.READ, T.ANALYZE))


def test_mutating_and_external_tools_are_never_safe_to_retry():
    for n, spec in T.TOOLS.items():
        k = P.tool(n).klass
        if spec.permission in (T.MUTATE, T.EXTERNAL): assert k not in ("SAFE_TO_RETRY", "SAFE_WITH_IDEMPOTENCY_KEY"), n
        if spec.permission == T.DRAFT: assert k != "SAFE_TO_RETRY", n
        if spec.permission == T.EXTERNAL: assert k == "DO_NOT_RETRY", n
        if spec.permission in (T.READ, T.ANALYZE): assert k == "SAFE_TO_RETRY", n


def test_non_tool_operations_are_all_classified_once():
    for n in ("llm_planner_call", "knowledge_retrieval", "db_write_unkeyed", "ops_store_write", "human_approval_execute_step", "http_upstream_get", "http_upstream_post_unkeyed", "http_upstream_post_with_idempotency_key", "agent_run_start"):
        assert P.op(n).classified
    assert {P.op(n).klass for n in P.cfg["operations"]} | {v["class"] for v in P.cfg["tools"].values()} == set(FP.OP_CLASSES)      # every class is used by something
    assert P.op("llm_planner_call").max_attempts == 1 + LP.MAX_RETRIES                                                                  # policy matches the planner's existing bounded retry


def test_unclassified_operation_fails_closed():
    o = P.op("brand_new_op"); assert not o.classified and o.klass == "DO_NOT_RETRY"
    assert P.tool("brand_new_tool").klass == "DO_NOT_RETRY"


def test_decision_table_is_total_and_has_the_documented_cells():
    for k, f in itertools.product(FP.OP_CLASSES, FP.FAILURE_CLASSES): assert FP.decide(k, f, policy=P).action in FP.ACTIONS
    d = lambda k, f, **kw: FP.decide(k, f, policy=P, **kw).action
    assert d("SAFE_TO_RETRY", "TRANSIENT") == "RETRY" and d("SAFE_TO_RETRY", "RATE_LIMIT") == "RETRY"
    assert d("SAFE_TO_RETRY", "VALIDATION") == d("SAFE_TO_RETRY", "AUTH") == d("SAFE_TO_RETRY", "PERMANENT") == "FAIL_FAST"
    assert d("SAFE_TO_RETRY", "DEPENDENCY_DOWN") == "FAIL_FAST" and d("SAFE_TO_RETRY", "MALFORMED_RESULT") == "FAIL_FAST"
    assert d("RECONCILE_BEFORE_RETRY", "TIMEOUT_AMBIGUOUS") == "RECONCILE_THEN_RETRY" and d("RECONCILE_BEFORE_RETRY", "TIMEOUT_AMBIGUOUS", can_reconcile=False) == "DEAD_LETTER"
    assert d("DO_NOT_RETRY", "TIMEOUT_AMBIGUOUS") == "DEAD_LETTER" and d("DO_NOT_RETRY", "AUTH") == "FAIL_FAST"
    assert d("SAFE_WITH_IDEMPOTENCY_KEY", "TIMEOUT_AMBIGUOUS", has_key=True) == "RETRY" and d("SAFE_WITH_IDEMPOTENCY_KEY", "TIMEOUT_AMBIGUOUS", has_key=False) == "DEAD_LETTER"
    assert all(d("HUMAN_REVIEW_REQUIRED", f) == "DEAD_LETTER" for f in FP.FAILURE_CLASSES)
    assert d("SAFE_TO_RETRY", "TRANSIENT", attempts_made=3, max_attempts=3, side_effects=False) == "FAIL_FAST"          # retry limit
    assert d("SAFE_TO_RETRY", "TRANSIENT", budget_ok=False, side_effects=False) == "FAIL_FAST"                           # budget


def test_failure_classification():
    c = lambda code, se: FP.classify_failure(code, se, P)
    assert c("TIMEOUT", False) == "TRANSIENT" and c("TIMEOUT", True) == "TIMEOUT_AMBIGUOUS" and c("UPSTREAM_FAILURE", True) == "TRANSIENT"
    assert c("RATE_LIMITED", False) == "RATE_LIMIT" and c("CIRCUIT_OPEN", False) == "DEPENDENCY_DOWN" and c("MODEL_UNAVAILABLE", False) == "DEPENDENCY_DOWN"
    assert c("INVALID_ARGUMENTS", True) == "VALIDATION" and c("REJECTED", True) == "VALIDATION" and c("NOT_FOUND", False) == "PERMANENT"
    assert c("APPROVAL_REQUIRED", True) == c("TAINTED_ARGUMENT", True) == c("FORBIDDEN_EXTERNAL_ACTION", True) == "AUTH"
    assert c("MALFORMED_RESULT", False) == "MALFORMED_RESULT"
    assert c("SOMETHING_NEW", True) == "TIMEOUT_AMBIGUOUS" and c("SOMETHING_NEW", False) == "PERMANENT"


def _runner(**kw): return FP.PolicyRunner(P, FP.OpsStore(), sleep=lambda s: None, **kw)


def _failing(code, n_fail, calls):
    def attempt(i):
        calls.append(i)
        return FP.Outcome(True, "ok") if i > n_fail else FP.Outcome(False, None, code, "x")
    return attempt


def test_backoff_is_exponential_jittered_bounded_and_seeded():
    op = P.op("http_upstream_get"); calls = []; r1 = _runner(seed=1).run(op, _failing("UPSTREAM_FAILURE", 2, calls), correlation_id="c1")
    r2 = _runner(seed=1).run(op, _failing("UPSTREAM_FAILURE", 2, []), correlation_id="c1")
    d = P.cfg["retry_defaults"]; assert r1.ok and r1.attempts == 3 and r1.delays_ms == r2.delays_ms and len(r1.delays_ms) == 2
    for n, x in enumerate(r1.delays_ms, 1):
        nominal = min(d["max_ms"], d["base_ms"] * d["factor"] ** (n - 1)); assert nominal * (1 - d["jitter"]) - 1e-6 <= x <= nominal * (1 + d["jitter"]) + 1e-6


def test_retry_limit_is_enforced_and_no_side_effect_op_fails_fast_not_dead_letter():
    calls = []; r = _runner().run(P.op("knowledge_retrieval"), _failing("UPSTREAM_FAILURE", 99, calls), correlation_id="c")
    assert not r.ok and r.attempts == P.op("knowledge_retrieval").max_attempts == len(calls) and r.dead_letter is None and r.actions[-1] == "FAIL_FAST"


def test_rate_limit_honours_retry_after_floor():
    seq = iter([FP.Outcome(False, None, "RATE_LIMITED", "", retry_after_ms=900), FP.Outcome(True, 1)])
    r = _runner().run(P.op("http_upstream_get"), lambda i: next(seq), correlation_id="c"); assert r.ok and r.delays_ms[0] >= 900


def test_retry_budget_stops_amplification():
    run = _runner(budget=FP.RetryBudget(ratio=0.0, min_retries=2), breaker=FP.CircuitBreaker(10**6, 1)); n = 0
    for k in range(6): n += run.run(P.op("http_upstream_get"), _failing("UPSTREAM_FAILURE", 99, []), correlation_id=f"c{k}").attempts
    assert run.budget.retries == 2 and n == 6 + 2           # six first attempts plus only the 2 budgeted retries


def test_circuit_breaker_hook_stops_calls_when_open():
    run = _runner(); op = P.op("http_upstream_get"); calls = []
    for k in range(3): run.run(op, _failing("UPSTREAM_FAILURE", 99, calls), correlation_id=f"c{k}")
    before = len(calls); r = run.run(op, _failing("UPSTREAM_FAILURE", 99, calls), correlation_id="z")
    assert r.circuit_open and r.code == "CIRCUIT_OPEN" and len(calls) == before


def test_dead_letter_record_is_persisted_with_reason_attempts_correlation_and_replay(tmp_path):
    path = str(tmp_path / "ops.db"); st = FP.OpsStore(path, clock=lambda: 1_800_000_000.0); run = FP.PolicyRunner(P, st, sleep=lambda s: None)
    r = run.run(P.tool("adjust_inventory_record"), _failing("TIMEOUT", 99, []), correlation_id="req-42", run_id="run-7", args={"location_id": "L01", "ingredient": "x", "api_key": "SECRET123456"}, tool="adjust_inventory_record")
    assert not r.ok and r.attempts == 1 and r.dead_letter
    st2 = FP.OpsStore(path); [dl] = st2.list()                       # a fresh connection reads it back
    assert dl["correlation_id"] == "req-42" and dl["run_id"] == "run-7" and dl["attempts"] == 1 and dl["failure_class"] == "TIMEOUT_AMBIGUOUS" and "TIMEOUT" in dl["reason"]
    assert "Do NOT re-run" in dl["replay_instructions"] and dl["status"] == "OPEN" and "SECRET123456" not in dl["args_json"] and dl["created"].startswith("2027")
    run.run(P.tool("adjust_inventory_record"), _failing("TIMEOUT", 99, []), correlation_id="req-42", run_id="run-7", args={"location_id": "L01", "ingredient": "x", "api_key": "SECRET123456"}, tool="adjust_inventory_record")
    assert len(st2.list()) == 1                                      # same failure converges to one keyed record
    st2.resolve_dead_letter(dl["dl_id"], "ALREADY_APPLIED", "checked inventory_movements"); assert st2.list() == [] and st2.get(dl["dl_id"])["resolution"]


def test_idempotency_key_suppresses_duplicate_side_effects():
    st = FP.OpsStore(); effects = []
    def write(key): effects.append(key); return {"row": len(effects)}
    a, hit_a = st.run_once("evt-1", "ops_store_write", write); b, hit_b = st.run_once("evt-1", "ops_store_write", write); c, _ = st.run_once("evt-2", "ops_store_write", write)
    assert effects == ["evt-1", "evt-2"] and a == b and not hit_a and hit_b and c != a


def test_keyed_operation_retries_with_the_same_key_and_unkeyed_is_dead_lettered():
    keys = []
    def attempt(i): keys.append("K"); return FP.Outcome(i > 1, "ok", None if i > 1 else "TIMEOUT")
    r = _runner().run(P.op("ops_store_write"), attempt, key="K", correlation_id="c"); assert r.ok and keys == ["K", "K"]
    r2 = _runner().run(P.op("ops_store_write"), attempt, key=None, correlation_id="c2"); assert not r2.ok and r2.dead_letter and r2.attempts == 1


def test_reconcile_found_absent_unknown():
    op = P.tool("draft_review_ticket")
    r = _runner().run(op, _failing("TIMEOUT", 99, c := []), reconcile=lambda: FP.Reconciled("found", "existing"), correlation_id="a", tool="draft_review_ticket")
    assert r.ok and r.reconciled and r.value == "existing" and len(c) == 1
    seq = [FP.Reconciled("absent"), FP.Reconciled("absent")]; c2 = []
    r = _runner().run(op, _failing("TIMEOUT", 1, c2), reconcile=lambda: seq.pop(), correlation_id="b", tool="draft_review_ticket"); assert r.ok and len(c2) == 2
    r = _runner().run(op, _failing("TIMEOUT", 99, []), reconcile=lambda: FP.Reconciled("unknown"), correlation_id="c", tool="draft_review_ticket"); assert not r.ok and r.dead_letter
    r = _runner().run(op, _failing("TIMEOUT", 99, []), correlation_id="d", tool="draft_review_ticket"); assert r.dead_letter           # no reconciler: cannot verify


def test_property_do_not_retry_and_human_review_are_never_retried():
    for k, f, ka, kr, kb, na in itertools.product(("DO_NOT_RETRY", "HUMAN_REVIEW_REQUIRED"), FP.FAILURE_CLASSES, (0, 1), (0, 1), (0, 1), (1, 2, 5)):
        assert FP.decide(k, f, attempts_made=na, max_attempts=9, has_key=bool(ka), can_reconcile=bool(kr), budget_ok=bool(kb), policy=P).action in ("FAIL_FAST", "DEAD_LETTER")
    rng = random.Random(7); codes = ["TIMEOUT", "UPSTREAM_FAILURE", "RATE_LIMITED", "MALFORMED_RESULT", "REJECTED", "NOT_FOUND", "CIRCUIT_OPEN", "WHATEVER", "APPROVAL_REQUIRED"]
    ops = [P.tool(n) for n, e in P.cfg["tools"].items() if e["class"] == "DO_NOT_RETRY"] + [P.op(n) for n, e in P.cfg["operations"].items() if e["class"] in ("DO_NOT_RETRY", "HUMAN_REVIEW_REQUIRED")]
    assert ops
    for _ in range(300):
        op = rng.choice(ops); calls = []; seq = [rng.choice(codes) for _ in range(5)]
        FP.PolicyRunner(P, FP.OpsStore(), sleep=lambda s: None).run(op, lambda i: (calls.append(i), FP.Outcome(False, None, seq[i - 1]))[1], key="k", reconcile=lambda: FP.Reconciled("absent"), correlation_id="p")
        assert len(calls) == 1, (op.name, seq)


# ---- integration with the real tool executor
@pytest.fixture(scope="module")
def pool(): return R.clean_pool()


def test_policy_stack_reconciles_an_ambiguous_draft_without_duplicating(pool):
    sc = next(s for s in pool["heldout"] if s.event_family == "INVENTORY" and "DRAFT_PURCHASE_RECOMMENDATION" in s.expected["action"])
    st = FP.PolicyStack(store=FP.OpsStore(), sleep=lambda s: None, faults=FL.FaultPlan(commit_then_timeout={"draft_purchase_recommendation"}))
    env = R.make_env(sc, "deterministic", stack=st); rid, _ = R.drive(env, decisions=[])
    assert env.world.q("SELECT COUNT(*) n FROM drafts WHERE kind='PURCHASE_RECOMMENDATION' AND run_id=?", rid)[0]["n"] == 1 and env.ops.record(rid)["action"] == "DRAFT_PURCHASE_RECOMMENDATION"
    smp = [s for s in st.samples if s["tool"] == "draft_purchase_recommendation"][0]; assert smp["policy"]["reconciled"] and smp["ok"]


def test_policy_stack_dead_letters_an_ambiguous_mutation_and_never_retries_it(pool):
    sc = next(s for s in pool["heldout"] if s.event_family == "DATA_QUALITY")
    st = FP.PolicyStack(store=FP.OpsStore(), sleep=lambda s: None, faults=FL.FaultPlan(commit_then_timeout={"flag_record_for_review"}))
    env = R.make_env(sc, "deterministic", stack=st); rid, _ = R.drive(env)
    assert [s["attempts"] for s in st.samples if s["tool"] == "flag_record_for_review"] == [1]
    [dl] = st.runner.store.list(); assert dl["tool"] == "flag_record_for_review" and dl["run_id"] == rid and dl["op_class"] == "DO_NOT_RETRY"


def test_committed_trial_results_show_the_measured_numbers():
    d = load_json(os.path.join(RESULTS_DIR, "failure_policy_trials.json"))
    a = d["draft_ambiguous_timeout"]; assert a["naive_retry"]["runs_with_duplicate_drafts"] == 10 and a["failure_policy"]["runs_with_duplicate_drafts"] == 0 and a["failure_policy"]["runs_reaching_the_draft_proposal"] == 10
    m = d["mutation_ambiguous_timeout"]; assert m["failure_policy"]["total_attempts_on_the_mutation"] == m["failure_policy"]["runs"] and m["failure_policy"]["open_dead_letters"] == m["failure_policy"]["runs"]
    assert d["transient_timeout_first_attempt"]["failure_policy"]["action_equals_clean"]["k"] == 20
