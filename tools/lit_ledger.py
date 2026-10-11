#!/usr/bin/env python3
"""Literature ledger (Sprint 15): Question -> candidate paper -> DOI -> metadata -> abstract note -> evidence quality -> NASHA relevance.
Append-only CSV at research/LITERATURE-LEDGER.csv. It RECORDS what a human or a connector (e.g. Consensus/PubMed) returned; it never invents a citation,
never fetches (hosts blocked here), and refuses an entry without a DOI-or-URL and an explicit evidence grade. Quote nothing you have not read.
  python3 tools/lit_ledger.py add --question Q --title T --year 2020 --doi 10.x/y --evidence-grade peer-reviewed|preprint|patent|review|abstract-only|secondary --relevance "..." --found-via "Consensus|PubMed|WebSearch" --read abstract|full|snippet
  python3 tools/lit_ledger.py list | selftest"""
import argparse, csv, os, re, sys, tempfile, datetime
F = "research/LITERATURE-LEDGER.csv"
COLS = ["id","date_added","question","title","year","doi_or_url","evidence_grade","how_much_read","found_via","nasha_relevance","limitations","tier"]
GRADES = {"peer-reviewed","preprint","patent","review","abstract-only","secondary"}; READ = {"snippet","abstract","full"}
DOI = re.compile(r"^10\.\d{4,9}/\S+$")
def add(a, path=F):
    if not (DOI.match(a.doi) or a.doi.startswith("http")): raise SystemExit("REFUSED: need a DOI (10.x/...) or URL")
    if a.evidence_grade not in GRADES or a.read not in READ: raise SystemExit("REFUSED: evidence grade or read-level invalid")
    rows = list(csv.DictReader(open(path, encoding="utf-8"))) if os.path.exists(path) else []
    if any(r["doi_or_url"] == a.doi for r in rows): raise SystemExit("DUPLICATE DOI/URL")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS)
        if new: w.writeheader()
        w.writerow(dict(id=f"L-{len(rows)+1:03d}", date_added=datetime.date.today().isoformat(), question=a.question, title=a.title, year=a.year, doi_or_url=a.doi, evidence_grade=a.evidence_grade,
            how_much_read=a.read, found_via=a.found_via, nasha_relevance=a.relevance, limitations=a.limitations, tier="T1" if a.read != "full" else "T2"))
def selftest():
    d = tempfile.mkdtemp(); p = f"{d}/l.csv"
    class A: question="q"; title="t"; year="2020"; doi="10.1000/xyz"; evidence_grade="peer-reviewed"; read="abstract"; found_via="test"; relevance="r"; limitations="l"
    add(A, p); assert open(p).read().count("L-001") == 1
    try: add(A, p); raise AssertionError("dup")
    except SystemExit as e: assert "DUPLICATE" in str(e)
    A.doi = "nonsense"
    try: add(A, p); raise AssertionError("bad doi")
    except SystemExit as e: assert "REFUSED" in str(e)
    print("selftest ok: append, duplicate refusal, DOI/URL requirement")
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest()
    elif sys.argv[1:] == ["list"]: print(open(F).read() if os.path.exists(F) else "LEDGER EMPTY")
    elif sys.argv[1:2] == ["add"]:
        p = argparse.ArgumentParser(); p.add_argument("cmd"); [p.add_argument("--" + k.replace("_", "-"), required=r, default="") for k, r in (("question",1),("title",1),("year",1),("doi",1),("evidence_grade",1),("relevance",1),("found_via",1),("read",1),("limitations",0))]
        add(p.parse_args())
    else: print(__doc__)
