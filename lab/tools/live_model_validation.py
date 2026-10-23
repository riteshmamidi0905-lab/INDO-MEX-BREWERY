"""Live model validation harness. Run on a machine that has a permitted LOCAL OpenAI-compatible runtime (Ollama, llama.cpp server, vLLM):
    NASHA_LIVE_MODEL_PROVIDER=ollama AP_OLLAMA_BASE_URL=http://localhost:11434/v1 AP_OLLAMA_MODEL=<model> python tools/live_model_validation.py
It writes results/model-validation/live.json. `executed` is true ONLY when a runtime answered a real /models call and the live test (tests/test_growth_model_live.py) ran and passed; otherwise it is false
and the file records why and the single decision needed. Scripted outputs and the offline heuristic are never counted as model execution. Paid providers are never used here."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
OUT = LAB / "results" / "model-validation" / "live.json"
BASE = os.environ.get("AP_OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
NEEDED = ("Founder decision needed to obtain a model run: either (a) allow outbound access to huggingface.co and its CDN hosts in the environment network policy so a small instruct model can be "
          "downloaded and served locally, (b) point AP_OLLAMA_BASE_URL at an approved OpenAI-compatible endpoint, or (c) approve a capped paid key via NASHA_ALLOW_PAID_MODEL=1 (not used by default).")


def probe():
    t = time.time()
    try:
        with urllib.request.urlopen(BASE + "/models", timeout=3) as r:
            data = json.load(r)
        return True, [m.get("id") for m in data.get("data", [])], round((time.time() - t) * 1000), None
    except Exception as e:  # noqa: BLE001
        return False, [], None, f"{type(e).__name__}: {e}"


def main():
    ok, models, ms, err = probe()
    res = dict(executed=False, runtime_base_url=BASE, runtime_reachable=ok, models=models, probe_ms=ms, reason=err, live_test=None, decision_needed=None)
    if ok and os.environ.get("NASHA_LIVE_MODEL_PROVIDER") == "ollama":
        env = dict(os.environ, NASHA_LIVE_MODEL_PROVIDER="ollama")
        p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_growth_model_live.py", "-q", "-rs"], cwd=LAB, env=env, capture_output=True, text=True)
        tail = p.stdout.strip().splitlines()[-3:]
        res.update(live_test=dict(returncode=p.returncode, tail=tail), executed=p.returncode == 0 and "skipped" not in " ".join(tail) and "passed" in " ".join(tail))
        if not res["executed"]:
            res["reason"] = "live test did not pass or was skipped"
    else:
        res["reason"] = res["reason"] or "NASHA_LIVE_MODEL_PROVIDER is not set to 'ollama'"
    if not res["executed"]:
        res["decision_needed"] = NEEDED
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("executed", "runtime_reachable", "reason")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
