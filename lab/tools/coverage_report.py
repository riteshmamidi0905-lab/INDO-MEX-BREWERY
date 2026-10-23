#!/usr/bin/env python3
"""Measured line coverage of the governed package by the governed test files (coverage.py). Writes results/release-gate/coverage.json. Line coverage only: it says which lines ran, not that the assertions are strong.
    cd lab && python3 tools/coverage_report.py"""
import json
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
OUT = LAB / "results/release-gate"
TESTS = ["tests/test_governed_workflow.py", "tests/test_governed_api.py", "tests/test_governed_incident.py", "tests/test_governed_contradiction.py", "tests/test_governed_evaluation.py", "tests/test_release_gate.py"]
SRC = "nasha_lab/governed"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = OUT / ".coverage"
    subprocess.run([sys.executable, "-m", "coverage", "run", f"--data-file={data}", f"--source={SRC}", "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS], cwd=LAB, check=True)
    subprocess.run([sys.executable, "-m", "coverage", "json", f"--data-file={data}", "-o", str(OUT / "coverage_raw.json")], cwd=LAB, check=True)
    raw = json.loads((OUT / "coverage_raw.json").read_text())
    files = {Path(f).stem: dict(path=f, statements=v["summary"]["num_statements"], covered=v["summary"]["covered_lines"], percent=round(v["summary"]["percent_covered"], 1)) for f, v in sorted(raw["files"].items())}
    tot = raw["totals"]
    rep = dict(schema="coverage/1", tool=f"coverage.py {raw['meta']['version']}", measure="line coverage", source=SRC, tests=TESTS, totals=dict(statements=tot["num_statements"], covered=tot["covered_lines"], percent=round(tot["percent_covered"], 1)), files=files,
               caveat="Line coverage of the governed package by the governed test files only; it does not measure assertion strength, branch coverage, or the rest of the repository.")
    (OUT / "coverage.json").write_text(json.dumps(rep, indent=1))
    (OUT / "coverage_raw.json").unlink(); data.unlink()
    print(json.dumps(rep["totals"]))


if __name__ == "__main__":
    main()
