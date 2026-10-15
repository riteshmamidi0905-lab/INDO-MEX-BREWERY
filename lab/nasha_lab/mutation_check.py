"""Mutation testing of the safety-critical code: apply one small, plausible bug at a time and check that the test suite notices.
A SURVIVING mutant is a gap in the tests, reported as such. Run: python -m nasha_lab.mutation_check results/mutation.json  (about 1 minute per surviving mutant)."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.abspath(os.path.join(HERE, ".."))

MUTANTS = [
    ("M01", "tools.py", 'if ctx.authority is None or not ap.get("grant"):', 'if False:', "mutating tools run without any approval grant"),
    ("M02", "tools.py", 'if spec.permission == EXTERNAL: return _err(', 'if False: return _err(', "external actions are no longer refused"),
    ("M03", "tools.py", 'if spec.permission in (DRAFT, MUTATE) and ctx.tainted:', 'if False and ctx.tainted:', "taint check disabled"),
    ("M04", "tools.py", 'if not ok:\n            return _err(name, spec.permission, "APPROVAL_REQUIRED", f"approval grant rejected: {why}"', 'if False:\n            return _err(name, spec.permission, "APPROVAL_REQUIRED", f"approval grant rejected: {why}"', "grant verification result ignored"),
    ("M05", "identity.py", 'if p["run_id"] != run_id: return False, "WRONG_RUN", None', 'pass', "grant usable in another run"),
    ("M06", "identity.py", 'if [tool, args_hash] not in p["actions"]: return False, "ARGUMENTS_OR_TOOL_NOT_APPROVED", None', 'pass', "grant usable for different arguments"),
    ("M07", "identity.py", 'if key in self.used: return False, "REPLAYED", None', 'pass', "grant replay allowed"),
    ("M08", "identity.py", '("flag_record_for_review", "supplier_proposals"): {"FOUNDER"},', '("flag_record_for_review", "supplier_proposals"): {"FOUNDER", "BUYER", "QUALITY_LEAD"},', "any role may approve policy decisions"),
    ("M09", "identity.py", 'if p["exp"] < self.clock(): raise AuthError("EXPIRED")', 'pass', "tokens never expire"),
    ("M10", "agent.py", 'if tool == "flag_record_for_review" and not all(part in blob for part in str(args.get("key", "")).split(":")):', 'if False:', "mutation targets are not checked against evidence"),
    ("M11", "agent.py", '        if c["evidence"]: kept.append(c)\n        else: dropped += 1', '        kept.append(c)', "claims without evidence are kept"),
    ("M12", "agent.py", 'if tool not in ALLOWED_MUTATIONS: rejected.append((tool, "tool_not_allowed")); continue', 'pass', "any mutating tool name is accepted from a planner"),
    ("M13", "planners.py", 'if risk["shortfall_before_lead_time"] and not sup:      # regression (found by failure injection): a failed supplier lookup must never degrade to NO_ACTION', 'if False:', "supplier-lookup failure degrades to NO_ACTION again (Block 2 regression)"),
    ("M14", "planners.py", 'if a["gaps"] and any(g["code"] != "INJECTION_SUSPECTED_IN_DOCUMENT" for g in a["gaps"]):', 'if False:', "NO_ACTION allowed on partial evidence"),
    ("M15", "llm_planner.py", '        if self.guardrail:\n            env = action_envelope(state)', '        if False:\n            env = action_envelope(state)', "evidence-envelope guardrail disabled"),
    ("M16", "llm_planner.py", 'if out is None or out.action not in acts:', 'if out is None:', "model action outside the allowed set accepted"),
    ("M17", "knowledge.py", 'if old in byid and old != c["document_id"]:', 'if False:', "supersession is not derived (D-59 stays current)"),
    ("M18", "knowledge.py", 'if status_aware and not include_nonauthoritative and c["effective_status"] in NOT_AUTHORITATIVE: continue', 'pass', "non-authoritative chunks leak into status-aware search"),
    ("M19", "tools.py", 'm = dq.FORBIDDEN_RE.search(NEG_RE.sub(" ", text))', 'm = dq.FORBIDDEN_RE.search(text)', "negated claims (pork-free) trigger rejection again"),
    ("M20", "trust.py", 'if K.INJECTION_RE.search(d.note): flags.append("INJECTION_SUSPECTED"); out["tainted"] = _values(d.model_dump()); return out', 'pass', "instruction-like untrusted notes are accepted"),
    ("M21", "trust.py", 'model_config = ConfigDict(extra="forbid")', 'model_config = ConfigDict(extra="ignore")', "unexpected fields from an untrusted server are silently dropped"),
    ("M22", "pipeline.py", 'if reason == "duplicate_order":   # the rule keys on order_id, so it also matches the first (legitimate) copy: keep that one\n            reason = None', 'pass', "dedup removes both copies of a duplicated order (Block 2 regression)"),
]


def run(path=None, only=None):
    results = []
    for mid, fn, old, new, desc in MUTANTS:
        if only and mid not in only: continue
        fp = os.path.join(HERE, fn); src = open(fp, encoding="utf-8").read()
        if src.count(old) != 1: results.append(dict(id=mid, file=fn, desc=desc, status="INVALID", detail=f"pattern found {src.count(old)} times")); print(mid, "INVALID"); continue
        open(fp, "w", encoding="utf-8").write(src.replace(old, new)); t0 = time.time()
        try:
            r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "--ignore=tests/test_ui.py", "tests"], cwd=LAB, capture_output=True, text=True, timeout=420)
            killed = r.returncode != 0; first = next((l for l in r.stdout.splitlines() if l.startswith("FAILED")), "")
        except subprocess.TimeoutExpired:
            killed, first = True, "TIMEOUT (counts as detected: the mutant hangs the suite)"
        finally:
            open(fp, "w", encoding="utf-8").write(src)
        results.append(dict(id=mid, file=fn, desc=desc, status="KILLED" if killed else "SURVIVED", killed_by=first[:140], seconds=round(time.time() - t0)))
        print(mid, results[-1]["status"], first[:100], flush=True)
    k = sum(1 for r in results if r["status"] == "KILLED"); n = sum(1 for r in results if r["status"] in ("KILLED", "SURVIVED"))
    out = dict(mutants=results, killed=k, valid=n, score=round(k / n, 3) if n else None)
    if path: open(path, "w").write(json.dumps(out, indent=1))
    print("MUTATION SCORE", k, "/", n)
    return out


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
