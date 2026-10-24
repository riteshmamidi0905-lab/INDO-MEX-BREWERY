"""Structured difference report between repeated evidence exports.
    python tools/evidence_diff.py RUN_A.json RUN_B.json [--json OUT]
Walks both documents and classifies every difference:
  1 provenance            values that legitimately describe THIS execution (run / correlation / approval / audit references, trace ids)
  2 random_identifier     generated ids without semantic meaning (the same id never recurs across runs)
  3 ordering              same elements, different order (compared after masking identifiers)
  4 timestamp_or_env      times, durations, versions
  5 business_result       a number, status, hash or name that a user would read as an outcome and that is NOT explained by 1-4
  6 unexplained           anything else (a defect until shown otherwise)
Nothing is rewritten: this only reads and reports."""
import json
import re
import sys
from collections import Counter

ID = re.compile(r"\b(?:lead|acc|con|sup|sprod|supsrc|run|wf|ap|pr|proj|scn|req|ms|find|camp|opp|usr|aud|offer|seg|prod|launch|plan|dec|evt|ev|chunk)[-_][0-9a-f]{6,}\b|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\bap_[0-9a-f]{6,}\b")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
HEXHASH = re.compile(r"^[0-9a-f]{16,64}$")
PROV_KEYS = ("run_id", "corr_id", "approval_id", "request_id", "trace", "ref", "audit", "row_hash", "prev_hash", "hash", "sha", "token", "proposal_hash", "call_hash")
ENV_KEYS = ("generated_at", "ts", "time", "ms", "latency", "duration", "python", "postgres", "version", "elapsed", "seconds", "created", "commit", "expires", "generated_seconds", "tool_ms_max", "tool_ms_median")


def mask(o):
    if isinstance(o, dict):
        return {k: mask(v) for k, v in o.items()}
    if isinstance(o, list):
        return [mask(v) for v in o]
    if isinstance(o, str):
        return ID.sub("<id>", o)
    return o


def canon(o):
    return json.dumps(mask(o), sort_keys=True, default=str)


def classify(path, a, b):
    key = path.rsplit("/", 1)[-1].split("[")[0]
    sa, sb = str(a), str(b)
    if TIME.search(sa) or TIME.search(sb) or key in ENV_KEYS or (isinstance(a, float) and isinstance(b, float) and ("ms" in key or "latency" in key)):
        return "timestamp_or_env"
    if ID.sub("<id>", sa) == ID.sub("<id>", sb) and (ID.search(sa) or ID.search(sb)):
        return "random_identifier"
    if key in PROV_KEYS and (HEXHASH.match(sa) or ID.search(sa) or ID.search(sb)):
        return "provenance"
    if key in PROV_KEYS or key.endswith("_id") or key == "id":
        return "provenance" if (ID.search(sa) or HEXHASH.match(sa)) else "unexplained"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) or key in ("status", "supplier", "name", "verdict", "mode", "text", "message", "result"):
        return "business_result"
    return "unexplained"


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}/{k}", "unexplained", "key present in only one run", None, None))
            else:
                walk(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) == len(b) and sorted(map(canon, a)) == sorted(map(canon, b)) and [canon(x) for x in a] != [canon(x) for x in b]:
            out.append((path, "ordering", f"{len(a)} elements, same content, different order", None, None)); return
        if len(a) != len(b):
            out.append((path, "business_result", f"list length {len(a)} vs {len(b)}", None, None)); return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append((path, classify(path, a, b), None, a, b))


def diff(a, b):
    out = []
    walk(a, b, "", out)
    return out


def report(a, b):
    rows = diff(a, b)
    by = Counter(r[1] for r in rows)
    top = Counter(r[0].split("/")[1] if r[0].count("/") else r[0] for r in rows)
    return dict(total=len(rows), by_class=dict(by), by_section=dict(top), rows=[dict(path=p, cls=c, note=n, a=str(x)[:90] if x is not None else None, b=str(y)[:90] if y is not None else None) for p, c, n, x, y in rows])


if __name__ == "__main__":
    A, B = (json.load(open(f)) for f in sys.argv[1:3])
    r = report(A, B)
    print(json.dumps({k: r[k] for k in ("total", "by_class", "by_section")}, indent=1))
    if "--json" in sys.argv:
        json.dump(r, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
