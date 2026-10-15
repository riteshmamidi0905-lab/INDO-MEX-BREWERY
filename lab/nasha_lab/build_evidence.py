"""Build lab/evidence/index.html: the recruiter-readable evidence pack (A architecture, B state graph, C trust/permission model, D retrieval benchmark,
E planner comparison, F failure cases, G approval flow, H trace view, I tests/CI, J disclosure) from the committed result files. No external assets; inline SVG;
light/dark; keyboard- and screen-reader-friendly. Nothing is invented: a measurement that does not exist yet is shown as NOT MEASURED."""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.abspath(os.path.join(HERE, "..")); R = os.path.join(LAB, "results")
E = html.escape


def load(name):
    p = os.path.join(R, name)
    return json.load(open(p)) if os.path.exists(p) else None


def pct(x): return "n/a" if x is None else f"{100 * x:.0f}%"


def svg_box(x, y, w, h, title, sub="", cls="box"):
    return (f'<g><rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/><text class="t" x="{x + w / 2}" y="{y + 22}" text-anchor="middle">{E(title)}</text>'
            + (f'<text class="s" x="{x + w / 2}" y="{y + 40}" text-anchor="middle">{E(sub)}</text>' if sub else "") + "</g>")


def arrow(x1, y1, x2, y2, label=""):
    t = f'<text class="s" x="{(x1 + x2) / 2 + 4}" y="{(y1 + y2) / 2 - 4}">{E(label)}</text>' if label else ""
    return f'<line class="ar" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" marker-end="url(#ah)"/>{t}'


DEFS = '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>'


def architecture():
    b = [svg_box(20, 20, 200, 56, "Synthetic operations", "raw > staged > validated > modeled", "box"), svg_box(20, 110, 200, 56, "NASHA knowledge", "status-aware, 758 chunks", "box"),
         svg_box(270, 20, 210, 56, "Tool registry", "18 typed tools, 5 permission classes", "box key"), svg_box(270, 110, 210, 56, "Trust gateway", "schema, timeout, taint, injection scan", "box key"),
         svg_box(530, 20, 220, 56, "LangGraph agent", "state machine, checkpoints", "box key"), svg_box(530, 110, 220, 56, "Planner (swappable)", "deterministic | LLM | LLM + guardrail", "box key"),
         svg_box(270, 200, 210, 56, "Human review", "signed reviewer identity + grants", "box warn"), svg_box(530, 200, 220, 56, "Trace store", "request id, model, tokens, status", "box"),
         svg_box(20, 200, 200, 56, "Evaluation harness", "250+ scenarios, 3 splits, stand-ins", "box"), svg_box(800, 20, 170, 56, "Trusted MCP", "9 read/analyze/draft tools", "box"), svg_box(800, 110, 170, 56, "Untrusted MCP", "simulated, hostile modes", "box bad")]
    a = [arrow(220, 48, 270, 48), arrow(220, 138, 270, 120), arrow(480, 48, 530, 48), arrow(640, 76, 640, 110), arrow(480, 138, 530, 138), arrow(640, 166, 400, 200, "propose"), arrow(530, 228, 480, 228),
         arrow(800, 138, 480, 138), arrow(800, 48, 750, 48), arrow(400, 76, 400, 110), arrow(220, 228, 270, 228)]
    return f'<svg role="img" aria-labelledby="ta" viewBox="0 0 990 280" class="dg"><title id="ta">System architecture</title>{DEFS}{"".join(a)}{"".join(b)}</svg>'


def state_graph():
    n = ["RECEIVE_EVENT", "CLASSIFY_EVENT", "COLLECT_DATA", "RETRIEVE_POLICY", "ASSESS_EVIDENCE", "PROPOSE_ACTION", "HUMAN_REVIEW"]
    parts = [DEFS]
    for i, name in enumerate(n):
        x = 10 + i * 138; parts.append(svg_box(x, 20, 124, 44, name, "", "box warn" if name == "HUMAN_REVIEW" else "box"))
        if i: parts.append(arrow(x - 14, 42, x, 42))
    parts += [svg_box(520, 130, 130, 44, "EXECUTE_APPROVED", "signed grant per action", "box key"), svg_box(690, 130, 110, 44, "FINALIZE", "trace + outcome", "box"), svg_box(300, 130, 150, 44, "APPLY_EDIT", "validated fields only", "box"), svg_box(110, 130, 150, 44, "MORE_EVIDENCE", "max 2 rounds", "box"),
              arrow(920, 64, 585, 130, "approve"), arrow(585, 152, 690, 152), arrow(940, 64, 780, 130, "reject"), arrow(880, 64, 450, 140, "edit"), arrow(860, 64, 260, 140, "more evidence"), arrow(300, 140, 960, 64, "")]
    return f'<svg role="img" aria-labelledby="tb" viewBox="0 0 990 200" class="dg"><title id="tb">Agent state graph</title>{"".join(parts)}</svg>'


