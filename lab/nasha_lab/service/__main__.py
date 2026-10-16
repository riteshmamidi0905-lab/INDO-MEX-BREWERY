"""Operator CLI: `python -m nasha_lab.service check-config | mint-token --sub X --role R [--ttl N]`.
mint-token is for dev/test only and refuses to run when NASHA_SVC_ENV=staging (the service never mints tokens in staging)."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .config import ConfigError, load_settings


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nasha_lab.service", description="SYNTHETIC DATA / NOT PRODUCTION DEPLOYED")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-config", help="validate configuration and print it with secrets masked")
    m = sub.add_parser("mint-token", help="dev/test only"); m.add_argument("--sub", required=True); m.add_argument("--role", required=True); m.add_argument("--ttl", type=int, default=900)
    a = ap.parse_args(argv)
    try:
        s = load_settings()
    except ConfigError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr); return 78
    if a.cmd == "check-config":
        print(json.dumps(s.safe_dict(), indent=1, sort_keys=True)); return 0
    if s.env not in ("dev", "test"):
        print("mint-token refuses to run unless NASHA_SVC_ENV is dev or test", file=sys.stderr); return 2
    from .auth import TokenService
    t = TokenService(s.signing_keys(), s.jwt_active_kid, s.jwt_issuer, s.jwt_audience, leeway_s=s.jwt_leeway_s, max_ttl_s=s.token_max_ttl_s)
    print(t.issue(a.sub, a.role, a.ttl)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
