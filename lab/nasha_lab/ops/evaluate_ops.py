"""Experiment drivers for the Control Center and the reliability matrix. SYNTHETIC / SIMULATED / OFFLINE. Every committed number in lab/results/ops/*.json comes from here.

  python -m nasha_lab.ops.evaluate_ops control        # clean control set: false alerts
  python -m nasha_lab.ops.evaluate_ops faults         # 20 seeded trials per fault type
  python -m nasha_lab.ops.evaluate_ops regression     # evaluation-regression gate trials
  python -m nasha_lab.ops.evaluate_ops gaps           # P2: GAP-01..04, 08..10 experiments
  python -m nasha_lab.ops.evaluate_ops fleet          # simulated operating day -> metrics/incidents/slo/cost/sample traces
  python -m nasha_lab.ops.evaluate_ops all
Counts and rates are deterministic (seeded); wall-clock milliseconds are measurements of this machine and vary run to run."""
import json
import os
import random
import sqlite3
import sys
import time

from .. import identity as ID, tools as T
from . import LABEL, alerts as A, faultlib as FL, faults as F, gate as G, hardening as H, resilience as RS, runner as R, slo as SLO, telemetry as TM, versions as V
from .util import RESULTS_DIR, OPS_DIR, dump_json, load_json, quantile, rate, wilson

EVAL = A.AlertEvaluator()
REF_PATH = os.path.join(RESULTS_DIR, "gate_reference.json")


def out(name): return os.path.join(RESULTS_DIR, name)


def warm():
    R.run_scenario(R.clean_pool()["dev"][0]); FL.degraded_kb(R.shared_kb())      # build the degraded index up front so its construction is not charged to the first retrieval_miss trial


# ======================================================================================================= clean control
def control():
    warm(); pool = R.clean_pool(); scs = pool["heldout"] + pool["heldoutB"]; rows, recs = [], []
    for planner in ("deterministic", "rule-model"):
        for sc in scs:
            rec, ev, env = R.run_scenario(sc, planner); al = EVAL.scan_run_full(ev, rec)
            recs.append(rec); rows.append(dict(scenario=sc.id, planner=planner, family=rec["family"], alerts=[a["rule_id"] for a in al], classes=sorted({a["cls"] for a in al}), run_ms=rec["timing"]["run_ms"]))
    win = []
    for i in range(len(recs)):
        for a in EVAL.scan_window(recs, i): win.append(dict(index=i, rule=a["rule_id"], observed=a.get("observed")))
    fa = [r for r in rows if r["alerts"]]
    by_rule = {}
    for r in rows:
        for a in r["alerts"]: by_rule[a] = by_rule.get(a, 0) + 1
    res = dict(label=LABEL, experiment="clean control set (no faults)", scenarios=len(scs), planners=["deterministic", "rule-model"], runs=len(rows), threshold_calibration_split="dev (56 clean scenarios, 0 alerts)", evaluation_split="heldout + heldoutB clean scenarios",
               runs_with_any_event_or_run_alert=rate(len(fa), len(rows)), false_alerts_by_rule=by_rule, window_alert_evaluations=len(recs), window_alert_firings=len(win), window_firings=win[:20], false_alert_examples=fa[:10],
               run_ms=dict(p50=quantile([r["run_ms"] for r in rows], .5), p95=quantile([r["run_ms"] for r in rows], .95), max=max(r["run_ms"] for r in rows)))
    dump_json(out("control.json"), res); return res


# ======================================================================================================= fault trials
def faults(n=20):
    warm(); res = dict(label=LABEL, experiment="seeded fault injection", trials_per_fault=n, protocol=F.__doc__, faults={}, rows={})
    for f in F.RUN_FAULTS:
        t = time.time(); rows = F.run_trials(f, n); res["faults"][f] = F.summarize(rows, f); res["rows"][f] = rows
        s = res["faults"][f]; print(f, "detect", s["detection"]["k"], "/", s["detection"]["n"], "contain", s["containment"]["k"], "recover", s["recovery"]["k"], "/", s["recovery"]["n"], round(time.time() - t, 1), "s", flush=True)
    # latency spike
    lat = []
    for mag in (10, 25, 50, 100, 200):
        for k in range(4): lat.append(F.latency_trial(1000 * mag + k, mag))
    ctl = [F.latency_trial(9000 + k, 0, with_spike=False) for k in range(20)]
    by_mag = {}
    for r in lat:
        m = by_mag.setdefault(r["spike_per_call_ms"], dict(n=0, detected=0, ttd_runs=[], ttd_ms=[], by_event=0, resolved=[])); m["n"] += 1; m["detected"] += int(bool(r["detected"]))
        if r["detected"]: m["ttd_runs"].append(r["ttd_runs"]); m["ttd_ms"].append(r["ttd_ms"]); m["by_event"] += int(r["detected_by"] == "event")
        if r["resolved_after_runs"] is not None: m["resolved"].append(r["resolved_after_runs"])
    res["faults"]["latency_spike"] = dict(fault="latency_spike", trials=len(lat), detection=rate(sum(1 for r in lat if r["detected"]), len(lat)),
                                           by_magnitude_ms_per_tool_call={k: dict(n=v["n"], detected=v["detected"], median_ttd_runs=quantile(v["ttd_runs"], .5), median_ttd_ms=quantile(v["ttd_ms"], .5), detected_by_event_rule=v["by_event"], median_runs_until_window_clears=quantile(v["resolved"], .5)) for k, v in sorted(by_mag.items())},
                                           false_alert_before_onset=rate(sum(1 for r in lat if r["false_alert_before_onset"]), len(lat)),
                                           clean_sequence_control=dict(sequences=len(ctl), sequences_with_latency_alert=sum(1 for r in ctl if r["any_latency_alert_in_clean_sequence"])),
                                           note="trial = 8 clean runs, 6 runs with +X ms on EVERY tool call, 6 clean runs; windows are runs, not time")
    res["rows"]["latency_spike"] = lat; res["rows"]["latency_clean_control"] = ctl
    dump_json(out("fault_injection.json"), res); return res


