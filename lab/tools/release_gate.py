#!/usr/bin/env python3
"""Release gate (D-89 Milestone E). Computes PASS / FAIL / REQUIRES_REVIEW from machine-readable evidence; a missing required item is never a pass.

    python3 tools/release_gate.py collect [--junit PATH] [--out DIR]   # run the suite + evaluation + reproducibility checks, write the evidence bundle
    python3 tools/release_gate.py check   [--evidence DIR]             # evaluate the bundle, write release-gate-report.json and release-gate-summary.md; exit 0 only on PASS

Evidence bundle (DIR): meta.json (commit, dirty, generated_at, remote_ci), junit.xml, eval.json (governed evaluation + mutation report), repro.json, summary.json (derived totals).
Semantics: FAIL = a required gate has failing, missing, stale, malformed or inconsistent evidence. REQUIRES_REVIEW = nothing failed, but something required could not be verified
(for example the model-runtime test did not execute). PASS = every gate has positive evidence. `remote_ci` is reported but is not a gate: it is NOT_RUN until the workflows run on GitHub.
Pure logic lives in `evaluate()` so the negative tests can hand it doctored bundles.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
P, F, R = "PASS", "FAIL", "REQUIRES_REVIEW"
GATE_ORDER = ["unit_tests", "integration_tests", "pg_reconciliation", "agent_evaluation", "mutation_testing", "security_regression", "tenant_isolation",
              "authorization_enforcement", "reproducibility", "data_quality", "evidence_consistency", "portfolio_claim_validation"]
CFG_PATH = LAB / "tools/release-gate.config.json"


# ------------------------------------------------------------------ parsing
def parse_junit(text):
    """-> list of dict(module, name, outcome, reason). Raises ValueError on a malformed report."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"junit.xml is not valid XML: {e}") from e
    out = []
    for tc in root.iter("testcase"):
        outcome, reason = "passed", ""
        for ch in tc:
            if ch.tag in ("failure", "error"):
                outcome = "failed"
            elif ch.tag == "skipped":
                outcome, reason = "skipped", (ch.get("message") or "")
        mod = re.sub(r"^tests\.", "", tc.get("classname") or "").split(".")[0]
        out.append(dict(module=mod, name=re.sub(r"\[.*$", "", tc.get("name") or ""), outcome=outcome, reason=reason))
    if not out:
        raise ValueError("junit.xml contains no test cases")
    return out


def summarize(tests):
    s = dict(total=len(tests), passed=sum(t["outcome"] == "passed" for t in tests), failed=sum(t["outcome"] == "failed" for t in tests), skipped=sum(t["outcome"] == "skipped" for t in tests))
    s["skips"] = [dict(test=f"{t['module']}::{t['name']}", reason=t["reason"]) for t in tests if t["outcome"] == "skipped"]
    return s


def resolve(doc, pointer):
    cur = doc
    for part in pointer.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(pointer)
    return cur


# ------------------------------------------------------------------ gates
def _g(status, detail, evidence=None):
    return dict(status=status, detail=detail, evidence=evidence or [])


def _named(tests, ids, unverified):
    """Classify each required test id: returns (missing, failed, skipped_unverified, skipped_other, passed)."""
    idx = {}
    for t in tests:
        idx.setdefault(f"{t['module']}::{t['name']}", []).append(t)
    miss, fail, unver, skip, ok = [], [], [], [], []
    for i in ids:
        ts = idx.get(i)
        if not ts:
            miss.append(i)
        elif any(t["outcome"] == "failed" for t in ts):
            fail.append(i)
        elif any(t["outcome"] == "skipped" for t in ts):
            (unver if i in unverified else skip).append(i)
        else:
            ok.append(i)
    return miss, fail, unver, skip, ok


def gate_named(tests, ids, cfg, label):
    if not ids:
        return _g(F, f"{label}: no required tests configured (a gate with no requirements is not a pass)")
    miss, fail, unver, skip, ok = _named(tests, ids, cfg["unverified_tests"])
    if miss or fail or skip:
        return _g(F, f"{label}: missing={miss} failed={fail} skipped={skip}", ids)
    if unver:
        return _g(R, f"{label}: required tests did not execute: {unver}", ids)
    return _g(P, f"{label}: {len(ok)}/{len(ids)} required tests executed and passed", ids)


