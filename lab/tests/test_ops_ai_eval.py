"""The evaluation harness itself: it must pass on the real tools, be deterministic, and FAIL (with the right failure kind) when the tools are broken."""
import pytest

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import ops_ai, ops_ai_eval as E, pipeline

CFG = es.SimConfig(name="eval-test", months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_000, employees=60, open_at_start=3)


@pytest.fixture(scope="module")
def wh(tmp_path_factory):
    d = tmp_path_factory.mktemp("e"); es.generate(CFG, d / "src"); pipeline.run(d / "src", d / "w.db"); return d / "w.db"


def test_all_cases_pass_and_result_is_deterministic(wh, tmp_path):
    a = E.run_eval(wh, tmp_path / "a1.db"); b = E.run_eval(wh, tmp_path / "a2.db")
    assert a["summary"]["passed"] == a["summary"]["cases"] >= 30 and a["summary"]["failure_kinds"] == {"wrong_answer": 0, "false_allow": 0, "false_deny": 0, "wrong_refusal": 0}
    assert a["result_sha256"] == b["result_sha256"]                                  # latency lives outside the hashed part
    assert set(a["summary"]["by_category"]) == {"answer", "authorization", "adversarial", "abstention", "grounding"}


def test_harness_detects_a_wrong_answer_and_a_false_allow(wh, tmp_path, monkeypatch):
    real = ops_ai.TOOLS["company_month"]
    broken = ops_ai.Tool(real.name, real.description, real.roles, real.site_scoped, lambda con, a: ([dict(r, orders=r["orders"] + 1) for r in real.run(con, a)[0]], "mart_company_month"))
    monkeypatch.setitem(ops_ai.TOOLS, "company_month", broken)
    bad = E.run_eval(wh, tmp_path / "b.db")
    assert bad["summary"]["failure_kinds"]["wrong_answer"] >= 3
    monkeypatch.setitem(ops_ai.TOOLS, "company_month", real)
    leaky = ops_ai.Tool("location_month", "x", frozenset(ops_ai.ALL), False, ops_ai.TOOLS["location_month"].run)       # forgets site scoping
    monkeypatch.setitem(ops_ai.TOOLS, "location_month", leaky)
    bad2 = E.run_eval(wh, tmp_path / "c.db")
    assert bad2["summary"]["failure_kinds"]["false_allow"] >= 1                      # auth-other-site now answers


def test_rebuild_from_scratch_is_bit_identical():
    from nasha_lab.warehouse import repro
    h1, e1 = repro.build_once(CFG); h2, e2 = repro.build_once(CFG)
    assert h1 == h2 and e1 == e2 and len(h1) >= 20
    assert repro.environment()["python"]
