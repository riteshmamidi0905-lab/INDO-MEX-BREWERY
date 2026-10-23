"""The interview-defense package may only cite things that exist: every backticked repository path (and ::symbol) must resolve, every topic must have the required parts, and no experience claims."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs/interview/ADVANCED-INTERVIEW-DEFENSE-D90.md"
TOPICS = ["Python backend architecture", "PostgreSQL", "Data modeling", "Data engineering", "AI agents", "RAG", "MCP", "Tool calling", "Authorization", "THE WEIR", "Multi-tenant security", "Human approval",
          "Agent evaluation", "Mutation testing", "Observability", "CI/CD", "Reliability", "Reproducibility"]
PARTS = ["**Question.**", "**Expected explanation.**", "**Repository evidence.**", "**Code references.**", "**Follow-ups.**", "**Tradeoffs and limits.**"]


def test_every_required_topic_has_every_required_part():
    text = DOC.read_text()
    sections = re.split(r"\n## \d+\. ", text)[1:]
    assert [s.split("\n", 1)[0] for s in sections] == TOPICS
    for s in sections:
        assert all(p in s for p in PARTS), s.split("\n", 1)[0]


def test_every_cited_path_and_symbol_exists():
    refs = set(re.findall(r"`((?:lab|food|docs|\.github)/[\w./-]+?\.(?:py|json|md|yml))(?:::(\w+(?:\.\w+)?))?`", DOC.read_text()))
    assert len(refs) > 40
    bad = []
    for path, sym in refs:
        p = REPO / path
        if not p.exists():
            bad.append(path); continue
        if sym:
            last = sym.split(".")[-1]
            if not re.search(rf"(def|class) {last}\b", p.read_text()):
                bad.append(f"{path}::{sym}")
    assert not bad, bad


def test_package_does_not_claim_employment_or_production_use():
    low = DOC.read_text().lower()
    assert "does **not** describe employment" in low or "does not describe employment" in low.replace("**", "")
    for phrase in ("at my previous", "in my role at", "our customers", "in production at", "served users"):
        assert phrase not in low, phrase
