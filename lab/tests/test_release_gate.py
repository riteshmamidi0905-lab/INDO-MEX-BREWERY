"""Release gate: a complete synthetic evidence bundle passes; every kind of missing, stale, inconsistent or malformed evidence is rejected. The bundle is fabricated HERE, only to test the gate's logic."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_gate", LAB / "tools/release_gate.py")
RG = importlib.util.module_from_spec(spec); sys.modules["release_gate"] = RG; spec.loader.exec_module(RG)
CFG = json.loads((LAB / "tools/release-gate.config.json").read_text())
POLICY = json.loads((LAB / "tests/skip-policy.json").read_text())
NOW = 1_800_000_000.0
MODEL = "test_llm_planner::test_real_local_model_integration_smoke"


def junit(extra_failed=(), drop=(), skip=(), model_executed=False, units=320, integ=130):
    ids = {i for k, v in CFG["gates"].items() for i in v}
    rows = []
    for i in sorted(ids - set(drop)):
        m, n = i.split("::"); rows.append((m, n, "failed" if i in extra_failed else "passed", ""))
    for k in range(units):
        rows.append((f"test_unit_{k % 20}", f"test_u{k}", "passed", ""))
    for k in range(integ):
        rows.append((CFG["integration_modules"][k % 4], f"test_filler{k}", "passed", ""))
    m, n = MODEL.split("::")
    rows.append((m, n, "passed" if model_executed else "skipped", "" if model_executed else "no local model runtime reachable"))
    for s in skip:
        rows.append(("test_unit_1", s[0], "skipped", s[1]))
    body = ""
    for m, n, o, r in rows:
        inner = {"passed": "", "failed": "<failure message='x'/>", "skipped": f"<skipped message='{r}'/>"}[o]
        body += f"<testcase classname='tests.{m}' name='{n}'>{inner}</testcase>"
    return f"<testsuites><testsuite>{body}</testsuite></testcases>".replace("</testcases>", "</testsuites>")


def eval_report():
    res = []
    for c in CFG["evaluation"]["required_categories"]:
        for j in range(2):
            res.append(dict(id=f"{c}-{j}", category=c, expected="X", passed=True, reason="", observed_pos=0, ms=1.0))
    m = dict(cases=len(res), passed=len(res), pass_rate=1.0, unauthorized_action_rate=0.0, latency_ms_p50=1.0, by_category={})
    mu = [dict(mutant=f"m{k}", target_category="x", cases_run=2, failing_cases=["a"], killed=True) for k in range(9)]
    return dict(schema="governed-eval/1", scope="synthetic", metrics=m, results=res, result_hash="abc123", reproducible=True, mutants=mu, mutants_killed=9, mutants_total=9)


def bundle(model_executed=True, **kw):
    j = junit(model_executed=model_executed, **kw)
    s = RG.summarize(RG.parse_junit(j)); s.pop("skips")
    ev = eval_report()
    rep = dict(eval_hash_run1="abc123", eval_hash_run2="abc123", warehouse=dict(tables=47, identical=True, eval_hash_equal=True))
    docs = {"eval.json": ev, "summary.json": s, "repro.json": rep}
    claims = [dict(id="c1", text="tests passed in the suite", value=s["passed"], source=dict(file="summary.json", pointer="passed")),
              dict(id="c2", text="evaluation cases", value=ev["metrics"]["cases"], source=dict(file="eval.json", pointer="metrics.cases")),
              dict(id="c3", text="mutants killed", value=9, source=dict(file="eval.json", pointer="mutants_killed"))]
    export = dict(claims=claims, metrics={"release_evidence": {"tests_passed": s["passed"]}}, architecture=dict(nodes=[dict(id="n", status="implemented_and_tested", evidence=["x"])]))
    return dict(meta=dict(commit="abc1234", dirty_code=False, generated_at=NOW - 60, remote_ci="NOT_RUN"), junit=j, eval=ev, repro=rep, summary=s, export=export)


def run(b, head="abc1234", changed=()):
    return RG.evaluate(b, CFG, head, changed, now=NOW, policy=POLICY)


def failing(rep):
    return {g for g, v in rep["gates"].items() if v["status"] == "FAIL"}


def test_complete_evidence_passes_all_twelve_gates():
    rep = run(bundle())
    assert rep["overall"] == "PASS", {g: v["detail"] for g, v in rep["gates"].items() if v["status"] != "PASS"}
    assert list(rep["gates"]) == RG.GATE_ORDER and len(RG.GATE_ORDER) == 12
    assert rep["remote_ci"] == "NOT_RUN" and "no remote CI result is claimed" in rep["remote_ci_note"]


def test_unexecuted_model_runtime_test_requires_review_it_is_not_a_pass():
    rep = run(bundle(model_executed=False))
    assert rep["overall"] == "REQUIRES_REVIEW" and rep["gates"]["integration_tests"]["status"] == "REQUIRES_REVIEW" and not failing(rep)


def test_missing_evaluation_results_fail():
    b = bundle(); b["eval"] = None
    rep = run(b)
    assert rep["overall"] == "FAIL" and {"agent_evaluation", "mutation_testing", "reproducibility"} <= failing(rep)


def test_failed_security_test_fails_the_gate():
    victim = CFG["gates"]["security_regression"][0]
    rep = run(bundle(extra_failed=[victim]))
    assert rep["overall"] == "FAIL" and "security_regression" in failing(rep) and victim in rep["gates"]["security_regression"]["detail"]


def test_missing_required_test_is_a_failure_not_a_pass():
    victim = CFG["gates"]["tenant_isolation"][0]
    rep = run(bundle(drop=[victim]))
    assert "tenant_isolation" in failing(rep)


def test_unsupported_metric_in_the_evaluation_fails():
    b = bundle(); b["eval"]["metrics"]["customer_satisfaction"] = 0.99
    assert "agent_evaluation" in failing(run(b))


def test_metrics_that_do_not_match_the_case_rows_fail():
    b = bundle(); b["eval"]["metrics"]["passed"] = 1
    assert "agent_evaluation" in failing(run(b))


def test_stale_evidence_by_age_fails():
    b = bundle(); b["meta"]["generated_at"] = NOW - 10 * 86400
    rep = run(b)
    assert "evidence_consistency" in failing(rep) and "stale" in rep["gates"]["evidence_consistency"]["detail"]


def test_stale_evidence_by_code_change_since_collection_fails_but_docs_only_change_does_not():
    assert "evidence_consistency" in failing(run(bundle(), head="def5678", changed=["lab/nasha_lab/governed/agent.py"]))
    assert "evidence_consistency" not in failing(run(bundle(), head="def5678", changed=["docs/engineering/NOTES.md", "lab/portfolio/capability-matrix.json"]))


def test_uncommitted_code_at_collection_time_fails():
    b = bundle(); b["meta"]["dirty_code"] = True
    assert "evidence_consistency" in failing(run(b))


def test_incorrect_test_counts_fail():
    b = bundle(); b["summary"]["passed"] += 5
    rep = run(b)
    assert "evidence_consistency" in failing(rep) and "incorrect test counts" in rep["gates"]["evidence_consistency"]["detail"]
    b = bundle(); b["export"]["metrics"]["release_evidence"]["tests_passed"] += 1
    assert "evidence_consistency" in failing(run(b))


def test_too_few_tests_collected_fails_even_when_none_fail():
    assert "unit_tests" in failing(run(bundle(units=10)))


def test_missing_reproducibility_artifacts_fail():
    b = bundle(); b["repro"] = None
    assert "reproducibility" in failing(run(b))
    b = bundle(); b["repro"]["eval_hash_run2"] = "different"
    assert "reproducibility" in failing(run(b))
    b = bundle(); b["repro"]["warehouse"]["identical"] = False
    assert "reproducibility" in failing(run(b))


@pytest.mark.parametrize("breaker", [lambda b: b.__setitem__("junit", "<testsuites><oops"), lambda b: b.__setitem__("eval", {"__malformed__": True}),
                                     lambda b: b["eval"].__setitem__("results", "nope"), lambda b: b.__setitem__("export", {"__malformed__": True}), lambda b: b.__setitem__("meta", {"commit": "x"})])
def test_malformed_reports_fail_and_never_raise(breaker):
    b = bundle(); breaker(b)
    rep = run(b)
    assert rep["overall"] == "FAIL"


def test_unauthorized_workflow_execution_in_the_evaluation_fails_authorization_and_tenant_gates():
    b = bundle()
    for r in b["eval"]["results"]:
        if r["category"] == "approval_bypass":
            r["observed_pos"] = 1; break
    rep = run(b)
    assert "authorization_enforcement" in failing(rep) and "unauthorized workflow execution" in rep["gates"]["authorization_enforcement"]["detail"]
    b = bundle()
    for r in b["eval"]["results"]:
        if r["category"] == "cross_tenant":
            r["observed_pos"] = 1; break
    assert "tenant_isolation" in failing(run(b))


def test_a_surviving_mutant_fails_the_mutation_gate():
    b = bundle(); b["eval"]["mutants"][3]["killed"] = False; b["eval"]["mutants_killed"] = 8
    rep = run(b)
    assert "mutation_testing" in failing(rep) and "surviving" in rep["gates"]["mutation_testing"]["detail"]


def test_claims_must_resolve_and_match_the_evidence():
    b = bundle(); b["export"]["claims"][1]["value"] = 999
    assert "portfolio_claim_validation" in failing(run(b))
    b = bundle(); b["export"]["claims"][1]["source"]["pointer"] = "metrics.nonexistent"
    assert "portfolio_claim_validation" in failing(run(b))
    b = bundle(); b["export"]["claims"][0]["source"]["file"] = "made-up.json"
    assert "portfolio_claim_validation" in failing(run(b))
    b = bundle(); b["export"]["claims"] = []
    assert "portfolio_claim_validation" in failing(run(b))


def test_overclaiming_wording_is_rejected_even_when_the_number_is_right():
    b = bundle(); b["export"]["claims"][0]["text"] = "tests passed in a production-ready deployed system"
    rep = run(b)
    assert "portfolio_claim_validation" in failing(rep) and "unsupported wording" in rep["gates"]["portfolio_claim_validation"]["detail"]


def test_architecture_node_without_evidence_cannot_claim_tested():
    b = bundle(); b["export"]["architecture"]["nodes"][0]["evidence"] = []
    assert "portfolio_claim_validation" in failing(run(b))


def test_a_skip_forbidden_by_policy_fails():
    rep = run(bundle(skip=[("test_pg_skipped", "PostgreSQL unavailable here")]))
    assert "unit_tests" in failing(rep)


def test_unknown_skip_requires_review():
    rep = run(bundle(skip=[("test_something", "some new reason")]))
    assert rep["gates"]["unit_tests"]["status"] == "REQUIRES_REVIEW" and not failing(rep)


def test_a_required_test_that_is_skipped_fails():
    victim = CFG["gates"]["pg_reconciliation"][0]
    b = bundle(); m, n = victim.split("::")
    b["junit"] = b["junit"].replace(f"<testcase classname='tests.{m}' name='{n}'></testcase>", f"<testcase classname='tests.{m}' name='{n}'><skipped message='x'/></testcase>")
    assert "pg_reconciliation" in failing(run(b))


def test_summary_and_report_are_machine_and_human_readable():
    rep = run(bundle(model_executed=False))
    json.dumps(rep)
    md = RG.render(rep)
    assert "REQUIRES_REVIEW" in md and "pg_reconciliation" in md and "NOT_RUN" in md


def test_config_requires_real_tests_every_listed_test_exists_in_the_repository():
    import re
    for gate, ids in CFG["gates"].items():
        assert ids, gate
        for i in ids:
            mod, fn = i.split("::")
            assert re.search(rf"def {fn}\b", (LAB / "tests" / f"{mod}.py").read_text()), i