def regression(seeds=10):
    ref = load_json(REF_PATH); scs = G.suite(); res = dict(label=LABEL, experiment="injected evaluation regressions vs the frozen reference", suite=G.SUITE_ID, n_scenarios=len(scs), policy=G.POLICY, reference_pass_rate=ref["pass_rate"])
    clean = ref["rows"]; pcache = [_pl(sc) for sc in scs]
    full, timing = {}, {}
    G.run_rows(G.E.FACTORIES["deterministic"], scs)          # warm the per-document-set knowledge-base cache so the timings below measure the gate, not index builds
    for mode in ("no_action", "drop_evidence"):
        t = time.time(); full[mode] = G.run_rows(G.degraded_factory(1.0, 0, mode), scs); timing[mode] = round((time.time() - t) * 1000)
    # equivalence check on a real p<1 run
    p_check = 0.4; real = G.run_rows(G.degraded_factory(p_check, 3, "no_action"), scs)
    asm = []
    for ev, c, f in zip(pcache, clean, full["no_action"]): asm.append(f if G._u(3, ev) < p_check else c)
    res["assembly_equivalence_check"] = dict(p=p_check, seed=3, identical_pass_flags=[bool(a["pass"]) for a in asm] == [bool(r["pass"]) for r in real], identical_actions=[a["action"] for a in asm] == [r["action"] for r in real])
    trials, by_sev = [], {}
    for sev in (0.05, 0.1, 0.2, 0.4, 1.0):
        for mode in ("no_action", "drop_evidence"):
            for seed in range(seeds):
                rows = [full[mode][i] if G._u(seed, pcache[i]) < sev else clean[i] for i in range(len(scs))]
                g = G.evaluate(ref, rows); hit = sum(1 for a, b in zip(rows, clean) if a["pass"] != b["pass"])
                step = None
                for k in range(1, len(rows) + 1):          # first prefix of the suite at which a FAIL reason already holds
                    pre = G.evaluate(dict(ref, rows=ref["rows"]), rows[:k] + clean[k:])
                    if pre["verdict"] == "FAIL": step = k; break
                al = EVAL.scan_gate(g, f"gate:{mode}:{sev}:{seed}")
                trials.append(dict(severity=sev, mode=mode, seed=seed, scenarios_actually_changed=hit, verdict=g["verdict"], detected=g["verdict"] == "FAIL", alert=[a["rule_id"] for a in al], steps_to_detect=step,
                                   est_ms_to_detect=round(timing[mode] * step / len(rows)) if step else None, reasons=g["reasons"], newly_failing=g["newly_failing"]))
    for sev in (0.05, 0.1, 0.2, 0.4, 1.0):
        t = [x for x in trials if x["severity"] == sev]; eff = [x for x in t if x["scenarios_actually_changed"] > 0]
        by_sev[str(sev)] = dict(trials=len(t), detection=rate(sum(x["detected"] for x in t), len(t)), trials_where_nothing_changed=len(t) - len(eff), detection_among_trials_with_a_real_change=rate(sum(x["detected"] for x in eff), len(eff)),
                                missed=[dict(mode=x["mode"], seed=x["seed"], scenarios_actually_changed=x["scenarios_actually_changed"]) for x in t if not x["detected"] and x["scenarios_actually_changed"] > 0],
                                median_steps_to_detect=quantile([x["steps_to_detect"] for x in t if x["steps_to_detect"]], .5))
    named = {}
    for name in ("rule-model", "parrot", "parrot+guardrail", "taint-copier", "worst-case"):
        t = time.time(); g = G.evaluate(ref, G.run_rows(G.E.FACTORIES[name], scs)); named[name] = dict(verdict=g["verdict"], pass_rate=g["pass_rate_candidate"], reasons=g["reasons"], newly_failing=g["newly_failing"], newly_unsafe=g["newly_unsafe"], seconds=round(time.time() - t, 1))
    res.update(full_degradation_run_ms=timing, severity_curve=by_sev, trials=trials, named_candidates=named,
               control=dict(non_regressing_candidates=["rule-model", "parrot+guardrail", "taint-copier"], false_alarms=sum(1 for n in ("rule-model", "parrot+guardrail", "taint-copier") if named[n]["verdict"] == "FAIL"), n=3,
                            note="only three non-regressing candidate implementations exist in this lab, so the gate false-alarm rate is estimated from n=3 and is NOT a tight bound"))
    dump_json(out("regression_gate.json"), res); return res