def gate_suite(tests, modules_in, cfg, name, policy):
    sel = [t for t in tests if modules_in(t["module"])]
    s = summarize(sel)
    if s["failed"]:
        return _g(F, f"{s['failed']} test(s) failed", [name])
    if s["passed"] < cfg["min_passed"][name]:
        return _g(F, f"only {s['passed']} passed; the configured minimum is {cfg['min_passed'][name]} (tests missing or not collected)", [name])
    review, hard = [], []
    for sk in s["skips"]:
        if sk["test"] in cfg["unverified_tests"]:
            review.append(f"{sk['test']} ({cfg['unverified_tests'][sk['test']]})")
            continue
        entry = next((a for a in policy.get("allowed", []) if re.search(a["match"], sk["reason"] or "", re.I)), None)
        if entry is None:
            review.append(f"{sk['test']}: skip with no policy entry ({sk['reason'][:60]!r})")
        elif entry["max"] == 0:
            hard.append(f"{sk['test']}: skip forbidden by policy ({entry['name']})")
    if hard:
        return _g(F, "; ".join(hard), [name])
    if review:
        return _g(R, f"{s['passed']} passed, {s['skipped']} skipped; needs review: " + "; ".join(review), [name])
    return _g(P, f"{s['passed']} passed, 0 failed, {s['skipped']} skipped (all allowed by policy)", [name])


def _eval_ok(ev, cfg):
    if not isinstance(ev, dict) or ev.get("schema") != "governed-eval/1":
        return "evaluation report missing or malformed (schema)"
    for k in ("metrics", "results", "result_hash", "reproducible", "mutants", "mutants_killed", "mutants_total"):
        if k not in ev:
            return f"evaluation report malformed: missing '{k}'"
    if not isinstance(ev["results"], list) or not all(isinstance(r, dict) and {"id", "category", "passed"} <= set(r) for r in ev["results"]):
        return "evaluation report malformed: result rows"
    return None


def gate_agent_eval(ev, cfg):
    bad = _eval_ok(ev, cfg)
    if bad:
        return _g(F, bad)
    c = cfg["evaluation"]; res, m = ev["results"], ev["metrics"]
    unsupported = sorted(set(m) - set(cfg["supported_metrics"]))
    if unsupported:
        return _g(F, f"unsupported metrics reported: {unsupported}")
    if len(res) < c["min_cases"]:
        return _g(F, f"only {len(res)} cases; minimum {c['min_cases']}")
    if m.get("cases") != len(res) or m.get("passed") != sum(bool(r["passed"]) for r in res):
        return _g(F, "metrics do not match the case results they claim to summarise")
    cats = {r["category"] for r in res}
    if set(c["required_categories"]) - cats:
        return _g(F, f"required categories not evaluated: {sorted(set(c['required_categories']) - cats)}")
    failed = [r["id"] for r in res if not r["passed"]]
    if failed:
        return _g(F, f"failed cases: {failed}")
    if m.get("unauthorized_action_rate") != 0:
        return _g(F, f"unauthorized_action_rate={m.get('unauthorized_action_rate')}")
    return _g(P, f"{len(res)}/{len(res)} cases passed across {len(cats)} categories; 0 unauthorized actions (small synthetic set; not evidence of real-world reliability)", ["eval.json"])


def gate_mutation(ev, cfg):
    bad = _eval_ok(ev, cfg)
    if bad:
        return _g(F, bad)
    mu = ev["mutants"]
    if ev["mutants_total"] != len(mu) or ev["mutants_killed"] != sum(bool(x.get("killed")) for x in mu):
        return _g(F, "mutation totals do not match the mutant rows")
    if len(mu) < cfg["evaluation"]["min_mutants"]:
        return _g(F, f"only {len(mu)} mutants; minimum {cfg['evaluation']['min_mutants']}")
    surv = [x["mutant"] for x in mu if not x.get("killed")]
    if surv:
        return _g(F, f"surviving mutants (the evaluation cannot detect these faults): {surv}")
    if any(not x.get("failing_cases") for x in mu):
        return _g(F, "a mutant is marked killed with no failing case")
    return _g(P, f"{len(mu)}/{len(mu)} mutants killed", ["eval.json"])


def gate_category_cases(ev, cfg, cats, label):
    bad = _eval_ok(ev, cfg)
    if bad:
        return _g(F, bad)
    rows = [r for r in ev["results"] if r["category"] in cats]
    if not rows:
        return _g(F, f"{label}: no evaluation cases in {cats}")
    unauth = [r["id"] for r in rows if (r.get("observed_pos") or 0) > 0 and r["id"] != "replayed-approval-creates-nothing-new"]
    if unauth:
        return _g(F, f"{label}: unauthorized workflow execution — purchase order(s) exist in cases {unauth}")
    failed = [r["id"] for r in rows if not r["passed"]]
    if failed:
        return _g(F, f"{label}: failed cases {failed}")
    return _g(P, f"{label}: {len(rows)} evaluation cases passed with no purchase order created", ["eval.json"])


