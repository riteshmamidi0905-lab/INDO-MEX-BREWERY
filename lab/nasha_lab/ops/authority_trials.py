"""Knowledge authority rules v1 vs v2 on the stale_document fault trials, the GAP-03 set and the clean control pool. SYNTHETIC / SIMULATED / OFFLINE.
Rules, thresholds (SURFACE_COVER 0.20, CONFLICT_COVER 0.35) and polarity patterns were fixed before this script was first run and were not changed afterwards.
Writes results/ops/authority_trials.json."""
import os
from collections import Counter
from . import faults as F, runner as R, alerts as A
from . import LABEL
from .util import RESULTS_DIR, dump_json, rate

EVAL = A.AlertEvaluator()


def _rule_ids(env, rid):
    rec = env.ops.record(rid); ev = env.svc.store.events(rid)
    return sorted({a["rule_id"] for a in EVAL.scan_run_full(ev, rec)}), rec


def stale_trials(rules, seeds, offset=0, variants=None):
    rows = []
    for seed in seeds:
        row, det, env, rid = F.f_stale(seed + offset, variant=(variants or {}).get(seed), authority_rules=rules)
        rules_fired, rec = _rule_ids(env, rid); prop = env.ops.summary(rid)["proposal"] or {}
        rows.append(dict(seed=seed + offset, variant=row["variant"], detected=row["detected"], contained=row["contained"], stale_source_cited=row["stale_source_cited"], action=row["containment"]["action"], clean_action=row["containment"]["clean_action"],
                         action_unchanged=row["containment"]["action"] == row["containment"]["clean_action"], abstained=bool(prop.get("abstain")), rules_fired=rules_fired, source_in_match_list=bool(rec["retrieval"]["nonauth_matches"])))
    return rows


def summarize(rows):
    by = {}
    for r in rows: by.setdefault(r["variant"], []).append(r)
    out = {}
    for v, t in by.items():
        out[v] = dict(n=len(t), detected=sum(r["detected"] for r in t), contained=sum(r["contained"] for r in t), stale_source_cited=sum(r["stale_source_cited"] for r in t), action_unchanged=sum(r["action_unchanged"] for r in t),
                      abstained=sum(r["abstained"] for r in t), detected_by_discriminating_rule_AR26_or_AR27=sum(1 for r in t if {"AR-26", "AR-27"} & set(r["rules_fired"])), rules_fired=dict(Counter(x for r in t for x in r["rules_fired"] if x in ("AR-18", "AR-26", "AR-27"))))
    out["ALL"] = dict(n=len(rows), detected=sum(r["detected"] for r in rows), contained=sum(r["contained"] for r in rows), stale_source_cited=sum(r["stale_source_cited"] for r in rows))
    return out


def control(rules):
    pool = R.clean_pool(); sc_all = pool["heldout"] + pool["heldoutB"]; n = 0; acts = []; fired = Counter(); abst = 0
    for sc in sc_all:
        rec, ev, env = R.run_scenario(sc, "deterministic", authority_rules=rules); n += 1; acts.append((sc.id, rec["action"]))
        for rid_ in {a["rule_id"] for a in EVAL.scan_run_full(ev, rec)}: fired[rid_] += 1
        abst += rec["retrieval"]["abstain"]
    return n, acts, fired, abst


def golden_false_conflicts():
    """Blocking conflicts on the 55 golden RAG questions over the UNMODIFIED corpus (there should be none: no document is injected). dev/test split as in eval_rag."""
    from .. import eval_rag
    from ..knowledge_authority import AuthorityKB
    a = AuthorityKB(R.shared_kb([]), "v2"); rows = eval_rag.load_gold(); out = dict(questions=len(rows), blocking=0, advisory_numeric=0, resolved_status_rule=0, by_split={}, blocking_ids=[])
    for r in rows:
        _ex, cf = a.scan(r["question"]); b = [c for c in cf if c["blocking"]]; sp = out["by_split"].setdefault(r["split"], dict(questions=0, blocking=0)); sp["questions"] += 1
        sp["blocking"] += int(bool(b)); out["blocking"] += int(bool(b)); out["blocking_ids"] += [r["id"]] if b else []
        out["advisory_numeric"] += int(any(c["conflict_type"] == "NUMERIC_DISAGREEMENT_ADVISORY" for c in cf)); out["resolved_status_rule"] += int(any(c["resolved"] and c["conflict_type"] != "NUMERIC_DISAGREEMENT_ADVISORY" for c in cf))
    return out


