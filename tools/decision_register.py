#!/usr/bin/env python3
"""Decision register and contradiction check (Sprint 19). Parses docs/decisions/DECISIONS.md (table rows | D-n | date | decision | status/owner | rationale |) into
docs/decisions/decision-register.csv with derived fields, never rewriting history, and scans repo docs for superseded phrases (docs/decisions/superseded-phrases.csv)
that appear without a nearby marker such as 'older wording' or 'superseded'.
  python3 tools/decision_register.py write    regenerate the register     python3 tools/decision_register.py check    fail on duplicate/dangling ids or stale/unmarked superseded phrases
  python3 tools/decision_register.py selftest"""
import csv, glob, os, re, sys
DEC, REG, PHR = "docs/decisions/DECISIONS.md", "docs/decisions/decision-register.csv", "docs/decisions/superseded-phrases.csv"
COLS = ["id", "date", "decision", "status", "owner_or_status_text", "supersedes", "superseded_by", "founder_required"]
ROW = re.compile(r"^\|\s*(D-\d+)\s*\|\s*([\d-]+)\s*\|(.*)$")
def parse(text):
    out = []
    for line in text.splitlines():
        m = ROW.match(line)
        if not m: continue
        cells = [c.strip() for c in m.group(3).split("|")]
        cells = [c for c in cells if c != ""] if cells and cells[-1] == "" else cells
        dec = cells[0] if cells else ""; owner = cells[1] if len(cells) > 1 else ""; rat = " ".join(cells[2:])
        whole = dec + " " + owner + " " + rat
        up = whole.upper()
        status = "ACTIVE"
        ou = owner.upper()
        pending = ("PENDING" in ou or "PROPOSAL" in ou or "PROPOSED BY PROJECT AGENTS" in ou or "AGENT-PROPOSED" in ou or "FOUNDER APPROVAL OF THESE THRESHOLDS" in up)
        if pending and "FROZEN" in up: status = "FROZEN (thresholds agent-proposed; founder confirmation pending)"
        elif pending and re.search(r"NEW EVIDENCE", up) and re.search(r"FINDING", ou): status = "FINDING (founder decision pending)"
        elif pending: status = "PROPOSED (founder confirmation pending)"
        elif "FROZEN" in up: status = "FROZEN"
        elif re.search(r"SUPERSEDED BY D-\d+", up): status = "SUPERSEDED"
        elif "PROVISIONAL" in up: status = "PROVISIONAL"
        sup = sorted(set(re.findall(r"\*{0,2}Supersedes\*{0,2}[^|]*?(D-\d+)", whole, flags=re.I)))
        by = sorted(set(re.findall(r"SUPERSEDED BY (D-\d+)", whole, flags=re.I)))
        fr = "YES" if pending else ("founder decision" if re.search(r"founder", owner, re.I) else "")
        out.append(dict(id=m.group(1), date=m.group(2), decision=re.sub(r"\*\*", "", dec)[:300], status=status, owner_or_status_text=re.sub(r"\*\*", "", owner)[:200],
                        supersedes="|".join(sup), superseded_by="|".join(by), founder_required=fr))
    # a later decision that says it (provisionally) CONFIRMS D-nn updates that decision's status; history is never rewritten
    byid = {r["id"]: r for r in out}
    for r in out:
        if not (re.search(r"founder", r["owner_or_status_text"], re.I) and not re.search(r"proposal|agent", r["owner_or_status_text"], re.I)): continue   # only a founder-owned decision can confirm another
        for t in re.findall(r"(?:provisionally )?confirms (D-\d+)", r["decision"], flags=re.I):
            if t in byid and byid[t]["status"].startswith("PROPOSED"):
                byid[t]["status"] = f"PROVISIONALLY CONFIRMED by founder ({r['id']})"; byid[t]["founder_required"] = ""
    return out