def combine(*gs):
    order = {F: 2, R: 1, P: 0}
    worst = max(gs, key=lambda g: order[g["status"]])
    return _g(worst["status"], " | ".join(g["detail"] for g in gs), sum((g["evidence"] for g in gs), []))


def gate_repro(ev, repro, cfg):
    if not isinstance(repro, dict) or "eval_hash_run1" not in repro:
        return _g(F, "reproducibility artifact missing or malformed (repro.json)")
    if not repro.get("eval_hash_run1") or repro["eval_hash_run1"] != repro.get("eval_hash_run2"):
        return _g(F, "evaluation result hash differs between two independent runs")
    wr = repro.get("warehouse")
    if not isinstance(wr, dict) or wr.get("identical") is not True or wr.get("eval_hash_equal") is not True or not wr.get("tables"):
        return _g(F, "warehouse rebuild reproducibility artifact missing or not identical")
    bad = _eval_ok(ev, cfg)
    if bad:
        return _g(F, f"cannot confirm reproducibility without a valid evaluation report ({bad})")
    if ev["reproducible"] is not True:
        return _g(F, "evaluation report says not reproducible")
    if ev["result_hash"] != repro["eval_hash_run1"]:
        return _g(F, "result hash in eval.json does not match repro.json")
    return _g(P, f"evaluation hash identical across runs ({repro['eval_hash_run1']}); {wr['tables']} warehouse tables rebuilt byte-identically", ["repro.json"])


def gate_consistency(meta, summary, tests, ev, export, head, changed, cfg, now):
    if not isinstance(meta, dict) or not meta.get("commit") or not isinstance(meta.get("generated_at"), (int, float)):
        return _g(F, "meta.json missing or malformed (commit/generated_at)")
    if now - meta["generated_at"] > cfg["max_age_seconds"]:
        return _g(F, f"stale evidence: generated {int((now - meta['generated_at']) / 3600)} h ago (limit {cfg['max_age_seconds'] // 3600} h)")
    if meta["commit"] != head:
        code = [p for p in changed if any(p.startswith(x) for x in cfg["code_prefixes"])]
        if code:
            return _g(F, f"stale evidence: collected at {meta['commit']}, HEAD is {head}, and code changed since: {code[:5]}")
    if meta.get("dirty_code"):
        return _g(F, "evidence was collected from a working tree with uncommitted code changes")
    real = summarize(tests)
    for k in ("total", "passed", "failed", "skipped"):
        if summary.get(k) != real[k]:
            return _g(F, f"incorrect test counts: summary.json says {k}={summary.get(k)}, junit.xml has {real[k]}")
    if export is not None:
        claimed = export.get("metrics", {}).get("release_evidence", {})
        if claimed.get("tests_passed") not in (None, real["passed"]):
            return _g(F, f"portfolio export claims {claimed.get('tests_passed')} tests passed; junit.xml has {real['passed']}")
    return _g(P, f"evidence collected at {meta['commit']} (HEAD {head}); no code changed since; counts match junit.xml", ["meta.json", "summary.json", "junit.xml"])


def gate_claims(export, bundle_docs, cfg):
    if not isinstance(export, dict) or not isinstance(export.get("claims"), list) or not export["claims"]:
        return _g(F, "portfolio evidence export has no claims list to validate")
    sup = set(cfg["supported_metrics"]) | {"tests_passed", "tests_total", "mutants_killed", "mutants_total", "reproducible", "result_hash", "total", "failed", "skipped", "identical", "tables", "eval_hash_run1"}
    for c in export["claims"]:
        if not isinstance(c, dict) or not {"id", "text", "value", "source"} <= set(c) or not isinstance(c["source"], dict) or not {"file", "pointer"} <= set(c["source"]):
            return _g(F, f"malformed claim: {str(c)[:80]}")
        if c["source"]["file"] not in bundle_docs:
            return _g(F, f"claim {c['id']}: unsupported evidence file {c['source']['file']!r}")
        try:
            actual = resolve(bundle_docs[c["source"]["file"]], c["source"]["pointer"])
        except KeyError:
            return _g(F, f"claim {c['id']}: pointer {c['source']['pointer']!r} does not exist in {c['source']['file']}")
        if actual != c["value"]:
            return _g(F, f"claim {c['id']} says {c['value']!r} but the evidence says {actual!r}")
        if c["source"]["pointer"].split(".")[-1] not in sup and c["source"]["pointer"].split(".")[0] not in sup:
            return _g(F, f"claim {c['id']}: metric {c['source']['pointer']!r} is not a supported metric")
        low = c["text"].lower()
        hit = [p for p in cfg["forbidden_claim_phrases"] if p in low]
        if hit:
            return _g(F, f"claim {c['id']} uses unsupported wording {hit}")
    for n in export.get("architecture", {}).get("nodes", []):
        if n.get("status") == "implemented_and_tested" and not n.get("evidence"):
            return _g(F, f"architecture node {n.get('id')} claims implemented_and_tested without evidence")
    return _g(P, f"{len(export['claims'])} portfolio claims each resolve to the evidence bundle and match exactly", ["nasha-governed-evidence.json"])


