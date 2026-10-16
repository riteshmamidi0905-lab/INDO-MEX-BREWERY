"""Re-analysis of the FROZEN planner result files for the P3 product case (SYNTHETIC DATA, same author, offline).

Nothing here runs a planner, a model or a benchmark. It reads `results/*.json` (never writes there) and the scenario REGISTRY
(`nasha_lab.scenarios.build`, which only constructs scenario definitions) to attach each row's expected answer, then answers
workflow-specific questions the original reports did not break out:

  Q1  Where did the raw 1.5B model's silent `NO_ACTION` (all-clear when action was needed) occur: which event family?
  Q2  What did each planner do on the D-54 policy family, in which direction did its errors lean?
  Q3  How many scenarios in the suite have "no action" as the correct answer (this limits any false-alarm claim)?
  Q4  Latency on the same scenario ids.
  Q5  A tiny probe of the NON-AI baseline's weak spot: the D-54 screen is a lexicon (14 tokens + a hidden-derivative list).

Pre-stated decision rules (written before looking at Q1/Q2/Q5 output):
  Q1  If the silent all-clear concentrates in INVENTORY events, the choice of the inventory workflow for the case is the right place
      to apply the strictest rule (no LLM may be the only thing standing between an exception and a human).
  Q5  Existence probe, NOT a rate: the terms are author-selected and outside the lexicon by construction, so a miss is guaranteed
      for them. The rule is: if at least one clearly beef/pork-derived term returns NO_POLICY_SIGNAL, the lexicon needs an owner and
      an update process (requirement FR-12) and the screen's display must never read as a clearance.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
RESULTS = LAB / "results"

# planner result files used (all committed, all frozen or recovered-from-CI)
FILES = {
    "deterministic": "planner_deterministic.json",        # 259 scenarios, 4 splits
    "qwen1.5b_raw": "planner_qwen1.5b_run2_raw.json",      # 140 scenarios, CI run 38784135017
    "qwen1.5b_guardrail": "planner_qwen1.5b_run2_guardrail.json",
    "qwen7b_raw": "planner_qwen7b_raw.json",               # 35 scenarios, CI run 38787190128
    "qwen7b_guardrail": "planner_qwen7b_guardrail.json",
}


def wilson(k: int, n: int, z: float = 1.96):
    """Wilson score interval (the same family of interval the lab's result files use)."""
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 3), round(min(1.0, c + h), 3))


def _registry():
    from nasha_lab import scenarios as S
    dev, held, adv = S.build()
    hb = S.build_b()
    reg = {}
    for s in dev + held + adv + hb:
        reg[s.id] = s            # one id is duplicated in the frozen set (results/ERRATA.md item 4); the later definition wins, expectations are identical in kind
    return reg


def load_rows(key: str):
    return json.loads((RESULTS / FILES[key]).read_text())["rows"]


def _need(s):      # an exception that REQUIRES an action: NO_ACTION is not an acceptable answer
    return "NO_ACTION" not in s.expected["action"]


def _healthy(s):   # NO_ACTION is the only acceptable answer
    return s.expected["action"] == {"NO_ACTION"}


def family_breakdown(key: str, reg=None):
    """Per event family: how many scenarios needed action, how many got a silent NO_ACTION, how many got the acceptable action."""
    reg = reg or _registry()
    out = {}
    for fam in ("INVENTORY", "DATA_QUALITY", "POLICY"):
        rows = [r for r in load_rows(key) if reg[r["id"]].event_family == fam]
        need = [r for r in rows if _need(reg[r["id"]])]
        healthy = [r for r in rows if _healthy(reg[r["id"]])]
        silent = sum(1 for r in need if r["action"] == "NO_ACTION")
        act_ok = sum(1 for r in need if r["action_ok"])
        fa = sum(1 for r in healthy if r["action"] != "NO_ACTION")
        out[fam] = dict(
            n=len(rows), need_action=len(need), silent_all_clear=silent, silent_ci95=wilson(silent, len(need)),
            correct_action_when_needed=act_ok, correct_action_ci95=wilson(act_ok, len(need)),
            healthy_n=len(healthy), false_alarms_on_healthy=fa, pass_all_checks=sum(1 for r in rows if r["pass"]),
        )
    return out


def policy_direction(key: str, reg=None):
    """D-54 family: where the planner's action fell relative to the oracle's acceptable set."""
    reg = reg or _registry()
    rows = [r for r in load_rows(key) if reg[r["id"]].event_family == "POLICY"]
    c = Counter()
    for r in rows:
        exp = reg[r["id"]].expected["action"]
        a = r["action"]
        if a in exp:
            c["acceptable"] += 1
        elif a == "RECOMMEND_HUMAN_CONFIRM_SPEC":
            c["leans_toward_confirm_where_oracle_required_abstain_or_reject"] += 1
        elif a == "RECOMMEND_REJECT_SUBSTITUTION":
            c["rejects_where_oracle_allowed_only_abstain_or_confirm"] += 1
        elif a in ("ABSTAIN_REQUIRE_REVIEW", "ESCALATE_INSUFFICIENT_EVIDENCE"):
            c["abstains_where_oracle_wanted_a_specific_recommendation"] += 1
        else:
            c["other"] += 1
    return dict(n=len(rows), **dict(sorted(c.items())))


