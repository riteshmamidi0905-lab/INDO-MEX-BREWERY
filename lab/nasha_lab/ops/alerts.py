"""Declarative alert rules + evaluator + incident generation (P1 item 5). SYNTHETIC / SIMULATED / OFFLINE.
Rules live in lab/ops/alert-rules.json; classes and severities in lab/ops/failure-taxonomy.json. The evaluator replays a run's trace events in order, so
every alert carries the position (step) and elapsed time (ms, from the trace timestamps) at which its triggering evidence first existed."""
import os
import re

from .util import OPS_DIR, load_json, quantile, sha
from . import LABEL

RULES_PATH = os.path.join(OPS_DIR, "alert-rules.json")
TAXONOMY_PATH = os.path.join(OPS_DIR, "failure-taxonomy.json")


def load_rules(path=RULES_PATH): return load_json(path)
def load_taxonomy(path=TAXONOMY_PATH): return load_json(path)


def _get(obj, path):
    for p in path.split("."):
        if isinstance(obj, dict) and p in obj: obj = obj[p]
        else: return None
    return obj


def _match(value, cond):
    if isinstance(cond, dict):
        for op, arg in cond.items():
            if op == "in" and value not in arg: return False
            elif op == "regex" and not (isinstance(value, str) and re.search(arg, value)): return False
            elif op == "not_regex" and (not isinstance(value, str) or re.search(arg, value)): return False
            elif op == "gte" and not (isinstance(value, (int, float)) and value >= arg): return False
            elif op == "gt" and not (isinstance(value, (int, float)) and value > arg): return False
            elif op not in ("in", "regex", "not_regex", "gte", "gt"): raise ValueError(f"unknown operator {op}")
        return True
    return value == cond


def _when(obj, when): return all(_match(_get(obj, k) if "." in k else obj.get(k), c) for k, c in when.items())


def window_metric(records, metric, agg):
    if metric == "tool_failure_rate":
        calls = sum(r["tool_calls"] for r in records); return (sum(r["tool_failures"] for r in records) / calls) if calls else 0.0
    vals = [_get(r, metric) for r in records]; vals = [v for v in vals if v is not None]
    if agg.startswith("p"): return quantile(vals, int(agg[1:]) / 100)
    if agg == "mean": return sum(vals) / len(vals) if vals else None
    raise ValueError(agg)


class AlertEvaluator:
    def __init__(self, rules=None, taxonomy=None):
        self.cfg = rules or load_rules(); self.tax = taxonomy or load_taxonomy()
        self.rules = {r["id"]: r for r in self.cfg["rules"]}; self.classes = {c["id"]: c for c in self.tax["classes"]}
        bad = [r["id"] for r in self.cfg["rules"] if r["class"] not in self.classes]
        if bad: raise ValueError(f"rules reference unknown classes: {bad}")

    def _alert(self, rule, subject, step, ts_ms, detail, count=1):
        c = self.classes[rule["class"]]
        return dict(alert_id="AL-" + sha(f"{rule['id']}|{subject}|{step}", 8), rule_id=rule["id"], cls=rule["class"], severity=rule["severity"], runbook=c["runbook"], subject=subject,
                    step=step, elapsed_ms=round(ts_ms, 3) if ts_ms is not None else None, detail=detail, count=count)

    def scan_events(self, events, subject=None, start=0, t0=None):
        """Replay events in order. One alert per rule; `count` says how many events matched. `step` is the 1-based position of the first matching event,
        counted from `start` (events before `start` are skipped); elapsed_ms is measured from `t0` (default: the first replayed event)."""
        out, seen = [], {}
        if t0 is None and len(events) > start: t0 = events[start]["ts"]
        for i, e in enumerate(events, 1):
            if i <= start: continue
            for r in self.cfg["rules"]:
                if r["scope"] != "event" or not _when(e, r["when"]): continue
                if r["id"] in seen: seen[r["id"]]["count"] += 1; continue
                a = self._alert(r, subject, i - start, (e["ts"] - t0) * 1000, f"{e['kind']}: " + ", ".join(f"{k}={str(e.get(k))[:60]}" for k in ("tool", "code", "error", "message") if e.get(k) is not None))
                seen[r["id"]] = a; out.append(a)
        return out

    def scan_run(self, record, n_events=None, span_ms=None):
        out = []
        for r in self.cfg["rules"]:
            if r["scope"] == "run" and _when(record, r["when"]):
                out.append(self._alert(r, record["run_id"], (n_events or record["trace_events"]) + 1, span_ms if span_ms is not None else record["timing"]["trace_span_ms"], f"run-level: {r['description'][:80]}"))
        return out

    def scan_window(self, records, index):
        """Evaluate window rules after run `index` (0-based) completed. Returns alerts whose condition holds NOW (the caller tracks firing/resolution)."""
        out = []
        for r in self.cfg["rules"]:
            if r["scope"] != "window": continue
            w = records[max(0, index + 1 - r["window"]): index + 1]
            if len(w) < r["min_runs"]: continue
            v = window_metric(w, r["metric"], r["agg"])
            if v is not None and ((r["op"] == ">" and v > r["value"]) or (r["op"] == ">=" and v >= r["value"])):
                a = self._alert(r, f"window@{index}", index, None, f"{r['agg']}({r['metric']}) over {len(w)} runs = {round(v, 3)} {r['op']} {r['value']}"); a["observed"] = round(v, 3); out.append(a)
        return out

    def scan_gate(self, gate_result, subject="gate"):
        return [self._alert(r, subject, 0, None, "gate: " + "; ".join(gate_result.get("reasons", []))[:200]) for r in self.cfg["rules"] if r["scope"] == "gate" and _when(gate_result, r["when"])]

    def scan_run_full(self, events, record):
        """All event + run alerts for one run, ordered by step."""
        al = self.scan_events(events, record["run_id"]) + self.scan_run(record, len(events), (events[-1]["ts"] - events[0]["ts"]) * 1000 if events else 0.0)
        return sorted(al, key=lambda a: (a["step"], a["rule_id"]))


