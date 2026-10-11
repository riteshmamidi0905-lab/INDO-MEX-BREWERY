#!/usr/bin/env python3
"""Small-sample experiment analysis for T1-style tests (Sprint 14). Honest by design: with n<8 it reports descriptives and the raw values only and
says no inference is justified. Never invents data; reads food/t1-results/t1-results.csv (real_cook rows only).
  python3 tools/experiment_stats.py            analyse the results file (reports NO DATA today)
  python3 tools/experiment_stats.py selftest
Provides: descriptive stats per construction/time, bootstrap 95% CI of the mean (labelled exploratory), Wilcoxon signed-rank when n>=8 paired."""
import csv, os, sys
import numpy as np
from scipy import stats
F = "food/t1-results/t1-results.csv"
def boot_ci(x, n=5000, seed=7):
    x = np.asarray(x, float); rng = np.random.default_rng(seed)
    m = [rng.choice(x, len(x)).mean() for _ in range(n)]; return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
def describe(x):
    x = np.asarray(x, float); d = dict(n=len(x), mean=round(float(x.mean()), 2), sd=round(float(x.std(ddof=1)), 2) if len(x) > 1 else None, values=list(map(float, x)))
    if len(x) >= 8: d["boot95_exploratory"] = tuple(round(v, 2) for v in boot_ci(x))
    else: d["inference"] = "NONE: n<8, raw values only; a small directional R&D panel"
    return d
def paired(a, b):
    if len(a) < 8: return "NOT RUN: n<8 pairs"
    return stats.wilcoxon(a, b).pvalue
def selftest():
    d = describe([4, 5, 4]); assert d["inference"].startswith("NONE") and d["mean"] == 4.33
    d = describe([3, 4, 5, 4, 4, 5, 3, 4]); assert "boot95_exploratory" in d
    assert paired([1, 2], [2, 3]).startswith("NOT RUN")
    print("selftest ok: small-n guard, bootstrap CI, paired test guard")
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest(); sys.exit()
    rows = [r for r in csv.DictReader(open(F, encoding="utf-8"))] if os.path.exists(F) else []
    rows = [r for r in rows if r.get("data_source") == "real_cook"]
    if not rows: print("NO DATA: no real_cook rows in the T1 results file. Nothing to analyse."); sys.exit()
    for col in ("chicken_identity_0_5","totopo_identity_0_5","fusion_coherence_0_5","crispness_0_5","structural_integrity_0_5","another_bite_0_5"):
        for c in sorted({r["construction"] for r in rows}):
            for t in ("0","5","10"):
                v = [float(r[col]) for r in rows if r["construction"] == c and r["time_min"] == t and r[col] not in ("", "NOT MEASURED")]
                if v: print(col, c, "T+" + t, describe(v))