def _pl(sc):
    w = F.R.S.fresh_world(1, getattr(sc, "menu_version", "v1"), getattr(sc, "po_coverage", "v1")); return dict(payload=sc.setup(w))


# ======================================================================================================= P2 gap experiments
def _clean_action(sc, planner="deterministic"): return F.clean_twin(sc, planner)[0]


def gaps():
    warm(); res = dict(label=LABEL, experiment="P2 reliability gap experiments (sequential runs; NOT a concurrent load test)")
    inv = F.pool(["INVENTORY"]); mixed = F.pool(["INVENTORY", "POLICY"])
    # ---------------- GAP-01 retries / backoff / idempotency
    pol = RS.RetryPolicy(max_attempts=3, base_ms=10, max_ms=40, seed=1); g1 = dict(retry_policy=dict(max_attempts=3, base_ms=10, factor=2.0, max_ms=40, jitter=0.25), nominal_backoff_ms=pol.schedule())
    arms = {"no_retry": None, "retry": pol}; tr = {}
    for arm, rp in arms.items():
        ok = esc = alerts_fired = 0; ms = []; n = 0
        for seed in range(20):
            r = F.rng_for("gap01", seed); sc = r.choice(inv); tools = sorted(set(sc.expected["required"]) - F.EVIDENCE_TOOLS_EXCLUDED)
            if not tools: continue
            tool = r.choice(tools); ca = _clean_action(sc); plan = FL.FaultPlan(transient={tool: dict(fail_first=1, code="TIMEOUT")})
            env = R.make_env(sc, "deterministic", stack=TM.ExecStack(faults=plan, retry=rp, breaker=None)); rid, s = R.drive(env, decisions=[]); rec = env.ops.record(rid); n += 1
            ok += int(rec["action"] == ca); esc += int(F.conservative(rec["action"]) and rec["action"] != ca); ms.append(rec["timing"]["run_ms"])
            alerts_fired += int(any(a["cls"] == "TOOL_TIMEOUT" for a in EVAL.scan_events(env.svc.store.events(rid), rid)))
        tr[arm] = dict(runs=n, action_equals_clean=rate(ok, n), escalated_instead=esc, alert_still_fired=alerts_fired, run_ms_median=quantile(ms, .5))
    g1["transient_timeout_first_attempt_only"] = tr
    br = RS.CircuitBreaker(threshold=3, reset_s=60); codes = []; bst = TM.ExecStack(retry=RS.RetryPolicy(max_attempts=2, base_ms=5, max_ms=10), breaker=br); sc = inv[0]; tool = sorted(set(sc.expected["required"]) - F.EVIDENCE_TOOLS_EXCLUDED)[0]
    for k in range(6):
        env = R.make_env(sc, "deterministic", stack=bst, faults={**dict(sc.faults), tool: "slow"}, timeout_s=0.05); rid, s = R.drive(env, decisions=[]); sm = [x for x in bst.samples if x["run_id"] == rid and x["tool"] == tool][0]
        codes.append(dict(run=k, code=sm["code"], attempts=sm["attempts"], ms=sm["ms"], breaker=br.state(tool)))
    g1["persistent_timeout_with_retry_and_breaker"] = codes
    drafts = {}
    dsc = [s for s in inv if "DRAFT_PURCHASE_RECOMMENDATION" in s.expected["action"]][:10]
    for arm, kw in {"no_retry": dict(), "naive_retry": dict(retry=RS.RetryPolicy(max_attempts=3, base_ms=5, max_ms=10), naive_draft_retry=True), "retry_with_reconcile": dict(retry=RS.RetryPolicy(max_attempts=3, base_ms=5, max_ms=10), reconcile_drafts=True)}.items():
        dup = orphans = ok = n = 0
        for sc in dsc:
            plan = FL.FaultPlan(commit_then_timeout={"draft_purchase_recommendation"}); env = R.make_env(sc, "deterministic", stack=TM.ExecStack(faults=plan, **kw)); rid, s = R.drive(env, decisions=[]); n += 1
            cnt = env.world.q("SELECT COUNT(*) n FROM drafts WHERE kind='PURCHASE_RECOMMENDATION' AND run_id=?", rid)[0]["n"]; dup += int(cnt > 1); orphans += int(cnt >= 1 and (env.ops.record(rid)["action"] or "").startswith("ESCALATE")); ok += int(env.ops.record(rid)["action"] == "DRAFT_PURCHASE_RECOMMENDATION")
        drafts[arm] = dict(runs=n, runs_with_duplicate_drafts=dup, runs_with_orphan_committed_draft_but_escalated=orphans, runs_reaching_the_draft_proposal=ok)
    g1["ambiguous_failure_on_draft_commit_then_timeout"] = drafts
    res["GAP-01"] = g1
    # ---------------- GAP-02 dependency chaos (sequential runs)
    conds = {}
    def chaos(name, mk, n=20, pool_=mixed):
        rows = []
        for seed in range(n):
            r = F.rng_for("gap02" + name, seed); sc = r.choice(pool_); ca = _clean_action(sc); env, kw = mk(sc, seed)
            s = env.ops.start(env.eid, "chaos"); rid = (s.get("run") or {}).get("run_id")
            if rid is None: rows.append(dict(crashed=True)); continue
            rec = env.ops.record(rid); al = EVAL.scan_run_full(env.svc.store.events(rid), rec)
            rows.append(dict(crashed=bool(s.get("crashed")), completed_to_review=bool(s["awaiting_human"]), action_ok=rec["action"] == ca or F.conservative(rec["action"]), safe=rec["safety"]["approval_boundary_ok"] and rec["safety"]["external_actions"] == 0, run_ms=rec["timing"]["run_ms"], classes=sorted({a["cls"] for a in al})))
        conds[name] = dict(runs=n, crashed=sum(r["crashed"] for r in rows), reached_human_review=rate(sum(r.get("completed_to_review", False) for r in rows), n), action_correct_or_conservative=rate(sum(r.get("action_ok", False) for r in rows), n),
                           safety_invariants_held=rate(sum(r.get("safe", False) for r in rows), n), run_ms_p50=quantile([r.get("run_ms") for r in rows if "run_ms" in r], .5), run_ms_p95=quantile([r.get("run_ms") for r in rows if "run_ms" in r], .95), alert_classes=sorted({c for r in rows for c in r.get("classes", [])}))
    chaos("baseline_no_fault", lambda sc, s: (R.make_env(sc, "deterministic"), None))
    chaos("mcp_portal_timeout", lambda sc, s: (R.make_env(sc, "deterministic", portal="timeout"), None), pool_=inv)
    chaos("mcp_portal_error", lambda sc, s: (R.make_env(sc, "deterministic", portal="error"), None), pool_=inv)
    chaos("database_slow_40ms_per_call", lambda sc, s: (R.make_env(sc, "deterministic", stack=TM.ExecStack(faults=FL.FaultPlan(delay_ms={"*": 40}))), None))
    def dbmid(sc, s):
        plan = FL.FaultPlan(); env = R.make_env(sc, "deterministic", stack=TM.ExecStack(faults=plan), flaky_db=True); t = sorted(set(sc.expected["required"]) - F.EVIDENCE_TOOLS_EXCLUDED)
        plan.db_break_on = (env.flaky, t[0]) if t else None
        if not t: env.flaky.broken = True
        return env, None
    chaos("database_locked_mid_run", dbmid)
    def dbdown(sc, s):
        env = R.make_env(sc, "deterministic", flaky_db=True); env.flaky.broken = True; return env, None
    chaos("database_down_at_start", dbdown)
    res["GAP-02"] = dict(conditions=conds, note="sequential runs, one fault per condition, 20 seeded runs each; concurrency, saturation and a real killed process are NOT exercised")
    # ---------------- GAP-03 stale / conflicting documents
    rows = []
    for variant in ("superseded_policy_doc", "unverified_note", "contradictory_canonical"):
        for seed in range(7):
            row, det, env, rid = F.f_stale(seed + 300, variant=variant); rec = env.ops.record(rid); prop = env.ops.summary(rid)["proposal"]
            rows.append(dict(variant=variant, seed=seed, stale_source_cited=row["stale_source_cited"], action=row["containment"]["action"], clean_action=row["containment"]["clean_action"], action_unchanged=row["containment"]["action"] == row["containment"]["clean_action"],
                             abstained=bool(prop.get("abstain")), flagged_by_alert=row["detected"], source_matched=bool(rec["retrieval"]["nonauth_matches"]), citations=prop.get("citations", [])[:4]))
    g3 = {}
    for v in ("superseded_policy_doc", "unverified_note", "contradictory_canonical"):
        t = [r for r in rows if r["variant"] == v]
        g3[v] = dict(n=len(t), stale_source_cited=sum(r["stale_source_cited"] for r in t), action_unchanged=sum(r["action_unchanged"] for r in t), alert_fired=sum(r["flagged_by_alert"] for r in t), source_matched_in_retrieval=sum(r["source_matched"] for r in t))
    res["GAP-03"] = dict(by_variant=g3, rows=rows, note="no conflict DETECTION exists: a contradictory CANONICAL document is handled by ranking (D-54 first), not by noticing the conflict")
    # ---------------- GAP-04 retriever down -> lexical fallback
    arms = {}
    for arm in ("no_fallback", "lexical_fallback"):
        rows = []
        for seed in range(20):
            r = F.rng_for("gap04", seed); sc = r.choice(mixed); ca, crec = F.clean_twin(sc)
            env = R.make_env(sc, "deterministic", kb_wrap="faultable", resilient_kb=(arm == "lexical_fallback"))
            inner = env.kb._kb if arm == "lexical_fallback" else env.kb; inner.fault = "down"
            rid, s = R.drive(env, decisions=[]); rec = env.ops.record(rid); al = EVAL.scan_run_full(env.svc.store.events(rid), rec)
            cites = {c for it in (env.svc.graph.get_state(env.svc._cfg(rid)).values.get("policy") or {}).get("items", []) for c in [x["document_id"] for x in it.get("citations", [])]}
            rows.append(dict(action_equals_clean=rec["action"] == ca, conservative=F.conservative(rec["action"]), retrieval_failed=rec["retrieval"]["miss"], fallback_used=rec["retrieval"]["fallback"], abstained=rec["retrieval"]["abstain"], cites=len(cites), alert=sorted({a["cls"] for a in al})))
        arms[arm] = dict(runs=20, action_equals_clean=rate(sum(r["action_equals_clean"] for r in rows), 20), action_equals_clean_or_conservative=rate(sum(r["action_equals_clean"] or r["conservative"] for r in rows), 20),
                         policy_retrievals_failed=sum(r["retrieval_failed"] for r in rows), runs_using_fallback=sum(1 for r in rows if r["fallback_used"]), runs_with_policy_citation=sum(1 for r in rows if r["cites"]), alert_classes=sorted({c for r in rows for c in r["alert"]}))
    res["GAP-04"] = dict(arms=arms, note="the fallback is BM25 over the same chunks through the same status-aware answer code; a smaller candidate generator can change which sources are found (see retrieval evaluation docs)")
    # ---------------- GAP-08 migration with rollback
    con = sqlite3.connect(":memory:"); m = H.Migrator(con, H.MIGRATIONS); m.migrate(target=1)
    recs = [json.dumps(dict(run_id=f"r{i}", outcome_category="COMPLETED_ACTION", timing=dict(run_ms=10.0 + i))) for i in range(50)]
    con.execute("BEGIN"); [con.execute("INSERT INTO ops_runs VALUES(?,?)", (f"r{i}", j)) for i, j in enumerate(recs)]; con.execute("COMMIT")
    chk = lambda: con.execute("SELECT COUNT(*), SUM(LENGTH(record_json)) FROM ops_runs").fetchone()
    before = chk(); backup = m.backup()
    def bad(c): c.execute("ALTER TABLE ops_runs ADD COLUMN outcome_category TEXT"); raise RuntimeError("injected failure after the DDL")
    mm = H.Migrator(con, [(1, "x", H._m1), (2, "bad migration", bad)])
    try: mm.migrate(); failed = None
    except H.MigrationError as e: failed = str(e)[:200]
    cols_after_fail = [r[1] for r in con.execute("PRAGMA table_info(ops_runs)")]
    ok_applied = H.Migrator(con, H.MIGRATIONS).migrate(); cols_after = [r[1] for r in con.execute("PRAGMA table_info(ops_runs)")]
    backfilled = con.execute("SELECT COUNT(*) FROM ops_runs WHERE run_ms IS NOT NULL").fetchone()[0]
    m.restore(backup); res["GAP-08"] = dict(rows_before=before[0], failed_migration_message=failed, version_after_failed_migration=1 if "outcome_category" not in cols_after_fail else "UNEXPECTED", partial_ddl_left_behind="outcome_category" in cols_after_fail,
                                          data_unchanged_after_failure=chk() == before, then_applied_versions=ok_applied, columns_after_good_migration=cols_after, rows_backfilled=backfilled, restore_from_backup_ok=chk() == before and con.execute("PRAGMA user_version").fetchone()[0] >= 0,
                                          scope="the ops telemetry store only; the lab's world and trace databases are rebuilt from code/seeds and have no migration path")
    # ---------------- GAP-09 secrets
    f, a = H.scan_tree(); res["GAP-09"] = dict(scanned_root="lab/", findings=len(f), finding_detail=f[:10], allowlisted=len(a), allowlisted_rules=sorted({x["rule"] for x in a}), config_boundary=H.config_boundary_report(),
                                              scope="regex scan of text files under lab/; NOT a history scan, NOT entropy-based, NOT a substitute for a managed secret scanner")
    dump_json(out("reliability_gaps.json"), res); return res


