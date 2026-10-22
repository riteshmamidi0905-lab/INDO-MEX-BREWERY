import json

import pytest

from learning import diagnostic as d


def test_question_bank_is_valid_and_covers_the_nine_areas():
    qs = d.load_questions()
    assert {q["area"] for q in qs} == {"Python", "SQL", "APIs", "Data engineering", "LLMs", "RAG", "Agents", "Docker", "System design"}
    for area in {q["area"] for q in qs}:
        kinds = {q["type"] for q in qs if q["area"] == area}
        assert kinds == {"mcq", "short"}, area


def test_scoring_never_counts_a_skip_or_invalid_choice_as_correct():
    q = next(q for q in d.load_questions() if q["type"] == "mcq")
    assert d.score_mcq(q, q["answer"]) is True
    assert d.score_mcq(q, (q["answer"] + 1) % len(q["options"])) is False
    for bad in (None, -1, 99, "1", 1.0):
        assert d.score_mcq(q, bad) is None


def test_summary_marks_short_answers_pending_and_unattempted_items():
    qs = d.load_questions()
    mc = next(q for q in qs if q["type"] == "mcq" and q["area"] == "SQL")
    sh = next(q for q in qs if q["type"] == "short" and q["area"] == "SQL")
    s = d.summarize(qs, [{"id": mc["id"], "choice": mc["answer"]}, {"id": sh["id"], "answer": "window function"}])
    assert s["SQL"]["mcq_correct"] == 1 and s["SQL"]["short_pending_review"] == 1
    assert s["Python"]["unattempted"] == 3


def test_malformed_bank_is_rejected(tmp_path, monkeypatch):
    bad = [{"id": "X-01", "area": "A", "level": 1, "type": "mcq", "prompt": "p", "options": ["a"], "answer": 3}]
    f = tmp_path / "q.json"
    f.write_text(json.dumps(bad))
    monkeypatch.setattr(d, "QUESTIONS", f)
    with pytest.raises(ValueError):
        d.load_questions()
