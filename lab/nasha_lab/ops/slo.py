"""SLO design targets + multi-window burn-rate evaluation over run records (P1 item 7). DESIGN TARGETS (ASSUMPTIONS) on SYNTHETIC telemetry.
Windows are counted in runs, not time (see lab/ops/slo-design-targets.json)."""
import os

from .util import OPS_DIR, load_json
from . import LABEL

SLO_PATH = os.path.join(OPS_DIR, "slo-design-targets.json")
AVAIL_BAD = ("TIMEOUT", "UPSTREAM_FAILURE", "MALFORMED_RESULT", "CIRCUIT_OPEN")


def load_slos(path=SLO_PATH): return load_json(path)


def sli(slo_id, rec, cfg):
    """(good, total) for one run record. total == 0 means the run does not count toward this SLO."""
    if slo_id == "SLO-1": return (0 if rec["outcome_category"] in ("CRASHED", "FAILED") else 1), 1
    if slo_id == "SLO-2":
        bad = sum(n for v in rec["tools"].values() for c, n in v["codes"].items() if c in AVAIL_BAD)
        return rec["tool_calls"] - bad, rec["tool_calls"]
    if slo_id == "SLO-3":
        thr = next(s for s in cfg["slos"] if s["id"] == "SLO-3")["latency_threshold_ms"]
        return (1 if rec["timing"]["run_ms"] <= thr else 0), 1
    if slo_id == "SLO-4":
        r = rec["retrieval"]; return r["hit"] + r["abstain"], r["hit"] + r["abstain"] + r["miss"]
    if slo_id == "SLO-5": return (1 if rec["safety"]["approval_boundary_ok"] and rec["safety"]["external_actions"] == 0 else 0), 1
    if slo_id == "SLO-6":
        p = rec["planner"]
        if not (p["llm_calls"] or p["llm_errors"]): return 0, 0
        return (0 if p["llm_errors"] or p["planner_failure"] else 1), 1
    raise KeyError(slo_id)


def burn(good, total, objective):
    if total == 0: return 0.0
    bad = (total - good) / total
    return float("inf") if objective >= 1.0 and bad > 0 else (0.0 if objective >= 1.0 else bad / (1.0 - objective))


def _window(records, i, n, slo_id, cfg):
    g = t = 0
    for r in records[max(0, i + 1 - n): i + 1]:
        a, b = sli(slo_id, r, cfg); g += a; t += b
    return g, t


def evaluate(records, cfg=None):
    """Replay the records in order; after each run evaluate every (SLO, burn alert) pair. Returns attainment per SLO and the burn-alert firings."""
    cfg = cfg or load_slos(); out_slos, firings = [], []
    for slo in cfg["slos"]:
        g = t = 0
        for r in records: a, b = sli(slo["id"], r, cfg); g += a; t += b
        allowed = (1.0 - slo["objective"]) * t
        out_slos.append(dict(id=slo["id"], name=slo["name"], objective=slo["objective"], good=g, total=t, attainment=round(g / t, 4) if t else None,
                             budget_allowed_bad=round(allowed, 3), bad=t - g, budget_consumed=(round((t - g) / allowed, 3) if allowed > 0 else (None if t - g == 0 else "exhausted (zero budget)")),
                             status="NO_DATA" if not t else ("MET" if g / t >= slo["objective"] else "BREACHED")))
        for ba in cfg["burn_alerts"]:
            first, last, n_fire, peak = None, None, 0, 0.0
            for i in range(len(records)):
                if i + 1 < ba["short_window"]: continue
                gl, tl = _window(records, i, ba["long_window"], slo["id"], cfg); gs, ts = _window(records, i, ba["short_window"], slo["id"], cfg)
                bl, bs = burn(gl, tl, slo["objective"]), burn(gs, ts, slo["objective"])
                if bl >= ba["burn_rate"] and bs >= ba["burn_rate"]:
                    first = i if first is None else first; last = i; n_fire += 1; peak = max(peak, min(bl, bs) if bl != float("inf") and bs != float("inf") else 9999.0)
            if first is not None:
                firings.append(dict(slo=slo["id"], burn_alert=ba["id"], severity="SEV1" if slo["objective"] >= 1.0 else ba["severity"], action=ba["action"], first_run_index=first, last_run_index=last, runs_firing=n_fire,
                                    peak_burn=peak if peak != 9999.0 else "inf"))
    return dict(slo_version=cfg["slo_version"], label=cfg["label"], runs=len(records), slos=out_slos, burn_alerts=firings, synthetic_label=LABEL)
