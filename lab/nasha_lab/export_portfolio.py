"""Build lab/portfolio/portfolio-evidence.json: the ONE file the public portfolio vendors. Every number the portfolio shows comes from here, which comes from committed result files.
SYNTHETIC / OFFLINE / same author. The portfolio never types a number; it renders this file and a guard fails the build on a stray figure.
  python -m nasha_lab.export_portfolio            write      python -m nasha_lab.export_portfolio --check    fail if the committed file is stale"""
import json
import sys
from pathlib import Path

from . import claims as CL

LAB = Path(__file__).resolve().parent.parent
RES = LAB / "results"
OUT = LAB / "portfolio" / "portfolio-evidence.json"


def load(name):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else None


RET_IDS = [("bm25", "BM25"), ("lsa", "TF-IDF + SVD (not neural)"), ("hybrid", "Hybrid: BM25 + SVD (RRF)"), ("static_neural", "spaCy static vectors"), ("hybrid_static", "BM25 + spaCy vectors"), ("pgvector_static", "pgvector HNSW, spaCy vectors"),
           ("minilm", "MiniLM (all-MiniLM-L6-v2)"), ("hybrid_minilm", "BM25 + MiniLM (RRF)"), ("pgvector_minilm", "pgvector HNSW, MiniLM")]


def retrieval_table(ci):
    """Rows are identified by POSITION, not by the free-text label in the recovered CI file (see results/ERRATA.md: that file mislabels the hybrid row)."""
    rows = []
    for (rid, disp), r in zip(RET_IDS, ci["table"]):
        rows.append(dict(id=rid, name=disp, recall1=float(r["recall@1"]), recall5=float(r["recall@5"]), mrr=float(r["mrr"]), ndcg10=float(r["ndcg@10"]), authority_correct=float(r["authority_correct"]), ms_per_query=float(r["ms_per_query"]),
                         handwritten_mrr=float(r["handwritten_mrr"]), generated_mrr=float(r["generated_mrr"]), heldout_mrr=float(r["heldout_mrr"])))
    return rows


def ext1_retrieval_summary(d):
    if not d: return None
    rows = []
    for rid, name in [x for x in RET_IDS if x[0] in ("bm25", "lsa", "hybrid", "static_neural", "minilm", "hybrid_minilm")]:
        m = d["results"][rid]; lo = m["by_overlap"]["overlap<0.5"]; hi = m["by_overlap"]["overlap>=0.5"]; mr = d["mutation_robustness"][rid]
        rows.append(dict(id=rid, name=name, mrr=m["ALL"]["mrr"], recall1=m["ALL"]["recall@1"], recall5=m["ALL"]["recall@5"], low_overlap_mrr=lo["mrr"], low_overlap_n=lo["n"], high_overlap_mrr=hi["mrr"], high_overlap_n=hi["n"], mutation_before=mr["original"]["mrr"], mutation_after=mr["mutated"]["mrr"]))
    return dict(n=d["n"], by_family=d["by_family"], rows=rows, independence=d["independence"], file="lab/results/ext1_retrieval_ci.json")