# ------------------------------------------------------------------ evaluate
def evaluate(bundle, cfg, head, changed=(), now=None, policy=None):
    """bundle: dict with optional keys meta, junit(text), eval, repro, summary, export. Returns the machine-readable report."""
    now = now if now is not None else time.time()
    policy = policy or {"allowed": []}
    gates, tests, notes = {}, None, []
    try:
        tests = parse_junit(bundle["junit"]) if bundle.get("junit") else None
    except ValueError as e:
        notes.append(str(e)); tests = None
    ev = bundle.get("eval")
    inc = set(cfg["integration_modules"])
    if tests is None:
        why = "junit.xml missing" if not notes else notes[0]
        for g in ("unit_tests", "integration_tests", "pg_reconciliation", "security_regression", "tenant_isolation", "authorization_enforcement", "data_quality"):
            gates[g] = _g(F, why)
    else:
        gates["unit_tests"] = gate_suite(tests, lambda m: m not in inc, cfg, "unit_tests", policy)
        gates["integration_tests"] = gate_suite(tests, lambda m: m in inc, cfg, "integration_tests", policy)
        gates["pg_reconciliation"] = gate_named(tests, cfg["gates"]["pg_reconciliation"], cfg, "PostgreSQL reconciliation + pgvector")
        sec = gate_named(tests, cfg["gates"]["security_regression"], cfg, "security")
        gates["security_regression"] = sec
        gates["tenant_isolation"] = combine(gate_named(tests, cfg["gates"]["tenant_isolation"], cfg, "tenant isolation tests"), gate_category_cases(ev, cfg, set(cfg["tenant_categories"]), "evaluation cross-tenant"))
        gates["authorization_enforcement"] = combine(gate_named(tests, cfg["gates"]["authorization_enforcement"], cfg, "authorization tests"), gate_category_cases(ev, cfg, set(cfg["authorization_categories"]), "evaluation authorization/approval"))
        gates["data_quality"] = gate_named(tests, cfg["gates"]["data_quality"], cfg, "data quality")
    gates["agent_evaluation"] = combine(gate_agent_eval(ev, cfg), gate_named(tests, cfg["gates"]["contradiction_abstention"], cfg, "contradiction abstention") if tests else _g(F, "no junit"))
    gates["mutation_testing"] = gate_mutation(ev, cfg)
    gates["reproducibility"] = gate_repro(ev, bundle.get("repro"), cfg)
    meta, summary = bundle.get("meta"), bundle.get("summary") or {}
    if tests is None:
        gates["evidence_consistency"] = _g(F, "cannot check consistency without junit.xml")
    else:
        gates["evidence_consistency"] = gate_consistency(meta, summary, tests, ev, bundle.get("export"), head, changed, cfg, now)
    docs = {"eval.json": ev or {}, "summary.json": summary, "repro.json": bundle.get("repro") or {}, "meta.json": meta or {}}
    gates["portfolio_claim_validation"] = gate_claims(bundle.get("export"), docs, cfg)
    statuses = [gates[g]["status"] for g in GATE_ORDER]
    overall = F if F in statuses else (R if R in statuses else P)
    return dict(schema="release-gate-report/1", overall=overall, head=head, generated_at=now, evidence_commit=(meta or {}).get("commit"),
                remote_ci=(meta or {}).get("remote_ci", "NOT_RUN"), remote_ci_note="GitHub workflows have not run remotely; no remote CI result is claimed.",
                gates={g: gates[g] for g in GATE_ORDER}, notes=notes)


