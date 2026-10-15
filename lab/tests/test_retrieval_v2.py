import json, os, pathlib
import pytest
from nasha_lab import answerability as A, eval_rag2 as E2, knowledge as K, qgen

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATS = {"DIRECT", "DECISION_STATUS", "SUPERSEDED", "UNVERIFIED", "VISION", "UNANSWERABLE", "D54", "CONFLICTING", "NUMERIC", "OPERATIONAL", "ADVERSARIAL", "OUT_OF_DOMAIN", "MULTI_DOCUMENT"}


@pytest.fixture(scope="module")
def kb(): return K.default_kb()


def test_generated_questions_are_deterministic_and_structurally_valid(kb):
    rows = qgen.generate(kb)
    assert qgen.validate(kb, rows) == []
    committed = [json.loads(l) for l in open(ROOT / "eval" / "rag_golden_v2.jsonl") if l.strip()]
    assert rows == committed, "regenerate with: python -m nasha_lab.qgen"


def test_all_thirteen_categories_and_both_splits_are_present():
    rows = E2.load()
    assert {r["category"] for r in rows} == CATS and len(rows) >= 450
    assert {r["split"] for r in rows} == {"dev", "heldout"} and sum(r["split"] == "heldout" for r in rows) >= 130


def test_content_questions_are_split_by_source_document_not_by_question():
    rows = [r for r in E2.load() if r.get("source", "").startswith("generated:") and r["gold_docs"] and r["category"] in ("DIRECT", "OPERATIONAL", "UNVERIFIED", "VISION", "NUMERIC", "DECISION_STATUS")]
    dev = {g for r in rows if r["split"] == "dev" for g in r["gold_docs"][:1]}; held = {g for r in rows if r["split"] == "heldout" for g in r["gold_docs"][:1]}
    assert not (dev & held), sorted(dev & held)[:5]


def test_unanswerable_templates_are_disjoint_between_dev_and_heldout():
    src = lambda sp: {r["source"] for r in E2.load() if r["category"] == "UNANSWERABLE" and r["split"] == sp and r["source"].startswith("generated:unans-")}
    assert src("heldout") - {"generated:unans-missing-decision"} and not (src("dev") & src("heldout") - {"generated:unans-missing-decision"})


def test_labels_are_not_circular_expected_status_comes_from_corpus_metadata(kb):
    for r in E2.load():
        if r["gold_docs"] and r["expected_status"] and r.get("source", "").startswith("generated:"):
            assert r["expected_status"] in {c["effective_status"] for c in kb.chunks.values() if c["document_id"] == r["gold_docs"][0]}


def test_bm25_v2_results_reproduce_exactly(kb):
    committed = json.load(open(ROOT / "results" / "rag2_retrieval.json"))
    kb2 = K.default_kb(); fresh = E2.run(kb2, retrievers=["bm25"], with_models=False)
    assert fresh["retrieval"]["bm25"]["heldout"]["ALL"] == committed["retrieval"]["bm25"]["heldout"]["ALL"]


def test_answerability_gate_is_loaded_from_json_and_matches_the_feature_list(kb):
    g = kb.gate; assert g is not None and g.trained_on.startswith("dev split")
    assert json.load(open(ROOT / "eval" / "answerability_gate.json"))["features"] == A.FEATURES


def test_gate_trade_off_is_the_committed_one(kb):
    d = json.load(open(ROOT / "results" / "abstention_end_to_end.json"))["all/heldout"]
    rows = [r for r in E2.load() if r["split"] == "heldout"]
    una = [r for r in rows if r["must_abstain"]]; fa = sum(not kb.ask(r["question"])["abstained"] for r in una)
    assert f"{fa}/{len(una)}" == d["builtin_plus_gate"]["fa"] and d["builtin_plus_gate"]["fa_rate"] < d["builtin"]["fa_rate"]


# ---------------------------------------------------------------- neural + pgvector (skip loudly when the dependency is absent)
spacy = pytest.importorskip("spacy", reason="INTEGRATION UNAVAILABLE: spaCy not installed")
try: spacy.load("en_core_web_md"); HAVE_MD = True
except Exception: HAVE_MD = False
PG = os.environ.get("NASHA_PG_DSN") or ("postgresql://nasha:nasha@127.0.0.1/nasha" if os.environ.get("NASHA_PG") else None)


@pytest.mark.skipif(not HAVE_MD, reason="INTEGRATION UNAVAILABLE: spaCy model en_core_web_md missing")
def test_static_neural_retriever_is_normalised_and_findable(kb):
    from nasha_lab.embeddings import NeuralIndex, SpacyStaticEmbedder
    ni = NeuralIndex(list(kb.chunks.values()), SpacyStaticEmbedder())
    import numpy as np
    assert abs(float(np.linalg.norm(ni.M[0])) - 1.0) < 1e-3 and ni.M.shape == (len(kb.chunks), 300)
    assert "D-54" in [c for c, _ in ni.search("beef pork dietary policy", 10)]


def _pg_ok():
    if not PG: return False
    try:
        import psycopg; psycopg.connect(PG, connect_timeout=2).close(); return True
    except Exception: return False


@pytest.mark.skipif(not (HAVE_MD and _pg_ok()), reason="INTEGRATION UNAVAILABLE: PostgreSQL + pgvector not reachable (set NASHA_PG_DSN)")
def test_pgvector_matches_the_exact_scan_and_uses_hnsw_cosine(kb):
    from nasha_lab.embeddings import NeuralIndex, PgVectorIndex, SpacyStaticEmbedder
    import psycopg
    chunks = list(kb.chunks.values()); emb = SpacyStaticEmbedder(); exact = NeuralIndex(chunks, emb); pg = PgVectorIndex(chunks, emb, PG, "pgvector_test", table="nasha_chunks_test")
    qs = [r["question"] for r in E2.load() if r["gold_docs"]][:25]; overlap = []
    for q in qs:
        a = {c for c, _ in exact.search(q, 10)}; b = {c for c, _ in pg.search(q, 10)}; overlap.append(len(a & b) / 10)
    assert sum(overlap) / len(overlap) >= 0.9, overlap          # HNSW is approximate: allow a little recall loss, measure it
    idx = psycopg.connect(PG).execute("select indexdef from pg_indexes where tablename='nasha_chunks_test'").fetchall()
    assert any("hnsw" in i[0] and "vector_cosine_ops" in i[0] for i in idx)