# ======================================================================================================= fleet / operating day
SCHEDULE = {}
for i in range(40, 48): SCHEDULE[i] = ("latency_spike", 80)
for k, i in enumerate((60, 61, 62)): SCHEDULE[i] = ("tool_timeout", 100 + k)
SCHEDULE[75] = ("model_timeout", 100)
for k, i in enumerate((90, 91)): SCHEDULE[i] = ("retrieval_miss", 101 + k)
SCHEDULE[105] = ("permission_rejection", 105); SCHEDULE[106] = ("approval_expiry", 106)
for k, i in enumerate((115, 116)): SCHEDULE[i] = ("database_failure", 115 + k)
SCHEDULE[125] = ("malformed_tool_result", 125); SCHEDULE[126] = ("schema_violation", 126); SCHEDULE[127] = ("stale_document", 127)
N_FLEET = 160
FNS = dict(F.RUN_FAULTS)


def _brief(e, t0):
    d = {k: v for k, v in e.items() if k not in ("seq", "ts", "kind", "request_id", "args", "result_summary", "claims", "uncertainties", "mutating_actions", "not_proposed", "scores", "citations")}
    return dict(seq=e["seq"], t_ms=round((e["ts"] - t0) * 1000, 2), kind=e["kind"], **{k: (str(v)[:80]) for k, v in list(d.items())[:5]})


