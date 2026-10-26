"""Contract alignment (approved joint baseline D1-D8) for the Operations explanation module: lower-case diagnostics from one explicit table, source/provider provenance disambiguation, admission-time provenance and staleness, tenant-scoped versioned record hashing
with a strict downgrade guard, provider truncation as FAILED, the previously untested codes, immutability of the original M-OPS-1 evidence, and the golden-vector package (generated deterministically, verified by a standard-library-only verifier that shares no code with the reference
implementation, and consumable as a conformance suite). No model is called."""
import ast
import copy
import hashlib
import inspect
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from nasha_lab.growth import ops_explanation as O, ops_explanation_eval as E

LAB = Path(__file__).resolve().parents[1]
VEC = LAB / "contracts" / "ops_explanation_vectors" / "v1"
SRC = LAB / "nasha_lab" / "growth" / "ops_explanation.py"
META = dict(name="ollama", model=O.APPROVED_MODEL, digest=O.APPROVED_DIGEST, runtime_profile_sha256="a" * 64, actual_model_calls=1, prompt_tokens=100, completion_tokens=50, estimated_usage=False, latency_ms=1000)
GAP = E.IN["gap"]
GOOD = O.reference_output(GAP)


def boom(exc):
    def f(m):
        raise exc
    return f


# ============================================================ D4: one explicit, lower-case, injective table
def test_every_diagnostic_is_lower_case_snake_case_valid_for_the_published_result_schema_and_unique():
    codes = list(O.DIAGNOSTICS)
    assert all(re.fullmatch(r"[a-z][a-z0-9:_-]{0,95}", c) for c in codes) and len(set(codes)) == len(codes)
    assert {c.upper() for c in codes} - set(O.LEGACY_UPPER) == set(), "every code has a documented M-OPS-1 spelling"
    assert set(O.LEGACY_UPPER.values()) <= set(codes)


def test_the_two_provenance_codes_are_distinct_and_the_old_spellings_map_to_them():
    assert "source_provenance_missing" in O.DIAGNOSTICS and "provider_provenance_missing" in O.DIAGNOSTICS and "missing_provenance" not in O.DIAGNOSTICS and "provenance_missing" not in O.DIAGNOSTICS
    assert O.LEGACY_UPPER["MISSING_PROVENANCE"] == "source_provenance_missing" and O.LEGACY_UPPER["PROVENANCE_MISSING"] == "provider_provenance_missing"
    assert O.DIAGNOSTICS["source_provenance_missing"] == "source" and O.DIAGNOSTICS["provider_provenance_missing"] == "provider"


def test_every_code_the_module_can_emit_is_in_the_table_and_the_table_has_no_dead_entries():
    emitted = set(re.findall(r'"([a-z][a-z0-9]*(?:_[a-z0-9]+)*)"', SRC.read_text())) & set(O.DIAGNOSTICS)
    # codes reachable in source as literals; the rest are produced from StrictJSONError(code) literals and are found by the same scan
    seen = set()
    for c in E.CASES:
        seen |= set(E.run_case(c)["codes"])
    seen |= pipeline_codes()
    assert seen <= set(O.DIAGNOSTICS), seen - set(O.DIAGNOSTICS)
    assert set(O.DIAGNOSTICS) <= seen, f"codes never exercised by the matrix or the pipeline scenarios: {sorted(set(O.DIAGNOSTICS) - seen)}"
    assert emitted == set(O.DIAGNOSTICS)


def pipeline_codes():
    mi = GAP; trusted = E.TRUSTED_RIGHT
    runs = [O.explain(mi, boom(TimeoutError())), O.explain(mi, boom(RuntimeError("x"))), O.explain(mi, boom(O.ProviderTruncated())), O.explain(mi, lambda m: (GOOD, META, "length"), "LIVE_LLM", trusted_record_hashes=trusted),
            O.explain(mi, lambda m: GOOD, "LIVE_LLM", trusted_record_hashes=trusted), O.explain(mi, lambda m: (GOOD, META)), O.explain(mi, lambda m: GOOD, "CACHED_REPLAY"), O.explain(mi, lambda m: GOOD, record_hash_profile="record-hash.v0"),
            O.explain(mi, lambda m: GOOD, "LIVE_LLM")]
    out = set()
    for r in runs:
        out |= set(r["verdict"]["codes"]) | set(r["record"].get("codes", []))
    return out


