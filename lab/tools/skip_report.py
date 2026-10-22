#!/usr/bin/env python3
"""Skip report for CI. Reads a pytest JUnit XML, groups skips by reason, compares with tests/skip-policy.json and writes a Markdown summary.

    pytest ... -rs --junitxml=junit.xml ; python tools/skip_report.py junit.xml [--policy tests/skip-policy.json] [--md summary.md] [--strict]

Why: a module-level importorskip turns a whole test module into ONE skip, so a green "N passed, M skipped" can hide dozens of tests that never ran.
Without --strict the report never fails the build (report-only first, then flip). With --strict, a skip that matches no allowed entry, or exceeds its `max`, exits 1.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def collect(junit):
    root = ET.parse(junit).getroot()
    tot = {"tests": 0, "skipped": 0, "failures": 0, "errors": 0}
    skips = []
    for tc in root.iter("testcase"):
        tot["tests"] += 1
        for ch in tc:
            if ch.tag == "skipped":
                tot["skipped"] += 1
                skips.append({"test": f"{tc.get('classname')}::{tc.get('name')}", "reason": (ch.get("message") or "").strip()})
            elif ch.tag in ("failure", "error"):
                tot["failures" if ch.tag == "failure" else "errors"] += 1
    return tot, skips


def classify(skips, policy):
    groups = {}
    for s in skips:
        name = next((a["name"] for a in policy["allowed"] if re.search(a["match"], s["reason"], re.I)), None)
        key = name or "UNEXPECTED"
        g = groups.setdefault(key, {"count": 0, "reasons": Counter(), "tests": []})
        g["count"] += 1
        g["reasons"][s["reason"][:140]] += 1
        g["tests"].append(s["test"])
    problems = []
    limits = {a["name"]: a["max"] for a in policy["allowed"]}
    for k, g in groups.items():
        if k == "UNEXPECTED":
            problems.append(f"{g['count']} skip(s) match no allowed reason")
        elif g["count"] > limits[k]:
            problems.append(f"'{k}': {g['count']} skips, policy allows {limits[k]}")
    return groups, problems


def markdown(tot, groups, problems):
    out = [f"## Test skip report", f"{tot['tests']} test cases · {tot['skipped']} skipped · {tot['failures']} failed · {tot['errors']} errors", ""]
    if not groups:
        out.append("No skips.")
    for k, g in sorted(groups.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        out.append(f"- **{k}**: {g['count']}")
        for r, n in g["reasons"].most_common(3):
            out.append(f"    - {n}× {r}")
    out.append("")
    out.append("**Policy problems:** " + ("none" if not problems else "; ".join(problems)))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("junit"); ap.add_argument("--policy", default=str(Path(__file__).resolve().parents[1] / "tests/skip-policy.json")); ap.add_argument("--md"); ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    tot, skips = collect(a.junit)
    groups, problems = classify(skips, json.loads(Path(a.policy).read_text()))
    md = markdown(tot, groups, problems)
    print(md)
    if a.md:
        Path(a.md).write_text(md)
    return 1 if (a.strict and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
