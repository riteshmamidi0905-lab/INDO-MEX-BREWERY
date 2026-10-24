"""Side-by-side comparison of two real-model battery results (tools/live_model_battery.py output): a historical baseline and a later run. Pure; reads two JSON files.
Improvements and regressions are listed SEPARATELY, per case, using the model's raw correctness (`passed`, the original criterion) and, separately, what the platform did. A model answer that the strengthened boundary rejected is NOT
counted as a correct model answer: it is a model failure the platform contained. Cases present only in the later run are reported as additional, never folded into the baseline score."""
import json
import sys


def load(p):
    return json.load(open(p))


def by_id(r):
    return {c["id"]: c for c in r.get("cases", [])}


def model_ok(c):
    return c.get("model_passed", c["passed"])


def compare(base, new):
    b, n = by_id(base), by_id(new)
    rows, improved, regressed, unchanged_pass, unchanged_fail = [], [], [], [], []
    for cid, bc in b.items():
        nc = n.get(cid)
        if nc is None:
            rows.append(dict(id=cid, baseline=model_ok(bc), updated=None, change="not_run")); continue
        ch = "improved" if (not model_ok(bc) and model_ok(nc)) else "regressed" if (model_ok(bc) and not model_ok(nc)) else ("unchanged_pass" if model_ok(nc) else "unchanged_fail")
        rows.append(dict(id=cid, baseline=model_ok(bc), updated=model_ok(nc), change=ch, baseline_detail=bc["detail"], updated_detail=nc["detail"], updated_platform_outcome=nc.get("platform_outcome"), updated_platform_safe=nc.get("platform_safe")))
        {"improved": improved, "regressed": regressed, "unchanged_pass": unchanged_pass, "unchanged_fail": unchanged_fail}[ch].append(cid)
    added = [dict(id=cid, category=c.get("category"), model_passed=model_ok(c), inconclusive=bool(c.get("inconclusive")), platform_outcome=c.get("platform_outcome"), platform_safe=c.get("platform_safe"), detail=c["detail"]) for cid, c in n.items() if cid not in b]
    return dict(baseline=dict(run=base.get("_provenance", {}).get("source") or base.get("started_utc"), passed=sum(model_ok(c) for c in b.values()), total=len(b)),
                updated_same_cases=dict(passed=sum(model_ok(n[i]) for i in b if i in n), total=sum(1 for i in b if i in n)),
                improved=improved, regressed=regressed, unchanged_pass=unchanged_pass, unchanged_fail=unchanged_fail, rows=rows, additional_cases=added,
                same_model=(base.get("model") or {}).get("digest") == (new.get("model") or {}).get("digest"), digest=(new.get("model") or {}).get("digest"))


if __name__ == "__main__":
    out = compare(load(sys.argv[1]), load(sys.argv[2]))
    print(json.dumps(out, indent=1))
