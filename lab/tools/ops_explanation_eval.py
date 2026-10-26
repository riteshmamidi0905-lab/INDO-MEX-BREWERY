"""Run the scripted Operations-explanation matrix (no model is called) and write the evidence file. `--check` exits non-zero if the committed file differs from a fresh run. Pure and deterministic."""
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from nasha_lab.growth import ops_explanation_eval as E  # noqa: E402

OUT = LAB / "results" / "ops-explanation" / "m-ops-1-offline-matrix.json"


def render():
    s = E.summary()
    s["cases_detail"] = [dict(id=r["id"], group=r["group"], expect=r["expect"], got_status=r["got"]["status"], got_codes=r["got"]["codes"], flags=r["got"]["flags"], exact=r["exact"]) for r in E.run_cases()]
    s["note"] = "SCRIPTED test doubles only: no language model was called and nothing here shows how a model behaves. Written by the M-OPS-1 offline milestone."
    return json.dumps(s, indent=1, sort_keys=True) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text() == text else 1)
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(text)
    print(f"wrote {OUT} ({len(text)} bytes)")
