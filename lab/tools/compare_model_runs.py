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


# What differed between the runs, from the commit history (the older records did not write a `conditions` block). Used to tell a reader which differences cannot be attributed to the model alone.
KNOWN_CHANGES = {
    "run1": [dict(change="supplier documents name the supplier on every product line; stale agent documents removed on re-ingest", applies_to="every case", since="run 2"),
             dict(change="boundary rules added: entity binding, comparative claims, absence claims, untrusted-source, instruction-echo patterns", applies_to="platform containment of every case", since="runs 2-4"),
             dict(change="report asked to stay within 200 words (RunConstraints.max_words)", applies_to="every case", since="run 4"),
             dict(change="corpus quarantine of documents addressed to the assistant (off for C12)", applies_to="C07, C14 and any poisoned document", since="run 4"),
             dict(change="research question v2 names the 8 costliest ingredients", applies_to="C15 and the governed workflow runs (C11); direct case queries are unchanged", since="run 4"),
             dict(change="Ollama server runs with the intended settings (the installer's service no longer answers); Ollama version may differ", applies_to="latency and resources", since="run 3")],
    "run3": [dict(change="report asked to stay within 200 words (RunConstraints.max_words)", applies_to="every case", since="run 4"),
             dict(change="research question v2 names the 8 costliest ingredients", applies_to="C15 and the governed workflow runs (C11); direct case queries are unchanged", since="run 4"),
             dict(change="boundary rules added: comparative claims, absence claims, untrusted-source, instruction-echo patterns", applies_to="platform containment of every case", since="run 4"),
             dict(change="corpus quarantine of documents addressed to the assistant (off for C12)", applies_to="C07, C14 and any poisoned document", since="run 4"),
             dict(change="cases C14 and C15 are new", applies_to="additional cases, not part of any earlier score", since="run 4")]}


def compare_all(new, baselines):
    """`baselines`: {label: record}, label 'run1' or 'run3' (or any). Per baseline: the id-matched comparison, the cases that exist only in the new run, and the changed conditions. Newly added cases are never folded into a baseline score."""
    out = dict(model_digest=(new.get("model") or {}).get("digest"), new_cases=[c["id"] for c in new.get("cases", [])], comparisons={})
    new_ids = {c["id"] for c in new.get("cases", [])}
    for label, rec in baselines.items():
        c = compare(rec, new)
        c["matched_case_ids"] = sorted(i for i in by_id(rec) if i in new_ids)
        c["newly_added_vs_this_baseline"] = sorted(new_ids - set(by_id(rec)))
        c["not_run_again"] = sorted(set(by_id(rec)) - new_ids)
        c["changed_conditions"] = KNOWN_CHANGES.get(label, [])
        c["baseline_conditions_recorded"] = bool(rec.get("conditions"))
        out["comparisons"][label] = c
    return out


if __name__ == "__main__":
    if sys.argv[1] == "--new":                       # compare_model_runs.py --new NEW.json --against run1=A.json --against run3=B.json
        new = load(sys.argv[2]); bases = {}
        args = sys.argv[3:]
        while args:
            assert args[0] == "--against"; lab, path = args[1].split("=", 1); bases[lab] = load(path); args = args[2:]
        print(json.dumps(compare_all(new, bases), indent=1))
    else:
        print(json.dumps(compare(load(sys.argv[1]), load(sys.argv[2])), indent=1))
