"""Version registry + rollback drill (P1 item 3). SYNTHETIC / OFFLINE EVALUATION.
A 'version' pins everything that can change agent behaviour: planner id, prompt hash, tool-schema version/hash, knowledge-corpus version/hash and a reference
to the evaluation snapshot it was judged on. The registry is a committed JSON file; a test recomputes the live hashes and fails if code or corpus drifted
without a new registered version (change management by construction)."""
import inspect
import json
import os
import time

from .. import eval_planners as E, knowledge as K, llm_planner as LP, planners as PL, tools as T
from . import LABEL, gate as G
from .util import OPS_DIR, RESULTS_DIR, dump_json, load_json, sha

REGISTRY_PATH = os.path.join(OPS_DIR, "version-registry.json")

# factory key -> (how the planner is built, human description). The key is what a version's `factory` names.
FACTORIES = {"deterministic": E.FACTORIES["deterministic"], "rule-model": E.FACTORIES["rule-model"], "parrot": E.FACTORIES["parrot"], "worst-case": E.FACTORIES["worst-case"]}


def tool_schema_hash(): return sha(T.tool_catalog(exposed_only=False), 12)


def prompt_hash(factory_key):
    """LLM planners: hash of the system prompt, the catalog text and the prompt-building code. Deterministic planner has no prompt: hash of its decision logic."""
    if factory_key == "deterministic":
        return "logic-" + sha(inspect.getsource(PL.deterministic_decide) + inspect.getsource(PL.DeterministicPlanner.collect), 12)
    return "prompt-" + sha(LP.SYSTEM + LP.tool_catalog_text() + inspect.getsource(LP.LLMPlanner.collect) + inspect.getsource(LP.LLMPlanner.decide), 12)


def corpus_hash(version="block3"):
    kb = K.default_kb(version); return "corpus-" + sha(sorted((c["chunk_id"], sha(c["text"], 8)) for c in kb.chunks.values()), 12)


def live_fingerprint(factory_key, corpus="block3"):
    return dict(prompt_hash=prompt_hash(factory_key), tool_schema_version=tool_schema_hash(), prompt_version=PL.PROMPT_VERSION, corpus_version=corpus, corpus_hash=corpus_hash(corpus))


def describe(version_id, factory_key, planner_id, note, eval_snapshot, status="CANDIDATE"):
    return dict(version_id=version_id, planner_id=planner_id, factory=factory_key, **live_fingerprint(factory_key), eval_snapshot=eval_snapshot, status=status, note=note)


def build_registry(reference=None):
    ref = reference or G.load_reference()
    ev = lambda verdict, pr, extra="": dict(suite=G.SUITE_ID, reference_rows_sha=ref["rows_sha"], gate_verdict=verdict, pass_rate=pr, note=extra)
    vs = [describe("v1", "deterministic", "deterministic@d1", "Block 3 control planner (rules over evidence). Frozen reference of the regression gate.", ev("REFERENCE", ref["pass_rate"], "the gate reference itself"), "ACTIVE"),
          describe("v2", "rule-model", "llm+rule-model-stand-in@s1/ts1", "Scripted rule-based stand-in behind the LLM-planner interface; NOT a language model. Equivalent behaviour, different implementation: a no-regression control.", ev("PASS", None, "filled by `versions register`")),
          describe("v3", "parrot", "llm+parrot-stand-in@s1/ts1", "Scripted stand-in that obeys instructions found in data (injection-susceptible). A realistic bad candidate: regresses the adversarial split.", ev("FAIL", None, "filled by `versions register`")),
          dict(version_id="v4-recorded", planner_id="llm+ollama qwen2.5:1.5b (recorded)", factory=None, prompt_hash="prompt-recorded", tool_schema_version="ts1", prompt_version="p1", corpus_version="block3", corpus_hash=None,
               eval_snapshot=dict(path="results/planner_qwen1.5b_run1_guardrail.json", suite="Block 3 full 138-scenario recorded run", gate_verdict="NOT RUN", note="recorded real-model result from a local Ollama run in an earlier block; not re-run here (no local LLM runtime); the gate suite differs, so no gate verdict is claimed"),
               status="RECORDED_ONLY", note="Listed so the registry shows what was evaluated offline; it cannot be activated or drilled here.")]
    # run the gate for the two candidates so the snapshot references are measured, not typed
    for v in vs[1:3]:
        rows = G.run_rows(FACTORIES[v["factory"]]); res = G.evaluate(ref, rows)
        v["eval_snapshot"].update(gate_verdict=res["verdict"], pass_rate=res["pass_rate_candidate"], reasons=res["reasons"], note="measured by `python -m nasha_lab.ops.versions register`")
    return dict(registry_version="version-registry-v1", label=LABEL, versions=vs, active="v1", history=[dict(seq=1, action="register", version="v1"), dict(seq=2, action="activate", version="v1")])


