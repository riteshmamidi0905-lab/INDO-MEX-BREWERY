"""Static, accessible HTML dashboard (no CDN, no external requests) rendered from lab/results/analytics/*.json."""
import html
import os

from .render_docs import RES, R

OUT = os.path.join(RES, "dashboard.html")
E = html.escape


def bars(items, vmax, label, fmt="{:.2f}", w=560):
    """Horizontal bar chart as inline SVG. items: [(name, value)]"""
    h = 26 * len(items) + 8
    rows = []
    for i, (n, v) in enumerate(items):
        bw = 0 if vmax == 0 else (w - 230) * v / vmax
        rows.append(f'<text x="0" y="{i * 26 + 18}" class="lab">{E(str(n))}</text><rect x="210" y="{i * 26 + 5}" width="{bw:.1f}" height="16" rx="2" class="bar"/>'
                    f'<text x="{214 + bw:.1f}" y="{i * 26 + 18}" class="val">{fmt.format(v)}</text>')
    return f'<svg role="img" aria-label="{E(label)}" viewBox="0 0 {w} {h}" width="100%" height="{h}">{"".join(rows)}</svg>'


def interval_chart(rows, truth, label, w=560):
    """rows: [(name, est, lo, hi)]; vertical reference line at truth."""
    lo_all = min(min(r[2] for r in rows), truth, 0); hi_all = max(max(r[3] for r in rows), truth)
    sx = lambda v: 150 + (w - 170) * (v - lo_all) / (hi_all - lo_all)
    h = 34 * len(rows) + 30
    parts = [f'<line x1="{sx(truth):.1f}" x2="{sx(truth):.1f}" y1="6" y2="{h - 20}" class="truth"/><text x="{sx(truth):.1f}" y="{h - 4}" class="val" text-anchor="middle">injected truth {truth:.3f}</text>',
             f'<line x1="{sx(0):.1f}" x2="{sx(0):.1f}" y1="6" y2="{h - 20}" class="zero"/>']
    for i, (n, est, lo, hi) in enumerate(rows):
        y = i * 34 + 22
        parts.append(f'<text x="0" y="{y + 4}" class="lab">{E(n)}</text><line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y}" y2="{y}" class="whisk"/><circle cx="{sx(est):.1f}" cy="{y}" r="5" class="dot"/>')
    return f'<svg role="img" aria-label="{E(label)}" viewBox="0 0 {w} {h}" width="100%" height="{h}">{"".join(parts)}</svg>'


