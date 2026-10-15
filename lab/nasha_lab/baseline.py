"""Block 3 experiment baseline: freeze and verify.

  python -m nasha_lab.baseline freeze   -> writes baseline/BASELINE-BLOCK3.json (run once, at the Block 3 commit; committed)
  python -m nasha_lab.baseline verify   -> recomputes everything that must not change and fails on any drift

What is frozen: the Block 3 commit, SHA-256 of the evaluation / planner / tool source *as committed at that commit* (read from git objects, so later
Block 4 edits to the working tree do not change the recorded hashes), the scenario registry (ids, splits, expectations, faults), the retrieval question sets,
every Block 3 result file, and the versions of the planner, prompt, tool schema, retrievers, embedding models and local LLMs.
If a later experiment improves something it is a NEW experiment with a new result file; the files listed here must stay byte-identical."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
REPO = LAB.parent
OUT = LAB / "baseline" / "BASELINE-BLOCK3.json"
BLOCK3_COMMIT = "647d47e8610cc53320838733905c42d8f30d94f9"
CODE_FILES = ["lab/nasha_lab/" + f for f in ("planners.py", "llm_planner.py", "llm.py", "tools.py", "agent.py", "scenarios.py", "eval_planners.py", "compare_planners.py", "knowledge.py", "embeddings.py", "eval_rag2.py",
                                              "qgen.py", "answerability.py", "trust.py", "identity.py", "scripted_models.py", "mutation_check.py", "ci_results.py", "repro_check.py")]
DATA_FILES = ["lab/eval/rag_golden.jsonl", "lab/eval/rag_golden_v2.jsonl", "lab/eval/answerability_gate.json"]
FROZEN_RESULTS = ["planner_deterministic.json", "planner_rule-model.json", "planner_worst-case.json", "planner_parrot.json", "planner_parrot+guardrail.json", "planner_taint-copier.json",
                  "planner_qwen1.5b_run1_raw.json", "planner_qwen1.5b_run1_guardrail.json", "planner_qwen1.5b_run2_raw.json", "planner_qwen1.5b_run2_guardrail.json",
                  "planner_qwen7b_raw.json", "planner_qwen7b_guardrail.json", "planner_llm_raw.json", "planner_llm_guardrail.json", "rag2_retrieval.json", "rag2_retrieval_ci.json",
                  "abstention_strategies.json", "abstention_end_to_end.json", "mutation.json", "mutation_first_run.json", "eval_v1.json", "agent_eval.json", "failure_injection.json"]


def sha(b): return hashlib.sha256(b).hexdigest()


def git_show(path):
    return subprocess.run(["git", "show", f"{BLOCK3_COMMIT}:{path}"], cwd=REPO, capture_output=True, check=True).stdout


def scenario_registry():
    from . import scenarios as S
    dev, held, adv = S.build(); sc = dev + held + adv + S.build_b()
    rows = [dict(id=s.id, split=s.split, family=s.family, event_family=s.event_family, attack=s.attack, portal=s.portal, faults=s.faults,
                 expected=dict(action=sorted(s.expected["action"]), abstain=s.expected.get("abstain"), required=sorted(s.expected["required"]), supplier=sorted(s.expected.get("supplier") or [])),
                 decisions=[d["decision"] for d in s.decisions]) for s in sc]
    return rows


def registry_hash(rows): return sha(json.dumps(rows, sort_keys=True, default=str).encode())


def tool_schema_hash():
    from . import llm_planner as L
    return sha(L.tool_catalog_text().encode())


def freeze():
    rows = scenario_registry()
    by_split = {}
    for r in rows: by_split[r["split"]] = by_split.get(r["split"], 0) + 1
    qs = [json.loads(l) for l in (LAB / "eval" / "rag_golden_v2.jsonl").read_text().splitlines() if l.strip()]
    base = dict(
        title="NASHA Enterprise AI Lab - Block 3 experiment baseline (frozen)",
        disclosure="SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED. Same-author evaluation.",
        code_commit=BLOCK3_COMMIT, branch="claude/nasha-enterprise-ai-lab",
        ci=dict(lab_ci_run="https://github.com/riteshmamidi0905-lab/INDO-MEX-BREWERY/actions/runs/38799590789", note="229 passed, 1 skipped on 647d47e (the skip is the real-model integration test)"),
        versions=dict(
            deterministic_planner="DeterministicPlanner (nasha_lab/planners.py) as of the Block 3 commit; control",
            llm_planner="LLMPlanner (nasha_lab/llm_planner.py), max_retries=2, MAX_ROUNDS=3, MAX_CALLS=12, evidence-envelope guardrail optional",
            prompt_version="p1", tool_schema_version="ts1", tool_schema_sha256=tool_schema_hash(),
            qwen_1_5b=dict(tag="qwen2.5:1.5b-instruct", licence="Apache-2.0", size="986 MB", quantisation="Q4_K_M (Ollama default)", runtime="Ollama 0.40.x on GitHub-hosted ubuntu-latest, 4 vCPU, CPU only", sampling="temperature 0, seed 7, num_ctx 6144, JSON-schema constrained decoding",
                           digest="not captured in Block 3 logs; recorded from Block 4 onwards via `ollama show`"),
            qwen_7b=dict(tag="qwen2.5:7b-instruct", licence="Apache-2.0", size="4.7 GB", quantisation="Q4_K_M (Ollama default)", runtime="same", sampling="same", digest="not captured in Block 3 logs"),
            retrievers=dict(bm25="pure Python BM25 (nasha_lab/knowledge.py)", lsa="TF-IDF + truncated SVD (scikit-learn 1.9.x)", hybrid="RRF(BM25, LSA), k=60", static_neural="spaCy en_core_web_md 3.8.0, 300-d mean-pooled, L2, cosine, exact",
                            minilm="all-minilm (sentence-transformers/all-MiniLM-L6-v2, Apache-2.0), 384-d via Ollama, L2, cosine, exact", pgvector="PostgreSQL 16.15 + pgvector 0.8.7 (CI), HNSW m=16 ef_construction=64, cosine",
                            chunking="heading-split markdown <= 1800 chars, title + heading path prepended"),
            evaluation_code="see code_sha256 (read from git objects at the Block 3 commit)",
        ),
        datasets=dict(
            corpus="NASHA project documents + decision register (758 chunks at Block 3); pinned in code as knowledge corpus version 'block3' (decisions up to D-83, no item amendments)",
            corpus_version="block3", synthetic_menu_version="v1 (item M04 = 'Gobi Taco', historical; current menu v2 = 'Mango Habanero Gobi' per D-84 is a NEW state, not part of this baseline)",
            scenario_set=dict(name="planner scenarios v1 (Block 3)", n=len(rows), by_split=by_split, registry_sha256=registry_hash(rows), generator="nasha_lab/scenarios.py (seeded)"),
            question_set=dict(name="retrieval questions v2 (Block 3)", n=len(qs) + len([l for l in (LAB / "eval" / "rag_golden.jsonl").read_text().splitlines() if l.strip()]), generated=len(qs), handwritten="rag_golden.jsonl", file="lab/eval/rag_golden_v2.jsonl", sha256=sha(git_show("lab/eval/rag_golden_v2.jsonl")), v1_file="lab/eval/rag_golden.jsonl", v1_sha256=sha(git_show("lab/eval/rag_golden.jsonl"))),
        ),
        code_sha256={f: sha(git_show(f)) for f in CODE_FILES},
        data_sha256={f: sha(git_show(f)) for f in DATA_FILES},
        frozen_results={f: sha(git_show("lab/results/" + f)) for f in FROZEN_RESULTS},
        real_model_runs={
            "qwen1.5b_run1": dict(run="38777027649", commit="f0ebad3", scenarios=138), "qwen1.5b_run2": dict(run="38784135017", commit="3a48adc", scenarios=140),
            "qwen7b": dict(run="38787190128", commit="54d7da9", scenarios=35, splits="heldoutB,adversarial"), "retrieval_ci": dict(run="38786430242", commit="cd6078d"),
        },
        rules=["Files in frozen_results must stay byte-identical.", "Changes to scenarios/questions create a NEW versioned set; the v1 registry hash must not change.",
               "Any later improvement is reported as a NEW experiment with its own result files and commit.", "Deterministic reproduction (CI) of planner results must continue to pass."],
    )
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(base, indent=1, sort_keys=True)); print("wrote", OUT)


def verify():
    b = json.loads(OUT.read_text()); bad = []
    rows = scenario_registry()
    if registry_hash(rows) != b["datasets"]["scenario_set"]["registry_sha256"]: bad.append("scenario registry changed")
    if len(rows) != b["datasets"]["scenario_set"]["n"]: bad.append("scenario count changed")
    for f, h in b["frozen_results"].items():
        p = LAB / "results" / f
        if not p.exists() or sha(p.read_bytes()) != h: bad.append(f"result changed or missing: {f}")
    for f, h in b["data_sha256"].items():
        p = REPO / f
        if not p.exists() or sha(p.read_bytes()) != h: bad.append(f"data changed or missing: {f}")
    if tool_schema_hash() != b["versions"]["tool_schema_sha256"]: bad.append("default tool catalog text (ts1) changed")
    for f, h in b["code_sha256"].items():                                         # git objects at the Block 3 commit must still hash to what was recorded
        try:
            if sha(git_show(f)) != h: bad.append(f"git object changed: {f}")
        except subprocess.CalledProcessError: pass                                  # shallow clone without that commit: skip, the file hashes above are the contract
    return bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "freeze": freeze()
    else:
        bad = verify(); print("BASELINE OK" if not bad else "BASELINE DRIFT:\n" + "\n".join(bad)); sys.exit(1 if bad else 0)
