"""Recover planner-experiment results from a GitHub Actions job log (the model-eval workflow prints `LLM|LLMG|DET SUMMARY|BYFAMILY|ROW <json>` lines).

Artifacts and raw log downloads are blocked in the authoring sandbox, so results are recovered from the log text returned by the GitHub job-log API.
  python -m nasha_lab.ci_results LOGFILE LABEL      -> results/planner_<LABEL>_{raw,guardrail}.json and results/planner_<LABEL>_paired.json
The deterministic control for the paired test is NOT taken from CI: it is re-run locally on exactly the same scenario ids (it is deterministic and byte-reproducible)."""
import json
import re
import sys
from pathlib import Path

from . import compare_planners as CP
from . import eval_planners as EP

RES = Path(__file__).resolve().parent.parent / "results"
LINE = re.compile(r"\S+ (DET|LLMG|LLM) (SUMMARY|BYFAMILY|ROW) (.*)")


def parse(text):
    try: text = json.loads(text)["logs_content"]          # saved MCP tool output
    except Exception: pass
    lines = text.split("\n") if "\n" in text else text.split("\\n")
    out = {}
    for l in lines:
        m = LINE.match(l.strip())
        if not m: continue
        tag, kind, body = m.groups()
        try: j = json.loads(body)
        except ValueError: continue
        d = out.setdefault(tag, {"rows": []})
        if kind == "ROW": d["rows"].append(j)
        elif kind == "SUMMARY": d["summary"] = j
        else: d["by_family"] = j
    return out


def main(logfile, label):
    parsed = parse(Path(logfile).read_text())
    names = {"LLM": "raw", "LLMG": "guardrail"}
    saved = {}
    for tag, nm in names.items():
        d = parsed.get(tag)
        if not d or "summary" not in d: print("missing", tag); continue
        res = {**d["summary"], "by_family": d.get("by_family", {}), "rows": d["rows"], "source": "GitHub Actions job log (free runner, Ollama, CPU)"}
        (RES / f"planner_{label}_{nm}.json").write_text(json.dumps(res, indent=1)); saved[nm] = res
    if not saved: return
    ids = {r["id"] for r in next(iter(saved.values()))["rows"]}
    splits = sorted({r["split"] for r in next(iter(saved.values()))["rows"]})
    det = EP.run_suite(EP.FACTORIES["deterministic"], "deterministic", splits=tuple(splits), only=lambda sc: sc.id in ids)
    paired = {"deterministic_n": det["n"]}
    for nm, res in saved.items():
        paired[nm] = CP.compare(det, res)
    (RES / f"planner_{label}_paired.json").write_text(json.dumps(paired, indent=1, default=str))
    print(json.dumps({k: (v if k == "deterministic_n" else {x: v[x] for x in ("n", "both_pass", "only_first", "only_second", "both_fail", "p_value_exact_sign_test")}) for k, v in paired.items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