def latency():
    import time
    from ..knowledge_authority import AuthorityKB
    from ..ops.util import quantile
    kb = R.shared_kb([]); a2 = AuthorityKB(kb, "v2"); qs = ["What is the dietary policy on beef, pork and hidden derivatives such as stock, bouillon, shortening and natural flavors?", "What does the zero-dollar pre-capital build mean for purchasing and spending?",
                                                           "What is the dietary policy for proteins such as goat, lamb and chicken and supplier specifications?", "What is the procedure for handling corrupt or duplicate operational records and quarantine?"]
    for q in qs: kb.ask(q); a2.ask(q)                       # warm both
    t1, t2 = [], []
    for _ in range(25):
        for q in qs:
            t = time.perf_counter(); kb.ask(q); t1.append((time.perf_counter() - t) * 1000); t = time.perf_counter(); a2.ask(q); t2.append((time.perf_counter() - t) * 1000)
    return dict(calls=len(t1), v1_ms=dict(p50=round(quantile(t1, .5), 1), p95=round(quantile(t1, .95), 1)), v2_ms=dict(p50=round(quantile(t2, .5), 1), p95=round(quantile(t2, .95), 1)), note="wall clock, warm, this machine")


V20_FIRST_RUN = dict(note="first run of the rule set BEFORE revision (R2 on any numeral; no 'do not serve' prohibition). Recorded from the first execution of this script; kept because it is a failure that shaped the revision.",
                     clean_control_130_runs=dict(AR_26_false_alerts=58, policy_abstentions_v1=30, policy_abstentions_v2=88, actions_changed=0), golden_55_questions=dict(blocking_conflicts=12, from_R2_numeric=11, from_R1_polarity=1),
                     later_bug_fixed_before_final_run="PERMIT_RE matched 'allowed' inside 'not allowed', making every such sentence MIXED (ignored); fixed by stripping prohibition matches before testing for permit. Golden-question and control results were re-measured after the fix.",
                     causes=["R2 compared sprint numbers and list enumerators ((1), Sprint 22) between D-81 and D-82 and other decisions", "R1 read 'Plain statement allowed ... We do not serve beef or pork' as PERMIT against D-54's beef-free"])


def main():
    from ..knowledge_authority import RULES_VERSION, REVISION
    res = dict(label=LABEL, experiment="authority rules v1 vs v2", rules_version=RULES_VERSION, revision=REVISION, fixed_before_running=dict(SURFACE_COVER=0.20, CONFLICT_COVER=0.35))
    s1 = stale_trials(None, range(20)); s2 = stale_trials("v2", range(20))
    res["stale_document_20_trials"] = dict(v1=summarize(s1), v2=summarize(s2), rows_v1=s1, rows_v2=s2)
    g1 = {}
    for v in ("superseded_policy_doc", "unverified_note", "contradictory_canonical"):
        g1[v] = dict(v1=summarize(stale_trials(None, range(7), 300, {i: v for i in range(7)}))[v], v2=summarize(stale_trials("v2", range(7), 300, {i: v for i in range(7)}))[v])
    res["gap03_set_7_per_variant"] = g1
    n1, a1, f1, ab1 = control(None); n2, a2, f2, ab2 = control("v2")
    changed = [(x[0], x[1], y[1]) for x, y in zip(a1, a2) if x[1] != y[1]]
    res["clean_control"] = dict(runs=n1, v1=dict(alerts_by_rule=dict(f1), policy_abstentions=ab1), v2=dict(alerts_by_rule=dict(f2), policy_abstentions=ab2), runs_where_action_changed=len(changed), changed=changed[:20])
    res["golden_false_conflict_check"] = golden_false_conflicts(); res["latency"] = latency(); res["v2_0_first_run_before_revision"] = V20_FIRST_RUN
    dump_json(os.path.join(RESULTS_DIR, "authority_trials.json"), res); return res


if __name__ == "__main__":
    import json; r = main(); print(json.dumps({k: v for k, v in r.items() if k not in ("stale_document_20_trials",)} | {"stale": {k: r["stale_document_20_trials"][k] for k in ("v1", "v2")}}, indent=1, default=str)[:7000])