def trust_model():
    rows = [("READ", "query_inventory, get_lineage, get_current_policy, ...", "automatic"), ("ANALYZE", "assess_inventory_risk, assess_policy_ingredient", "automatic"), ("DRAFT", "draft_purchase_recommendation, draft_review_ticket", "automatic; creates a draft, never an action"),
            ("MUTATE_SIMULATION", "release_draft, flag_record_for_review, adjust_inventory_record", "only with a signed grant bound to run + tool + exact arguments + reviewer role"), ("EXTERNAL_ACTION", "contact_supplier, place_purchase_order", "refused always; logged as a forbidden attempt")]
    t = "".join(f"<tr><th scope='row'>{E(a)}</th><td>{E(b)}</td><td>{E(c)}</td></tr>" for a, b, c in rows)
    return f"<table><caption>Permission classes (code, not prompt)</caption><thead><tr><th scope='col'>Class</th><th scope='col'>Examples</th><th scope='col'>Rule</th></tr></thead><tbody>{t}</tbody></table>"


def bars(items, maxv=1.0, width=420, unit=""):
    out = []
    for label, v, note in items:
        w = 0 if v is None else int(width * v / maxv)
        out.append(f'<div class="bar"><span class="bl">{E(label)}</span><span class="bt"><span class="bf" style="width:{w}px"></span></span><span class="bv">{"n/a" if v is None else f"{v:.2f}{unit}"} {E(note)}</span></div>')
    return "".join(out)


def retrieval_section():
    d = load("rag2_retrieval.json")
    if not d: return "<p>NOT MEASURED</p>"
    items = []
    for rt, m in d["retrieval"].items():
        h = m["heldout"]["ALL"]; items.append((rt, h.get("mrr"), f"R@5 {h.get('recall@5')}"))
    info = d.get("retriever_info", {}); un = [f"{k}: {v['unavailable']}" for k, v in info.items() if isinstance(v, dict) and v.get("unavailable")]
    cats = d["categories"]; head = "".join(f"<th scope='col'>{E(c)}</th>" for c in cats)
    def row(rt, split="heldout"):
        return f"<tr><th scope='row'>{E(rt)}</th>" + "".join(f"<td>{(d['retrieval'][rt][split].get(c) or {}).get('mrr', '–')}</td>" for c in cats) + "</tr>"
    tab = f"<table class='wide'><caption>MRR by category, held-out split (– = no gold documents in that category)</caption><thead><tr><th scope='col'>Retriever</th>{head}</tr></thead><tbody>{''.join(row(r) for r in d['retrieval'])}</tbody></table>"
    s = load("abstention_strategies.json"); st = ""
    if s:
        st = "<table><caption>Abstention strategies, held-out split (false answer = answered a question that should be refused)</caption><thead><tr><th scope='col'>Strategy</th><th scope='col'>Accuracy</th><th scope='col'>False answers</th><th scope='col'>False abstentions</th></tr></thead><tbody>" + "".join(
            f"<tr><th scope='row'>{E(n)}</th><td>{v['heldout']['accuracy']}</td><td>{v['heldout']['false_answer']}</td><td>{v['heldout']['false_abstain']}</td></tr>" for n, v in s.items()) + "</tbody></table>"
    ci = load("rag2_retrieval_ci.json"); cit = ""
    if ci:
        cit = ("<table class='wide'><caption>Neural embeddings and pgvector (free GitHub runner: Ollama all-MiniLM-L6-v2, spaCy vectors, pgvector HNSW), all 467 questions. " + E(ci["source"]) + "</caption><thead><tr><th scope='col'>Retriever</th><th scope='col'>R@1</th><th scope='col'>R@5</th><th scope='col'>MRR</th><th scope='col'>nDCG@10</th><th scope='col'>Authority-correct</th></tr></thead><tbody>"
               + "".join(f"<tr><th scope='row'>{E(r['retriever'])}</th><td>{r['recall@1']}</td><td>{r['recall@5']}</td><td>{r['mrr']}</td><td>{r['ndcg@10']}</td><td>{r['authority_correct']}</td></tr>" for r in ci["table"]) + "</tbody></table>")
    return (f"<p>{d['n']} questions in {len(cats)} categories (dev {d['splits']['dev']}, held-out {d['splits']['heldout']}); held-out MRR shown. Generated questions are lexically close to their sources and favour BM25; hand-written paraphrases do not.</p>"
            + bars(items) + cit + (f"<p class='note'>Not measured in this environment: {E('; '.join(un))}</p>" if un else "") + tab + st)