def tbl(headers, rows, caption):
    th = "".join(f'<th scope="col">{E(h)}</th>' for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{E(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table><caption>{E(caption)}</caption><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def render():
    ms, mr, dq, fc, ex, rc = R("mart_summary"), R("metrics_reconciliation"), R("dq_evaluation"), R("forecast_backtest"), R("experiment"), R("recovery_checks")
    met = {r["metric"]: r for r in mr["rows"]}
    tot = lambda name: sum(v for v in met[name]["mart"].values())
    kpis = [("Orders (accepted)", f"{ms['row_counts']['fact_order']:,}", "synthetic"), ("Gross sales, placeholder prices", f"${tot('gross_sales_usd'):,.0f}", "not revenue"),
            ("Metrics reconciled", f"{sum(r['ok'] for r in mr['rows'])} / {len(mr['rows'])}", "mart vs source"),
            ("Injected defect types found", f"{sum(1 for v in dq['score']['per_defect_type_any_rule_recall'].values() if v['recall'] == 1.0)} / {len(dq['score']['per_defect_type_any_rule_recall'])}", "same-author test")]
    kp = "".join(f'<div class="kpi"><div class="k">{E(a)}</div><div class="v">{E(b)}</div><div class="s">{E(c)}</div></div>' for a, b, c in kpis)
    dqi = [(t.replace("_", " "), v["recall"]) for t, v in dq["score"]["per_defect_type_any_rule_recall"].items()]
    fci = [(m, v["WAPE"]) for m, v in fc["overall"].items()]
    sup = [(a, b) for a, b, _n in rc["late_supplier_recovery"]["observed_on_time_rate_worst_first"]]
    sr = ex["single_run"]["m04_units"]
    mcm = ex["monte_carlo_with_effect"]["metrics"]["m04_units"]
    ir = [(k, sr[k]["est"], sr[k]["ci95"][0], sr[k]["ci95"][1]) for k in ("unadjusted", "cuped", "stratified")]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>NASHA Analytics Mart</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#5b5b55;--card:#fff;--line:#d9d6cc;--bar:#2b6f8f;--acc:#b5532a;--warn:#fff3cd;--warnfg:#4a3b00}}
@media (prefers-color-scheme:dark){{:root{{--bg:#15161a;--fg:#ececea;--mut:#a5a59d;--card:#1e2026;--line:#3a3d45;--bar:#6fb4d4;--acc:#e8905f;--warn:#3b3320;--warnfg:#f3e2a8}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:980px;margin:0 auto;padding:16px}}
.banner{{background:var(--warn);color:var(--warnfg);padding:10px 14px;border-radius:6px;font-weight:600}}
h1{{font-size:1.5rem;margin:.8rem 0}} h2{{font-size:1.15rem;margin:0 0 .4rem}}
.grid{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}}
.kpi,section{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}}
section{{margin-top:14px}} .k{{color:var(--mut);font-size:.85rem}} .v{{font-size:1.6rem;font-weight:700}} .s{{color:var(--mut);font-size:.8rem}}
svg{{max-width:100%}} .lab,.val{{font-size:15px;fill:var(--fg)}} .bar{{fill:var(--bar)}} .dot{{fill:var(--bar)}} .whisk{{stroke:var(--bar);stroke-width:3}}
.truth{{stroke:var(--acc);stroke-width:2;stroke-dasharray:4 3}} .zero{{stroke:var(--line);stroke-width:1}}
table{{border-collapse:collapse;width:100%;font-size:.85rem;margin-top:6px}} caption{{text-align:left;color:var(--mut);padding:4px 0}}
th,td{{border-bottom:1px solid var(--line);padding:3px 6px;text-align:left}} details{{margin-top:6px}} summary{{cursor:pointer}}
p.note{{color:var(--mut);font-size:.88rem;margin:.3rem 0}}
:focus-visible{{outline:3px solid var(--acc);outline-offset:2px}}
</style></head><body><main>
<p class="banner" role="note">SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED. NASHA has no customers or sales. Prices are placeholders; costs and recipes are assumptions.</p>
<h1>NASHA analytics mart: evidence summary</h1>
<div class="grid" role="list" aria-label="Key figures">{kp}</div>
<section aria-labelledby="h-dq"><h2 id="h-dq">Data-quality recall by injected defect type</h2>
<p class="note">Recall of the SQL rule set, seeds 1 to 10. Same author wrote defects and rules; recall of 1.0 is not evidence for real data. Timezone-slip probe: {dq['novel_defect_probe']['timezone_slip_5h']['detected']} of {dq['novel_defect_probe']['timezone_slip_5h']['planted']} detected.</p>
{bars(dqi, 1.0, "Recall by defect type, all 1.00", "{:.2f}")}
<details><summary>Data table</summary>{tbl(["Defect type", "Recall"], [(a, f"{b:.3f}") for a, b in dqi], "Recall by defect type")}</details></section>
<section aria-labelledby="h-fc"><h2 id="h-fc">Forecast backtest: WAPE by model (lower is better)</h2>
<p class="note">Rolling origin, 7-day horizon, synthetic usage. Says nothing about real demand.</p>
{bars(fci, max(v for _n, v in fci), "WAPE by forecasting model", "{:.3f}")}
<details><summary>Data table</summary>{tbl(["Model", "WAPE", "Bias %"], [(m, f"{v['WAPE']:.3f}", f"{v['bias_pct_of_actual']:.1f}") for m, v in fc["overall"].items()], "Forecast metrics")}</details></section>
<section aria-labelledby="h-sup"><h2 id="h-sup">Supplier on-time rate (simulated lateness, worst first)</h2>
{bars(sup, 1.0, "On-time rate by supplier", "{:.2f}")}
<details><summary>Data table</summary>{tbl(["Supplier", "On-time rate"], [(a, f"{b:.3f}") for a, b in sup], "Supplier on-time")}</details></section>
<section aria-labelledby="h-ex"><h2 id="h-ex">Synthetic experiment: estimate of the injected effect</h2>
<p class="note">One simulated run, 95% CI per estimator, against the injected truth. Power at this effect size is about {100 * mcm['unadjusted']['reject_rate']:.0f}%; over {ex['monte_carlo_with_effect']['reps']} repeated randomisations the estimators are unbiased (bias {mcm['unadjusted']['bias']:+.3f}) with {100 * mcm['unadjusted']['ci_coverage']:.0f}% coverage. Underpowered by design.</p>
{interval_chart(ir, ex['truth']['m04_units_per_treated_guest'], "Estimates and 95 percent intervals versus injected truth")}
<details><summary>Data table</summary>{tbl(["Estimator", "Estimate", "CI low", "CI high"], [(a, f"{b:.3f}", f"{c:.3f}", f"{d:.3f}") for a, b, c, d in ir], "Primary metric estimates")}</details></section>
<p class="note">The 2026-04-13 menu-change date used in the simulation is a SYNTHETIC SCENARIO DATE / DESIGN ASSUMPTION, not a real NASHA date.</p>
<p class="note">Rendered from lab/results/analytics/*.json by analytics/dashboard.py. Static page; no scripts, no external requests.</p>
</main></body></html>
"""


def write():
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render())