def test_diagnostic_classes_decide_rejected_versus_failed_and_an_unknown_code_is_a_bug():
    for code, cls in O.DIAGNOSTICS.items():
        assert O.status_for([code]) == ("FAILED" if cls in ("provider", "config") else "REJECTED"), code
    assert O.status_for(["value_mismatch", "incorrect_difference"]) == "REJECTED" and O.status_for(["input_refused", "provider_timeout"]) == "FAILED"
    with pytest.raises(O.ContractMismatch):
        O.status_for(["made_up_code"])
    with pytest.raises(O.ContractMismatch):
        O.make_envelope(GAP, "REJECTED", "DETERMINISTIC_REPLAY", ["provider_timeout"], rendered=O.REJECTED_TEXT)      # a FAILED-class code cannot be reported as an ordinary rejection
    with pytest.raises(O.ContractMismatch):
        O.make_envelope(GAP, "FAILED", "DETERMINISTIC_REPLAY", ["value_mismatch"], rendered=O.FAILED_TEXT)              # and the reverse


def test_schema_enums_keep_their_published_upper_case_spelling_only_diagnostics_are_lower_case():
    r = O.explain(E.IN["miss"], lambda m: O.reference_output(m), audit_complete=True)["envelope"]
    assert r["model_output"]["reason_codes"] == ["MISSING_REQUIRED_EVIDENCE"] and r["status"] == "ABSTAINED"
    ok = O.explain(GAP, lambda m: GOOD, audit_complete=True)["envelope"]["model_output"]
    assert ok["status"] == "ANSWER" and {c["kind"] for c in ok["claims"]} == {"OBSERVE", "DIFFERENCE", "LIMITATION"} and next(c for c in ok["claims"] if c["kind"] == "LIMITATION")["code"] == "CAUSE_NOT_ESTABLISHED"


# ============================================================ D5: REJECTED versus FAILED, end to end
@pytest.mark.parametrize("label,call,code", [
    ("timeout", lambda: O.explain(GAP, boom(TimeoutError())), "provider_timeout"),
    ("transport error", lambda: O.explain(GAP, boom(ConnectionError("x"))), "provider_error"),
    ("raised truncation", lambda: O.explain(GAP, boom(O.ProviderTruncated())), "provider_truncated"),
    ("finish_reason length", lambda: O.explain(GAP, lambda m: (GOOD, META, "length"), "LIVE_LLM", trusted_record_hashes=E.TRUSTED_RIGHT), "provider_truncated"),
    ("finish_reason other", lambda: O.explain(GAP, lambda m: (GOOD, META, "content_filter"), "LIVE_LLM", trusted_record_hashes=E.TRUSTED_RIGHT), "provider_error"),
    ("no provider evidence", lambda: O.explain(GAP, lambda m: GOOD, "LIVE_LLM", trusted_record_hashes=E.TRUSTED_RIGHT), "provider_provenance_missing"),
    ("replay carrying provider metadata", lambda: O.explain(GAP, lambda m: (GOOD, META)), "mode_mismatch"),
    ("unsupported mode", lambda: O.explain(GAP, lambda m: GOOD, "CACHED_REPLAY"), "mode_unsupported"),
    ("v0 pinned by the host", lambda: O.explain(GAP, lambda m: GOOD, record_hash_profile="record-hash.v0"), "record_hash_profile_unsupported"),
    ("unknown profile pinned by the host", lambda: O.explain(GAP, lambda m: GOOD, record_hash_profile="record-hash.v9"), "record_hash_profile_unsupported"),
    ("empty profile", lambda: O.explain(GAP, lambda m: GOOD, record_hash_profile=""), "record_hash_profile_unsupported")])
def test_infrastructure_and_configuration_failures_stay_FAILED_and_show_no_model_content(label, call, code):
    r = call()
    env = r["envelope"]
    assert env["status"] == "FAILED" and env["validation_codes"] == [code] and env["model_output"] is None and env["accepted_result_sha256"] is None and env["rendered_explanation"] == O.FAILED_TEXT, label
    assert r["verdict"]["status"] == "FAILED" and O.result_invariants(env) == []


def test_a_failed_profile_pin_never_calls_the_provider():
    calls = []
    for prof in ("record-hash.v0", "record-hash.v9", ""):
        O.explain(GAP, lambda m: calls.append(1) or GOOD, record_hash_profile=prof)
    assert calls == []