def phrases(path=PHR): return list(csv.DictReader(open(path, encoding="utf-8")))
SCOPE = ("docs/", "food/CORE5", "food/sessions/", "food/t1-test-sheets/1", "beer/CORE5", "beer/pilot-briefs/", "beer/BREWERY", "research/CORE5-PRODUCT-SYSTEM.md", "ip/", "brand/TRADEMARK", "website/data/", "visuals/CONCEPT")   # current canonical areas; older v1 documents are historical and not scanned
SKIP = ("docs/decisions/DECISIONS.md", "docs/decisions/CORRECTIONS.md", "docs/decisions/REJECTED.md", "docs/decisions/superseded-phrases.csv", "docs/decisions/decision-register.csv")
def scan(root=".", files=None):
    bad = []
    pats = [(re.compile(p["phrase_regex"], re.I), re.compile(p["allowed_context_regex"], re.I) if p["allowed_context_regex"] else None, p["superseded_by"]) for p in phrases()]
    for f in (files or [x for x in glob.glob(os.path.join(root, "**", "*.md"), recursive=True) if "node_modules" not in x and "/archive/" not in x]):
        rel = os.path.relpath(f, root)
        if rel in SKIP or (files is None and not rel.startswith(SCOPE)): continue
        lines = open(f, encoding="utf-8", errors="ignore").read().splitlines()
        for i, l in enumerate(lines):
            for rx, ok, by in pats:
                if rx.search(l):
                    ctx = " ".join(lines[max(0, i - 1): i + 2])
                    if not (ok and ok.search(ctx)): bad.append((rel, i + 1, by, l.strip()[:110]))
    return bad
def check():
    rows = parse(open(DEC, encoding="utf-8").read()); errs = []
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)): errs.append("duplicate decision ids: " + ", ".join(sorted({i for i in ids if ids.count(i) > 1})))
    known = set(ids)
    for r in rows:
        for ref in (r["supersedes"] + "|" + r["superseded_by"]).split("|"):
            if ref and ref not in known: errs.append(f"{r['id']} references unknown {ref}")
    if os.path.exists(REG):
        cur = list(csv.DictReader(open(REG, encoding="utf-8")))
        if [(c["id"], c["status"], c["founder_required"]) for c in cur] != [(r["id"], r["status"], r["founder_required"]) for r in rows]: errs.append("decision-register.csv is stale: run python3 tools/decision_register.py write")
    else: errs.append("decision-register.csv missing")
    for f, n, by, txt in scan(): errs.append(f"superseded wording without a marker ({by}): {f}:{n}: {txt}")
    return errs
def write():
    rows = parse(open(DEC, encoding="utf-8").read())
    with open(REG, "w", encoding="utf-8", newline="") as o:
        w = csv.DictWriter(o, fieldnames=COLS, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    print(f"wrote {REG}: {len(rows)} decisions")
def selftest():
    t = "| D-1 | 2026-01-01 | **A thing** | Founder | |\n| D-2 | 2026-01-02 | New thing **Supersedes** D-1 | Agent-proposed; Founder confirmation pending | why |\n| D-3 | 2026-01-03 | Old | SUPERSEDED by D-2 | |\n"
    r = parse(t); assert [x["id"] for x in r] == ["D-1", "D-2", "D-3"] and r[1]["supersedes"] == "D-1" and r[1]["status"].startswith("PROPOSED") and r[2]["status"] == "SUPERSEDED" and r[2]["superseded_by"] == "D-2", r
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.md"); open(p, "w").write("If it fails, nothing else launches\n"); assert scan(d, [p])
        open(p, "w").write("If it fails, nothing else launches (older wording)\n"); assert not scan(d, [p])
    t2 = "| D-1 | 2026-01-01 | X | Agent proposal; Founder confirmation pending | |\n| D-2 | 2026-01-02 | Agents say this confirms D-1 | Project agents (proposal) | |\n"
    r2 = parse(t2); assert r2[0]["status"].startswith("PROPOSED")   # an agent-written decision cannot confirm another
    print("selftest ok: parse, supersedes/superseded-by, status, and superseded-phrase marker logic")
if __name__ == "__main__":
    a = sys.argv[1:2]
    if a == ["selftest"]: selftest()
    elif a == ["write"]: write()
    elif a == ["check"]:
        e = check(); print("DECISIONS: " + ("FAIL\n  " + "\n  ".join(e) if e else "ok")); sys.exit(1 if e else 0)
    else: print(__doc__)
