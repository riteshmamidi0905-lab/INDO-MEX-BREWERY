"""EXTERNALIZED / INDEPENDENT-STYLE EVAL v1 (ext1), retrieval part.  SYNTHETIC / OFFLINE / same author: this is NOT independent in the sense of a third party.

What is different from the Block 3 benchmark (rag_golden_v2): a different generation method per family, different seeds, gold labels from authoritative metadata or by construction,
and a lexical-overlap analysis that asks whether the Block 3 ranking (BM25 > MiniLM) survives when the question shares fewer words with its source.
  R1 SUPERSESSION-METADATA   gold = the decision register's own `supersedes` links (authoritative metadata), questions phrased both directions
  R2 TERSE-KEYWORD           3-5 content words sampled from a chunk, accepted only if the gold document is the UNIQUE document containing all of them (validated by construction)
  R3 MUTATED-PARAPHRASE      the 55 hand-written questions under mutation operators (typo, stopword drop, synonym swap, filler, clause move); gold unchanged, so it measures robustness
Candidate generation by an external model was NOT used (no free model reachable in the authoring sandbox); nothing here is labelled by a model.
The Block 3 corpus is pinned (version 'block3'), so results are comparable with rag2_retrieval*.json.   python -m nasha_lab.eval_ext1 OUT.json"""
import json
import os
import random
import re
import sys
import zlib

from . import knowledge as K
K.use_version("block3")

from . import eval_rag2 as E2

SEED = 9100
STOP = K.STOP
SYN = {"decision": "ruling", "decided": "ruled", "policy": "rule", "rules": "policy", "allowed": "permitted", "permitted": "allowed", "menu": "dish list", "beer": "brew", "beers": "brews", "supplier": "vendor", "suppliers": "vendors",
       "current": "present", "binding": "mandatory", "what": "which", "status": "standing", "founder": "owner", "name": "title", "price": "cost", "safe": "secure", "served": "offered", "ingredients": "components"}


def content_tokens(text): return [t for t in K.tokenize(text) if t not in STOP and len(t) > 2]


def overlap(question, chunk_text):
    q = set(content_tokens(question)); c = set(K.tokenize(chunk_text))
    return len(q & c) / len(q) if q else 0.0


# ---------------------------------------------------------------- generators
def r1_supersession(kb):
    out = []
    for c in kb.chunks.values():
        if c["document_type"] != "DECISION": continue
        for old in filter(None, c["supersedes"].split("|")):
            if old not in kb.chunks: continue
            out.append(dict(id=f"X1-{c['document_id']}-{old}-a", category="SUPERSEDED", question=f"Which decision replaced {old}?", gold_docs=[c["document_id"]], expected_status="CURRENT", family="R1_supersession_metadata"))
            out.append(dict(id=f"X1-{c['document_id']}-{old}-b", category="SUPERSEDED", question=f"Does {c['document_id']} change what {old} said, and which of the two is in force?", gold_docs=[c["document_id"], old], expected_status="CURRENT", family="R1_supersession_metadata"))
    return out


def r2_terse(kb, n=120):
    rng = random.Random(SEED); docs = {}
    for c in kb.chunks.values():
        if c["effective_status"] in K.AUTHORITATIVE and len(c["text"]) > 120: docs.setdefault(c["document_id"], []).append(c)
    toks_by_doc = {d: set().union(*[set(K.tokenize(x["text"])) for x in cs]) for d, cs in docs.items()}
    out = []; ids = sorted(docs); rng.shuffle(ids)
    for d in ids:
        if len(out) >= n: break
        c = rng.choice(docs[d]); pool = [t for t in dict.fromkeys(content_tokens(c["text"])) if not t.startswith("d-") and not t.isdigit() and len(t) > 3]
        if len(pool) < 8: continue
        for _try in range(25):
            ws = rng.sample(pool, rng.choice([3, 4, 5])); need = set(ws)
            holders = [x for x, ts in toks_by_doc.items() if need <= ts]
            if holders == [d]:
                out.append(dict(id=f"X2-{len(out):03d}", category="DIRECT", question=" ".join(ws), gold_docs=[d], expected_status=docs[d][0]["effective_status"], family="R2_terse_keyword")); break
    return out


