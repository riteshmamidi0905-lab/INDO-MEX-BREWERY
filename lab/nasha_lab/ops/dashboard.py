"""Static, accessible dashboard rendered from the committed metrics/incident JSON (P1 item 9). No JavaScript, no CDN, no web fonts.
SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED. Dark/light follows the OS setting; every status is text plus a symbol, never colour alone.
  python -m nasha_lab.ops dashboard      ->  lab/results/ops/dashboard.html"""
import html
import os

from . import LABEL
from .util import RESULTS_DIR, OPS_DIR, load_json

E = html.escape
CSS = """
:root{--bg:#fbfaf7;--fg:#1d2127;--muted:#4f5762;--card:#ffffff;--line:#c9cfd6;--accent:#0b5cad;--ok:#116329;--warn:#8a4b00;--bad:#a4161a;--bar:#2b6cb0;--barbg:#e5e9ee;--banner:#fff4cc}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171b;--fg:#e8eaed;--muted:#aab2bc;--card:#1c2127;--line:#39424d;--accent:#7db5ff;--ok:#7bd88f;--warn:#f0b35c;--bad:#ff8a8d;--bar:#5aa2f0;--barbg:#2b333c;--banner:#3a3312}}
:root[data-theme="dark"]{--bg:#14171b;--fg:#e8eaed;--muted:#aab2bc;--card:#1c2127;--line:#39424d;--accent:#7db5ff;--ok:#7bd88f;--warn:#f0b35c;--bad:#ff8a8d;--bar:#5aa2f0;--barbg:#2b333c;--banner:#3a3312}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}a:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:var(--card);padding:8px;z-index:9}
header,main,footer{max-width:1100px;margin:0 auto;padding:0 16px}header{padding-top:20px}h1{font-size:1.6rem;margin:.2em 0}h2{font-size:1.25rem;margin:1.6em 0 .5em;border-bottom:1px solid var(--line);padding-bottom:.2em}h3{font-size:1.05rem;margin:1em 0 .3em}
.banner{background:var(--banner);border:1px solid var(--line);padding:10px 12px;border-radius:6px;font-weight:600}
nav ul{list-style:none;display:flex;flex-wrap:wrap;gap:6px 16px;padding:0;margin:12px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.card .k{color:var(--muted);font-size:.85rem}.card .v{font-size:1.5rem;font-weight:700}.card .s{font-size:.85rem;color:var(--muted)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.9rem;background:var(--card)}caption{text-align:left;color:var(--muted);padding:4px 0}th,td{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}th{background:var(--barbg)}
.num{text-align:right;font-variant-numeric:tabular-nums}.ok{color:var(--ok);font-weight:600}.warn{color:var(--warn);font-weight:600}.bad{color:var(--bad);font-weight:600}
details{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 10px;margin:6px 0}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;word-break:break-word;font-size:.82rem;margin:6px 0;overflow-x:auto}
.bar{display:flex;align-items:center;gap:8px;margin:3px 0}.bar .l{width:210px;flex:none;font-size:.85rem}.bar .t{flex:1;background:var(--barbg);height:16px;border-radius:3px;overflow:hidden}.bar .f{height:100%;background:var(--bar)}.bar .n{width:90px;flex:none;font-size:.85rem;font-variant-numeric:tabular-nums}
@media (max-width:640px){.bar .l{width:120px}}footer{padding:20px 16px 40px;color:var(--muted);font-size:.85rem}
"""


def status(s):
    s = str(s)
    good = s in ("HEALTHY", "MET", "PASS", "RESOLVED", "CONTAINED", "ACTIVE", "approved")
    bad = s in ("BREACHED", "FAIL", "UNRESOLVED", "OPEN", "DEGRADED", "expired", "denied_pending")
    return f'<span class="{"ok" if good else "bad" if bad else "warn"}">{"&#10003;" if good else "&#9888;" if bad else "&#9679;"} {E(s)}</span>'


def pct(x): return "n/a" if x is None else f"{100 * x:.1f}%"


def bars(title, items, maxv=1.0, fmt=pct):
    rows = "".join(f'<div class="bar"><span class="l">{E(str(l))}</span><span class="t" aria-hidden="true"><span class="f" style="display:block;width:{max(0, min(100, 100 * (v or 0) / maxv)):.1f}%"></span></span><span class="n">{E(fmt(v))}{E(" " + note) if note else ""}</span></div>' for l, v, note in items)
    return f'<figure style="margin:0"><figcaption><strong>{E(title)}</strong></figcaption>{rows}</figure>'


