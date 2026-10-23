"""Reproduce the audit-chain concurrency incident and record before/after results to results/audit-concurrency/incident.json.
'before' = the same test file run with the pre-fix _audit re-installed by tools/legacy_audit_plugin.py; 'after' = the committed code. Repeats are real runs; nothing here is estimated."""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "audit-concurrency" / "incident.json"
SELECT = "concurrent or storm or lock_is_held or rolls_back"
TEST = "tests/test_growth_audit_guarantee.py"
REPEATS = int(os.environ.get("INCIDENT_REPEATS", "10"))


def run(legacy):
    env = dict(os.environ, PYTHONPATH=f"{ROOT / 'tools'}{os.pathsep}{os.environ.get('PYTHONPATH', '')}")
    cmd = [sys.executable, "-m", "pytest", TEST, "-q", "-p", "no:cacheprovider", "-k", SELECT, "-rf", "-W", "error::pytest.PytestUnhandledThreadExceptionWarning"]
    if legacy:
        cmd[3:3] = ["-p", "legacy_audit_plugin"]
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    out = p.stdout + p.stderr
    m = re.search(r"(?:(\d+) failed)?[, ]*(?:(\d+) passed)?", out.strip().splitlines()[-1]) if out.strip() else None
    failed = sorted(set(re.findall(r"^FAILED \S+::(\S+)", out, re.M)))
    summary = out.strip().splitlines()[-1]
    return dict(returncode=p.returncode, summary=summary, failed_tests=[f.split(" ")[0] for f in failed], unique_violation_seen="audit_log_pkey" in out)


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "nasha_lab", "tests", "tools"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    before = [run(True) for _ in range(3)]
    after = [run(False) for _ in range(REPEATS)]
    doc = dict(
        title="Preventing Audit-Chain Corruption Under Concurrent Requests", commit=commit, dirty_code=dirty, selection=SELECT, test_file=TEST,
        original_failure=dict(
            observed_in="full-suite run at engineering commit cb4ae79: suite passed, but pytest reported 3 unhandled thread exceptions",
            test="test_two_concurrent_conversions_of_the_same_lead_produce_exactly_one_opportunity", postgres_error='psycopg.errors.UniqueViolation: duplicate key value violates unique constraint "audit_log_pkey"',
            path="convert_lead -> _write: Blocked -> self._audit(..., 'deny', ...) -> INSERT INTO audit_log", threads_failed=3, threads_total=6),
        before_fix=dict(runs=before, note="same tests, pre-fix _audit re-installed by tools/legacy_audit_plugin.py"),
        after_fix=dict(runs=after, passed_runs=sum(r["returncode"] == 0 for r in after), repeats=REPEATS),
        file_sha256={f: sha(f) for f in ("nasha_lab/growth/service.py", TEST, "tools/legacy_audit_plugin.py")},
        limitations=["Intermittent by nature: the pre-fix failure depends on thread timing, so a pass of the old code in any single run proves nothing; the deterministic pause test is the strong evidence.",
                     "Single PostgreSQL instance, one process; no multi-node or failover behaviour is claimed.",
                     "No throughput or latency measurement was made; none is claimed."])
    OUT.write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({k: doc[k] for k in ("commit", "dirty_code")}), "before:", [r["summary"] for r in before], "after passed:", doc["after_fix"]["passed_runs"], "/", REPEATS)


if __name__ == "__main__":
    main()