def load_registry(path=REGISTRY_PATH): return load_json(path)


class Registry:
    def __init__(self, data): self.d = data
    @property
    def active(self): return next(v for v in self.d["versions"] if v["version_id"] == self.d["active"])
    def get(self, vid): return next(v for v in self.d["versions"] if v["version_id"] == vid)

    def activate(self, vid, reason=""):
        v = self.get(vid)
        if v["factory"] is None: raise ValueError(f"{vid} is RECORDED_ONLY and cannot be activated")
        prev = self.d["active"]; self.d["active"] = vid
        self.d["history"].append(dict(seq=len(self.d["history"]) + 1, action="activate", version=vid, previous=prev, reason=reason)); return prev

    def planner_factory(self): return FACTORIES[self.active["factory"]]
    def version_ids(self): return dict(version_id=self.active["version_id"], planner_id=self.active["planner_id"], prompt_hash=self.active["prompt_hash"], tool_schema_version=self.active["tool_schema_version"], corpus_version=self.active["corpus_version"])


def drift(registry):
    """Compare live fingerprints with the registered ones. Returns a list of human-readable drift findings (empty = consistent)."""
    out = []
    for v in registry["versions"]:
        if not v.get("factory"): continue
        live = live_fingerprint(v["factory"], v["corpus_version"])
        for k in ("prompt_hash", "tool_schema_version", "corpus_hash"):
            if live[k] != v[k]: out.append(f"{v['version_id']}: {k} registered {v[k]} but live {live[k]}")
    return out