def latency_same_ids(reg=None):
    """File-stated p50 latencies (`overall.latency_ms_p50`) plus the deterministic median on the 140 ids the 1.5B run used.
    Deterministic rows and model rows come from different hosts (a 4-vCPU CI runner for the models): ratios are order-of-magnitude only."""
    def p50(key):
        return json.loads((RESULTS / FILES[key]).read_text())["overall"]["latency_ms_p50"]
    det = {r["id"]: r for r in load_rows("deterministic")}
    ids = [r["id"] for r in load_rows("qwen1.5b_raw")]
    d140 = statistics.median(det[i]["latency_ms"] for i in ids)
    d259, q15, q7 = p50("deterministic"), p50("qwen1.5b_raw"), p50("qwen7b_raw")
    return dict(deterministic_p50_ms_259=d259, deterministic_median_ms_same_140_ids_recomputed=round(d140, 1), qwen1_5b_p50_ms=q15, qwen7b_p50_ms=q7,
                ratio_1_5b_over_det_259=round(q15 / d259), ratio_1_5b_over_det_same_ids=round(q15 / d140), ratio_7b_over_det_259=round(q7 / d259),
                note="ratios are order-of-magnitude only (different hosts; medians, not means)")


def no_action_share(reg=None):
    reg = reg or _registry()
    rows = load_rows("deterministic")
    h = sum(1 for r in rows if _healthy(reg[r["id"]]))
    return dict(n=len(rows), expected_exactly_no_action=h, share=round(h / len(rows), 3), ci95=wilson(h, len(rows)))


# --------------------------------------------------------------------------- Q5: the non-AI baseline's weak spot
PROBE_IN_LEXICON = ["beef stock", "pork lard", "bacon bits", "beef tallow", "gelatin"]
PROBE_OUT_OF_LEXICON_ANIMAL = [        # beef/pork-derived by common culinary knowledge; author-selected; outside the 14-token lexicon on purpose
    "suet", "pepperoni", "pancetta", "gelatine", "oxtail", "ribeye", "bone marrow", "hamburger patty", "salami", "prosciutto"]
PROBE_BENIGN = ["cauliflower", "sunflower oil", "Hamilton sauce", "corn masa"]


def lexicon_probe():
    from nasha_lab import tools as T

    def verdict(text):
        return T.t_assess_policy_ingredient(None, T.PolicyAssessIn(ingredient_text=text, declared_source="unspecified", spec_sheet_status="MISSING"), None)["verdict"]
    res = {
        "in_lexicon": {t: verdict(t) for t in PROBE_IN_LEXICON},
        "out_of_lexicon_animal": {t: verdict(t) for t in PROBE_OUT_OF_LEXICON_ANIMAL},
        "benign": {t: verdict(t) for t in PROBE_BENIGN},
    }
    miss = [t for t, v in res["out_of_lexicon_animal"].items() if v != "PROHIBITED"]
    res["summary"] = dict(
        in_lexicon_prohibited=f"{sum(v == 'PROHIBITED' for v in res['in_lexicon'].values())}/{len(PROBE_IN_LEXICON)}",
        out_of_lexicon_not_flagged=f"{len(miss)}/{len(PROBE_OUT_OF_LEXICON_ANIMAL)}",
        benign_prohibited=f"{sum(v == 'PROHIBITED' for v in res['benign'].values())}/{len(PROBE_BENIGN)}",
        caveat="existence probe, not a rate: out-of-lexicon terms were chosen to be outside the lexicon, same author, n=10",
    )
    return res


def build_all():
    reg = _registry()
    out = dict(
        note="SYNTHETIC; re-analysis of frozen result files; nothing re-run",
        families={k: family_breakdown(k, reg) for k in ("deterministic", "qwen1.5b_raw", "qwen1.5b_guardrail", "qwen7b_raw", "qwen7b_guardrail")},
        policy_direction={k: policy_direction(k, reg) for k in ("deterministic", "qwen1.5b_raw", "qwen1.5b_guardrail", "qwen7b_raw")},
        latency=latency_same_ids(reg),
        no_action_share=no_action_share(reg),
        lexicon_probe=lexicon_probe(),
    )
    return out


if __name__ == "__main__":
    dest = Path(__file__).resolve().parent / "results"
    dest.mkdir(exist_ok=True)
    data = build_all()
    (dest / "analysis.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(json.dumps(data["families"]["qwen1.5b_raw"]["INVENTORY"], sort_keys=True))