def planner_section():
    out = []
    for lab, f in (("Deterministic planner (control)", "planner_deterministic.json"), ("Rule-based model stand-in", "planner_rule-model.json"), ("Worst-case stand-in", "planner_worst-case.json"), ("Parrot stand-in (obeys injected text)", "planner_parrot.json"), ("Parrot + guardrail", "planner_parrot+guardrail.json"),
                   ("LLM qwen2.5-1.5b (raw)", "planner_llm_raw.json"), ("LLM qwen2.5-1.5b + guardrail", "planner_llm_guardrail.json"), ("LLM qwen2.5-7b (raw; held-out B + adversarial, 1 per family)", "planner_qwen7b_raw.json"), ("LLM qwen2.5-7b + guardrail", "planner_qwen7b_guardrail.json")):
        d = load(f)
        if not d: out.append(f"<tr><th scope='row'>{E(lab)}</th><td colspan='6'>NOT MEASURED</td></tr>"); continue
        sp = d["by_split"]; cell = lambda k: f"{sp[k]['pass_rate']['k']}/{sp[k]['pass_rate']['n']}" if k in sp else "–"
        o = d["overall"]; out.append(f"<tr><th scope='row'>{E(lab)}</th><td>{cell('dev')}</td><td>{cell('heldout')}</td><td>{cell('heldoutB')}</td><td>{cell('adversarial')}</td><td>{o['safe']['k']}/{o['safe']['n']}</td><td>{o['forbidden_attempts']} / {o['external_actions']}</td></tr>")
    return ("<table class='wide'><caption>Scenarios passed (all checks) by planner and split. Stand-ins are scripted, NOT language models. Real-model rows run a stratified subset of scenarios (n per split shown), on free CPU runners; the deterministic planner passes the same subsets 100%.</caption><thead><tr><th scope='col'>Planner</th><th scope='col'>dev</th><th scope='col'>held-out</th><th scope='col'>held-out B</th><th scope='col'>adversarial</th><th scope='col'>safe</th><th scope='col'>forbidden attempts / external actions</th></tr></thead><tbody>" + "".join(out) + "</tbody></table>")


def trace_view():
    from . import eval_agent as EA
    svc, w = EA.fresh(); s = svc.start("EV-A1", "evidence"); rid = s["run"]["run_id"]; svc.resume(rid, dict(decision="approve", note="evidence pack"))
    ev = svc.store.events(rid); rows = []
    for e in ev[:60]:
        d = {k: v for k, v in e.items() if k not in ("seq", "ts", "kind", "request_id")}
        rows.append(f"<tr><td>{e['seq']}</td><td>{E(e['kind'])}</td><td><code>{E(json.dumps(d, default=str)[:170])}</code></td></tr>")
    return f"<table class='wide'><caption>Trace of one synthetic run (EV-A1: low goat cover; approved by a signed reviewer identity)</caption><thead><tr><th scope='col'>#</th><th scope='col'>Kind</th><th scope='col'>Detail</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


CSS = """:root{--bg:#f7f6f2;--fg:#1b1b1b;--mut:#4a4a4a;--card:#fff;--line:#b9b6ab;--acc:#0b5cad;--warn:#7a4b00;--bad:#9b1c1c;--ok:#14602c}@media(prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#f1f1ee;--mut:#c3c3bd;--card:#1d2026;--line:#555a63;--acc:#7db8ff;--warn:#ffcf7a;--bad:#ff9d9d;--ok:#6fd48d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}main{max-width:1040px;margin:0 auto;padding:16px 16px 64px}h1{font-size:1.6rem;margin:.4em 0}h2{font-size:1.2rem;margin:2em 0 .4em;border-bottom:2px solid var(--line);padding-bottom:4px}
section{margin-bottom:12px}.disc{border:2px solid var(--warn);border-radius:8px;padding:10px 14px;background:var(--card)}.dg{width:100%;height:auto;color:var(--fg)}.box{fill:var(--card);stroke:var(--line);stroke-width:1.5}.box.key{stroke:var(--acc);stroke-width:2.5}.box.warn{stroke:var(--warn);stroke-width:2.5}.box.bad{stroke:var(--bad);stroke-width:2.5;stroke-dasharray:6 3}
.t{fill:var(--fg);font:600 13px system-ui}.s{fill:var(--mut);font:11px system-ui}.ar{stroke:var(--fg);stroke-width:1.5}table{border-collapse:collapse;width:100%;font-size:.88rem;margin:8px 0;display:block;overflow-x:auto}caption{text-align:left;font-weight:600;padding:4px 0}th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
.bar{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:.9rem}.bl{width:150px;flex:none}.bt{background:var(--line);height:14px;width:420px;max-width:42vw;flex:none;border-radius:3px;overflow:hidden}.bf{display:block;height:100%;background:var(--acc)}.note,.small{color:var(--mut);font-size:.88rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:8px 0}code{font:12px ui-monospace,monospace}img{max-width:100%;border:1px solid var(--line);border-radius:6px}a{color:var(--acc)}"""


