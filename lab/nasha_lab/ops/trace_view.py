"""Trace inspection (P1 item 8): view a run's timeline, approval state and alerts. SYNTHETIC / SIMULATED.
  python -m nasha_lab.ops trace --list                      # runs available in results/ops/sample_traces.json
  python -m nasha_lab.ops trace RUN_ID [--file F.json]      # one run from a saved sample file
  python -m nasha_lab.ops trace RUN_ID --store S.sqlite     # a run in a live trace store (nasha_lab.trace.Store path)"""
import json
import os
import sys

from . import LABEL
from .util import RESULTS_DIR, load_json


def render(t):
    L = [LABEL, f"run {t['run_id']}  family={t.get('family')}  planner={t.get('planner')} ({t.get('model')})  ground truth={t.get('ground_truth', 'n/a')}",
         f"outcome={t.get('outcome')}  category={t.get('outcome_category')}  approval state={t.get('approval_state')}  action={t.get('action')}  run_ms={t.get('run_ms')}",
         "versions: " + ", ".join(f"{k}={v}" for k, v in (t.get("versions") or {}).items()), "alerts: " + (", ".join(f"{a['rule']}:{a['cls']}({a['severity']}) @step {a['step']}" for a in t.get("alerts", [])) or "none"), "-" * 78]
    for e in t["events"]:
        extra = " ".join(f"{k}={v}" for k, v in e.items() if k not in ("seq", "t_ms", "kind"))
        L.append(f"{e['seq']:>3} {e['t_ms']:>9.2f} ms  {e['kind']:<22} {extra}")
    if t.get("events_total", 0) > len(t["events"]): L.append(f"... {t['events_total'] - len(t['events'])} more events not shown")
    return "\n".join(L)


def from_store(path, run_id):
    from ..trace import Store
    st = Store(path); run = st.run(run_id)
    if not run: raise SystemExit(f"no run {run_id} in {path}")
    ev = st.events(run_id); t0 = ev[0]["ts"]
    from .runner import K  # noqa: F401  (pins nothing new; keeps import side effects identical to other entry points)
    from .evaluate_ops import _brief
    return dict(run_id=run_id, family=next((e.get("family") for e in ev if e.get("family")), None), outcome=run["outcome"], outcome_category=run["status"], approval_state=("approved" if any(e.get("decision") == "approve" for e in ev) else "pending/other"),
                events=[_brief(e, t0) for e in ev], events_total=len(ev), alerts=[])


def main(argv):
    a = list(argv)
    path = os.path.join(RESULTS_DIR, "sample_traces.json")
    if "--file" in a: i = a.index("--file"); path = a[i + 1]; del a[i:i + 2]
    store = None
    if "--store" in a: i = a.index("--store"); store = a[i + 1]; del a[i:i + 2]
    if "--list" in a or not a:
        for t in load_json(path)["traces"]: print(f"{t['run_id']}  {t['ground_truth']:<24} {t['outcome_category']:<18} approval={t['approval_state']:<10} alerts={[x['rule'] for x in t['alerts']]}")
        return 0
    t = from_store(store, a[0]) if store else next((x for x in load_json(path)["traces"] if x["run_id"] == a[0]), None)
    if t is None: print("run not found", file=sys.stderr); return 1
    print(render(t)); return 0