# ======================================================================================================= rollback drill
def rollback_drill(reference=None, registry=None, bad="v3", good="v1", safe_candidate="v2", k_post=6):
    """Switch to a candidate, run the regression gate, roll back on FAIL, re-run the gate, and confirm live behaviour. Every number is measured here."""
    from . import alerts as A, runner as R
    ref = reference or G.load_reference(); reg = Registry(registry or load_registry()); log = []
    def step(name, **kw): log.append(dict(step=len(log) + 1, name=name, **kw)); return log[-1]
    t_all = time.perf_counter()
    # 0. baseline sanity
    t = time.perf_counter(); rows = G.run_rows(reg.planner_factory()); g0 = G.evaluate(ref, rows)
    step("baseline gate on the active version", version=reg.active["version_id"], verdict=g0["verdict"], pass_rate=g0["pass_rate_candidate"], ms=round((time.perf_counter() - t) * 1000))
    # 1. positive control: a safe candidate is allowed to promote
    t = time.perf_counter(); prev = reg.activate(safe_candidate, "promote candidate after gate"); rows = G.run_rows(reg.planner_factory()); gs = G.evaluate(ref, rows)
    step("switch to a safe candidate and run the gate", version=safe_candidate, verdict=gs["verdict"], pass_rate=gs["pass_rate_candidate"], decision="KEEP" if gs["verdict"] == "PASS" else "ROLLBACK", ms=round((time.perf_counter() - t) * 1000))
    if gs["verdict"] != "PASS": reg.activate(good, "rollback: safe candidate failed gate")
    else: reg.activate(good, "drill: return to baseline before the bad-candidate step")
    # 2. the drill proper
    t = time.perf_counter(); reg.activate(bad, "promote candidate after gate (drill: expected to fail)"); rows = G.run_rows(reg.planner_factory()); gb = G.evaluate(ref, rows)
    t_detect = round((time.perf_counter() - t) * 1000)
    step("switch to the bad candidate and run the gate", version=bad, verdict=gb["verdict"], pass_rate=gb["pass_rate_candidate"], reasons=gb["reasons"], newly_failing=gb["newly_failing"], ms=t_detect)
    alerts = A.AlertEvaluator().scan_gate(gb, subject=f"gate:{bad}"); incs = A.make_incidents(alerts) if alerts else []
    step("alert evaluation", alerts=[a["rule_id"] for a in alerts], incident=[i["incident_id"] for i in incs], runbook=[i["runbook_id"] for i in incs])
    rolled = gb["verdict"] == "FAIL"
    t = time.perf_counter()
    if rolled: reg.activate(good, "ROLLBACK: regression gate failed for " + bad)
    t_rb = round((time.perf_counter() - t) * 1000, 3)
    step("rollback (registry switch)", active=reg.active["version_id"], ms=t_rb)
    t = time.perf_counter(); rows = G.run_rows(reg.planner_factory()); ga = G.evaluate(ref, rows)
    step("re-run the gate after rollback", version=reg.active["version_id"], verdict=ga["verdict"], pass_rate=ga["pass_rate_candidate"], ms=round((time.perf_counter() - t) * 1000))
    # 3. live behaviour after rollback: real instrumented runs on the active version
    pool = R.clean_pool()["heldout"][:k_post]; outs = []
    for sc in pool:
        rec, ev_, env = R.run_scenario(sc, "deterministic"); outs.append(dict(scenario=sc.id, completed=rec["ok"], action=rec["action"], expected=sorted(sc.expected["action"]), action_ok=rec["action"] in sc.expected["action"]))
    step("post-rollback live runs", n=len(outs), all_completed=all(o["completed"] for o in outs), actions_ok=sum(o["action_ok"] for o in outs))
    for i in incs:
        A.advance(i, "CONTAINED", "candidate not promoted: gate FAIL blocks promotion", step=len(log)); A.advance(i, "RESOLVED", f"rolled back to {good}; gate re-run verdict {ga['verdict']}", step=len(log))
    return dict(drill="rollback-drill-1", label=LABEL, procedure=log, registry_active_after=reg.active["version_id"], registry_history=reg.d["history"], incidents=incs,
                summary=dict(gate_caught_bad_candidate=gb["verdict"] == "FAIL", safe_candidate_allowed=gs["verdict"] == "PASS", rolled_back_to=reg.active["version_id"], post_rollback_gate=ga["verdict"],
                             time_to_detect_ms=t_detect, time_to_rollback_ms=t_rb, post_rollback_actions_ok=f"{sum(o['action_ok'] for o in outs)}/{len(outs)}"), post_rollback_runs=outs)


def main(argv=None):
    import sys
    a = argv or sys.argv[1:]
    if a and a[0] == "register":
        dump_json(REGISTRY_PATH, build_registry()); print("registry written", REGISTRY_PATH)
    elif a and a[0] == "drift":
        d = drift(load_registry()); print("\n".join(d) or "no drift"); sys.exit(1 if d else 0)
    elif a and a[0] == "drill":
        res = rollback_drill(); dump_json(os.path.join(RESULTS_DIR, "rollback_drill.json"), res); print(json.dumps(res["summary"], indent=1))
    else: print("usage: python -m nasha_lab.ops.versions register|drift|drill")


if __name__ == "__main__":
    main()