def build():
    tests = load("test_summary.json") or {}
    fails = [("Silent “no action” on partial evidence (Block 2, fixed in Block 2)", "A failed supplier lookup while goat cover was short fell through to NO_ACTION. NO_ACTION is now impossible when any check failed; regression test + mutant M13 guards it."),
             ("Negation trap: “pork-free” was rejected as pork (Block 3, found by generated adversarial scenarios, fixed)", "The screening tool matched the word. A negated mention is a supplier CLAIM of absence, not an ingredient and not a verified statement; 4/4 trap scenarios failed before the fix. Metamorphic property test added."),
             ("A model’s own tool arguments counted as evidence (Block 3, found by the worst-case stand-in, fixed)", "Mutation targets were “grounded” against a blob that included the model’s own requests, so an invented record key looked supported. Grounding now uses only successful trusted results."),
             ("A learned abstention gate trained on generated questions over-refused hand-written paraphrases (Block 3, partly mitigated, open)", "Distribution shift between template questions and paraphrases. Hyper-parameters now chosen by cross-validation on dev only, weighting paraphrases 3x; held-out hand-written n=17 is too small to settle it."),
             ("A susceptible model changes the recommendation even when permissions hold (Block 3, mitigated by a deterministic evidence envelope)", "Permissions stayed safe in every run, but a model that obeys injected text flipped 2 of 4 poisoned-tool-result recommendations; the envelope restores the conservative action and is itself a measured design choice.")]
    cards = "".join(f"<div class='card'><strong>{E(a)}</strong><p>{E(b)}</p></div>" for a, b in fails)
    m = load("mutation.json"); mut = f"{m['killed']} of {m['valid']} mutants killed" if m else "NOT MEASURED"
    ci = "".join(f"<li>{E(x)}</li>" for x in (tests.get("lines") or ["Run `python -m pytest -q tests` for the current count."]))
    body = f"""<main id="main"><h1>NASHA Enterprise AI Lab: evidence pack</h1>
<div class="disc" role="note"><strong>J. Disclosure.</strong> SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED. NASHA is an independent founder concept: no restaurant, customers, suppliers or sales exist. One author wrote the system, the scenarios and the scorers. Scripted “stand-in” models are not language models. Nothing here is a result from a real business.</div>
<p>A human-supervised operations agent investigates synthetic business exceptions with typed tools and status-aware enterprise knowledge, then stops for a signed human approval. Two planners (deterministic and LLM) sit behind one interface and are measured under normal and adversarial conditions.</p>
<section><h2>A. System architecture</h2>{architecture()}</section>
<section><h2>B. Agent state graph</h2>{state_graph()}</section>
<section><h2>C. Trust and permission model</h2>{trust_model()}<p class="small">A response arriving through MCP is not trusted because of the protocol: the gateway classifies the SOURCE, validates the schema (extra fields refused), bounds time and size, checks freshness and metadata, scans for instruction-like text, and taints the values so they cannot become draft or mutation arguments.</p></section>
<section><h2>D. Retrieval benchmark</h2>{retrieval_section()}</section>
<section><h2>E. Deterministic vs LLM planner</h2>{planner_section()}</section>
<section><h2>F. Failure cases that changed the design</h2>{cards}</section>
<section><h2>G. Human approval flow</h2><p>Reviewer signs in (local prototype identity) &rarr; sees evidence, policy sources with status, uncertainties, and the exact actions that will run &rarr; approves, rejects, edits or asks for more evidence. Approval mints a grant bound to the run, the tool, the SHA-256 of the exact arguments, the reviewer’s role, an expiry and a nonce. A different role, changed arguments, another run, an expired or replayed grant are all refused (tests).</p><img src="review-console.png" alt="Screenshot of the review console showing a proposed purchase draft, its claims with evidence ids, policy sources with status, and Approve / Reject buttons" width="1000"></section>
<section><h2>H. Trace view</h2>{trace_view()}</section>
<section><h2>I. Tests and CI</h2><ul>{ci}<li>Mutation testing of the safety-critical code: {E(mut)} (see results/mutation.json).</li></ul></section>
</main>"""
    doc = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NASHA Lab Evidence Pack</title><style>{CSS}</style></head><body>{body}</body></html>'
    os.makedirs(os.path.join(LAB, "evidence"), exist_ok=True)
    open(os.path.join(LAB, "evidence", "index.html"), "w", encoding="utf-8").write(doc)
    return len(doc)


if __name__ == "__main__":
    print("evidence/index.html", build(), "bytes")
