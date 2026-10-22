"""Collects one record per failure scenario. EXPECTED is written in the test BEFORE the call is made; OBSERVED holds deterministic facts (statuses, codes, counts);
wall-clock values are kept apart and labelled as such. With P5_WRITE_RESULTS=1 the collection is written to lab/results/p5/failure_scenarios.json."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

RECORDS: list[dict[str, Any]] = []
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "results", "p5", "failure_scenarios.json")
LABEL = "SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED. Fault injection against a local PostgreSQL (pgserver or a CI service container) and an in-process agent."


def record(sid: str, name: str, expected: str, observed: dict[str, Any], passed: bool, wall_ms: Optional[float] = None, note: str = "") -> None:
    RECORDS[:] = [r for r in RECORDS if r["id"] != sid]
    RECORDS.append({"id": sid, "scenario": name, "expected_stated_before_running": expected, "observed": observed, "passed": bool(passed), "note": note,
                    "wall_clock_ms_NOT_DETERMINISTIC": None if wall_ms is None else round(wall_ms, 1)})


def flush() -> None:
    if os.environ.get("P5_WRITE_RESULTS") != "1" or not RECORDS: return
    existing: dict[str, Any] = {}
    if os.path.exists(OUT):
        try: existing = {r["id"]: r for r in json.load(open(OUT, encoding="utf-8"))["scenarios"]}
        except Exception: existing = {}
    for r in RECORDS: existing[r["id"]] = r
    doc = {"label": LABEL, "determinism": "statuses, codes and counts are deterministic; fields named wall_clock_ms_NOT_DETERMINISTIC are one measured run on one machine and vary",
           "scenarios": [existing[k] for k in sorted(existing)]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f: f.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