# ======================================================================================================= incidents
def correlate(alerts, taxonomy):
    """Group alerts per subject. A class that the taxonomy lists as a child of another class present on the same subject is attached to that parent's incident."""
    child_of = {}
    for parent, kids in taxonomy["correlation"].items():
        for k in kids: child_of.setdefault(k, set()).add(parent)
    by_sub = {}
    for a in alerts: by_sub.setdefault(a["subject"], []).append(a)
    groups = []
    for sub, al in by_sub.items():
        al = sorted(al, key=lambda x: (x["step"], x["rule_id"])); present = {a["cls"] for a in al}
        primaries = {c for c in present if not (child_of.get(c, set()) & present)}
        gs = {c: dict(subject=sub, primary=next(a for a in al if a["cls"] == c), related=[]) for c in sorted(primaries)}
        for a in al:
            home = a["cls"] if a["cls"] in gs else sorted(child_of[a["cls"]] & present)[0]
            while home not in gs: home = sorted(child_of[home] & present)[0]
            if gs[home]["primary"] is not a: gs[home]["related"].append(a)
        groups += list(gs.values())
    return groups


def make_incidents(alerts, taxonomy=None, context=None):
    """One INCIDENT per correlated alert group. status starts OPEN; the caller advances it with `advance`. context: {subject: {timeline entries / meta}}."""
    taxonomy = taxonomy or load_taxonomy(); classes = {c["id"]: c for c in taxonomy["classes"]}; out = []
    for g in correlate(alerts, taxonomy):
        a = g["primary"]; c = classes[a["cls"]]
        inc = dict(incident_id="INC-" + sha(f"{a['rule_id']}|{a['subject']}", 8), cls=a["cls"], severity=a["severity"], detection_rule=a["rule_id"], runbook_id=c["runbook"], status="OPEN", subject=a["subject"],
                   layer=c["layer"], expected_containment=c["expected_containment"], opened_step=a["step"], opened_elapsed_ms=a["elapsed_ms"], related_alerts=[x["rule_id"] + "@" + str(x["step"]) for x in g["related"]],
                   timeline=[dict(step=a["step"], t_ms=a["elapsed_ms"], event="DETECTED", detail=f"{a['rule_id']} {a['detail']}")], label=LABEL)
        if context and a["subject"] in context: inc["context"] = context[a["subject"]]
        out.append(inc)
    return out


def advance(inc, status, event, detail="", step=None, t_ms=None):
    assert status in ("OPEN", "CONTAINED", "RECOVERING", "RESOLVED", "UNRESOLVED")
    inc["status"] = status; inc["timeline"].append(dict(step=step, t_ms=t_ms, event=event, detail=detail)); return inc