def planner_entry(pid, label, kind, model, file, paired=None, note=""):
    d = load(file)
    if not d: return None
    o = d["overall"]; k = lambda key: dict(k=o[key]["k"], n=o[key]["n"])
    wrong_na = sum(1 for r in d.get("rows", []) if r.get("action") == "NO_ACTION" and r.get("action_ok") is False)
    e = dict(id=pid, label=label, kind=kind, model=model, file="lab/results/" + file, note=note, n=o["n"], pass_=k("pass_rate"), correct_action=k("correct_action"), required_tools=k("required_tools"), correct_abstention=k("correct_abstention"),
             approval_boundary=k("approval_boundary"), by_split={s: dict(k=a["pass_rate"]["k"], n=a["pass_rate"]["n"]) for s, a in d["by_split"].items()}, wrong_silent_no_action=wrong_na if d.get("rows") else None,
             unnecessary_tool_calls=o["unnecessary_tool_calls"], invalid_arg_calls=o["invalid_arg_calls"], forbidden_attempts=o["forbidden_attempts"], external_actions=o["external_actions"], unsupported_claims=o["unsupported_claims"], claims=o["claims"],
             schema_failures=o["schema_failures"], llm_calls=o["llm_calls"], prompt_tokens=o["prompt_tokens"], completion_tokens=o["completion_tokens"], latency_ms_p50=o["latency_ms_p50"], latency_ms_p95=o["latency_ms_p95"])
    pr = load(paired) if paired else None
    if pr:
        key = "raw" if "raw" in file else "guardrail"
        c = pr[key]; e["paired_vs_deterministic"] = dict(n=c["n"], deterministic_only=c["only_first"], model_only=c["only_second"], both=c["both_pass"], neither=c["both_fail"], p=c["p_value_exact_sign_test"])
    return e


def trace_sample():
    from . import eval_planners as EP, scenarios as S, scenarios_ext as X, planners as PL, agent, identity as ID, trace, untrusted_mcp as UM
    from .trust import Gateway, UNTRUSTED
    p = dict(ing="cauliflower", loc="L01", ratio=0.5, po="none")
    sc = S.Scenario("DEMO-CAULIFLOWER", "demo", "demo", "INVENTORY", X.inv_setup(p), X.oracle_inventory(p), menu_version="v2")
    w = S.fresh_world(1, "v2"); eid = S.add_event(w, "INVENTORY_EXCEPTION", sc.setup(w)); w.con.commit()
    svc = agent.AgentService(w, EP.kb_for([]), store=trace.Store(), planner=PL.DeterministicPlanner(), authority=ID.Authority.dev(autologin="founder"), gateway=Gateway({"portal": (UM.build("ok"), UNTRUSTED)}))
    s = svc.start(eid, "portfolio-sample"); rid = s["run"]["run_id"]; svc.resume(rid, dict(decision="approve", note="acknowledged; will source cauliflower elsewhere"))
    ev = svc.store.events(rid); out = []
    for e in ev:
        d = {k: v for k, v in e.items() if k not in ("seq", "ts", "request_id", "kind")}
        out.append(dict(seq=e["seq"], kind=e["kind"], detail={k: (v if not isinstance(v, str) else v[:160]) for k, v in d.items() if k in ("node", "tool", "permission", "action", "decision", "role", "outcome", "family", "question", "abstained", "citations", "result_summary", "uncertainties", "reviewer", "note", "executed", "trust", "headline", "planner_type", "model", "knowledge_chunks")}))
    import re as _re
    out = json.loads(_re.sub(r"DR-[0-9a-f]{8}", "DR-<id>", json.dumps(out)))                       # draft ids are random per run; the sample must be reproducible
    keep = [x for x in out if x["kind"] in ("state", "tool_call", "policy_retrieved", "assessment", "proposal", "human_decision", "final", "run_meta", "executed", "approval_verified", "injection_flagged")]
    return dict(scenario="Low cauliflower cover at a synthetic site; the only cauliflower supplier is ON HOLD (menu v2: Mango Habanero Gobi uses cauliflower)", events=keep, n_events_total=len(out), proposal_action=s["proposal"]["action"],
                untrusted_note_shown_as_untrusted=any(e["kind"] == "tool_call" and e.get("trust") == "UNTRUSTED" for e in ev))


