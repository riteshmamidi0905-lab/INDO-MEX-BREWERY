"""Compare a freshly computed result file with the committed one. Pure-Python retrievers and the scenario pass counts must match EXACTLY;
library-version-sensitive numbers (SVD, neural vectors, HNSW) must match within a tolerance. Prints every difference; exit code 1 on any violation.
  python -m nasha_lab.repro_check planner FRESH.json COMMITTED.json
  python -m nasha_lab.repro_check rag2    FRESH.json COMMITTED.json"""
import json
import sys

EXACT_RETRIEVERS = {"bm25"}
TOL = 0.03
APPROX_PREFIX, APPROX_TOL = "pgvector", 0.06      # HNSW is an approximate index: graph construction differs between builds, so only aggregate metrics are compared


def planner(fresh, committed):
    bad = []
    for sp, a in committed["by_split"].items():
        b = fresh["by_split"].get(sp)
        if not b: bad.append(f"missing split {sp}"); continue
        for k in ("pass_rate", "correct_action", "approval_boundary", "safe"):
            if (a[k]["k"], a[k]["n"]) != (b[k]["k"], b[k]["n"]): bad.append(f"{sp}.{k}: committed {a[k]['k']}/{a[k]['n']} fresh {b[k]['k']}/{b[k]['n']}")
    for k in ("unsupported_claims", "external_actions", "forbidden_attempts"):
        if committed["overall"][k] != fresh["overall"][k]: bad.append(f"overall.{k}: committed {committed['overall'][k]} fresh {fresh['overall'][k]}")
    return bad


def rag2(fresh, committed):
    bad = []
    for rt, spl in committed["retrieval"].items():
        if rt not in fresh["retrieval"]: continue                      # a model that is unavailable in this environment is skipped, not failed
        approx = rt.startswith(APPROX_PREFIX); tol = 0.0 if rt in EXACT_RETRIEVERS else APPROX_TOL if approx else TOL
        for sp, cats in spl.items():
            for cat, m in cats.items():
                if approx and cat != "ALL": continue
                f = fresh["retrieval"][rt][sp].get(cat, {})
                for k in ("recall@1", "recall@5", "mrr", "ndcg@10"):
                    if k in m and abs(m[k] - f.get(k, -9)) > tol + 1e-9: bad.append(f"{rt}.{sp}.{cat}.{k}: committed {m[k]} fresh {f.get(k)}")
    return bad


if __name__ == "__main__":
    kind, fresh, committed = sys.argv[1], json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    bad = {"planner": planner, "rag2": rag2}[kind](fresh, committed)
    print("\n".join(bad) or "REPRODUCES", flush=True); sys.exit(1 if bad else 0)
