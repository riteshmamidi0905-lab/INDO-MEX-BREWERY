"""Recording-completeness requirements (docs/growth-os/PHASE2-RECORDING-REQUIREMENTS.md, prospective; acceptance criteria v1.0 is unchanged). A result that declares recording format 2 and lacks any rejection evidence is INCOMPLETE, never MET;
a legacy result (run #4) keeps the verdict it was given and is reported with what it lacks; evaluating it strictly shows INCOMPLETE. Hand-built results; no model is involved."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_acceptance_evaluator import E, LAB, good, status  # noqa: E402

CLAIM = "Firm white fish fillet, skinless (species TBD: mahi/redfish/cod) (i-white-fish) is quoted by Synthetic Specialty Importer (specialty) at $12.16 per kg, Synthetic Broadline Distributor A (broadline) at $11.67 per kg and B at $11.89 per kg; Distributor A holds the lowest."
assert len(CLAIM) > 200
CTX = [dict(id="e1", doc_id="supplier-a", title="A", text_chars=90, text_sha256="a" * 64)]


def rejected_run(run):
    run.update(model_output_accepted=False, deterministic_fallback=True, agent_mode="deterministic_fallback", fallback_reason="agent output failed verification", boundary_status="rejected", rejected_agent_output=dict(codes=["COMPARATIVE_FALSE"], problems=["x"], platform_ok=True),
               claims=[], recording_version=2, query="the query", corpus_version="v1", evidence_context=CTX, report_reviewed=dict(title="t", answer="a", claims=[dict(text=CLAIM, evidence_ids=["e1"])]), platform_verification_full=dict(ok=True, groundedness=1.0),
               rejected_claims_full=[dict(text=CLAIM, text_chars=len(CLAIM), codes=["COMPARATIVE_FALSE"], evidence_ids=["e1"], cited_doc_ids=["supplier-a"], mentioned_supplier_ids=["a"], detail=dict(price_binding=None, comparative=dict(verdict="false")),
                                          cited_passages=[dict(id="e1", doc_id="supplier-a", title="A", text="[A] ...", text_chars=7)])],
               comparisons=[dict(verdict="false", claim_full=CLAIM, set_detail=[dict(supplier_id="a", supplier="A", price_cents=1167.41)])])
    return run


def complete():
    r = good(); r["recording_version"] = 2
    for run in r["governed_workflow"]["runs"]:
        run.update(recording_version=2, query="q", corpus_version="v", evidence_context=CTX, platform_verification_full=dict(ok=True))
    rejected_run(r["governed_workflow"]["runs"][0])
    r["governed_workflow"].update(model_output_accepted=1, deterministic_fallbacks=1)
    for c in r["cases"]:
        if c["id"].startswith("C15"):
            c["run"]["evidence_fingerprint"] = CTX
    return r


def s7(res):
    return next(g for g in res["gates"] if g["id"] == "S7")


def test_a_complete_format_2_record_with_a_rejected_workflow_output_is_accepted_as_complete():
    r = complete()
    assert E.rejection_evidence_problems(r) == []
    out = E.evaluate(r)
    assert s7(out)["status"] == "MET" and out["recording"]["enforced"] is True and out["recording"]["missing_rejection_evidence"] == []


@pytest.mark.parametrize("label,mutate,expect", [
    ("truncated text", lambda r: r["governed_workflow"]["runs"][0]["rejected_claims_full"][0].update(text=CLAIM[:120]), "missing or truncated"),
    ("text length not recorded", lambda r: r["governed_workflow"]["runs"][0]["rejected_claims_full"][0].pop("text_chars"), "missing or truncated"),
    ("no rule", lambda r: r["governed_workflow"]["runs"][0]["rejected_claims_full"][0].update(codes=[]), "no rejection rule"),
    ("no cited passages", lambda r: r["governed_workflow"]["runs"][0]["rejected_claims_full"][0].update(cited_passages=[]), "cited evidence"),
    ("no rule detail", lambda r: r["governed_workflow"]["runs"][0]["rejected_claims_full"][0].pop("detail"), "no rule detail"),
    ("no rejected claim at all", lambda r: r["governed_workflow"]["runs"][0].update(rejected_claims_full=[]), "no complete rejected claim"),
    ("comparison not recorded", lambda r: r["governed_workflow"]["runs"][0].update(comparisons=[]), "comparative claim and its comparison set"),
    ("comparison claim truncated", lambda r: r["governed_workflow"]["runs"][0]["comparisons"][0].update(claim_full=CLAIM[:200]), "comparative claim and its comparison set"),
    ("no stored-quote detail", lambda r: r["governed_workflow"]["runs"][0]["comparisons"][0].update(set_detail=[]), "no stored-quote detail"),
    ("binding not recorded", lambda r: r["governed_workflow"]["runs"][0]["rejected_claims_full"][0].update(codes=["COMPARATIVE_FALSE", "PRICE_NOT_FROM_NAMED_SUPPLIER"]), "binding"),
    ("no complete report", lambda r: r["governed_workflow"]["runs"][0].update(report_reviewed=None), "complete reviewed report"),
    ("no query", lambda r: r["governed_workflow"]["runs"][1].update(query=None), "query not recorded"),
    ("no corpus version", lambda r: r["governed_workflow"]["runs"][1].update(corpus_version=None), "corpus_version not recorded"),
    ("no evidence context", lambda r: r["governed_workflow"]["runs"][1].update(evidence_context=None), "no evidence context"),
    ("verifier decision missing", lambda r: r["governed_workflow"]["runs"][0].update(platform_verification_full=None, agent_mode="engine_model"), "verifier's decision"),
    ("C15 cannot be compared", lambda r: [c["run"].pop("evidence_fingerprint") for c in r["cases"] if c["id"].startswith("C15")], "evidence fingerprint"),
    ("a direct rejected claim truncated", lambda r: r["cases"][4].update(run=dict(completed=True, telemetry={"verification": [{}]}, boundary=dict(rejected=[dict(text="x", codes=["X"])], rejected_detail=[dict(full_text="x", text_chars=500)]))), "missing or truncated")])
def test_missing_rejection_evidence_in_a_format_2_record_is_incomplete_never_met(label, mutate, expect):
    r = complete(); mutate(r)
    problems = E.rejection_evidence_problems(r)
    assert any(expect in p for p in problems), (label, problems)
    out = E.evaluate(r)
    assert s7(out)["status"] == "INCOMPLETE" and out["verdict"] == "INCOMPLETE_EVIDENCE", label


def test_a_result_that_omits_the_format_marker_cannot_dodge_the_requirement_when_the_workflow_requires_it():
    r = complete(); r.pop("recording_version")
    assert s7(E.evaluate(r))["status"] == "MET", "without the marker the evaluator is lenient by itself"
    out = E.evaluate(r, require_recording=2)
    assert s7(out)["status"] == "INCOMPLETE" and "below the required 2" in s7(out)["detail"]


def test_the_model_live_workflow_requires_recording_format_2():
    assert "evaluate_acceptance.py results/model-validation/live-battery.json --require-recording=2" in (LAB.parent / ".github" / "workflows" / "model-live.yml").read_text()


def test_the_preserved_run_4_keeps_its_historical_verdict_and_is_reported_as_lacking_the_rejection_evidence():
    d = LAB / "results" / "model-validation" / "run-40242794366"
    r = json.loads((d / "result.json").read_text()); r["cases"] = [json.loads(x) for x in (d / "cases.jsonl").read_text().splitlines()]
    legacy = E.evaluate(r)
    assert legacy["verdict"] == "MODEL_BACKED_WORKFLOW_NOT_DEMONSTRATED" and s7(legacy)["status"] == "MET" and legacy["recording"]["enforced"] is False, "the historical verdict is not rewritten"
    assert legacy["recording"]["result_format"] == 1 and any("no complete rejected claim" in p for p in legacy["recording"]["missing_rejection_evidence"]) and legacy["recording"]["note"]
    strict = E.evaluate(r, require_recording=2)
    assert strict["verdict"] == "INCOMPLETE_EVIDENCE" and s7(strict)["status"] == "INCOMPLETE"


def test_the_historical_acceptance_json_of_run_4_is_byte_identical_to_what_was_preserved():
    d = LAB / "results" / "model-validation" / "run-40242794366"
    sums = {l.split()[1]: l.split()[0] for l in (d / "SHA256SUMS").read_text().splitlines() if l.strip() and not l.split()[1] == "README.md"}
    import hashlib
    assert sums and all(hashlib.sha256((d / n).read_bytes()).hexdigest() == h for n, h in sums.items())


def test_accepted_model_output_with_a_complete_record_is_unaffected_by_the_new_requirement():
    r = good(); r["recording_version"] = 2
    for run in r["governed_workflow"]["runs"]:
        run.update(recording_version=2, query="q", corpus_version="v", evidence_context=CTX, platform_verification_full=dict(ok=True))
    for c in r["cases"]:
        if c["id"].startswith("C15"):
            c["run"]["evidence_fingerprint"] = CTX
    assert E.rejection_evidence_problems(r) == [] and s7(E.evaluate(r))["status"] == "MET"
