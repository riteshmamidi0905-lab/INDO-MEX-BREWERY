from __future__ import annotations

import uuid
from typing import Any, Iterator

from fastapi.testclient import TestClient

from nasha_lab.service.app import create_hardened_app
from nasha_lab.service.config import Settings


def idem() -> dict[str, str]: return {"Idempotency-Key": "k-" + uuid.uuid4().hex}