def mutate(q, rng):
    ws = q.rstrip("?.! ").split(); ops = []
    def typo(w):
        if len(w) < 5: return w
        i = rng.randrange(1, len(w) - 1); return w[:i] + w[i + 1] + w[i] + w[i + 2:]
    kind = rng.choice(["typo", "stop", "syn", "filler", "move"])
    if kind == "typo": i = rng.randrange(len(ws)); ws[i] = typo(ws[i])
    elif kind == "stop": ws = [w for w in ws if w.lower() not in STOP] or ws
    elif kind == "syn": ws = [SYN.get(w.lower(), w) for w in ws]
    elif kind == "filler": ws = ["please", "tell", "me", "quickly:"] + ws
    else:
        if len(ws) > 5: ws = ws[len(ws) // 2:] + ws[:len(ws) // 2]
    return " ".join(ws) + "?", kind


def r3_mutated():
    rng = random.Random(SEED + 1); out = []
    for r in [r for r in E2.load() if r.get("source") == "handwritten" and r["gold_docs"]]:
        for j in range(3):
            q, kind = mutate(r["question"], rng)
            if q != r["question"] + "": out.append(dict(id=f"X3-{r['id']}-{j}", category=r["category"], question=q, gold_docs=r["gold_docs"], expected_status=r["expected_status"], family="R3_mutated_paraphrase", mutation=kind, base_id=r["id"], base_question=r["question"]))
    return out


def build(kb):
    return r1_supersession(kb) + r2_terse(kb) + r3_mutated()


# ---------------------------------------------------------------- evaluation
def best_overlap(kb, row):
    return max((overlap(row["question"], c["text"]) for c in kb.chunks.values() if c["document_id"] in row["gold_docs"]), default=0.0)


def bins(rows, kb):
    for r in rows: r["overlap"] = round(best_overlap(kb, r), 3)
    return rows


def metrics_by(rows, ranks, key):
    out = {}
    for v in sorted({key(r) for r in rows}, key=str):
        out[str(v)] = E2.retrieval_metrics([r for r in rows if key(r) == v], ranks)
    return out


def run(kb=None, with_models=True, pg_dsn=None, retrievers=None):
    kb = kb or K.default_kb("block3"); info = E2.build_retrievers(kb, with_models, pg_dsn)
    rows = bins(build(kb), kb); v2 = bins([r for r in E2.load() if r["gold_docs"]], kb)
    names = retrievers or [n for n in ("bm25", "lsa", "hybrid", "static_neural", "hybrid_static", "pgvector_static", "minilm", "hybrid_minilm", "pgvector_minilm") if n in kb.retrievers and kb.retrievers[n] is not None or n in ("bm25", "lsa", "hybrid")]
    low = lambda r: "overlap<0.5" if r["overlap"] < 0.5 else "overlap>=0.5"
    out = dict(name="EXTERNALIZED / INDEPENDENT-STYLE EVAL v1 (retrieval)", independence="structurally different generation, same author; not third-party", n=len(rows), by_family={f: sum(1 for r in rows if r["family"] == f) for f in sorted({r["family"] for r in rows})},
               retriever_info=info, results={}, v2_overlap_bins={}, mutation_robustness={})
    for rt in names:
        ranks = {r["id"]: E2.rank_docs(kb, r["question"], rt) for r in rows}; ranks2 = {r["id"]: E2.rank_docs(kb, r["question"], rt) for r in v2}
        out["results"][rt] = dict(ALL=E2.retrieval_metrics(rows, ranks), by_family=metrics_by(rows, ranks, lambda r: r["family"]), by_overlap=metrics_by(rows, ranks, low))
        out["v2_overlap_bins"][rt] = metrics_by(v2, ranks2, low)
        base = {r["id"]: E2.rank_docs(kb, r["base_question"], rt) for r in rows if r["family"] == "R3_mutated_paraphrase"}
        r3 = [r for r in rows if r["family"] == "R3_mutated_paraphrase"]
        out["mutation_robustness"][rt] = dict(original=E2.retrieval_metrics([dict(r, id=r["id"]) for r in r3], {r["id"]: base[r["id"]] for r in r3}), mutated=E2.retrieval_metrics(r3, ranks),
                                              by_mutation=metrics_by(r3, ranks, lambda r: r["mutation"]))
    out["questions_sample"] = [dict(id=r["id"], family=r["family"], question=r["question"], gold_docs=r["gold_docs"], overlap=r["overlap"]) for r in rows[:6] + rows[-4:]]
    out["review_note"] = "Gold labels come from register metadata (R1), uniqueness-validated construction (R2) and the unchanged hand-written labels (R3). No model labelled anything. A manual-review sheet is in results/ext1_review_sheet.csv for the founder (optional)."
    return out, rows


if __name__ == "__main__":
    pg = os.environ.get("NASHA_PG_DSN")
    o, rows = run(with_models=os.environ.get("NASHA_EXT_MODELS", "0") == "1", pg_dsn=pg)
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(o, indent=1))
    print("EXT1", o["n"], o["by_family"])
    for rt, m in o["results"].items():
        a = m["ALL"]; lo = m["by_overlap"].get("overlap<0.5", {}); hi = m["by_overlap"].get("overlap>=0.5", {})
        print(f'EXT1 {rt:14s} MRR {a["mrr"]} R@1 {a["recall@1"]} R@5 {a["recall@5"]} | low-overlap MRR {lo.get("mrr")} (n={lo.get("n")}) high-overlap MRR {hi.get("mrr")} (n={hi.get("n")}) | v2 bins {json.dumps({k: (v["mrr"], v["n"]) for k, v in o["v2_overlap_bins"][rt].items()})} | mutation {o["mutation_robustness"][rt]["original"]["mrr"]}->{o["mutation_robustness"][rt]["mutated"]["mrr"]}')