def fleet():
    warm(); reg = V.load_registry(); ver = {k: v for k, v in V.Registry(reg).version_ids().items()}
    rng = random.Random("fleet"); p = R.clean_pool(); allclean = p["dev"] + p["heldout"] + p["heldoutB"]
    registry, logger = TM.MetricsRegistry(), TM.JsonLogger(); recs, events_by_run, ctx_rows, kinds, truth = [], {}, {}, [], []
    for i in range(N_FLEET):
        sched = SCHEDULE.get(i)
        if sched and sched[0] == "latency_spike":
            sc = rng.choice(allclean); plan = FL.FaultPlan(delay_ms={"*": sched[1]}); env = R.make_env(sc, "deterministic", stack=TM.ExecStack(faults=plan), registry=registry, logger=logger, versions=ver); rid, s = R.drive(env); row = None; truth.append("latency_spike")
        elif sched:
            row, det, env, rid = FNS[sched[0]](sched[1]); truth.append(sched[0])
            if rid is None: continue
        else:
            sc = rng.choice(allclean); planner = "rule-model" if i % 2 else "deterministic"; env = R.make_env(sc, planner, registry=registry, logger=logger, versions=ver); rid, s = R.drive(env); row = None; truth.append("clean")
        rec = env.ops.record(rid); rec["versions"] = ver; recs.append(rec); events_by_run[rid] = env.svc.store.events(rid); ctx_rows[rid] = row; TM.observe(registry, rec)
        logger.info("run.recorded", run_id=rid, index=i, outcome_category=rec["outcome_category"], run_ms=rec["timing"]["run_ms"], ground_truth=truth[-1])
    # ---- alerts + incidents
    alerts, per_run = [], {}
    for i, rec in enumerate(recs):
        al = EVAL.scan_run_full(events_by_run[rec["run_id"]], rec); per_run[rec["run_id"]] = al; alerts += al
    incidents = A.make_incidents(alerts)
    for inc in incidents:
        row = ctx_rows.get(inc["subject"]); i = next(k for k, r in enumerate(recs) if r["run_id"] == inc["subject"]); inc["run_index"] = i; inc["ground_truth"] = truth[i]
        if truth[i] == "clean": A.advance(inc, "UNRESOLVED", "FALSE ALERT: the run was a clean control run", step=inc["opened_step"]); continue
        if row:
            c = row["containment"]; A.advance(inc, "CONTAINED" if row["contained"] else "UNRESOLVED", "containment check", f"action {c['action']} (clean action {c['clean_action']}); mutations executed {c['mutations_executed']}; external actions {c['external_actions']}; ungrounded claims {c['ungrounded_claims']}", step=inc["opened_step"] + 1)
            if row["recovered"] is True: A.advance(inc, "RESOLVED", "recovery verified", "fault healed; reviewer asked for more evidence (or equivalent); proposal matches the clean twin", step=None)
            elif row["recovered"] is None: A.advance(inc, "RESOLVED" if row["contained"] else "UNRESOLVED", "no recovery action applicable", row["recovery"].get("note", ""), step=None)
            else: A.advance(inc, "UNRESOLVED", "recovery NOT verified", json.dumps({k: v for k, v in row["recovery"].items() if k != "recovered"})[:160], step=None)
        else: A.advance(inc, "CONTAINED", "latency only: calls completed under their timeouts", "no action was affected", step=None)
    # ---- window alerts as incidents (contiguous firings)
    win_inc, state = [], {}
    for i in range(len(recs)):
        now = {a["rule_id"]: a for a in EVAL.scan_window(recs, i)}
        for rid_, a in now.items():
            if rid_ not in state: state[rid_] = dict(start=i, alert=a, peak=a["observed"])
            else: state[rid_]["peak"] = max(state[rid_]["peak"], a["observed"])
        for rid_ in list(state):
            if rid_ not in now: win_inc.append(_win_inc(state.pop(rid_), i - 1, i, truth));
    for rid_, st in state.items(): win_inc.append(_win_inc(st, len(recs) - 1, None, truth))
    incidents += win_inc
    staged = []
    for idx, (f, seed) in sorted(SCHEDULE.items()):
        if f == "latency_spike": staged.append(dict(index=idx, fault=f, detected=any(w["cls"] == "LATENCY_DEGRADATION" and 40 <= w["run_index"] <= 52 for w in win_inc), by="window rule AR-23 (block of 8 runs reported per run)")); continue
        staged.append(dict(index=idx, fault=f, detected=any(a["cls"] in F.EXPECTED[f] for a in per_run[recs[idx]["run_id"]]), by="event/run rules"))
    clean_idx = [i for i in range(len(recs)) if truth[i] == "clean"]
    fleet_detection = dict(staged_fault_runs=len(staged), staged_detected=sum(x["detected"] for x in staged), staged=staged, clean_runs=len(clean_idx), clean_runs_with_alert=sum(1 for i in clean_idx if per_run[recs[i]["run_id"]]))
    # ---- SLO
    slo_res = SLO.evaluate(recs)
    for b in slo_res["burn_alerts"]:
        i = b["first_run_index"]; incidents.append(dict(incident_id="INC-" + V.sha(f"{b['slo']}|{b['burn_alert']}", 8), cls="SLO_BURN", severity=b["severity"], detection_rule=f"{b['burn_alert']}/{b['slo']}", runbook_id="RB-SLO-BURN", status="RESOLVED" if b["last_run_index"] < len(recs) - 1 else "OPEN",
                                                         subject=f"slo:{b['slo']}", layer="slo", run_index=i, ground_truth=truth[i], timeline=[dict(step=i, t_ms=None, event="DETECTED", detail=f"{b['burn_alert']} fired at run {i}, last firing run {b['last_run_index']}, {b['runs_firing']} runs, peak burn {b['peak_burn']}")], label=LABEL))
    # ---- evaluation regression: the rollback drill
    drill = load_json(out("rollback_drill.json"));
    for inc in drill["incidents"]: inc = dict(inc, run_index=None, ground_truth="evaluation_regression (rollback drill)"); incidents.append(inc)
    incidents.sort(key=lambda x: (x.get("run_index") if x.get("run_index") is not None else 10 ** 6, x["incident_id"]))
    # ---- metrics
    ms = [r["timing"]["run_ms"] for r in recs]; tools = {}
    for r in recs:
        for t, v in r["tools"].items():
            d = tools.setdefault(t, dict(calls=0, ok=0, fail=0, codes={}, ms=[]))
            d["calls"] += v["calls"]; d["ok"] += v["ok"]; d["fail"] += v["fail"]; d["ms"].append(v["ms_max"])
            for c, n in v["codes"].items(): d["codes"][c] = d["codes"].get(c, 0) + n
    tool_tab = {t: dict(calls=d["calls"], success_rate=round(d["ok"] / d["calls"], 4), failures=d["fail"], error_codes=d["codes"], per_run_max_ms_p50=quantile(d["ms"], .5), per_run_max_ms_p95=quantile(d["ms"], .95)) for t, d in sorted(tools.items())}
    cats = {}; appr = {}
    for r in recs: cats[r["outcome_category"]] = cats.get(r["outcome_category"], 0) + 1; appr[r["approval"]["state"]] = appr.get(r["approval"]["state"], 0) + 1
    ret = {k: sum(r["retrieval"][k] for r in recs) for k in ("hit", "abstain", "miss", "fallback")}
    steps = {}
    for r in recs:
        for s in r["timing"]["steps"]: steps.setdefault(s["node"], []).append(s["ms"])
    cost = cost_table(recs)
    tail = recs[-20:]; tail_slo = SLO.evaluate(tail)
    health = dict(whole_day=dict(status="DEGRADED" if any(s["status"] == "BREACHED" for s in slo_res["slos"]) else "HEALTHY", breached=[s["id"] for s in slo_res["slos"] if s["status"] == "BREACHED"]),
                  latest_20_runs=dict(status="DEGRADED" if any(s["status"] == "BREACHED" for s in tail_slo["slos"]) else "HEALTHY", breached=[s["id"] for s in tail_slo["slos"] if s["status"] == "BREACHED"]))
    gate_ref = load_json(REF_PATH); regs = load_json(out("regression_gate.json")) if os.path.exists(out("regression_gate.json")) else None
    metrics = dict(label=LABEL, kind="simulated operating day", runs=len(recs), schedule_note="160 runs; faults staged at fixed indices (see schedule); the rest are clean control runs; planner alternates deterministic / rule-model (scripted stand-in, NOT a language model)",
                   schedule={str(k): v for k, v in sorted(SCHEDULE.items())}, health=health, agent_run_health=dict(outcome_categories=cats, approval_states=appr, operational_success=rate(sum(r["ok"] for r in recs), len(recs))),
                   latency=dict(run_ms=dict(p50=quantile(ms, .5), p95=quantile(ms, .95), max=max(ms)), steps_ms={k: dict(p50=quantile(v, .5), p95=quantile(v, .95)) for k, v in steps.items()}, note="wall-clock of this machine; design target SLO-3 is 600 ms"),
                   tools=tool_tab, retrieval=dict(counts=ret, definition="hit = answered with citations; abstain = INSUFFICIENT VERIFIED EVIDENCE; miss = the retrieval call itself failed"),
                   tokens=dict(prompt=sum(r["planner"]["prompt_tokens"] for r in recs), completion=sum(r["planner"]["completion_tokens"] for r in recs), llm_calls=sum(r["planner"]["llm_calls"] for r in recs), note="scripted stand-in token counts are character/4 estimates, not a tokenizer"),
                   cost=cost, evaluation_regression=dict(gate_suite=G.SUITE_ID, reference_pass_rate=gate_ref["pass_rate"], last_gate_verdict=drill["procedure"][-2]["verdict"] if False else drill["summary"]["post_rollback_gate"], drill=drill["summary"],
                                                          severity_curve={k: v["detection"] for k, v in regs["severity_curve"].items()} if regs else None), slo=slo_res, version=ver,
                   staged_fault_detection=fleet_detection, alerts=dict(total=len(alerts), by_rule={k: sum(1 for a in alerts if a["rule_id"] == k) for k in sorted({a["rule_id"] for a in alerts})}, window_incidents=len(win_inc)),
                   otel_style_instruments=registry.snapshot(), log_lines=len(logger.lines))
    dump_json(out("metrics.json"), metrics); dump_json(out("incidents.json"), dict(label=LABEL, incidents=incidents, taxonomy=A.load_taxonomy()["taxonomy"], count=len(incidents)))
    dump_json(out("slo.json"), slo_res); dump_json(out("cost.json"), cost)
    with open(out("structured_logs_sample.jsonl"), "w") as f:
        for l in logger.lines[:120]: f.write(json.dumps(dict(l, ts=round(l["ts"], 3)), sort_keys=True, default=str) + "\n")
    # ---- sample traces
    picks, seen = [], set()
    for i, r in enumerate(recs):
        t = truth[i]
        if t not in seen: seen.add(t); picks.append((i, r))
    samples = []
    for i, r in picks:
        ev = events_by_run[r["run_id"]]; t0 = ev[0]["ts"]
        samples.append(dict(run_id=r["run_id"], index=i, ground_truth=truth[i], event_id=r["event_id"], family=r["family"], planner=r["planner"]["type"], model=r["planner"]["model"], outcome=r["outcome"], outcome_category=r["outcome_category"], approval_state=r["approval"]["state"],
                            action=r["action"], run_ms=r["timing"]["run_ms"], versions=ver, alerts=[dict(rule=a["rule_id"], cls=a["cls"], severity=a["severity"], step=a["step"]) for a in per_run[r["run_id"]]], events=[_brief(e, t0) for e in ev][:60], events_total=len(ev)))
    dump_json(out("sample_traces.json"), dict(label=LABEL, traces=samples))
    print("fleet", len(recs), "runs", len(incidents), "incidents", health); return metrics


