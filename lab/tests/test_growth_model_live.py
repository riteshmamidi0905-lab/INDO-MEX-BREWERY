"""Live model-backed execution of the supplier research workflow. SKIPPED unless a permitted LOCAL runtime is configured: set NASHA_LIVE_MODEL_PROVIDER=ollama and have Ollama serving at AP_OLLAMA_BASE_URL (default
http://localhost:11434/v1) with the model named by AP_OLLAMA_MODEL. A paid hosted provider is never used by this test. Until it runs and passes, NO model-backed claim is made anywhere in this repository and the release gate
reports REQUIRES_REVIEW. What it asserts when it does run: the output crossed the model-output boundary (accepted, abstained or rejected-with-fallback, all valid), the mode says a model ran only if one did, and the
recommendation hash equals the deterministic one."""
import os

import pytest

pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
import urllib.request

PROVIDER = os.environ.get("NASHA_LIVE_MODEL_PROVIDER")
BASE = os.environ.get("AP_OLLAMA_BASE_URL", "http://localhost:11434/v1")


def _reachable():
    try:
        urllib.request.urlopen(BASE.rstrip("/").rsplit("/v1", 1)[0] + "/api/tags", timeout=2)
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(PROVIDER != "ollama" or not _reachable(), reason="INTEGRATION UNAVAILABLE: no local model runtime reachable (set NASHA_LIVE_MODEL_PROVIDER=ollama and serve a model with Ollama). Run via a machine that has one.")


def _live(world):
    from nasha_lab.growth import agent_research as AR
    base_wf = _make(world); r0 = base_wf.run(_tok(base_wf), _project(world), 4); base = base_wf.status(r0["corr_id"])["proposal_hash"]; base_wf.close()
    agent = AR.SupplierResearchAgent(world["dsn"], "tenant-nasha", world["root"] / "live", provider="ollama")
    wf = _make(world, agent=agent)
    r = wf.run(_tok(wf), _project(world), 4)
    run = wf.status(r["corr_id"])
    ev = [e for e in wf.trace(r["corr_id"]) if e.get("name") in ("agent_research", "agent_fallback")]
    wf.close()
    return r, run, ev, base


def _make(world, **kw):
    from test_growth_launch import make
    return make(world, **kw)


def _tok(wf):
    from test_growth_launch import tok
    return tok(wf, "ana")


def _project(world):
    from test_growth_launch import project
    return project(world)


from test_growth_launch import dsn, world  # noqa: E402,F401  (fixtures only; the network guard fixture is deliberately NOT imported here)


def test_a_real_local_model_runs_the_supplier_research_workflow_through_the_boundary(world):  # noqa: F811
    r, run, ev, base = _live(world)
    assert r["status"] == "AWAITING_APPROVAL" and run["proposal_hash"] == base, "a model never changes the recommendation"
    assert ev, "the boundary verdict or the fallback reason is recorded in the trace"
    if run["agent_mode"] == "engine_model":
        assert run["research"]["boundary"]["status"] == "accepted" and run["research"]["boundary"]["uncertainty"]
    else:
        assert run["agent_mode"] == "deterministic_fallback" and run["research"]["fallback_reason"]
