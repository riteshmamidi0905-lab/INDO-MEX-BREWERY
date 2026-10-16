"""P3 product case: the documents stay honest. Every test named in the PRD exists, every cited file exists, every assumption id used is defined,
and the documents state no tool count, no unlabelled numbers from the wrong place and carry the required labels."""
import re
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
DOCS = LAB / "docs" / "product"
FILES = sorted(DOCS.glob("*.md"))


def _text(p):
    return p.read_text()


def test_the_case_has_the_expected_files():
    names = {p.name for p in FILES}
    for n in ("README.md", "01-problem-and-workflow.md", "02-requirements-and-metrics.md", "03-options-and-decision-matrix.md", "04-prd-and-user-stories.md",
              "05-evidence-and-evaluation.md", "06-decision-memo.md", "07-rollout-and-roadmap.md", "08-assumptions-register.md", "09-evidence-map.md"):
        assert n in names


def test_every_test_named_in_the_documents_exists():
    pat = re.compile(r"`?(tests/test_[a-z0-9_]+\.py)::([A-Za-z0-9_*]+)`?")
    missing = []
    seen = 0
    for p in FILES:
        for f, name in pat.findall(_text(p)):
            seen += 1
            src = (LAB / f).read_text()
            if name.endswith("*"):
                ok = re.search(rf"def {re.escape(name[:-1])}", src) is not None
            else:
                ok = re.search(rf"def {re.escape(name)}\b", src) is not None
            if not ok:
                missing.append((p.name, f, name))
    assert seen > 40 and not missing, missing


def test_shortened_test_references_in_the_prd_resolve_to_the_preceding_file():
    """The PRD writes `::name` after a full path to save space; each shortened reference must exist in the most recent file named before it."""
    text = _text(DOCS / "04-prd-and-user-stories.md") + _text(DOCS / "02-requirements-and-metrics.md")
    last, bad = None, []
    def exists(f, n):
        src = (LAB / f).read_text()
        return re.search(rf"def {re.escape(n[:-1])}", src) is not None if n.endswith("*") else re.search(rf"def {re.escape(n)}\b", src) is not None
    for tok in re.findall(r"tests/test_[a-z0-9_]+\.py(?:::[A-Za-z0-9_]+\*?)?|(?<![A-Za-z0-9_/.])::[A-Za-z0-9_]+\*?", text):
        if tok.startswith("tests/"):
            last = tok.split("::")[0]
            if "::" in tok and not exists(last, tok.split("::")[1]):
                bad.append(tok)
        elif tok.startswith("::") and last and not exists(last, tok[2:]):
            bad.append((last, tok))
    assert not bad, bad


def test_backticked_result_and_code_paths_exist():
    pat = re.compile(r"`((?:results|nasha_lab|product_case|docs|baseline|claims)/[A-Za-z0-9_.+\-/]+\.(?:json|py|md|jsonl))`")
    missing = set()
    for p in FILES:
        for rel in pat.findall(_text(p)):
            if rel.startswith("docs/decisions"):
                ok = (LAB.parent / rel).exists()
            elif rel.startswith("product_case/results"):
                ok = (LAB / rel).exists()
            else:
                ok = (LAB / rel).exists()
            if not ok:
                missing.add((p.name, rel))
    assert not missing, sorted(missing)


def test_result_file_wildcards_used_in_prose_match_real_files():
    for pat in ("planner_*.json", "ext1_planner_deterministic*.json", "planner_qwen*.json"):
        assert list((LAB / "results").glob(pat)), pat


def test_every_assumption_id_used_is_defined_in_the_register():
    reg = _text(DOCS / "08-assumptions-register.md")
    defined = set(re.findall(r"^\| (A-\d\d[a-z]?) \|", reg, re.M))
    assert len(defined) >= 22
    used = set()
    for p in FILES:
        if p.name.startswith("08"):
            continue
        used |= set(re.findall(r"\bA-(\d\d)[a-z]?\b", _text(p)))
    for u in used:
        assert f"A-{u}" in defined, u
    # every register row has an owner, a falsification and an effect (six cells)
    rows = [l for l in reg.splitlines() if re.match(r"^\| A-\d\d", l)]
    assert all(len([c for c in l.strip("|").split("|") if c.strip()]) == 6 for l in rows)


def test_no_tool_count_is_stated():
    bad = re.compile(r"\b(18|19|eighteen|nineteen)\s+(typed\s+|registered\s+|exposed\s+)?tools\b", re.I)
    for p in FILES:
        assert not bad.search(_text(p)), p.name


def test_labels_are_present_and_forbidden_claims_are_absent():
    for p in FILES:
        t = _text(p)
        assert re.search(r"SYNTHETIC|HYPOTHETICAL", t), p.name
    allt = " ".join(_text(p) for p in FILES)
    assert "SIMULATED" in _text(DOCS / "01-problem-and-workflow.md")
    assert "DESIGN TARGET" in _text(DOCS / "02-requirements-and-metrics.md")
    for banned in ("we interviewed", "customers told", "market size of", "survey of", "our customers", "validated with users", "halal certified", "halal-certified"):
        assert banned not in allt.lower(), banned
    assert "untested design hypothesis" in allt


def test_229_and_265_are_reported_as_two_different_things():
    ev = _text(DOCS / "05-evidence-and-evaluation.md")
    assert "229 passed, 1 skipped" in ev and "265 passed, 2 skipped" in ev
    assert "frozen Block 3 CI" in ev and "base commit" in ev