def _win_inc(st, last, cleared, truth):
    a = st["alert"]; first = st["start"]
    return dict(incident_id="INC-" + V.sha(f"{a['rule_id']}|win{first}", 8), cls=a["cls"], severity=a["severity"], detection_rule=a["rule_id"], runbook_id=EVAL.classes[a["cls"]]["runbook"], status="RESOLVED" if cleared is not None else "OPEN", subject=f"window@{first}", layer="window", run_index=first,
                ground_truth=truth[max(0, first - 0)], label=LABEL, timeline=[dict(step=first, t_ms=None, event="DETECTED", detail=f"{a['rule_id']} {a['detail']}"), dict(step=last, t_ms=None, event="PEAK", detail=f"peak observed {st['peak']}"), dict(step=cleared, t_ms=None, event="CLEARED" if cleared is not None else "STILL FIRING", detail="window condition no longer holds" if cleared is not None else "")])


def cost_table(recs):
    ca = load_json(os.path.join(OPS_DIR, "cost-assumptions.json")); rows = []
    def row(src, n, p, c, note):
        return dict(source=src, runs=n, prompt_tokens=p, completion_tokens=c, api_charge_usd=0.0, what_if_hosted={k: round(p / 1e6 * t["input_per_million_tokens"] + c / 1e6 * t["output_per_million_tokens"], 4) for k, t in ca["tiers"].items()}, note=note)
    llm = [r for r in recs if r["planner"]["llm_calls"]]
    rows.append(row("simulated operating day, rule-model stand-in", len(llm), sum(r["planner"]["prompt_tokens"] for r in llm), sum(r["planner"]["completion_tokens"] for r in llm), "scripted stand-in; token counts are chars/4 estimates; no charge"))
    for name, f in (("recorded local qwen2.5 1.5b run (guardrail)", "planner_qwen1.5b_run1_guardrail.json"), ("recorded local qwen2.5 7b run (raw)", "planner_qwen7b_raw.json")):
        d = load_json(os.path.join(os.path.dirname(RESULTS_DIR), f)); o = d["overall"]
        rows.append(row(name, d["n"], o["prompt_tokens"], o["completion_tokens"], f"recorded in results/{f}; local Ollama runtime, no API charge; the hosted figure is a WHAT-IF at ASSUMED prices"))
    return dict(label=LABEL, assumptions=ca, rows=rows)


def main(argv=None):
    a = (argv or sys.argv[1:]) or ["all"]
    for x in (["control", "faults", "regression", "gaps", "fleet"] if a[0] == "all" else a):
        t = time.time(); globals()[x](); print(x, "done", round(time.time() - t, 1), "s", flush=True)


if __name__ == "__main__":
    main()
