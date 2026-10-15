"""Claims ledger verifier. Every public-facing technical claim in claims/claims.json maps to evidence; machine-checkable claims carry `checks` that are
re-evaluated against the committed result files. A claim whose check fails (or whose public_wording drifts from the ledger) fails the test suite.

  python -m nasha_lab.claims verify          -> exit 1 on any failing check
  python -m nasha_lab.claims export OUT.json -> portfolio-facing subset (id, public_wording, scope, limitations, evidence links)

Check kinds:  {"file","path","op","value"}  path like "overall.pass_rate.k" or "table[retriever=bm25].mrr"; ops == != >= <= (numbers are coerced from strings)
              {"kind":"sum","files":[...],"path","op","value"}      sum of one numeric path over several files
              {"kind":"count_where","file","rows":"rows","where":{field:value},"op","value"}     count rows whose fields equal the given values
              {"kind":"exists","file"}                                    the evidence file exists in the repository"""
import json
import operator
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
REPO = LAB.parent
LEDGER = LAB / "claims" / "claims.json"
OPS = {"==": operator.eq, "!=": operator.ne, ">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return x


def get(obj, path):
    for seg in path.split("."):
        m = re.fullmatch(r"(\w[\w\-+.]*)\[(\w+)=([^\]]+)\]", seg) if "[" in seg else None
        if m:
            obj = next(x for x in obj[m.group(1)] if str(x[m.group(2)]) == m.group(3))
        else:
            obj = obj[int(seg)] if isinstance(obj, list) else obj[seg]
    return obj


def _load(f):
    p = REPO / f if f.startswith("lab/") else LAB / f
    return json.loads(p.read_text())


def run_check(c):
    kind = c.get("kind", "value")
    if kind == "exists": return (REPO / c["file"]).exists(), c["file"]
    if kind == "sum":
        v = sum(_num(get(_load(f), c["path"])) for f in c["files"])
    elif kind == "count_where":
        rows = get(_load(c["file"]), c["rows"]); v = sum(1 for r in rows if all(r.get(k) == val for k, val in c["where"].items()))
    else:
        v = _num(get(_load(c["file"]), c["path"]))
    ok = OPS[c["op"]](v, _num(c["value"]))
    return ok, f'{c.get("file", c.get("files"))} {c.get("path", c.get("where", ""))} = {v} (want {c["op"]} {c["value"]})'


def verify():
    ledger = json.loads(LEDGER.read_text()); bad = []; seen = set()
    for c in ledger["claims"]:
        if c["claim_id"] in seen: bad.append(f'{c["claim_id"]}: duplicate id')
        seen.add(c["claim_id"])
        for k in ("claim_id", "claim", "scope", "evidence", "commit", "limitations", "public_wording"):
            if not c.get(k): bad.append(f'{c.get("claim_id")}: missing {k}')
        if not c.get("checks") and not c.get("external_evidence"): bad.append(f'{c["claim_id"]}: neither machine checks nor external evidence')
        for ch in c.get("checks", []):
            try: ok, msg = run_check(ch)
            except Exception as e: ok, msg = False, f"{type(e).__name__}: {e}"
            if not ok: bad.append(f'{c["claim_id"]}: {msg}')
        for e in c.get("evidence", []):
            if not e.startswith(("http", "run:")) and not (REPO / e).exists() and not (LAB / e).exists(): bad.append(f'{c["claim_id"]}: evidence path missing: {e}')
    return bad


if __name__ == "__main__":
    if sys.argv[1] == "export":
        led = json.loads(LEDGER.read_text()); keep = ("claim_id", "title", "public_wording", "scope", "limitations", "evidence", "commit", "status")
        out = dict(note=led["note"], prohibited_claims=led["prohibited_claims"], claims=[{k: c[k] for k in keep if k in c} for c in led["claims"]])
        Path(sys.argv[2]).write_text(json.dumps(out, indent=1)); print("exported", len(out["claims"]))
    else:
        bad = verify(); print("CLAIMS OK" if not bad else "CLAIM FAILURES:\n" + "\n".join(bad)); sys.exit(1 if bad else 0)