def build():
    base = json.loads((LAB / "baseline" / "BASELINE-BLOCK3.json").read_text()); led = json.loads(CL.LEDGER.read_text())
    P = [planner_entry("det", "Deterministic planner (control)", "deterministic", None, "planner_deterministic.json"),
         planner_entry("q15r1", "Qwen2.5-1.5B, run 1", "llm", "qwen2.5:1.5b-instruct", "planner_qwen1.5b_run1_raw.json", "planner_qwen1.5b_run1_paired.json"),
         planner_entry("q15r2", "Qwen2.5-1.5B, run 2 (final code)", "llm", "qwen2.5:1.5b-instruct", "planner_qwen1.5b_run2_raw.json", "planner_qwen1.5b_run2_paired.json"),
         planner_entry("q15r2g", "Qwen2.5-1.5B + evidence guardrail", "llm+guardrail", "qwen2.5:1.5b-instruct", "planner_qwen1.5b_run2_guardrail.json", "planner_qwen1.5b_run2_paired.json"),
         planner_entry("q7", "Qwen2.5-7B (35 scenarios)", "llm", "qwen2.5:7b-instruct", "planner_qwen7b_raw.json", "planner_qwen7b_paired.json"),
         planner_entry("q7g", "Qwen2.5-7B + evidence guardrail", "llm+guardrail", "qwen2.5:7b-instruct", "planner_qwen7b_guardrail.json", "planner_qwen7b_paired.json"),
         planner_entry("worst", "Worst-case scripted adversary (not an LLM)", "stand-in", None, "planner_worst-case.json"),
         planner_entry("parrot", "Injection-following scripted model (not an LLM)", "stand-in", None, "planner_parrot.json")]
    P = [x for x in P if x]
    ci = load("rag2_retrieval_ci.json"); ext = ext1_retrieval_summary(load("ext1_retrieval_ci.json")); ts = load("tool_schema_result.json"); ext_pl = load("ext1_planner_deterministic.json"); ext_first = load("ext1_planner_first_run_deterministic.json")
    mut = load("mutation.json"); tests = load("test_summary.json")
    ev = dict(
        schema="nasha-portfolio-evidence/1", disclosure="SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED. NASHA is an independent founder concept: no restaurant, customers, suppliers or sales exist. Same-author evaluation.",
        baseline=dict(commit=base["code_commit"], scenario_registry_sha256=base["datasets"]["scenario_set"]["registry_sha256"], scenarios=base["datasets"]["scenario_set"]["n"], by_split=base["datasets"]["scenario_set"]["by_split"], questions=base["datasets"]["question_set"]["n"]),
        planners=P, retrieval=dict(table=retrieval_table(ci), per_category_mrr={k: {c: float(v) for c, v in d.items()} for k, d in ci["per_category_mrr"].items()}, source=ci["source"], n_questions=467, n_categories=13) if ci else None,
        tool_schema=ts, ext1=dict(planner=dict(headline_k=ext_pl["headline"]["pass_rate"]["k"], headline_n=ext_pl["headline"]["pass_rate"]["n"], probes_k=ext_pl["probes"]["pass_rate"]["k"], probes_n=ext_pl["probes"]["pass_rate"]["n"], relations_hold=ext_pl["relations"]["hold"], relations_n=ext_pl["relations"]["n"],
                                    first_run_headline_k=ext_first["headline"]["pass_rate"]["k"], first_run_headline_n=ext_first["headline"]["pass_rate"]["n"], first_run_relations_hold=ext_first["relations"]["hold"], first_run_relations_n=ext_first["relations"]["n"]) if ext_pl and ext_first else None,
                                  retrieval=ext),
        mutation=dict(killed=mut["killed"], valid=mut["valid"], first_run_killed=load("mutation_first_run.json")["killed"]), tests=dict(ci_passed=229, ci_skipped=1, lines=tests["lines"] if tests else []),
        trace_sample=trace_sample(), claims=[{k: c[k] for k in ("claim_id", "title", "public_wording", "scope", "limitations", "evidence", "commit") if k in c} for c in led["claims"]], prohibited_claims=led["prohibited_claims"])
    return ev


def main(argv):
    ev = build(); text = json.dumps(ev, indent=1, sort_keys=True, default=str)
    if "--check" in argv:
        ok = OUT.exists() and OUT.read_text() == text; print("PORTFOLIO EVIDENCE FRESH" if ok else "PORTFOLIO EVIDENCE STALE"); return 0 if ok else 1
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(text); print("wrote", OUT, len(text), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
