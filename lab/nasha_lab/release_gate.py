"""Deterministic release-readiness gate for the NASHA Enterprise AI Lab.

This gate never claims production readiness. It answers a narrower question:
does the synthetic/offline engineering evidence meet the thresholds required
before this branch may be presented as a portfolio-ready technical case study?
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from . import eval_failures


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    measured: float
    threshold: float
    unit: str
    evidence: str


def _read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _fraction(ok: int, total: int) -> float:
    return 0.0 if total == 0 else ok / total


def evaluate(root: Path | None = None, failure_runner: Callable[[], dict] = eval_failures.run_all) -> dict:
    root = root or Path(__file__).resolve().parents[1]
    results = root / "results"

    failures = failure_runner()
    failure_pass = sum(bool(v.get("passed")) for v in failures.values())
    failure_rate = _fraction(failure_pass, len(failures))

    dq = _read_json(results / "eval_v1.json")
    planner = _read_json(results / "planner_deterministic.json")
    rag = _read_json(results / "rag2_retrieval.json")

    # Keep extraction deliberately defensive: result formats are historical evidence
    # and should fail closed if a required metric disappears.
    defect_rows = (dq.get("injected") or {}).get("per_rule") or dq.get("per_defect") or dq.get("defects") or {}
    defect_metrics = list(defect_rows.values()) if isinstance(defect_rows, dict) else defect_rows
    recalls = [float(x["recall"]) for x in defect_metrics if isinstance(x, dict) and "recall" in x]
    precisions = [float(x["precision"]) for x in defect_metrics if isinstance(x, dict) and "precision" in x]
    min_recall = min(recalls) if recalls else 0.0
    min_precision = min(precisions) if precisions else 0.0

    rows = planner.get("rows") or planner.get("scenarios") or planner.get("results") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    planner_pass = sum(bool(x.get("passed") or x.get("all_checks_pass")) for x in rows if isinstance(x, dict))
    planner_rate = _fraction(planner_pass, len(rows))

    retrieval = rag.get("summary") or rag.get("retrievers") or {}
    bm25 = retrieval.get("bm25") or retrieval.get("BM25") or {}
    bm25_mrr = float(bm25.get("mrr", bm25.get("MRR", 0.0))) if isinstance(bm25, dict) else 0.0

    checks = [
        Check("failure_injection", failure_rate == 1.0, failure_rate, 1.0, "pass_rate", "nasha_lab.eval_failures"),
        Check("data_quality_precision", min_precision >= 0.99, min_precision, 0.99, "minimum_precision", "results/eval_v1.json"),
        Check("data_quality_recall", min_recall >= 0.90, min_recall, 0.90, "minimum_recall", "results/eval_v1.json"),
        Check("deterministic_planner", planner_rate >= 0.99, planner_rate, 0.99, "scenario_pass_rate", "results/planner_deterministic.json"),
        Check("retrieval_bm25", bm25_mrr >= 0.80, bm25_mrr, 0.80, "MRR", "results/rag2_retrieval.json"),
    ]
    passed = all(c.passed for c in checks)
    return {
        "schema_version": 1,
        "portfolio_release_ready": passed,
        "scope": "synthetic/offline engineering evidence; not production readiness or business validation",
        "generated_unix": int(time.time()),
        "checks": [asdict(c) for c in checks],
        "failure_cases": failures,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out")
    args = p.parse_args()
    report = evaluate()
    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    return 0 if report["portfolio_release_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
