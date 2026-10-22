"""ASGI factory: `uvicorn --factory nasha_lab.service.serve:app`. Configuration errors stop the process with a clear, value-free message (exit code 78)."""
from __future__ import annotations

import sys
from typing import Any

from .config import ConfigError, load_settings


def app() -> Any:
    try:
        settings = load_settings()
    except ConfigError as e:
        sys.stderr.write(f"CONFIG ERROR: {e}\n")
        raise SystemExit(78) from None
    from .app import create_hardened_app
    return create_hardened_app(settings)
