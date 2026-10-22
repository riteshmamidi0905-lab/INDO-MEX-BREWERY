from __future__ import annotations

import uuid




def idem() -> dict[str, str]: return {"Idempotency-Key": "k-" + uuid.uuid4().hex}
