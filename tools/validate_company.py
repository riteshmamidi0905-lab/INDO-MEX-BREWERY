#!/usr/bin/env python3
"""Company-building system checks (Sprint 19): data files parse, generated founder control center is fresh, decision register and contradiction check pass, every agent
analysis file carries its banner, no dollar amounts or invented figures in company planning files, no respondent data in customer templates, finance inputs blank or classified."""
import csv, glob, os, re, subprocess, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # run from the repo root wherever invoked
errs = []
def fail(m): errs.append(m)
for f in glob.glob("docs/company/data/*.csv") + ["docs/decisions/decision-register.csv", "ops/finance/scenario-fields.csv", "ops/finance/assumptions.csv", "ip/IP-ASSET-TRACKER.csv", "ops/rd/iteration-log.csv", "research/customer-discovery/purchase-conversion-tracker.csv", "research/customer-discovery/repeat-intent-tracker.csv", "research/customer-discovery/tasting-responses.csv", "research/customer-discovery/coded-quotes.csv", "ops/templates/expenses-receipts.csv"]:
    try:
        rows = list(csv.reader(open(f, encoding="utf-8")))
        n = len(rows[0])
        for i, r in enumerate(rows[1:], 2):
            if len(r) != n: fail(f"{f}:{i}: {len(r)} cells, header has {n}")
    except Exception as e: fail(f"{f}: {e}")
for f in glob.glob("docs/company/*.md"):
    first = open(f, encoding="utf-8").readline().strip()
    if not (first.startswith("AGENT ANALYSIS") or first.startswith("DRAFT ONLY")): fail(f"{f}: first line must carry the AGENT ANALYSIS (or DRAFT ONLY) banner")
for f in glob.glob("docs/company/**/*", recursive=True) + glob.glob("research/customer-discovery/*"):
    if os.path.isfile(f) and f.endswith((".md", ".csv")) and "market-map" not in f.lower():   # market-map files may quote OBSERVED public prices with source and tier
        t = open(f, encoding="utf-8").read()
        if re.search(r"\$\s?\d|\bUSD\b|\d\s*dollars", t, re.I): fail(f"{f}: dollar amount in a planning file (no unsourced prices)")
for f in ("research/customer-discovery/purchase-conversion-tracker.csv", "research/customer-discovery/repeat-intent-tracker.csv", "research/customer-discovery/tasting-responses.csv", "research/customer-discovery/coded-quotes.csv", "ops/rd/iteration-log.csv"):
    if len(list(csv.reader(open(f, encoding="utf-8")))) > 1: fail(f"{f}: has data rows; templates must stay header-only until real data exists")
for r in csv.DictReader(open("ops/finance/assumptions.csv", encoding="utf-8")):
    if (r["value"] or "").strip() and (r.get("provenance_class") or "UNKNOWN").upper() == "UNKNOWN": fail(f"assumptions.csv: {r['assumption_id']} has a value but provenance_class UNKNOWN")
for cmd, msg in ((["tools/founder_center.py", "--check"], "docs/FOUNDER-CONTROL-CENTER.md is stale: run python3 tools/founder_center.py"), (["tools/decision_register.py", "check"], "decision register/contradiction check failed: python3 tools/decision_register.py check")):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    if r.returncode: fail(msg + " " + r.stdout[-300:])
print("COMPANY: " + ("FAIL\n  " + "\n  ".join(errs) if errs else "ok (company data parses, control center fresh, decisions consistent, no unsourced dollar amounts, templates empty)"))
sys.exit(1 if errs else 0)