def table(caption, head, rows, num=()):
    th = "".join(f'<th scope="col">{E(h)}</th>' for h in head)
    body = "".join("<tr>" + "".join(f'<td class="{"num" if i in num else ""}">{c if isinstance(c, str) and c.startswith("<span") else E(str(c))}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tw" tabindex="0" role="region" aria-label="{E(caption)}"><table><caption>{E(caption)}</caption><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def render(d):
    m, inc, fi, rg, ctl, st, reg, dr = (d[k] for k in ("metrics", "incidents", "faults", "regression", "control", "traces", "registry", "drill"))
    h = m["health"]; slo = m["slo"]; lat = m["latency"]["run_ms"]; ar = m["agent_run_health"]
    cards = [("Service health (whole day)", status(h["whole_day"]["status"]), "breached: " + (", ".join(h["whole_day"]["breached"]) or "none")), ("Service health (latest 20 runs)", status(h["latest_20_runs"]["status"]), "breached: " + (", ".join(h["latest_20_runs"]["breached"]) or "none")),
             ("Runs in the simulated day", str(m["runs"]), f"operational success {pct(ar['operational_success']['rate'])}"), ("Run latency p50 / p95", f"{lat['p50']:.0f} / {lat['p95']:.0f} ms", "compute time, this machine; design target p95 under 600 ms"),
             ("Evaluation regression gate", status(dr["summary"]["post_rollback_gate"]), f"drill: bad candidate {'caught' if dr['summary']['gate_caught_bad_candidate'] else 'MISSED'}, rolled back to {dr['summary']['rolled_back_to']}"), ("Incidents generated", str(inc["count"]), "from synthetic failures only")]
    o = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NASHA Ops Control Center</title><meta name="color-scheme" content="light dark"><style>{CSS}</style></head><body>',
         '<a class="skip" href="#main">Skip to main content</a>', f'<header><h1>NASHA AI Operations Control Center</h1><p class="banner" role="note">{E(LABEL)}. Every number on this page was produced by running the synthetic lab; none is production traffic, a real SLA or a real cost. SLO targets are design targets (assumptions).</p>',
         '<nav aria-label="Sections"><ul>' + "".join(f'<li><a href="#{a}">{E(t)}</a></li>' for a, t in [("health", "Health"), ("slo", "SLOs"), ("incidents", "Incidents"), ("faults", "Fault injection"), ("gate", "Regression gate"), ("tools", "Tools"), ("retrieval", "Retrieval"), ("cost", "Tokens and cost"), ("versions", "Versions"), ("traces", "Trace inspector"), ("limits", "Limits")]) + '</ul></nav></header><main id="main">',
         '<section id="health" aria-labelledby="h-health"><h2 id="h-health">Health</h2><div class="cards">' + "".join(f'<div class="card"><div class="k">{E(k)}</div><div class="v">{v if v.startswith("<span") else E(v)}</div><div class="s">{E(s)}</div></div>' for k, v, s in cards) + '</div>',
         table("Outcome categories (agent-run health)", ["category", "runs"], sorted(ar["outcome_categories"].items(), key=lambda x: -x[1]), num=(1,)), table("Approval states", ["state", "runs"], sorted(ar["approval_states"].items(), key=lambda x: -x[1]), num=(1,)), '</section>']
    o += ['<section id="slo" aria-labelledby="h-slo"><h2 id="h-slo">Service level objectives (design targets)</h2><p>Windows are counted in runs. Burn rate = bad fraction / (1 - objective).</p>',
          table("SLO attainment over the simulated day", ["SLO", "name", "objective", "attainment", "bad / total", "budget consumed", "status"], [(s["id"], s["name"], f"{s['objective']:.3f}", "n/a" if s["attainment"] is None else f"{s['attainment']:.4f}", f"{s['bad']} / {s['total']}", str(s["budget_consumed"]), status(s["status"])) for s in slo["slos"]]),
          table("Burn-rate alert firings", ["SLO", "alert", "severity", "action", "first run", "last run", "runs firing", "peak burn"], [(b["slo"], b["burn_alert"], b["severity"], b["action"], b["first_run_index"], b["last_run_index"], b["runs_firing"], b["peak_burn"]) for b in slo["burn_alerts"]] or [("none", "", "", "", "", "", "", "")], num=(4, 5, 6)), '</section>']
    rows = []
    for i in inc["incidents"]:
        tl = "".join(f"<li>step {E(str(t.get('step')))}: <strong>{E(t['event'])}</strong> {E(str(t.get('detail', '')))}</li>" for t in i["timeline"])
        rows.append(f'<details><summary>{E(i["incident_id"])} &middot; {E(i["severity"])} &middot; {E(i["cls"])} &middot; {status(i["status"])} &middot; rule {E(i["detection_rule"])} &middot; ground truth: {E(str(i.get("ground_truth")))}</summary><p>Runbook <code>{E(i["runbook_id"])}</code> (lab/ops/runbooks/{E(i["runbook_id"])}.md). Expected containment: {E(i.get("expected_containment", "see taxonomy"))}</p><ol>{tl}</ol></details>')
    o += ['<section id="incidents" aria-labelledby="h-inc"><h2 id="h-inc">Incidents</h2><p>Generated by the alert rules from the simulated day. Each incident has a class, a severity, the detecting rule, a runbook and a timeline. An incident whose ground truth is "clean" would be a false alert.</p>' + "".join(rows) + '</section>']
    fr = [(f, v["detection"], v) for f, v in fi["faults"].items()]
    o += ['<section id="faults" aria-labelledby="h-f"><h2 id="h-f">Fault injection (20 seeded trials per fault)</h2>', bars("Detection rate by fault (expected alert class fired)", [(f, v["detection"]["rate"], f'{v["detection"]["k"]}/{v["detection"]["n"]}') for f, _, v in fr]),
          table("Detection, containment, recovery and time to detect", ["fault", "trials", "detected", "contained", "recovered", "TTD steps (median / max)", "TTD ms (median / p95)"],
                [(f, v["trials"], f'{v["detection"]["k"]}/{v["detection"]["n"]}', (f'{v["containment"]["k"]}/{v["containment"]["n"]}' if "containment" in v else "see detail"), (f'{v["recovery"]["k"]}/{v["recovery"]["n"]}' if "recovery" in v else "n/a"),
                  (f'{v["ttd_steps"]["median"]} / {v["ttd_steps"]["max"]}' if "ttd_steps" in v else "runs, see detail"), (f'{v["ttd_ms"]["median"]} / {v["ttd_ms"]["p95"]}' if "ttd_ms" in v and v["ttd_ms"]["median"] is not None else "n/a")) for f, _, v in fr], num=(1,)),
          f'<p>Clean control: {ctl["runs_with_any_event_or_run_alert"]["k"]} of {ctl["runs_with_any_event_or_run_alert"]["n"]} clean runs raised an event or run alert; {ctl["window_alert_firings"]} window-alert firings over {ctl["window_alert_evaluations"]} evaluations.</p>']
    miss = [(f, len(v.get("missed", []))) for f, v in fi["faults"].items() if v.get("missed")]
    o += [("<p><strong>Misses:</strong> " + "; ".join(f"{E(f)}: {n} undetected" for f, n in miss) + ". See the evaluation document for which variants.</p>") if miss else "", '</section>']
    sc = rg["severity_curve"]
    o += ['<section id="gate" aria-labelledby="h-g"><h2 id="h-g">Evaluation regression gate</h2>', bars("Gate detection rate by injected regression severity (fraction of events degraded)", [(f"severity {k}", v["detection"]["rate"], f'{v["detection"]["k"]}/{v["detection"]["n"]}') for k, v in sc.items()]),
          table("Named candidates against the frozen reference", ["candidate", "verdict", "pass rate", "newly failing", "reasons"], [(k, status(v["verdict"]), v["pass_rate"], v["newly_failing"], "; ".join(v["reasons"])) for k, v in rg["named_candidates"].items()]),
          table("Rollback drill", ["step", "what", "result"], [(p["step"], p["name"], ", ".join(f"{k}={v}" for k, v in p.items() if k in ("version", "verdict", "pass_rate", "decision", "active", "ms", "alerts"))) for p in dr["procedure"]]), '</section>']
    o += ['<section id="tools" aria-labelledby="h-t"><h2 id="h-t">Tool success and latency</h2>', table("Per tool over the simulated day", ["tool", "calls", "success rate", "failures", "error codes", "per-run max ms p50", "p95"],
          [(t, v["calls"], pct(v["success_rate"]), v["failures"], ", ".join(f"{k}:{n}" for k, n in v["error_codes"].items()) or "none", v["per_run_max_ms_p50"], v["per_run_max_ms_p95"]) for t, v in m["tools"].items()], num=(1, 3, 5, 6)), '</section>']
    rc = m["retrieval"]["counts"]
    o += ['<section id="retrieval" aria-labelledby="h-r"><h2 id="h-r">Retrieval</h2>', table("Policy retrievals", ["result", "count"], [(k, v) for k, v in rc.items()], num=(1,)), f'<p>{E(m["retrieval"]["definition"])}</p></section>']
    o += ['<section id="cost" aria-labelledby="h-c"><h2 id="h-c">Tokens and estimated cost (assumption-labelled)</h2>', f'<p>{E(m["cost"]["assumptions"]["label"])}</p>',
          table("Token use and what-if cost", ["source", "runs", "prompt tokens", "completion tokens", "API charge (USD)", "what-if small tier", "what-if large tier"], [(r["source"], r["runs"], r["prompt_tokens"], r["completion_tokens"], r["api_charge_usd"], r["what_if_hosted"]["assumed_small_hosted"], r["what_if_hosted"]["assumed_large_hosted"]) for r in m["cost"]["rows"]], num=(1, 2, 3, 4, 5, 6)), '</section>']
    o += ['<section id="versions" aria-labelledby="h-v"><h2 id="h-v">Version registry</h2>', f'<p>Active version: <strong>{E(reg["active"])}</strong>.</p>',
          table("Registered versions", ["version", "planner", "prompt / logic hash", "tool schema", "corpus", "evaluation snapshot", "status"], [(v["version_id"], v["planner_id"], v["prompt_hash"], v["tool_schema_version"], str(v["corpus_version"]), f'{v["eval_snapshot"].get("gate_verdict")} {v["eval_snapshot"].get("pass_rate")}', status(v["status"])) for v in reg["versions"]]), '</section>']
    tr = []
    for t in st["traces"]:
        ev = "\n".join(f"{e['seq']:>3} {e['t_ms']:>8.1f} ms  {e['kind']:<22} " + " ".join(f"{k}={v}" for k, v in e.items() if k not in ("seq", "t_ms", "kind")) for e in t["events"])
        tr.append(f'<details><summary>{E(t["run_id"])} &middot; {E(t["ground_truth"])} &middot; approval: {E(t["approval_state"])} &middot; alerts: {E(", ".join(a["rule"] for a in t["alerts"]) or "none")}</summary><p>Outcome {E(str(t["outcome"]))} ({E(t["outcome_category"])}); action {E(str(t["action"]))}; planner {E(str(t["planner"]))}; run {t["run_ms"]} ms.</p><pre tabindex="0">{E(ev)}</pre></details>')
    o += ['<section id="traces" aria-labelledby="h-tr"><h2 id="h-tr">Trace inspector</h2><p>One representative run per scenario type. CLI: <code>python -m nasha_lab.ops trace --list</code> then <code>python -m nasha_lab.ops trace RUN_ID</code>.</p>' + "".join(tr) + '</section>']
    o += ['<section id="limits" aria-labelledby="h-l"><h2 id="h-l">What this is not</h2><ul><li>Not production telemetry: no real users, traffic, incidents, SLAs or spend.</li><li>Latency numbers are wall-clock on one development machine and vary run to run.</li><li>Alert thresholds and SLOs are design targets chosen by the author.</li><li>Same-author evaluation; the injected faults are the ones the author thought of.</li></ul></section>', '</main>',
          f'<footer>{E(LABEL)} &middot; rendered from lab/results/ops/*.json by nasha_lab.ops.dashboard</footer></body></html>']
    return "".join(o)


def load():
    r = lambda n: load_json(os.path.join(RESULTS_DIR, n))
    inc = r("incidents.json"); tax = {c["id"]: c for c in load_json(os.path.join(OPS_DIR, "failure-taxonomy.json"))["classes"]}
    for i in inc["incidents"]: i.setdefault("expected_containment", tax[i["cls"]]["expected_containment"])
    return dict(metrics=r("metrics.json"), incidents=inc, faults=r("fault_injection.json"), regression=r("regression_gate.json"), control=r("control.json"), traces=r("sample_traces.json"), registry=load_json(os.path.join(OPS_DIR, "version-registry.json")), drill=r("rollback_drill.json"))


def main(argv=None):
    p = os.path.join(RESULTS_DIR, "dashboard.html")
    with open(p, "w", encoding="utf-8") as f: f.write(render(load()))
    print("wrote", p)


if __name__ == "__main__":
    main()