def test_a_model_fault_is_REJECTED_not_FAILED_including_truncated_text_when_the_host_gave_no_finish_reason():
    bad = O.explain(GAP, lambda m: json.dumps(E.edit(lambda o: E.claim(o, "c3").update(claimed_difference=1))(GAP)))
    assert bad["envelope"]["status"] == "REJECTED" and bad["envelope"]["validation_codes"] == ["incorrect_difference"]
    cut = json.dumps(GOOD)[:60]
    r = O.explain(GAP, lambda m: cut)
    assert r["envelope"]["status"] == "REJECTED" and r["envelope"]["validation_codes"] == ["not_json"], "indistinguishable from a bad answer WITHOUT the provider's finish_reason - which is why the host must pass it"
    assert O.explain(GAP, lambda m: (cut, None, "length"))["envelope"]["status"] == "FAILED"
    assert O.explain(GAP, lambda m: (GOOD, None, "stop"))["envelope"]["status"] == "AUDIT_PENDING"


# ============================================================ D6: provenance and staleness at admission, before any provider call
def test_stale_and_unverifiable_snapshots_are_refused_before_the_provider_is_called():
    calls = []
    cand = lambda m: calls.append(1) or GOOD
    stale = O.explain(GAP, cand, now="2027-10-25T00:00:00Z", max_age_seconds=86400)
    assert stale["envelope"]["status"] == "REJECTED" and stale["envelope"]["validation_codes"] == ["input_refused", "stale_snapshot"] and stale["record"]["refused_before_provider"]
    future = O.explain(GAP, cand, now="2026-10-24T00:00:00Z", max_age_seconds=86400)
    assert "stale_snapshot" in future["envelope"]["validation_codes"], "a snapshot dated after 'now' is refused too"
    missing = O.explain(GAP, cand, trusted_record_hashes={})
    assert missing["envelope"]["validation_codes"] == ["input_refused", "source_provenance_missing"]
    wrong = dict(E.TRUSTED_RIGHT); k = next(iter(wrong)); wrong[k] = "0" * 64
    assert O.explain(GAP, cand, trusted_record_hashes=wrong)["envelope"]["validation_codes"] == ["input_refused", "source_hash_mismatch"]
    live_no_map = O.explain(GAP, cand, "LIVE_LLM")
    assert live_no_map["envelope"]["status"] == "REJECTED" and live_no_map["envelope"]["validation_codes"] == ["input_refused", "source_provenance_missing"]
    assert calls == []
    ok = O.explain(GAP, cand, audit_complete=True, now="2026-10-25T12:00:00Z", max_age_seconds=86400, trusted_record_hashes=E.TRUSTED_RIGHT)
    assert ok["envelope"]["status"] == "ACCEPTED" and calls == [1]


def test_source_provenance_codes_are_rejections_the_model_is_not_blamed_and_provider_provenance_is_a_failure():
    assert O.status_for(["source_provenance_missing"]) == "REJECTED" and O.status_for(["provider_provenance_missing"]) == "FAILED"


# ============================================================ D2: record-hash profiles and the downgrade guard
def test_v0_reproduces_the_published_example_hashes_and_v1_is_a_different_tenant_scoped_hash():
    ex = json.load(open(LAB / "contracts" / "ops_explanation" / "examples" / "model-input.json"))
    for f in ex["facts"]:
        assert O.record_sha256(O.HISTORICAL_RECORD_HASH_PROFILE, f, ex["tenant_scope_id"]) == f["provenance"]["record_sha256"]
        assert O.record_sha256(O.LIVE_RECORD_HASH_PROFILE, f, ex["tenant_scope_id"]) != f["provenance"]["record_sha256"]
    assert sorted(O.record_preimage("record-hash.v0", ex["facts"][0], "x")) == ["field", "subject_id", "unit", "value"]


