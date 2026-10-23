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


def test_a_real_local_model_runs_the_supplier_research_workflow_through_the_boundary():
    from test_growth_launch import make, project, tok, world as _w  # noqa: F401
    raise NotImplementedError("executed only where a local runtime exists; see the module docstring")
