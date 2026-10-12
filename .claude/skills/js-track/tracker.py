#!/usr/bin/env python3
"""tracker.py - private application tracker (CSV). Local only; default ~/.claude/jobsearch/applications.csv
(override with JS_TRACKER). It records state; it never contacts anyone or submits anything.
  add --company X --role Y --url U [--source S] [--notes N]     -> status=SAVED
  set ID --status STATUS [--note N] [--follow-up YYYY-MM-DD] [--approved]
  list [--status STATUS]    due [--today YYYY-MM-DD]    show ID
Statuses: SAVED, TAILORING, READY_FOR_YOUR_APPROVAL, APPLIED, RECRUITER_CONTACT, SCREEN, INTERVIEW, OFFER, REJECTED, WITHDRAWN, CLOSED
Gate: APPLIED requires --approved (you confirm YOU submitted it)."""
import argparse, csv, datetime, os, sys
PATH = os.environ.get("JS_TRACKER", os.path.expanduser("~/.claude/jobsearch/applications.csv"))
COLS = ["id", "company", "role", "url", "source", "status", "added", "updated", "follow_up", "applied_confirmed_by_user", "notes"]
ST = "SAVED TAILORING READY_FOR_YOUR_APPROVAL APPLIED RECRUITER_CONTACT SCREEN INTERVIEW OFFER REJECTED WITHDRAWN CLOSED".split()

def load():
    if not os.path.exists(PATH): return []
    with open(PATH, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def save(rows):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(rows)
    try: os.chmod(PATH, 0o600)
    except OSError: pass
def today(): return datetime.date.today().isoformat()
def show(r): return f"{r['id']:>3}  {r['status']:<24} {r['company']} | {r['role']} | follow-up {r['follow_up'] or '-'}"

def main(argv=None):
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); [a.add_argument(f"--{k}", default="") for k in ("company", "role", "url", "source", "notes")]
    s = sub.add_parser("set"); s.add_argument("id"); s.add_argument("--status", choices=ST); s.add_argument("--note", default=""); s.add_argument("--follow-up", default=""); s.add_argument("--approved", action="store_true")
    l = sub.add_parser("list"); l.add_argument("--status", choices=ST)
    d = sub.add_parser("due"); d.add_argument("--today", default=today())
    w = sub.add_parser("show"); w.add_argument("id")
    x = ap.parse_args(argv); rows = load()
    if x.cmd == "add":
        if not (x.company and x.role): sys.exit("need --company and --role")
        if any(r["url"] and r["url"] == x.url for r in rows): sys.exit("already tracked (same url)")
        r = {c: "" for c in COLS}; r.update(id=str(max([int(r["id"]) for r in rows] + [0]) + 1), company=x.company, role=x.role, url=x.url, source=x.source, status="SAVED", added=today(), updated=today(), notes=x.notes)
        rows.append(r); save(rows); print("added", show(r))
    elif x.cmd == "set":
        r = next((r for r in rows if r["id"] == x.id), None) or sys.exit("no such id")
        if x.status == "APPLIED" and not x.approved: sys.exit("refused: APPLIED needs --approved (you confirm you submitted it yourself)")
        if x.status: r["status"] = x.status
        if x.status == "APPLIED": r["applied_confirmed_by_user"] = today()
        if x.follow_up: r["follow_up"] = x.follow_up
        if x.note: r["notes"] = (r["notes"] + " | " if r["notes"] else "") + f"{today()}: {x.note}"
        r["updated"] = today(); save(rows); print("updated", show(r))
    elif x.cmd == "list":
        [print(show(r)) for r in rows if not x.status or r["status"] == x.status] or None
    elif x.cmd == "due":
        due = [r for r in rows if r["follow_up"] and r["follow_up"] <= x.today and r["status"] not in ("REJECTED", "WITHDRAWN", "CLOSED", "OFFER")]
        [print("DUE", show(r)) for r in due]; print(f"{len(due)} follow-up(s) due")
    elif x.cmd == "show":
        r = next((r for r in rows if r["id"] == x.id), None) or sys.exit("no such id"); [print(f"{k}: {v}") for k, v in r.items()]
if __name__ == "__main__": main()
