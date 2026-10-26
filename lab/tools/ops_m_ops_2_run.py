#!/usr/bin/env python3
"""M-OPS-2 evaluation entry point. Three modes:
  --shim perfect|mixed   offline dry run with the scripted provider (no network, no model)
  --preflight-only       resource/integrity/digest checks, no inference
  --live                 the controlled run against a loopback Ollama; REFUSES unless M_OPS_2_LIVE_CONFIRM=RUN_M_OPS_2_ONCE and the run is inside GitHub Actions (the manual workflow). Never run by the offline tests.
Exit codes: 0 ran, 2 preflight failed (fail closed; nothing deleted or overwritten), 3 refused."""
import argparse
import json
import os
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nasha_lab.growth import ops_m_ops_2_harness as H  # noqa: E402
from nasha_lab.growth import ops_m_ops_2_shim as S  # noqa: E402

CONFIRM = "RUN_M_OPS_2_ONCE"


def environment():
    return dict(platform=platform.platform(), cpus=os.cpu_count(), github_run_id=os.environ.get("GITHUB_RUN_ID"), github_sha=os.environ.get("GITHUB_SHA"), ollama_context_length=os.environ.get("OLLAMA_CONTEXT_LENGTH"), commit_pinned_by=os.environ.get("GITHUB_SHA"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--shim", choices=("perfect", "mixed"))
    g.add_argument("--live", action="store_true")
    g.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--purpose", choices=("offline", "suite", "live"))
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    a = ap.parse_args(argv)
    if a.live and (os.environ.get("M_OPS_2_LIVE_CONFIRM") != CONFIRM or os.environ.get("GITHUB_ACTIONS") != "true"):
        print("REFUSED: a live run needs the manual workflow (GITHUB_ACTIONS) and M_OPS_2_LIVE_CONFIRM=" + CONFIRM, file=sys.stderr)
        return 3
    purpose = a.purpose or ("live" if a.live else "offline")
    if a.live:
        provider = H.OllamaProvider(a.base_url)
    else:
        doc = H.load_caseset()
        provider = H.ScriptedProvider(S.make_script(doc, S.MIXED_PLAN if a.shim == "mixed" else {}))
    pre = H.run_preflight(purpose, a.out, provider=provider if (a.live or a.shim or a.preflight_only) else None, base_url=a.base_url)
    if not pre["ok"] or a.preflight_only:
        print(json.dumps(pre, indent=1, sort_keys=True))
        return 0 if pre["ok"] else 2
    res = H.run_evaluation(a.out, provider, purpose=purpose, preflight=pre, environment=environment())
    print(f"M_OPS_2_RUN_COMPLETE kind={res['manifest']['kind']} cases={res['manifest']['cases_run']} requests={res['manifest']['provider_requests']} out={a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
