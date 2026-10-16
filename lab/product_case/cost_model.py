"""Expected-cost model for the inventory-exception workflow: rules vs LLM planner variants vs a rules-plus-LLM "add-only" hybrid.

SYNTHETIC / ASSUMPTION-DRIVEN. Not a forecast. NASHA has no operation, so every volume and every money figure below is a PLACEHOLDER
(assumptions A-05..A-12 in docs/product/08-assumptions-register.md). The only MEASURED inputs are the miss / wrong-action / false-alarm
counts that product_case.analysis derived from the frozen result files (inventory events only; small n, same author, wide intervals).

DEFINED BEFORE RUNNING
  Hypothesis H1: for the inventory-exception workflow, some AI planner variant has a lower expected cost than the rules-only baseline
                 across most of the plausible parameter space.
  Decision rule: the recommendation "do not use an LLM planner" is REVERSED for a variant V only if V has the lowest expected cost in
                 at least 50% of seeded parameter draws AND in the central case. If a variant only wins when an UNMEASURED parameter
                 (b = rule-gap catch rate of the model, or f = its false-alarm rate as a second opinion) takes favourable values,
                 the result is reported as "conditional on an unmeasured quantity", and the quantity becomes a pilot measurement.
  The model is deliberately generous to the LLM: every LLM option may catch a share b of the rule-gap misses that the rules make.

COST MODEL (per N events; A = actionable events, H = healthy events)
  rules-only        : A*[ g*C + (1-g)*(c_rev + w_det*k*c_rev) ] + H*f_det*c_rev
  LLM planner (x)   : m = s + (1-s)*g*(1-b)  (silent miss; s measured)
                      A*[ m*C + (1-m)*c_rev + w*k*c_rev ] + H*f*c_rev   (w = measured wrong-but-not-silent share; f = false-alarm rate)
  hybrid add-only   : rules decide; the model can only ADD escalations (never remove one):
                      A*[ g*(1-b)*C + (1-g*(1-b))*(c_rev + w_det*k*c_rev) ] + H*(1-(1-f_det)*(1-f_add))*c_rev
  C = cost of one silent miss; c_rev = human review of one proposal; k = rework multiplier; g = rules' silent rule-gap rate (unmeasured);
  b = share of that gap a model would catch (unmeasured); f_add = extra false alarms the model adds as a second opinion (unmeasured).
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20261016
DRAWS = 20000


def measured():
    """Inventory-event counts from product_case/results/analysis.json (derived from frozen result files by product_case.analysis)."""
    a = json.loads((HERE / "results" / "analysis.json").read_text())["families"]
    out = {}
    for key, label in (("deterministic", "rules"), ("qwen1.5b_raw", "llm15_raw"), ("qwen1.5b_guardrail", "llm15_env"), ("qwen7b_raw", "llm7_raw"), ("qwen7b_guardrail", "llm7_env")):
        f = a[key]["INVENTORY"]
        out[label] = dict(need=f["need_action"], silent=f["silent_all_clear"], correct=f["correct_action_when_needed"], healthy=f["healthy_n"], false_alarms=f["false_alarms_on_healthy"])
    return out


@dataclass(frozen=True)
class Params:
    N: int = 1000            # A-05 events per period (PLACEHOLDER)
    p_action: float = 0.20   # A-06 share of events that truly need action (the synthetic suite is 97% actionable and is NOT representative)
    c_miss: float = 500.0    # A-07 cost of one silent miss, currency units (PLACEHOLDER)
    c_rev: float = 5.0       # A-08 human review of one proposal (PLACEHOLDER)
    rework: float = 1.0      # A-09 rework multiplier for a wrong proposal
    g: float = 0.05          # A-10 rules' silent rule-gap rate on real exceptions (UNMEASURED; synthetic 0/119 is same-author)
    b: float = 0.30          # A-11 share of that gap a model would catch (UNMEASURED)
    f_det: float = 0.02      # A-12 rules' false-alarm rate on healthy events (synthetic 0/8; n tiny)
    w_det: float = 0.02      # rules' wrong-action rate on real exceptions (synthetic 0/119)
    f_add: float = 0.30      # A-11b extra false alarms a model adds as second opinion (UNMEASURED)


def _m(p: Params, key: str, M: dict, post_mean: bool = True):
    d = M[key]
    s = (d["silent"] + 1) / (d["need"] + 2) if post_mean else d["silent"] / d["need"]
    w = max(0.0, (d["need"] - d["correct"] - d["silent"]) / d["need"])
    f = (d["false_alarms"] + 1) / (d["healthy"] + 2) if d["healthy"] else None
    return s, w, f


def cost_rules(p: Params):
    A, H = p.N * p.p_action, p.N * (1 - p.p_action)
    miss = A * p.g * p.c_miss
    review = A * (1 - p.g) * p.c_rev
    rework = A * (1 - p.g) * p.w_det * p.rework * p.c_rev
    fa = H * p.f_det * p.c_rev
    return dict(miss=miss, review=review, rework=rework, false_alarm=fa, total=miss + review + rework + fa)


def cost_llm(p: Params, s: float, w: float, f: float):
    A, H = p.N * p.p_action, p.N * (1 - p.p_action)
    m = s + (1 - s) * p.g * (1 - p.b)
    miss = A * m * p.c_miss
    review = A * (1 - m) * p.c_rev
    rework = A * w * p.rework * p.c_rev
    fa = H * f * p.c_rev
    return dict(miss=miss, review=review, rework=rework, false_alarm=fa, total=miss + review + rework + fa)


def cost_hybrid(p: Params, f_add: float | None = None):
    f_add = p.f_add if f_add is None else f_add
    A, H = p.N * p.p_action, p.N * (1 - p.p_action)
    g_eff = p.g * (1 - p.b)
    miss = A * g_eff * p.c_miss
    review = A * (1 - g_eff) * p.c_rev
    rework = A * (1 - g_eff) * p.w_det * p.rework * p.c_rev
    fa = H * (1 - (1 - p.f_det) * (1 - f_add)) * p.c_rev
    return dict(miss=miss, review=review, rework=rework, false_alarm=fa, total=miss + review + rework + fa)


OPTIONS = ("rules_only", "llm15_raw", "llm15_envelope", "llm7_raw", "llm7_envelope", "hybrid_add_only")


def evaluate(p: Params, M: dict | None = None, f_unmeasured_7b: float = 0.5, f_add: float | None = None):
    """Expected cost per N events for every option at ONE parameter point (posterior means for the measured rates)."""
    M = M or measured()
    out = {"rules_only": cost_rules(p)}
    for opt, key in (("llm15_raw", "llm15_raw"), ("llm15_envelope", "llm15_env"), ("llm7_raw", "llm7_raw"), ("llm7_envelope", "llm7_env")):
        s, w, f = _m(p, key, M)
        f = f_unmeasured_7b if f is None else f
        out[opt] = cost_llm(p, s, w, f)
    out["hybrid_add_only"] = cost_hybrid(p, f_add)
    return out


def central_case(M=None):
    p = Params()
    r = evaluate(p, M)
    return dict(params=p.__dict__, cost={k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in r.items()},
                best=min(r, key=lambda k: r[k]["total"]))


def grid(M=None):
    """C_miss x p_action grid for rules vs hybrid (pessimistic f_add = measured planner false-alarm posterior mean; optimistic f_add = 0.05)."""
    M = M or measured()
    _, _, f_meas = _m(Params(), "llm15_raw", M)
    rows = []
    for pa in (0.05, 0.20, 0.50):
        for c in (50.0, 500.0, 5000.0):
            p = replace(Params(), p_action=pa, c_miss=c)
            base = evaluate(p, M)
            hp = cost_hybrid(p, f_meas)["total"]
            ho = cost_hybrid(p, 0.05)["total"]
            llm_best = min(base[k]["total"] for k in ("llm15_raw", "llm15_envelope", "llm7_raw", "llm7_envelope"))
            rows.append(dict(p_action=pa, c_miss=c, rules=round(base["rules_only"]["total"], 1), hybrid_pessimistic=round(hp, 1), hybrid_optimistic=round(ho, 1),
                             best_llm_planner=round(llm_best, 1),
                             winner=min((("rules", base["rules_only"]["total"]), ("hybrid_pessimistic", hp), ("hybrid_optimistic", ho), ("best_llm_planner", llm_best)), key=lambda x: x[1])[0]))
    return rows


def breakeven_c_miss(M=None, f_add_mode="optimistic"):
    """Smallest C_miss (currency) at which the add-only hybrid beats rules-only, other parameters central. None if not within 1e7."""
    M = M or measured()
    _, _, f_meas = _m(Params(), "llm15_raw", M)
    f_add = 0.05 if f_add_mode == "optimistic" else f_meas
    lo, hi = 1.0, 1e7
    p = Params()
    if cost_hybrid(replace(p, c_miss=hi), f_add)["total"] >= cost_rules(replace(p, c_miss=hi))["total"]:
        return None
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if cost_hybrid(replace(p, c_miss=mid), f_add)["total"] < cost_rules(replace(p, c_miss=mid))["total"]:
            hi = mid
        else:
            lo = mid
    return round(hi, 1)


def sensitivity(M=None, draws: int = DRAWS, seed: int = SEED):
    """Seeded random draws over the stated ranges. Measured rates are drawn from Beta(k+1, n-k+1) posteriors (uniform prior)."""
    M = M or measured()
    rng = random.Random(seed)
    wins = {"pess": {k: 0 for k in OPTIONS}, "opt": {k: 0 for k in OPTIONS}}
    ratio = {"pess": [], "opt": []}

    def beta(k, n):
        return rng.betavariate(k + 1, n - k + 1)
    for _ in range(draws):
        p = Params(N=1000, p_action=rng.uniform(0.05, 0.60), c_miss=math.exp(rng.uniform(math.log(50), math.log(5000))), c_rev=rng.uniform(1, 15),
                   rework=rng.uniform(0.5, 1.5), g=rng.uniform(0.0, 0.15), b=rng.uniform(0.0, 0.5), f_det=rng.uniform(0.0, 0.10), w_det=rng.uniform(0.0, 0.05))
        post = {}
        for key in ("llm15_raw", "llm15_env", "llm7_raw", "llm7_env"):
            d = M[key]
            s = beta(d["silent"], d["need"])
            wr = beta(d["need"] - d["correct"] - d["silent"], d["need"])     # wrong-but-not-silent share
            f = beta(d["false_alarms"], d["healthy"]) if d["healthy"] else rng.uniform(0.1, 1.0)
            post[key] = (s, wr, f)
        f_meas = beta(M["llm15_raw"]["false_alarms"], M["llm15_raw"]["healthy"])
        for mode, f_add in (("pess", f_meas), ("opt", rng.uniform(0.0, 0.2))):
            c = {"rules_only": cost_rules(p)["total"],
                 "llm15_raw": cost_llm(p, *post["llm15_raw"])["total"], "llm15_envelope": cost_llm(p, *post["llm15_env"])["total"],
                 "llm7_raw": cost_llm(p, *post["llm7_raw"])["total"], "llm7_envelope": cost_llm(p, *post["llm7_env"])["total"],
                 "hybrid_add_only": cost_hybrid(p, f_add)["total"]}
            wins[mode][min(c, key=c.get)] += 1
            ratio[mode].append(c["hybrid_add_only"] / c["rules_only"])
    out = {}
    for mode in ("pess", "opt"):
        r = sorted(ratio[mode])
        out[mode] = dict(win_share={k: round(v / draws, 3) for k, v in wins[mode].items()},
                         hybrid_over_rules_cost_ratio_p10_p50_p90=[round(r[int(0.1 * draws)], 3), round(r[int(0.5 * draws)], 3), round(r[int(0.9 * draws)], 3)])
    out["draws"], out["seed"] = draws, seed
    out["ranges"] = dict(p_action=[0.05, 0.60], c_miss_logU=[50, 5000], c_rev=[1, 15], rework=[0.5, 1.5], g=[0, 0.15], b=[0, 0.5], f_det=[0, 0.10], w_det=[0, 0.05],
                         f_add_pessimistic="Beta posterior of the 1.5B model's measured false-alarm rate on 4 healthy scenarios (4/4)", f_add_optimistic=[0, 0.2])
    return out


def drafting_breakeven(t_template_min=3.0, t_verify_min=2.0, wage_per_min=0.5, c_err=200.0):
    """LLM drafting-only vs a deterministic template. Net benefit per message of an LLM draft, as a function of the undetected factual-error rate q:
         benefit(q) = (t_template - t_verify) * wage - q * c_err        -> break-even q* = (t_template - t_verify) * wage / c_err
    Every figure is a PLACEHOLDER; the point is the SHAPE: the saving is minutes, so q* is small unless a deterministic validator bounds q."""
    save = (t_template_min - t_verify_min) * wage_per_min
    return dict(saving_per_message=round(save, 3), break_even_undetected_error_rate=round(save / c_err, 5) if c_err else None)


def drafting_table():
    rows = []
    for t_t, t_v in ((3.0, 2.0), (5.0, 2.0), (5.0, 1.0)):
        for c in (50.0, 200.0, 1000.0):
            d = drafting_breakeven(t_t, t_v, 0.5, c)
            rows.append(dict(t_template_min=t_t, t_verify_min=t_v, c_err=c, **d))
    return rows


def verdict(sens: dict, central_best: str | None = None):
    """Apply the decision rule stated in the module docstring to a `sensitivity()` result."""
    planner = ("llm15_raw", "llm15_envelope", "llm7_raw", "llm7_envelope")
    out = {}
    for mode in ("pess", "opt"):
        w = sens[mode]["win_share"]
        out[mode] = dict(llm_planner_combined_win_share=round(sum(w[k] for k in planner), 3), hybrid_win_share=w["hybrid_add_only"], rules_win_share=w["rules_only"])
    planner_reversal = any(out[m]["llm_planner_combined_win_share"] >= 0.5 for m in out) and (central_best is None or central_best in OPTIONS[1:5])
    hybrid_unconditional = all(out[m]["hybrid_win_share"] >= 0.5 for m in out)
    hybrid_any = any(out[m]["hybrid_win_share"] >= 0.5 for m in out)
    out["llm_planner"] = "REVERSE the recommendation" if planner_reversal else "recommendation stands: do not use an LLM as planner"
    out["hybrid_add_only"] = ("wins in both modes" if hybrid_unconditional else
                              "CONDITIONAL on unmeasured quantities (b, f_add): wins only under optimistic f_add; measure in shadow mode before any use" if hybrid_any else "does not win")
    return out


def build_all():
    M = measured()
    return dict(
        note="SYNTHETIC / ASSUMPTION-DRIVEN expected-cost model; PLACEHOLDER money; measured inputs from product_case/results/analysis.json",
        measured_inventory_inputs=M, central_case=central_case(M), grid=grid(M),
        breakeven_c_miss_hybrid_vs_rules=dict(optimistic=breakeven_c_miss(M, "optimistic"), pessimistic=breakeven_c_miss(M, "pessimistic")),
        sensitivity=(sens := sensitivity(M)), verdict=verdict(sens, central_case(M)["best"]), drafting_breakeven_table=drafting_table(),
    )


if __name__ == "__main__":
    data = build_all()
    (HERE / "results" / "cost_model.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(json.dumps(dict(central=data["central_case"]["best"], sens=data["sensitivity"]["pess"]["win_share"]), sort_keys=True))