def test_v1_hash_is_tenant_scoped_and_every_preimage_field_matters():
    a, b = E.base("count-gap", "A"), E.base("count-gap", "B")
    fa, fb = a["facts"][0], b["facts"][0]
    assert fa["provenance"]["record_sha256"] != fb["provenance"]["record_sha256"] and a["snapshot_sha256"] != b["snapshot_sha256"], "equal values in two tenants hash differently"
    base = O.record_preimage(O.LIVE_RECORD_HASH_PROFILE, fa, a["tenant_scope_id"])
    assert tuple(base) == O.V1_PREIMAGE_KEYS and base["profile"] == "record-hash.v1"
    h0 = O.sha256_hex(O.canonical(base))
    for k in O.V1_PREIMAGE_KEYS:
        pre = dict(base); pre[k] = "changed" if not isinstance(base[k], int) else base[k] + 1
        assert O.sha256_hex(O.canonical(pre)) != h0, k
    pre = dict(base); del pre["profile"]
    assert O.sha256_hex(O.canonical(pre)) != h0, "the profile string is part of the hashed bytes"


def test_record_hash_v0_is_never_accepted_for_a_live_snapshot_whatever_it_is_called():
    for key in ("v0_all", "mixed", "other_tenant", "rec_tampered"):
        r = O.explain(E.IN[key], lambda m: GOOD)
        assert r["envelope"]["status"] == "REJECTED" and r["envelope"]["validation_codes"] == ["input_refused", "source_hash_mismatch"] and r["record"]["refused_before_provider"], key
    assert O.check_input(E.IN["v0_all"]) == ["source_hash_mismatch"]


def test_nothing_in_the_input_the_output_or_the_public_signatures_can_select_the_profile():
    for forbidden in ("record_hash_profile", "hash_profile", "profile"):
        mi = E.rehash(dict(copy.deepcopy(GAP), **{forbidden: "record-hash.v0"}))
        assert "input_invalid" in O.check_input(mi), forbidden
        assert O.validate_output(json.dumps(dict(GOOD, **{forbidden: "record-hash.v0"})), GAP)["codes"] == ["unknown_key"]
        fact_with = copy.deepcopy(GAP); fact_with["facts"][0]["provenance"][forbidden] = "record-hash.v0"
        assert "input_invalid" in O.check_input(E.rehash(fact_with))
    for fn in (O.validate_output, O.check_input):
        assert "profile" not in " ".join(inspect.signature(fn).parameters), fn.__name__
    assert "record_hash_profile" in inspect.signature(O.explain).parameters and inspect.signature(O.explain).parameters["record_hash_profile"].default == O.LIVE_RECORD_HASH_PROFILE


