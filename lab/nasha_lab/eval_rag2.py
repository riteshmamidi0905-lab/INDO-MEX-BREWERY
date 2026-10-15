"""Retrieval + answer evaluation v2: 400+ generated questions (structurally validated) plus the 55 hand-written ones, 13 categories, dev / held-out
splits, per-category metrics, 7 retrievers (neural ones where the model is available), abstention strategies compared in answerability.py."""
import json
import math
import os
import sys
import time
from collections import defaultdict

from . import knowledge as K
K.use_version("block3")                      # frozen Block 3 benchmark: pin the Block 3 corpus (no D-84+, no item amendments)

HERE = os.path.dirname(os.path.abspath(__file__))
CAT_MAP = {"direct": "DIRECT", "status": "DECISION_STATUS", "superseded": "SUPERSEDED", "unverified": "UNVERIFIED", "multi": "MULTI_DOCUMENT", "conflict": "CONFLICTING", "d54": "D54", "ops": "OPERATIONAL",
           "unanswerable": "UNANSWERABLE", "adversarial": "ADVERSARIAL"}


def load():
    rows = [json.loads(l) for l in open(os.path.join(HERE, "..", "eval", "rag_golden_v2.jsonl")) if l.strip()]
    for l in open(os.path.join(HERE, "..", "eval", "rag_golden.jsonl")):
        if not l.strip(): continue
        r = json.loads(l); r["id"] = "H" + r["id"]; r["category"] = CAT_MAP[r["category"]]; r["split"] = "heldout" if int(r["id"][2:]) % 10 in (2, 5, 8) else "dev"; r["source"] = "handwritten"
        if r["question"].startswith(("What is the capital", )): r["category"] = "OUT_OF_DOMAIN"
        rows.append(r)
    return rows


def rank_docs(kb, q, retriever):
    seen, order = set(), []
    for h in kb.search(q, k=60, retriever=retriever, status_aware=False, include_nonauthoritative=True, candidates=80):
        if h["document_id"] not in seen: seen.add(h["document_id"]); order.append(h["document_id"])
    return order


def retrieval_metrics(rows, ranks):
    qs = [r for r in rows if r["gold_docs"]]
    if not qs: return dict(n=0)
    out = dict(n=len(qs))
    for k in (1, 5): out[f"recall@{k}"] = round(sum(len(set(ranks[r["id"]][:k]) & set(r["gold_docs"])) / len(r["gold_docs"]) for r in qs) / len(qs), 3)
    mrr = ndcg = 0.0
    for r in qs:
        g = set(r["gold_docs"]); pos = [i for i, d in enumerate(ranks[r["id"]], 1) if d in g]
        mrr += 1 / pos[0] if pos else 0
        dcg = sum(1 / math.log2(i + 1) for i in pos if i <= 10); idcg = sum(1 / math.log2(i + 1) for i in range(1, min(len(g), 10) + 1)); ndcg += dcg / idcg
    out["mrr"] = round(mrr / len(qs), 3); out["ndcg@10"] = round(ndcg / len(qs), 3)
    # authority correctness: is the best-ranked chunk of the top gold document carrying the expected effective status?
    return out


def authority_correct(kb, rows, retriever):
    """For questions with an expected status: the TOP-1 retrieved chunk (status-blind retrieval) must have that status or be a gold doc; reported as a rate."""
    qs = [r for r in rows if r["gold_docs"] and r["expected_status"]]
    if not qs: return None
    ok = 0
    for r in qs:
        h = kb.search(r["question"], k=1, retriever=retriever, status_aware=False, include_nonauthoritative=True)
        ok += bool(h) and h[0]["document_id"] in r["gold_docs"] and h[0]["effective_status"] == r["expected_status"]
    return round(ok / len(qs), 3)