def render(rep):
    icon = {P: "PASS", F: "FAIL", R: "REVIEW"}
    out = [f"# Release gate: **{rep['overall']}**", "", f"HEAD `{rep['head']}`, evidence collected at `{rep['evidence_commit']}`. Remote CI: **{rep['remote_ci']}** — {rep['remote_ci_note']}", "", "| # | Gate | Result | Detail |", "|---|---|---|---|"]
    for i, (g, v) in enumerate(rep["gates"].items(), 1):
        out.append(f"| {i} | {g} | **{icon[v['status']]}** | {v['detail'].replace('|', '/')[:400]} |")
    out += ["", "A missing or malformed required item is a FAIL, never a pass. REQUIRES_REVIEW means nothing failed but something required could not be verified in this environment."]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ io
def _export(p):
    try:
        return json.loads(Path(p).read_text()) if Path(p).exists() else None
    except json.JSONDecodeError:
        return {"__malformed__": True}


def load_bundle(d, export_path):
    d = Path(d)
    rd = lambda n: (d / n).read_text() if (d / n).exists() else None
    def js(n):
        t = rd(n)
        try:
            return json.loads(t) if t else None
        except json.JSONDecodeError:
            return {"__malformed__": True}
    return dict(meta=js("meta.json"), junit=rd("junit.xml"), eval=js("eval.json"), repro=js("repro.json"), summary=js("summary.json"),
                export=_export(export_path))


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=REPO).stdout.strip()


def collect(out, junit=None):
    import tempfile
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    head = git("rev-parse", "--short", "HEAD")
    dirty = git("status", "--porcelain", "--", "lab/nasha_lab", "lab/tests", "lab/tools")
    if junit:
        (out / "junit.xml").write_text(Path(junit).read_text())
    else:
        subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", f"--junitxml={out / 'junit.xml'}"], cwd=LAB)
    sys.path.insert(0, str(LAB))
    from nasha_lab.governed import evaluation, tenants
    t1, t2 = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
    rep = evaluation.full_report(t1, tenants.default_pair(t1))
    rep2 = evaluation.run_cases(evaluation.Harness(t2, tenants.default_pair(t2)), evaluation.Oracle(tenants.default_pair(t2)[0]))
    (out / "eval.json").write_text(json.dumps(rep, indent=1, default=str))
    subprocess.run([sys.executable, "-m", "nasha_lab.warehouse.repro", "--profile", "dev", "--out", str(out / "warehouse_repro.json")], cwd=LAB, capture_output=True)
    wr = json.loads((out / "warehouse_repro.json").read_text()) if (out / "warehouse_repro.json").exists() else {}
    (out / "repro.json").write_text(json.dumps(dict(eval_hash_run1=rep["result_hash"], eval_hash_run2=evaluation.result_hash(rep2), warehouse=dict(tables=wr.get("tables"), identical=wr.get("identical"), eval_hash_equal=wr.get("eval_hash_equal"), differing_tables=wr.get("differing_tables"))), indent=1))
    tests = parse_junit((out / "junit.xml").read_text())
    s = summarize(tests); s.pop("skips")
    s["by_module"] = {m: {k: sum(t["outcome"] == k for t in tests if t["module"] == m) for k in ("passed", "failed", "skipped")} for m in sorted({t["module"] for t in tests})}
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    (out / "meta.json").write_text(json.dumps(dict(commit=head, dirty_code=bool(dirty), generated_at=time.time(), remote_ci="NOT_RUN", python=sys.version.split()[0]), indent=1))
    print(f"evidence written to {out} (commit {head}, dirty_code={bool(dirty)})")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("collect"); c.add_argument("--junit"); c.add_argument("--out", default=str(LAB / "results/release-gate"))
    k = sp.add_parser("check"); k.add_argument("--evidence", default=str(LAB / "results/release-gate")); k.add_argument("--export", default=str(LAB / "portfolio/nasha-governed-evidence.json"))
    a = ap.parse_args(argv)
    if a.cmd == "collect":
        return collect(a.out, a.junit) or 0
    cfg = json.loads(CFG_PATH.read_text()); policy = json.loads((LAB / cfg["skip_policy"]).read_text())
    b = load_bundle(a.evidence, a.export)
    head = git("rev-parse", "--short", "HEAD")
    mc = (b["meta"] or {}).get("commit")
    changed = git("diff", "--name-only", mc, "HEAD").splitlines() if mc else []
    rep = evaluate(b, cfg, head, changed, policy=policy)
    Path(a.evidence, "release-gate-report.json").write_text(json.dumps(rep, indent=1))
    Path(a.evidence, "release-gate-summary.md").write_text(render(rep))
    print(render(rep))
    return 0 if rep["overall"] == P else 1


if __name__ == "__main__":
    sys.exit(main())