def test_the_historical_path_is_unreachable_from_explain():
    tree = ast.parse(SRC.read_text())
    explain = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "explain")
    called = {n.func.id for n in ast.walk(explain) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "validate_historical_vector" not in called and "_check_input" not in called and "_validate" not in called
    assert O.ADMISSIBLE_LIVE_RECORD_HASH_PROFILES == ("record-hash.v1",) and O.HISTORICAL_RECORD_HASH_PROFILE not in O.ADMISSIBLE_LIVE_RECORD_HASH_PROFILES
    with pytest.raises(O.ContractMismatch):
        O.record_preimage("record-hash.v9", GAP["facts"][0], GAP["tenant_scope_id"])


# ============================================================ previously untested codes
def test_input_oversize_and_not_json_text_are_exercised():
    big = E.IN["big"]
    assert len(O.canonical(big)) > O.MAX_INPUT_BYTES and O.check_input(big) == ["input_oversize"]
    assert O.explain(big, lambda m: GOOD)["envelope"]["validation_codes"] == ["input_oversize", "input_refused"]
    for raw in (123, None, 3.5, object(), True):
        v = O.validate_output(raw, GAP)
        assert v["status"] == "REJECTED" and v["codes"] == ["not_json_text"], raw
    with pytest.raises(O.StrictJSONError) as e:
        O.parse_strict(123)
    assert e.value.code == "not_json_text"


# ============================================================ D8: immutable historical evidence, unchanged contracts
def test_the_original_m_ops_1_evidence_is_byte_identical_to_what_commit_06fc273_published():
    p = LAB / "results" / "ops-explanation" / "m-ops-1-offline-matrix.json"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "09f4bac6e3b497a8c8b7e6e72f82b0e4cc0218e9eabe346c16d3b405f9ed61cc"
    old = json.loads(p.read_text()); new = json.loads((LAB / "results" / "ops-explanation" / "m-ops-contract-1-offline-matrix.json").read_text())
    assert old["validator_revision"] == "ops-validator-v1.0-m-ops-1" and new["validator_revision"] == O.VALIDATOR_REVISION and old["cases"] == 95 and new["cases"] >= 100
    assert "INCORRECT_DIFFERENCE" in json.dumps(old["cases_detail"]) and "incorrect_difference" not in json.dumps(old["cases_detail"]) and "incorrect_difference" in json.dumps(new["cases_detail"]), "the old file keeps the M-OPS-1 upper-case spelling; the new one the aligned spelling"


def test_the_published_codex_contracts_are_untouched_by_the_alignment():
    for rel, want in O.PINNED.items():
        assert hashlib.sha256((LAB / "contracts" / "ops_explanation" / rel).read_bytes()).hexdigest() == want
    assert (LAB / "contracts" / "ops_explanation" / "UPSTREAM.sha256").read_text().count("\n") == 8


# ============================================================ golden-vector package
def test_the_vector_package_is_exactly_what_the_generator_produces():
    r = subprocess.run([sys.executable, "tools/ops_golden_vectors.py", "--check"], cwd=LAB, env={"PYTHONPATH": str(LAB), "PATH": "/usr/bin:/bin"})
    assert r.returncode == 0, "contracts/ops_explanation_vectors/v1 is stale: run tools/ops_golden_vectors.py"


def verify(directory):
    return subprocess.run([sys.executable, "-I", str(VEC / "verify_vectors.py"), str(directory)], cwd="/", capture_output=True, text=True)


def test_the_standalone_verifier_imports_nothing_from_the_repository_and_accepts_the_package():
    tree = ast.parse((VEC / "verify_vectors.py").read_text())
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert mods <= {"hashlib", "html", "json", "re", "sys", "pathlib"}, mods
    r = verify(VEC)
    assert r.returncode == 0 and "ALL VECTORS VERIFIED" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize("file,mutate", [
    ("canonical_json.json", lambda d: d["positive"][1].update(sha256="0" * 64)),
    ("canonical_json.json", lambda d: d["negative"][0].update(expect="schema_invalid")),
    ("record_hashes.json", lambda d: d["v1_live"][0].update(sha256="0" * 64)),
    ("record_hashes.json", lambda d: d["v0_published_example"][0]["preimage"].update(value=999)),
    ("scenarios.json", lambda d: d["scenarios"][0]["model_input"]["facts"][0].update(value=41)),
    ("scenarios.json", lambda d: d["scenarios"][0].update(snapshot_sha256="0" * 64)),
    ("rendered.json", lambda d: d["answers"][0].update(text="The counted quantity is 61 units below expected.")),
    ("envelopes.json", lambda d: d["envelopes"][0]["expected_envelope"].update(accepted_result_sha256="0" * 64)),
    ("envelopes.json", lambda d: next(e for e in d["envelopes"] if e["expected_envelope"]["status"] == "FAILED")["expected_envelope"].update(status="REJECTED")),
    ("diagnostics.json", lambda d: d["codes"][0].update(code="Upper_Case")),
    ("verdicts.json", lambda d: d["cases"][0].update(expected_codes=["made_up_code"])),
    ("amara_adapter.json", lambda d: d["items"][0]["amara_current"].update(snapshot_sha256="0" * 64))])
def test_the_verifier_catches_a_tampered_vector_so_agreement_is_evidence_not_a_tautology(tmp_path, file, mutate):
    shutil.copytree(VEC, tmp_path / "v"); p = tmp_path / "v" / file
    d = json.loads(p.read_text()); mutate(d); p.write_text(json.dumps(d, indent=1, sort_keys=True))
    sums = [l for l in (tmp_path / "v" / "MANIFEST.sha256").read_text().splitlines() if not l.endswith(file)]
    sums.append(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + file)       # re-seal the manifest so ONLY the content check can fail
    (tmp_path / "v" / "MANIFEST.sha256").write_text("\n".join(sums) + "\n")
    r = verify(tmp_path / "v")
    assert r.returncode == 1 and "FAILURES" in r.stdout, (file, r.stdout)


def test_a_tampered_file_fails_the_manifest(tmp_path):
    shutil.copytree(VEC, tmp_path / "v"); p = tmp_path / "v" / "rendered.json"; p.write_text(p.read_text() + " ")
    assert verify(tmp_path / "v").returncode == 1


def test_the_package_is_a_conformance_suite_the_reference_implementation_reproduces_every_verdict():
    vd = json.loads((VEC / "verdicts.json").read_text()); n = 0
    for c in vd["cases"]:
        mi = vd["inputs"][c["input"]]
        if "output_text" in c and c["output_text"] is not None:
            raw = c["output_text"]
        elif "output_recipe" in c:
            raw = " " * c["output_recipe"]["prefix_spaces"] + c["output_recipe"]["then"]
        elif "output_hex" in c:
            raw = bytes.fromhex(c["output_hex"])
        else:
            raw = {"123": 123, "None": None}[c["output_non_text"]]
        opts = dict(c["options"])
        if "trusted_record_hashes" in opts:
            opts["trusted_record_hashes"] = {"right": E.TRUSTED_RIGHT, "one-hash-wrong": E.TRUSTED_WRONG, "empty": {}}[opts["trusted_record_hashes"]]
        for k in ("foreign_ids", "foreign_scopes"):
            if k in opts:
                opts[k] = set(opts[k])
        if c["input"] == "codex":
            v = O.validate_output(raw, mi, **opts)
        else:
            v = O.validate_output(raw, mi, **opts)
        assert (v["status"], v["codes"], sorted(v["flags"])) == (c["expected_status"], c["expected_codes"], c["expected_flags"]), c["id"]
        n += 1
    assert n >= 100


def test_the_envelope_vectors_are_reproduced_by_the_reference_implementation_and_validate_against_the_published_schema():
    jsonschema = pytest.importorskip("jsonschema"); referencing = pytest.importorskip("referencing")
    reg = referencing.Registry().with_resources([(n, referencing.Resource.from_contents(s, default_specification=referencing.jsonschema.DRAFT202012)) for n, s in O.SCHEMAS.items()])
    v = jsonschema.Draft202012Validator(O.SCHEMAS["result-envelope.schema.json"], registry=reg)
    statuses = set()
    for e in json.loads((VEC / "envelopes.json").read_text())["envelopes"]:
        env = e["expected_envelope"]
        assert not list(v.iter_errors(env)) and O.result_invariants(env) == [], e["name"]
        statuses.add(env["status"])
    assert statuses == {"ACCEPTED", "AUDIT_PENDING", "ABSTAINED", "REJECTED", "FAILED"}


def test_the_amara_adapter_expectations_name_the_wording_difference_and_the_pending_renderer_decision():
    am = json.loads((VEC / "amara_adapter.json").read_text())
    assert len(am["items"]) == 8 and all(i["text_differs_from_amara"] for i in am["items"]) and "PENDING CODEX" in am["d7_renderer_status"]
    assert am["field_map"] == {"expected": "expected_units", "counted": "counted_units"} and am["unit_map"] == {"units": "UNITS"} and am["classification_map"] == {"SYNTHETIC_SCENARIO_ASSUMPTION": "SCENARIO_ASSUMPTION"}
    miss = next(i for i in am["items"] if i["scenario"] == "missing-count")
    assert miss["amara_current"]["status"] == "ABSTAINED" and miss["shared_renderer_status"] == "ABSTAINED"


# ============================================================ source-level mutation tests for the aligned behavior
import types  # noqa: E402


def mutated(old, new):
    src = SRC.read_text()
    assert src.count(old) == 1, old
    mod = types.ModuleType("nasha_lab.growth._ops_align_mutant"); mod.__package__ = "nasha_lab.growth"; mod.__file__ = str(SRC)
    exec(compile(src.replace(old, new), str(SRC), "exec"), mod.__dict__)
    return mod


def pipeline_signature(mod):
    """Statuses and diagnostics of every pipeline-level scenario, so a mutant of the pipeline (not just the validator) changes it."""
    mi = GAP; trusted = E.TRUSTED_RIGHT; out = []
    scen = [lambda: mod.explain(mi, boom(TimeoutError())), lambda: mod.explain(mi, boom(mod.ProviderTruncated())), lambda: mod.explain(mi, lambda m: (GOOD, META, "length"), "LIVE_LLM", trusted_record_hashes=trusted),
            lambda: mod.explain(mi, lambda m: (GOOD, META, "content_filter"), "LIVE_LLM", trusted_record_hashes=trusted), lambda: mod.explain(mi, lambda m: GOOD, "LIVE_LLM"), lambda: mod.explain(mi, lambda m: GOOD, "LIVE_LLM", trusted_record_hashes=trusted),
            lambda: mod.explain(mi, lambda m: GOOD, record_hash_profile="record-hash.v0"), lambda: mod.explain(mi, lambda m: GOOD, now="2027-10-25T00:00:00Z", max_age_seconds=86400),
            lambda: mod.explain(mi, lambda m: GOOD, trusted_record_hashes={}), lambda: mod.explain(E.IN["v0_all"], lambda m: GOOD), lambda: mod.explain(mi, lambda m: (GOOD, META)), lambda: mod.explain(mi, lambda m: GOOD, "CACHED_REPLAY"),
            lambda: mod.explain(mi, lambda m: json.dumps(E.edit(lambda o: E.claim(o, "c3").update(claimed_difference=1))(mi)))]
    for f in scen:
        try:
            r = f(); out.append((r["envelope"]["status"], tuple(r["envelope"]["validation_codes"])))
        except Exception as e:                                                   # noqa: BLE001 - a crash is a different outcome
            out.append(("CRASH", type(e).__name__))
    return out


ALIGN_MUTANTS = [
    ("provider truncation ignored", 'if finish not in (None, "stop"):', 'if False:'),
    ("raised truncation reported as a generic provider error", 'except ProviderTruncated:\n        return _failed(model_input, mode, "provider_truncated", record)', 'except ProviderTruncated:\n        return _failed(model_input, mode, "provider_error", record)'),
    ("every failure class reported as REJECTED", 'return "FAILED" if any(DIAGNOSTICS[c] in FAILED_CLASSES for c in codes) else "REJECTED"', 'return "REJECTED"'),
    ("host profile pin not enforced", 'if record_hash_profile != LIVE_RECORD_HASH_PROFILE:', 'if False:'),
    ("live mode without trusted record hashes allowed", 'if mode == "LIVE_LLM" and trusted_record_hashes is None:', 'if False:'),
    ("staleness not checked at admission", 'if age > max_age_seconds or age < 0:', 'if False:'),
    ("missing trusted hash not reported", 'codes.add("source_provenance_missing")\n                elif', 'pass\n                elif'),
    ("v0 accepted as a fallback for a live snapshot", 'if "record_hash" in rules and any(f["provenance"]["record_sha256"] != record_sha256(profile, f, model_input["tenant_scope_id"]) for f in facts):',
     'if "record_hash" in rules and any(f["provenance"]["record_sha256"] not in (record_sha256(profile, f, model_input["tenant_scope_id"]), record_sha256(HISTORICAL_RECORD_HASH_PROFILE, f, model_input["tenant_scope_id"])) for f in facts):'),
    ("record hash not verified at admission", 'if "record_hash" in rules and any(f["provenance"]["record_sha256"] != record_sha256(profile, f, model_input["tenant_scope_id"]) for f in facts):', 'if False:'),
    ("provider provenance code renamed back to the ambiguous spelling", 'return _failed(model_input, mode, "provider_provenance_missing", record)', 'return _failed(model_input, mode, "provider_error", record)'),
    ("a historical vector validates with the live profile marker dropped", 'v["historical_vector"] = True', 'v["historical_vector"] = False'),
]


@pytest.mark.parametrize("label,old,new", ALIGN_MUTANTS, ids=[m[0] for m in ALIGN_MUTANTS])
def test_mutants_of_the_aligned_behavior_are_detected(label, old, new):
    mod = mutated(old, new)
    base_p, mut_p = pipeline_signature(O), pipeline_signature(mod)
    base_m = [(r["got"]["status"], r["got"]["codes"], r["exact"]) for r in E.run_cases(O)]
    mut_m = [(r["got"]["status"], r["got"]["codes"], r["exact"]) for r in E.run_cases(mod)]
    hist = None
    if label.startswith("a historical vector"):
        ex = json.load(open(LAB / "contracts" / "ops_explanation" / "examples" / "model-input.json")); out = json.load(open(LAB / "contracts" / "ops_explanation" / "examples" / "model-output.json"))
        hist = mod.validate_historical_vector(json.dumps(out), ex).get("historical_vector") is not True
    assert base_p != mut_p or base_m != mut_m or hist, label


def test_negative_control_a_neutral_edit_leaves_the_pipeline_signature_unchanged():
    mod = mutated('DIAGNOSTICS_VERSION = "ops-diagnostics.v1"', 'DIAGNOSTICS_VERSION = "renamed-but-identical"')
    assert pipeline_signature(O) == pipeline_signature(mod)
