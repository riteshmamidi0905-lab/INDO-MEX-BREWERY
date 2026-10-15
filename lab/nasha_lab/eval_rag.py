"""RAG evaluation on the author-written golden set (eval/rag_golden.jsonl). OFFLINE, same-author, small (n~55): descriptive, not proof."""
import json
import math
import os
import sys
import time

from . import knowledge as K

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(HERE, "..", "eval", "rag_golden.jsonl")


def load_gold():
    rows = [json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip()]
    for r in rows: r["split"] = "test" if int(r["id"][1:]) % 10 in (2, 5, 8) else "dev"
    return rows


def doc_ranking(kb, question, retriever, status_aware=False):
    seen, order = set(), []
    for h in kb.search(question, k=60, retriever=retriever, status_aware=status_aware, include_nonauthoritative=True, candidates=80):
        if h["document_id"] not in seen: seen.add(h["document_id"]); order.append(h["document_id"])
    return order


def retrieval_metrics(kb, rows, retriever):
    qs = [r for r in rows if r["gold_docs"]]
    out = {"n": len(qs)}
    for k in (1, 3, 5, 10):
        out[f"recall@{k}"] = round(sum(len(set(doc_ranking_cache[(r['id'], retriever)][:k]) & set(r["gold_docs"])) / len(r["gold_docs"]) for r in qs) / len(qs), 3)
    mrr = ndcg = 0.0
    for r in qs:
        rk = doc_ranking_cache[(r["id"], retriever)]; g = set(r["gold_docs"])
        pos = [i for i, d in enumerate(rk, 1) if d in g]
        mrr += 1 / pos[0] if pos else 0
        dcg = sum(1 / math.log2(i + 1) for i in pos if i <= 10); idcg = sum(1 / math.log2(i + 1) for i in range(1, min(len(g), 10) + 1))
        ndcg += dcg / idcg
    out["mrr"] = round(mrr / len(qs), 3); out["ndcg@10"] = round(ndcg / len(qs), 3)
    return out


doc_ranking_cache = {}


def contamination(kb, rows, retriever, status_aware):
    """Share of the top-5 chunks that are NOT authoritative (superseded, unverified, vision, historical, pending), over answerable questions."""
    n = bad = 0
    for r in rows:
        if not r["answerable"]: continue
        hits = kb.search(r["question"], k=5, retriever=retriever, status_aware=status_aware, include_nonauthoritative=not status_aware)
        n += len(hits); bad += sum(h["effective_status"] in K.NOT_AUTHORITATIVE for h in hits)
    return round(bad / max(1, n), 3)


def ask_metrics(kb, rows, retriever):
    m = dict(abst_ok=0, abst_n=0, cite_hit=0, cite_n=0, cite_prec=0.0, status_viol=0, notcite_viol=0, contain_viol=0, false_answer=0, unans_n=0, ungrounded=0, answers=0, lat=[])
    fails = []
    for r in rows:
        t = time.perf_counter(); a = kb.ask(r["question"], retriever=retriever); m["lat"].append(time.perf_counter() - t)
        want_abs = r["must_abstain"]
        m["abst_n"] += 1; ok = a["abstained"] == want_abs; m["abst_ok"] += ok
        if not ok: fails.append((r["id"], "abstention", "wanted abstain" if want_abs else "wanted answer", a["answer"][:80]))
        if not r["answerable"]:
            m["unans_n"] += 1; m["false_answer"] += (not a["abstained"])
        if a["abstained"]: continue
        m["answers"] += 1
        cited = [c["document_id"] for c in a["citations"]]
        if r["gold_docs"]:
            m["cite_n"] += 1; hit = any(c in r["gold_docs"] for c in cited); m["cite_hit"] += hit
            m["cite_prec"] += sum(c in r["gold_docs"] for c in cited) / len(cited)
            if not hit: fails.append((r["id"], "citation", cited, r["gold_docs"]))
        bad = [c for c in a["citations"] if c["effective_status"] in K.NOT_AUTHORITATIVE]
        if bad: m["status_viol"] += 1; fails.append((r["id"], "status", [c["effective_status"] for c in bad]))
        nc = [c for c in cited if c in r["must_not_cite"]]
        if nc: m["notcite_viol"] += 1; fails.append((r["id"], "must_not_cite", nc))
        if any(x.lower() in a["answer"].lower() for x in r["must_not_contain"]): m["contain_viol"] += 1; fails.append((r["id"], "must_not_contain", a["answer"][:80]))
        text = " ".join(kb.chunks[c["chunk_id"]]["text"].replace("\n", " ") for c in a["citations"])
        sents = a.get("answer_sentences") or [a["answer"]]
        if not all(s in text for s in sents): m["ungrounded"] += 1
    lat = sorted(m.pop("lat"))
    res = dict(abstention_accuracy=round(m["abst_ok"] / m["abst_n"], 3),
               citation_hit_rate=round(m["cite_hit"] / max(1, m["cite_n"]), 3), citation_precision=round(m["cite_prec"] / max(1, m["cite_n"]), 3),
               status_violations=m["status_viol"], must_not_cite_violations=m["notcite_viol"], must_not_contain_violations=m["contain_viol"],
               unsupported_answer_rate_on_unanswerable=round(m["false_answer"] / max(1, m["unans_n"]), 3), ungrounded_answers=m["ungrounded"],
               p50_ms=round(1000 * lat[len(lat) // 2], 1), p95_ms=round(1000 * lat[int(len(lat) * .95)], 1), n=m["abst_n"])
    return res, fails


def run_all(kb=None, retrievers=("tfidf", "bm25", "hashing", "lsa", "hybrid", "hybrid_hash")):
    kb = kb or K.default_kb(); rows = load_gold()
    for rt in retrievers:
        for r in rows: doc_ranking_cache[(r["id"], rt)] = doc_ranking(kb, r["question"], rt)
    out = {"synthetic_scope": "author-written golden set over the real NASHA corpus; same-author; n=%d" % len(rows), "corpus_chunks": len(kb.chunks), "retrieval": {}, "ask": {}, "contamination_top5": {}, "failures": {}}
    for rt in retrievers:
        out["retrieval"][rt] = {sp: retrieval_metrics(kb, [r for r in rows if sp == "all" or r["split"] == sp], rt) for sp in ("all", "dev", "test")}
        out["contamination_top5"][rt] = {"status_blind": contamination(kb, rows, rt, False), "status_aware": contamination(kb, rows, rt, True)}
        res, fails = ask_metrics(kb, rows, rt); out["ask"][rt] = res; out["failures"][rt] = fails
    return out


if __name__ == "__main__":
    o = run_all()
    path = sys.argv[1] if len(sys.argv) > 1 else None
    s = json.dumps(o, indent=1, default=str)
    if path: open(path, "w").write(s)
    for rt in o["retrieval"]:
        r = o["retrieval"][rt]["all"]; a = o["ask"][rt]
        print(f'{rt:12s} R@1 {r["recall@1"]} R@5 {r["recall@5"]} R@10 {r["recall@10"]} MRR {r["mrr"]} nDCG {r["ndcg@10"]} | contam {o["contamination_top5"][rt]} | abst {a["abstention_accuracy"]} citHit {a["citation_hit_rate"]} citPrec {a["citation_precision"]} statusV {a["status_violations"]} noCite {a["must_not_cite_violations"]} contain {a["must_not_contain_violations"]} falseAns {a["unsupported_answer_rate_on_unanswerable"]} p95 {a["p95_ms"]}ms')
