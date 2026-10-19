"""Deterministic, fail-safe release gate over offline engineering evidence."""
from __future__ import annotations
import argparse, json, math, time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal
from . import eval_failures

Decision = Literal["PASS", "FAIL", "REQUIRES_REVIEW"]

@dataclass(frozen=True)
class Check:
    name: str
    decision: Decision
    measured: float | None
    threshold: float | None
    unit: str
    evidence: str
    reason: str

    @property
    def passed(self) -> bool:
        return self.decision == "PASS"

def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: top-level JSON must be an object")
    return value

def _metric(name: str, value, threshold: float, unit: str, evidence: str, *, higher=True) -> Check:
    if value is None:
        return Check(name, "REQUIRES_REVIEW", None, threshold, unit, evidence, "required metric unavailable")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return Check(name, "REQUIRES_REVIEW", None, threshold, unit, evidence, "required metric malformed")
    measured = float(value)
    if not math.isfinite(measured):
        return Check(name, "REQUIRES_REVIEW", None, threshold, unit, evidence, "required metric non-finite")
    ok = measured >= threshold if higher else measured <= threshold
    return Check(name, "PASS" if ok else "FAIL", measured, threshold, unit, evidence,
                 "measured evidence satisfies policy" if ok else "measured evidence violates policy")

def _aggregate(checks: list[Check]) -> Decision:
    if any(c.decision == "FAIL" for c in checks):
        return "FAIL"
    if any(c.decision == "REQUIRES_REVIEW" for c in checks):
        return "REQUIRES_REVIEW"
    return "PASS"

def _version_check(doc: dict, expected: str, evidence: str) -> Check | None:
    # Historical committed artifacts predate explicit evaluator metadata and are handled
    # by their versioned legacy adapter. If metadata is present it must match.
    version = doc.get("evaluator_version")
    if version is None:
        return None
    if not isinstance(version, str):
        return Check("evaluator_version", "REQUIRES_REVIEW", None, None, "version", evidence, "evaluator version malformed")
    return Check("evaluator_version", "PASS" if version == expected else "REQUIRES_REVIEW",
                 None, None, "version", evidence,
                 "supported evaluator version" if version == expected else f"unsupported evaluator version {version!r}")

def evaluate(root: Path | None = None, failure_runner: Callable[[], dict] = eval_failures.run_all) -> dict:
    root = root or Path(__file__).resolve().parents[1]
    results = root / "results"
    checks: list[Check] = []
    failure_cases: dict = {}

    try:
        failure_cases = failure_runner()
        if not isinstance(failure_cases, dict) or not failure_cases:
            checks.append(Check("security_failure_injection", "REQUIRES_REVIEW", None, 1.0, "pass_rate",
                                "nasha_lab.eval_failures", "security evidence missing or incomplete"))
        elif any(not isinstance(v, dict) or "passed" not in v or not isinstance(v["passed"], bool)
                 for v in failure_cases.values()):
            checks.append(Check("security_failure_injection", "REQUIRES_REVIEW", None, 1.0, "pass_rate",
                                "nasha_lab.eval_failures", "security evidence malformed or incomplete"))
        else:
            passed = sum(v["passed"] for v in failure_cases.values())
            checks.append(_metric("security_failure_injection", passed / len(failure_cases), 1.0,
                                  "pass_rate", "nasha_lab.eval_failures"))
    except Exception as exc:
        checks.append(Check("security_failure_injection", "REQUIRES_REVIEW", None, 1.0, "pass_rate",
                            "nasha_lab.eval_failures", f"security evaluator unavailable: {type(exc).__name__}"))

    docs = {}
    for key, filename in (("dq", "eval_v1.json"), ("planner", "planner_deterministic.json"), ("rag", "rag2_retrieval.json")):
        try:
            docs[key] = _read_json(results / filename)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            checks.append(Check(key, "REQUIRES_REVIEW", None, None, "evidence", f"results/{filename}",
                                f"required evidence unavailable or malformed: {type(exc).__name__}"))

    dq = docs.get("dq")
    if dq is not None:
        vc = _version_check(dq, "1.0", "results/eval_v1.json")
        if vc: checks.append(vc)
        rows = ((dq.get("injected") or {}).get("per_rule") if isinstance(dq.get("injected"), dict) else None)
        if not isinstance(rows, dict) or not rows:
            checks.append(Check("data_quality", "REQUIRES_REVIEW", None, None, "metric", "results/eval_v1.json",
                                "DQ per-rule evidence missing"))
        else:
            def numeric(v):
                return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            malformed = any(
                not isinstance(v, dict)
                or not numeric(v.get("recall"))
                or (v.get("precision") is not None and not numeric(v.get("precision")))
                for v in rows.values()
            )
            if malformed:
                checks.append(Check("data_quality_schema", "REQUIRES_REVIEW", None, None, "metric",
                                    "results/eval_v1.json", "DQ per-rule metric malformed or non-finite"))
            supported = [v for v in rows.values() if isinstance(v, dict) and numeric(v.get("recall")) and v["recall"] > 0]
            precisions = [v.get("precision") for v in supported if numeric(v.get("precision"))]
            recalls = [v.get("recall") for v in supported]
            checks.append(_metric("data_quality_precision", min(precisions) if precisions else None, .99,
                                  "minimum_precision", "results/eval_v1.json"))
            checks.append(_metric("data_quality_recall", min(recalls) if recalls else None, .90,
                                  "minimum_recall", "results/eval_v1.json"))

    planner = docs.get("planner")
    if planner is not None:
        try: value = ((planner.get("overall") or {}).get("pass_rate") or {}).get("rate")
        except AttributeError: value = None
        checks.append(_metric("deterministic_planner", value, .99, "scenario_pass_rate",
                              "results/planner_deterministic.json"))

    rag = docs.get("rag")
    if rag is not None:
        try:
            retrieval = rag.get("retrieval") or rag.get("summary") or rag.get("retrievers") or {}
            bm25 = retrieval.get("bm25") or retrieval.get("BM25") or {}
            if isinstance(bm25, dict) and "all" in bm25: bm25 = (bm25.get("all") or {}).get("ALL") or {}
            value = bm25.get("mrr", bm25.get("MRR")) if isinstance(bm25, dict) else None
        except AttributeError:
            value = None
        checks.append(_metric("retrieval_bm25", value, .80, "MRR", "results/rag2_retrieval.json"))

    decision = _aggregate(checks)
    return {
        "schema_version": 2,
        "decision": decision,
        "portfolio_release_ready": decision == "PASS",
        "scope": "synthetic/offline engineering evidence; not production readiness or business validation",
        "generated_unix": int(time.time()),
        "checks": [asdict(c) | {"passed": c.passed} for c in checks],
        "failure_cases": failure_cases,
    }

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--out"); args=p.parse_args()
    report=evaluate(); payload=json.dumps(report, indent=2, sort_keys=True); print(payload)
    if args.out: Path(args.out).write_text(payload+"\n", encoding="utf-8")
    return 0 if report["decision"] == "PASS" else 3

if __name__ == "__main__": raise SystemExit(main())
