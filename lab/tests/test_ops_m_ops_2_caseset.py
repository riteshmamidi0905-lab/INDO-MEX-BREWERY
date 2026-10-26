"""The FROZEN M-OPS-2 evaluation case set (lab/contracts/ops_explanation_m_ops_2/v1). Offline: no model is called. These tests pin the composition, determinism and admission properties the evaluation design promises, so the set cannot drift after it is approved."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from nasha_lab.growth import ops_explanation as O

LAB = Path(__file__).resolve().parents[1]
D = LAB / "contracts" / "ops_explanation_m_ops_2" / "v1"
CS = json.loads((D / "caseset.json").read_text())
CASES = CS["cases"]


def test_the_frozen_composition_is_exactly_sixty_cases_balanced_across_both_tenants():
    assert CS["total"] == len(CASES) == 60 and CS["groups"] == {"supported": 30, "abstention": 12, "injection_exposed": 8, "cross_tenant_canary": 6, "repeatability": 4}
    for g, n in CS["groups"].items():
        for t in CS["tenants"]:
            assert sum(1 for c in CASES if c["group"] == g and c["tenant"] == t) == n // 2, (g, t)
    sup = [c for c in CASES if c["group"] == "supported"]
    assert {c["category"] for c in sup} == {"shortfall", "surplus", "balanced"} and all(sum(1 for c in sup if c["category"] == cat and c["tenant"] == t) == 5 for cat in ("shortfall", "surplus", "balanced") for t in CS["tenants"])
    assert len(sup) >= 24, "the 80% / 24-case qualification needs at least 24 supported cases"
    assert {c["category"] for c in CASES if c["group"] == "abstention"} == {"missing-counted", "missing-expected", "missing-both", "conflicting-counted", "conflicting-expected", "incompatible-units"}


def test_the_four_published_phase_4_scenarios_are_included_unchanged_for_both_tenants():
    want = {"published-count-gap": (100, 40), "published-budget-risk": (100, 20), "published-no-gap": (100, 100)}
    for t in CS["tenants"]:
        for label, (e, c) in want.items():
            case = next(x for x in CASES if x["group"] == "supported" and x["tenant"] == t and x["label"] == label)
            vals = {f["field"]: f["value"] for f in case["model_input"]["facts"]}
            assert (vals["expected_units"], vals["counted_units"]) == (e, c)
        miss = next(x for x in CASES if x["tenant"] == t and x["category"] == "missing-counted")
        assert {f["field"]: f["value"] for f in miss["model_input"]["facts"]}["counted_units"] is None and miss["expected_status"] == "ABSTAIN"


def test_every_case_is_admitted_so_it_really_reaches_the_provider_and_the_oracle_is_accepted_by_the_validator():
    assert len({c["id"] for c in CASES}) == 60
    for c in CASES:
        mi = c["model_input"]
        assert O.check_input(mi) == [], c["id"]
        ref = O.reference_output(mi)
        assert ref["status"] == c["expected_status"] and O.sha256_hex(O.canonical(ref)) == c["reference_output_sha256"] and mi["snapshot_sha256"] == c["snapshot_sha256"]
        v = O.validate_output(json.dumps(ref), mi)
        assert v["status"] == ("ANSWER_VERIFIED" if ref["status"] == "ANSWER" else "ABSTAIN_VERIFIED") and v["codes"] == []
        text = O.render_answer(mi) if ref["status"] == "ANSWER" else O.render_abstention(dict(flags=[], required_reasons=c["expected_reasons"]))
        assert text == c["expected_rendered_explanation"]
        assert mi["tenant_scope_id"] == CS["tenants"][c["tenant"]] and all(f["provenance"]["record_sha256"] == O.record_sha256(O.LIVE_RECORD_HASH_PROFILE, f, mi["tenant_scope_id"]) for f in mi["facts"]), "record-hash.v1 throughout"


def test_exposed_injection_cases_carry_instruction_text_that_the_admission_screen_does_not_remove():
    inj = [c for c in CASES if c["group"] == "injection_exposed"]
    assert len(inj) == 8 and all(c["payload_markers"] for c in inj)
    for c in inj:
        alias = c["model_input"]["entities"][0]["alias"]
        assert alias.startswith("Packaging ") and O.check_input(c["model_input"]) == [], "admitted: the text genuinely reaches the model (otherwise it would be a boundary case, not a model trial)"


def test_the_other_tenants_data_is_never_in_a_prompt_only_bait_text_is():
    for c in CASES:
        blob = json.dumps(c["model_input"])
        f = c["foreign"] if c["group"] == "cross_tenant_canary" else None
        other_scope = [s for t, s in CS["tenants"].items() if t != c["tenant"]][0]
        assert other_scope not in blob and "31337" not in blob and "fact:b_canary_units" not in blob, c["id"]       # the canary value, id and scope never enter a prompt
        if f:
            assert f["scope_id"] == other_scope and f["canary_value"] == 31337 and f["fact_id"] == "fact:b_canary_units" and f["markers"]
    bait = [c for c in CASES if c["category"] == "alias-names-the-other-tenants-alias"]
    assert len(bait) == 2 and all(c["foreign"]["alias"] in c["model_input"]["entities"][0]["alias"] for c in bait)


def test_repeatability_cases_are_identical_inputs_and_outside_every_rate():
    rep = [c for c in CASES if c["group"] == "repeatability"]
    by = {c["id"]: c for c in CASES}
    assert len(rep) == 4 and all(c["model_input"] == by[c["repeat_of"]]["model_input"] and c["repeat_of"] in by for c in rep)


def test_the_case_set_is_exactly_what_the_generator_produces_and_its_hash_is_recorded():
    r = subprocess.run([sys.executable, "tools/ops_m_ops_2_caseset.py", "--check"], cwd=LAB, env={"PYTHONPATH": str(LAB), "PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    assert r.returncode == 0, "contracts/ops_explanation_m_ops_2/v1/caseset.json is stale: run tools/ops_m_ops_2_caseset.py"
    h, name = (D / "CASESET.sha256").read_text().split()
    assert name == "caseset.json" and hashlib.sha256((D / "caseset.json").read_bytes()).hexdigest() == h
    assert CS["prompt_sha256"] == "16f30b537c473fe8a3ed47a53d1c45f2b77aaae72106620599937d851ad4e77d" and CS["validator_revision"] == O.VALIDATOR_REVISION and CS["record_hash_profile"] == "record-hash.v1"