def build_retrievers(kb, with_models=True, pg_dsn=None, log=print):
    info = {}
    try:
        from .embeddings import NeuralIndex, SpacyStaticEmbedder, PgVectorIndex
        ch = list(kb.chunks.values()); sp = SpacyStaticEmbedder()
        ni = NeuralIndex(ch, sp, "static_neural"); kb.add_retriever("static_neural", ni, "spacy-md-static"); kb.add_retriever("hybrid_static", K.Hybrid(kb.bm25, ni, "hybrid_static"))
        info["static_neural"] = dict(model="spacy en_core_web_md " + sp.version, dim=300, normalization="L2", metric="cosine", index="exact scan", chunking="heading-split <=1800 chars", kind="static pretrained word vectors, mean-pooled")
        if pg_dsn:
            try:
                pg = PgVectorIndex(ch, sp, pg_dsn, "pgvector_static"); kb.add_retriever("pgvector_static", pg)
                import psycopg
                v = psycopg.connect(pg_dsn).execute("select extversion from pg_extension where extname='vector'").fetchone()[0]
                info["pgvector_static"] = dict(model="same vectors as static_neural", pgvector=v, index="HNSW m=16 ef_construction=64", metric="cosine (<=>)")
            except Exception as e: info["pgvector_static"] = dict(unavailable=str(e)[:150])
    except Exception as e:
        info["static_neural"] = dict(unavailable=f"{type(e).__name__}: {str(e)[:150]}")
    if with_models:
        try:
            from .embeddings import NeuralIndex, OllamaEmbedder, PgVectorIndex
            oe = OllamaEmbedder(cache_path=os.environ.get("NASHA_EMBED_CACHE", "/tmp/nasha_embed_cache.json"))
            if oe.client.available() or oe.cache:
                ch = list(kb.chunks.values()); ni = NeuralIndex(ch, oe, "minilm"); kb.add_retriever("minilm", ni, "all-minilm"); kb.add_retriever("hybrid_minilm", K.Hybrid(kb.bm25, ni, "hybrid_minilm"))
                info["minilm"] = dict(model="all-minilm (sentence-transformers/all-MiniLM-L6-v2, Apache-2.0) via Ollama", dim=384, normalization="L2", metric="cosine", index="exact scan", chunking="heading-split <=1800 chars", kind="sentence embedding")
                if pg_dsn:
                    try:
                        kb.add_retriever("pgvector_minilm", PgVectorIndex(ch, oe, pg_dsn, "pgvector_minilm", table="nasha_chunks_minilm")); info["pgvector_minilm"] = dict(index="HNSW m=16 ef_construction=64", metric="cosine (<=>)")
                    except Exception as e: info["pgvector_minilm"] = dict(unavailable=str(e)[:150])
            else: info["minilm"] = dict(unavailable="no local Ollama runtime reachable (INTEGRATION UNAVAILABLE in this environment)")
        except Exception as e: info["minilm"] = dict(unavailable=f"{type(e).__name__}: {str(e)[:150]}")
    return info


def run(kb=None, retrievers=None, with_models=True, pg_dsn=None):
    kb = kb or K.default_kb(); rows = load(); info = build_retrievers(kb, with_models, pg_dsn)
    names = retrievers or [n for n in ("bm25", "lsa", "hybrid", "static_neural", "hybrid_static", "pgvector_static", "minilm", "hybrid_minilm", "pgvector_minilm") if n in kb.retrievers and kb.retrievers[n] is not None]
    out = dict(n=len(rows), categories=sorted({r["category"] for r in rows}), splits={s: sum(1 for r in rows if r["split"] == s) for s in ("dev", "heldout")}, retriever_info=info, retrieval={}, authority_correct={}, latency_ms={})
    for rt in names:
        t0 = time.perf_counter(); ranks = {r["id"]: rank_docs(kb, r["question"], rt) for r in rows if r["gold_docs"]}; dt = (time.perf_counter() - t0) / max(1, len(ranks)) * 1000
        out["latency_ms"][rt] = round(dt, 2)
        out["retrieval"][rt] = {sp: {"ALL": retrieval_metrics([r for r in rows if sp == "all" or r["split"] == sp], ranks),
                                     **{"SRC:" + src: retrieval_metrics([r for r in rows if (sp == "all" or r["split"] == sp) and (r.get("source") == "handwritten") == (src == "handwritten")], ranks) for src in ("handwritten", "generated")},
                                     **{c: retrieval_metrics([r for r in rows if (sp == "all" or r["split"] == sp) and r["category"] == c], ranks) for c in out["categories"]}} for sp in ("all", "dev", "heldout")}
        out["authority_correct"][rt] = {sp: authority_correct(kb, [r for r in rows if sp == "all" or r["split"] == sp], rt) for sp in ("all", "heldout")}
    return out


if __name__ == "__main__":
    pg = os.environ.get("NASHA_PG_DSN") or ("postgresql://nasha:nasha@127.0.0.1/nasha" if os.environ.get("NASHA_PG") else None)
    o = run(pg_dsn=pg); path = sys.argv[1] if len(sys.argv) > 1 else None
    if path: open(path, "w").write(json.dumps(o, indent=1))
    print(o["n"], o["splits"], {k: (v.get("unavailable") or "ok") for k, v in o["retriever_info"].items()})
    for rt, m in o["retrieval"].items():
        a = m["all"]["ALL"]; h = m["heldout"]["ALL"]
        print(f'{rt:16s} all R@1 {a["recall@1"]} R@5 {a["recall@5"]} MRR {a["mrr"]} nDCG {a["ndcg@10"]} | heldout R@5 {h["recall@5"]} MRR {h["mrr"]} | auth {o["authority_correct"][rt]["all"]} | {o["latency_ms"][rt]}ms')
