"""Formative engineering skill diagnostic (Python, SQL, APIs, data engineering, LLMs, RAG, agents, Docker, system design).

NOT mastery evidence and NOT an assessment under the 85/100 standard. Multiple-choice items are scored here; short answers
are only recorded and must be reviewed against the rubric by a person or in conversation. Nothing is marked mastered
automatically; a skill level comes only from independently demonstrated work (see SKILL-EVIDENCE-MATRIX.md).

    python -m learning.diagnostic run --out learning/results.jsonl     # take it (interactive)
    python -m learning.diagnostic summary --in learning/results.jsonl  # per-area result
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

QUESTIONS = Path(__file__).with_name("questions.json")


def load_questions():
    qs = json.loads(QUESTIONS.read_text())
    ids = [q["id"] for q in qs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate question ids")
    for q in qs:
        if q["type"] == "mcq":
            if not (0 <= q["answer"] < len(q["options"])):
                raise ValueError(f"{q['id']}: answer index out of range")
        elif q["type"] == "short":
            if not q.get("rubric"):
                raise ValueError(f"{q['id']}: short answer needs a rubric")
        else:
            raise ValueError(f"{q['id']}: unknown type")
    return qs


def score_mcq(q, choice):
    """True/False for a valid choice; None when the item was skipped or invalid (never counted as correct)."""
    if choice is None or not isinstance(choice, int) or not (0 <= choice < len(q["options"])):
        return None
    return choice == q["answer"]


def summarize(questions, records):
    by_id = {q["id"]: q for q in questions}
    out = defaultdict(lambda: {"mcq_correct": 0, "mcq_wrong": 0, "mcq_skipped": 0, "short_pending_review": 0, "unattempted": 0})
    seen = set()
    for r in records:
        q = by_id.get(r["id"])
        if not q:
            continue
        seen.add(q["id"])
        a = out[q["area"]]
        if q["type"] == "mcq":
            s = score_mcq(q, r.get("choice"))
            a["mcq_skipped" if s is None else ("mcq_correct" if s else "mcq_wrong")] += 1
        elif (r.get("answer") or "").strip():
            a["short_pending_review"] += 1
        else:
            a["mcq_skipped"] += 1
    for q in questions:
        if q["id"] not in seen:
            out[q["area"]]["unattempted"] += 1
    return dict(out)


def run(out_path):
    qs = load_questions()
    print("Formative diagnostic: answer from memory, no tools. Enter to skip. Not mastery evidence.\n")
    with open(out_path, "a") as fh:
        for q in qs:
            print(f"[{q['id']}] ({q['area']}, target level {q['level']}) {q['prompt']}")
            rec = {"id": q["id"]}
            if q["type"] == "mcq":
                for i, o in enumerate(q["options"]):
                    print(f"  {i}) {o}")
                raw = input("> ").strip()
                rec["choice"] = int(raw) if raw.isdigit() else None
            else:
                rec["answer"] = input("> ").strip()
            fh.write(json.dumps(rec) + "\n")
            print()
    print(f"Saved to {out_path}. Run: python -m learning.diagnostic summary --in {out_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--out", required=True)
    s = sub.add_parser("summary"); s.add_argument("--in", dest="inp", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        run(a.out)
        return 0
    qs = load_questions()
    recs = [json.loads(line) for line in Path(a.inp).read_text().splitlines() if line.strip()]
    for area, d in sorted(summarize(qs, recs).items()):
        print(f"{area:18} correct {d['mcq_correct']}  wrong {d['mcq_wrong']}  skipped {d['mcq_skipped']}  short answers awaiting review {d['short_pending_review']}  unattempted {d['unattempted']}")
    print("\nShort answers are not scored automatically. No skill level is assigned by this tool.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
