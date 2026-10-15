"""Score the data-quality layer against the injected ground truth. Reports precision/recall per defect type."""
import json
import sys
from collections import defaultdict

from . import dq, generator, pipeline

CASCADE_FREE = True  # cascade quarantines are not findings, so they never enter the score


def score(seeds, enabled=None, types=None, k=8):
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    fp_examples = []
    for s in seeds:
        raw, truth = generator.generate(seed=s, defects_per_type=k, types=types)
        _, rep = pipeline.run(raw, enabled_rules=enabled)
        found = {(f.rule, f.table, f.key) for f in rep["findings"] if f.rule != "price_drift" or True}
        for x in truth & found: tp[x[0]] += 1
        for x in truth - found: fn[x[0]] += 1
        for x in found - truth:
            fp[x[0]] += 1
            if len(fp_examples) < 5: fp_examples.append((s,) + x)
    rows = {}
    for t in sorted(set(tp) | set(fp) | set(fn)):
        p = tp[t] / (tp[t] + fp[t]) if tp[t] + fp[t] else None
        r = tp[t] / (tp[t] + fn[t]) if tp[t] + fn[t] else None
        rows[t] = {"tp": tp[t], "fp": fp[t], "fn": fn[t], "precision": None if p is None else round(p, 3), "recall": None if r is None else round(r, 3)}
    return {"seeds": list(seeds), "per_rule": rows, "fp_examples": fp_examples}


def clean_run(seeds, enabled=None):
    n = 0
    for s in seeds:
        raw, _ = generator.generate(seed=s, defects_per_type=0)
        _, rep = pipeline.run(raw, enabled_rules=enabled)
        n += len(rep["findings"])
    return n


if __name__ == "__main__":
    seeds = range(1, 6)
    label = sys.argv[1] if len(sys.argv) > 1 else "v1"
    enabled = [r for r in dq.ALL_RULES if r != "near_duplicate_order"] if label == "v0" else None
    out = {"label": label, "synthetic": True, "scope": "offline evaluation on SYNTHETIC data with injected defects; author-written generator and rules (same-author)",
           "clean_dataset_findings": clean_run(seeds, enabled), "injected": score(seeds, enabled)}
    print(json.dumps(out, indent=1, default=str))
