from learning import explain as e


def test_every_concept_has_a_followup_and_phrasings():
    for t, s in e.TOPICS.items():
        assert set(s["concepts"]) == set(s["followups"]), t
        assert all(p for _, p in s["concepts"].values())


def test_empty_transcript_misses_everything_and_is_flagged_short():
    r = e.check("rag_pipeline", "")
    assert r["mentioned"] == [] and len(r["not_mentioned"]) == len(e.TOPICS["rag_pipeline"]["concepts"]) and r["too_short"]
    assert len(r["followups"]) == len(r["not_mentioned"])


def test_partial_transcript_reports_what_is_missing_and_never_assigns_a_level():
    txt = "We chunk documents and index them, then retrieve with BM25 and embeddings. Access is checked by role before the model sees anything."
    r = e.check("rag_pipeline", txt)
    assert {"chunking_indexing", "query_retrieval", "permission_check"} <= set(r["mentioned"])
    assert "abstention" in r["not_mentioned"] and "evaluation" in r["not_mentioned"]
    assert "level" not in " ".join(k for k in r) and "Coverage check only" in r["caveat"]


def test_keyword_stuffing_is_not_understanding_but_is_reported_honestly():
    r = e.check("tool_governance", "schema default deny approval in code injection audit " * 3)
    assert r["not_mentioned"] == [] and "not understanding" in r["caveat"]
