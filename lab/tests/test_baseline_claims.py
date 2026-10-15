"""Block 4: the Block 3 baseline is frozen and every public claim is machine-checked against committed evidence."""
import json
import shutil
import pytest

from nasha_lab import baseline, claims


def test_block3_baseline_has_not_drifted():
    assert baseline.verify() == []


def test_baseline_records_every_required_version():
    b = json.loads(baseline.OUT.read_text())
    for k in ("deterministic_planner", "prompt_version", "tool_schema_version", "qwen_1_5b", "qwen_7b", "retrievers"): assert b["versions"][k]
    assert b["datasets"]["scenario_set"]["n"] == 259 and b["datasets"]["question_set"]["n"] == 467 and b["code_commit"].startswith("647d47e")


def test_every_claim_is_backed_by_evidence_that_still_holds():
    assert claims.verify() == []


def test_a_tampered_claim_is_detected(tmp_path, monkeypatch):
    led = json.loads(claims.LEDGER.read_text())
    led["claims"][1]["checks"][0]["value"] = 258                                         # claim says 258/259, evidence says 259
    p = tmp_path / "claims.json"; p.write_text(json.dumps(led)); monkeypatch.setattr(claims, "LEDGER", p)
    assert any("C02" in b for b in claims.verify())


def test_claims_without_evidence_or_wording_are_rejected(tmp_path, monkeypatch):
    led = json.loads(claims.LEDGER.read_text()); led["claims"].append(dict(claim_id="X1", claim="unsupported"))
    p = tmp_path / "claims.json"; p.write_text(json.dumps(led)); monkeypatch.setattr(claims, "LEDGER", p)
    assert any("X1" in b for b in claims.verify())


def test_prohibited_claims_listed():
    led = json.loads(claims.LEDGER.read_text()); assert any("customers" in p for p in led["prohibited_claims"]) and any("employment" in p for p in led["prohibited_claims"])
