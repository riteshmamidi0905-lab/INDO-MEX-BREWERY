"""M-OPS-1 (offline): the Operations explanation validator and renderer against Codex's published Phase 5 contracts. No model is called anywhere in this file; every candidate output is a scripted double.
Gates: every required offline test passes; zero accepted invalid claims; zero cross-tenant disclosures; zero authorization bypasses; every relevant adversarial mutant rejected; no model-written text reaches the explanation."""
import ast
import copy
import importlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema", reason="INTEGRATION UNAVAILABLE: jsonschema not installed (declared in requirements-ci-extras.txt)")
referencing = pytest.importorskip("referencing")

from nasha_lab.growth import ops_explanation as O, ops_explanation_eval as E  # noqa: E402

LAB = Path(__file__).resolve().parents[1]
CONTRACTS = LAB / "contracts" / "ops_explanation"
SRC = LAB / "nasha_lab" / "growth" / "ops_explanation.py"


def registry():
    res = [(f"{n}", referencing.Resource.from_contents(s, default_specification=referencing.jsonschema.DRAFT202012)) for n, s in O.SCHEMAS.items()]
    return referencing.Registry().with_resources(res)


def jsv(name):
    return jsonschema.Draft202012Validator(O.SCHEMAS[name], registry=registry())


def run(mi, raw, mode="DETERMINISTIC_REPLAY", **kw):
    return O.explain(mi, lambda m: raw if not callable(raw) else raw(m), mode, **kw)


# ============================================================ contract compatibility (Codex's published schemas are the source of truth)
def test_the_vendored_contracts_are_byte_identical_to_the_pinned_upstream_files():
    import hashlib
    for rel, want in O.PINNED.items():
        assert hashlib.sha256((CONTRACTS / rel).read_bytes()).hexdigest() == want, rel
    listed = {l.split()[1]: l.split()[0] for l in (CONTRACTS / "UPSTREAM.sha256").read_text().splitlines()}
    assert listed == O.PINNED


def test_a_changed_contract_stops_the_module_from_loading(monkeypatch, tmp_path):
    tmp = tmp_path / "ops"; (tmp / "contracts").mkdir(parents=True); (tmp / "examples").mkdir()
    for rel in O.PINNED:
        (tmp / rel).write_bytes((CONTRACTS / rel).read_bytes())
    p = tmp / "contracts" / "model-output.schema.json"; p.write_text(p.read_text().replace('"maxItems": 8', '"maxItems": 9', 1))
    monkeypatch.setattr(O, "CONTRACT_DIR", tmp)
    with pytest.raises(O.ContractMismatch, match="differs from the pinned upstream"):
        O._load_contracts()


def test_the_validator_refuses_a_schema_keyword_it_does_not_implement_instead_of_ignoring_it():
    with pytest.raises(O.ContractMismatch, match="unsupported schema keyword"):
        O.schema_errors({"type": "string", "propertyNames": {"pattern": "x"}}, "a")
    with pytest.raises(O.ContractMismatch, match="unresolvable"):
        O.schema_errors({"$ref": "nope.json"}, {})


def test_the_published_examples_are_valid_under_the_published_schemas_by_both_implementations():
    inp, out = (json.load(open(CONTRACTS / "examples" / f"model-{k}.json")) for k in ("input", "output"))
    assert not list(jsv("model-input.schema.json").iter_errors(inp)) and not list(jsv("model-output.schema.json").iter_errors(out))
    assert O.schema_errors(O.SCHEMAS["model-input.schema.json"], inp) == [] and O.schema_errors(O.SCHEMAS["model-output.schema.json"], out) == []


def test_the_example_snapshot_hash_follows_the_specifications_canonicalization():
    inp = json.load(open(CONTRACTS / "examples" / "model-input.json"))
    assert O.snapshot_sha256(inp) == inp["snapshot_sha256"], "the specified canonicalization reproduces the published example hash"


def test_the_published_example_answer_is_accepted_as_a_HISTORICAL_vector_and_never_as_a_live_explanation():
    inp = json.load(open(CONTRACTS / "examples" / "model-input.json")); out = json.load(open(CONTRACTS / "examples" / "model-output.json"))
    v = O.validate_historical_vector(json.dumps(out), inp)
    assert v["status"] == "ANSWER_VERIFIED" and v["historical_vector"] is True and v["codes"] == []
    assert O.render_answer(inp) == "In this synthetic snapshot, the expected quantity of the inventory item is 100 units and the counted quantity is 40 units. The counted quantity is 60 units below expected. These scenario assumptions do not establish a physical root cause.", "renderer v2: no server mapping for this tenant, so the generic label (the alias is never displayed)"
    assert O.render_answer(inp, labels={(inp["tenant_scope_id"], "item:packaging"): "Synthetic packaging"}) == "In this synthetic snapshot, the expected quantity of Synthetic packaging is 100 units and the counted quantity is 40 units. The counted quantity is 60 units below expected. These scenario assumptions do not establish a physical root cause."
    live = O.validate_output(json.dumps(out), inp)
    assert live["status"] == "REJECTED" and live["codes"] == ["input_refused", "source_hash_mismatch"], "its record hashes are record-hash.v0: not admissible for a live snapshot"
    r = run(inp, json.dumps(out), audit_complete=True)
    assert r["envelope"]["status"] == "REJECTED" and r["record"]["refused_before_provider"] is True


def test_the_reference_output_equals_the_published_example_up_to_the_order_of_a_set_valued_field():
    inp = json.load(open(CONTRACTS / "examples" / "model-input.json")); out = json.load(open(CONTRACTS / "examples" / "model-output.json"))
    ref = copy.deepcopy(O.reference_output(inp))
    for o in (ref, out):
        next(c for c in o["claims"] if c["kind"] == "LIMITATION")["fact_ids"].sort()
    assert ref == out


def test_our_schema_validator_agrees_with_the_reference_jsonschema_library_on_every_scripted_output():
    out_v, in_v = jsv("model-output.schema.json"), jsv("model-input.schema.json")
    checked = 0
    for c in E.CASES:
        mi = E.input_for(c)
        raw = c["out"](mi)
        data = raw if isinstance(raw, dict) else None
        if data is None:
            try:
                data = O.parse_strict(raw)
            except O.StrictJSONError:
                continue
        ours = not O.schema_errors(O.SCHEMAS["model-output.schema.json"], data)
        theirs = not list(out_v.iter_errors(data))
        assert ours == theirs, (c["id"], "ours", ours, "reference", theirs)
        checked += 1
    assert checked >= 70
    for key, mi in E.IN.items():
        ours = not O.schema_errors(O.SCHEMAS["model-input.schema.json"], mi)
        assert ours == (not list(in_v.iter_errors(mi))), key


# ============================================================ the scripted matrix
def test_every_scripted_case_has_the_expected_verdict_with_zero_false_accepts_and_zero_false_rejects():
    m = E.metrics()
    assert m["cases"] >= 90 and m["exact"] == m["cases"], m["failures"]
    assert m["false_accepts"] == 0 and m["false_rejects"] == 0 and m["accepted_invalid_claims"] == 0


def test_the_matrix_covers_every_required_category():
    groups = {c["group"] for c in E.CASES}
    assert {"correct", "arithmetic", "evidence", "cross-tenant", "injection", "structure", "abstention", "provenance", "claim-set", "observe", "input"} <= groups
    assert len({c["id"] for c in E.CASES}) == len(E.CASES)
    assert sum(1 for c in E.CASES if c["group"] == "injection") >= 10 and sum(1 for c in E.CASES if c["group"] == "structure") >= 15


def test_every_rule_matters_removing_any_one_rule_changes_at_least_one_verdict():
    mu = E.run_mutants()
    assert set(mu) == set(O.RULES) and all(v["killed"] for v in mu.values()), {k: v for k, v in mu.items() if not v["killed"]}


def mutated_module(old, new):
    src = SRC.read_text()
    assert src.count(old) == 1, old
    mod = types.ModuleType("nasha_lab.growth._ops_mutant"); mod.__package__ = "nasha_lab.growth"; mod.__file__ = str(SRC)
    exec(compile(src.replace(old, new), str(SRC), "exec"), mod.__dict__)
    return mod


OPERATOR_MUTANTS = [
    ("difference computed in the wrong direction", 'c["claimed_difference"] != e["value"] - o["value"]', 'c["claimed_difference"] != o["value"] - e["value"]'),
    ("arithmetic never compared", 'elif "arithmetic" in rules and c["claimed_difference"] != e["value"] - o["value"]:', 'elif False:'),
    ("observed value compared with <= instead of equality", 'c["claimed_value"] != f["value"]', 'c["claimed_value"] > f["value"]'),
    ("claim fact existence ignored", 'codes.append("cross_tenant_reference" if fid in foreign_ids and "foreign_refs" in rules else "unknown_evidence")\n        return None', 'pass\n        return {"subject_id": c.get("subject_id"), "inventory_item_id": c.get("subject_id"), "field": c.get("field"), "unit": c.get("unit"), "availability": "PRESENT", "value": c.get("claimed_value"), "id": fid}'),
    ("partial acceptance (rejected claims dropped, rest accepted)", 'out["status"] = "ANSWER_VERIFIED" if not codes else "REJECTED"', 'out["status"] = "ANSWER_VERIFIED"'),
    ("bindings reduced to the analysis id", 'for k in ("analysis_id", "tenant_scope_id", "workflow_id", "snapshot_id", "snapshot_sha256"):', 'for k in ("analysis_id",):'),
    ("duplicate JSON keys tolerated", 'raise StrictJSONError("duplicate_key", k)', 'pass'),
    ("floats tolerated", 'raise StrictJSONError("non_integer_number", text)', 'return int(float(text))'),
    ("bool accepted as integer", 'return isinstance(v, int) and not isinstance(v, bool)', 'return isinstance(v, int)'),
    ("unknown keys tolerated", 'elif schema.get("additionalProperties") is False:', 'elif False:'),
    ("deferred claim kinds accepted", 'return ["deferred_claim_kind"] if "deferred" in rules else []', 'return []'),
    ("abstention reasons unchecked", 'if reasons and given != reasons:', 'if False:'),
    ("unnecessary-abstention flag removed (claimed as an error instead)", 'out["flags"].append("unnecessary_abstention")', 'codes.add("wrong_abstention_reason")'),
    ("invented completion allowed", 'codes.add("invented_completion")', 'pass'),
    ("input admitted without the directive screen", 'if any(MB.directive_flags(x) or MB.INSTRUCTION_WORDS.search(x) for x in strings):', 'if False:'),
    ("renderer reads the model's claimed difference", 'd = e - c', 'd = 0'),
]


@pytest.mark.parametrize("label,old,new", OPERATOR_MUTANTS, ids=[m[0] for m in OPERATOR_MUTANTS])
def test_source_level_mutants_of_the_validator_are_detected_by_the_matrix(label, old, new):
    mod = mutated_module(old, new)
    baseline = E.run_cases(O)
    results = E.run_cases(mod)
    assert any((a["got"]["status"], a["got"]["codes"]) != (b["got"]["status"], b["got"]["codes"]) or a["exact"] != b["exact"] for a, b in zip(baseline, results)) or label.startswith("renderer"), label
    if label.startswith("renderer"):
        # the renderer is exercised through the pipeline, not the validator matrix: the rendered text must change for the count-gap snapshot
        assert mod.render_answer(E.IN["gap"]) != O.render_answer(E.IN["gap"])


# ============================================================ no model text reaches the explanation; deterministic rendering
def test_the_explanation_depends_only_on_the_snapshot_never_on_the_candidates_claim_ids_or_ordering():
    mi = E.IN["gap"]
    want = O.render_answer(mi)
    for variant in (E.edit(lambda o: o["claims"].reverse()), E.edit(lambda o: [c.update(claim_id=f"c{n}") for n, c in enumerate(reversed(o["claims"]), 1)]), E.edit(lambda o: E.claim(o, "c4").update(fact_ids=["fact:expected_units", "fact:counted_units"]))):
        r = run(mi, variant(mi), audit_complete=True)
        assert r["envelope"]["status"] == "ACCEPTED" and r["envelope"]["rendered_explanation"] == want


def test_the_rendered_text_is_composed_only_of_template_text_snapshot_integers_and_the_trusted_label():
    for key in ("gap", "budget", "nogap"):
        mi = E.IN[key]
        text = run(mi, O.reference_output(mi), audit_complete=True)["envelope"]["rendered_explanation"]
        e = next(f["value"] for f in mi["facts"] if f["field"] == "expected_units"); c = next(f["value"] for f in mi["facts"] if f["field"] == "counted_units")
        assert text.startswith(f"In this synthetic snapshot, the expected quantity of {O.TRUSTED_DISPLAY_LABELS[(mi['tenant_scope_id'], mi['entities'][0]['id'])]} is {e} units and the counted quantity is {c} units.")
        assert text.endswith("These scenario assumptions do not establish a physical root cause.") and len(text) <= O.MAX_RENDERED_CHARS
    assert "equals the expected quantity" in O.render_answer(E.IN["nogap"]) and "below expected" in O.render_answer(E.IN["gap"])
    ahead = copy.deepcopy(E.IN["gap"]); [f.update(value=150) for f in ahead["facts"] if f["field"] == "counted_units"]
    assert "50 units above expected" in O.render_answer(ahead)


def test_a_hostile_alias_never_reaches_the_rendered_text_at_all():
    """Renderer v2 supersedes the v1 escaping test: the alias is not read for wording, so there is nothing to escape (a trusted LABEL is still escaped; see tests/test_ops_renderer_v2.py)."""
    mi = copy.deepcopy(E.IN["gap"]); mi["entities"][0]["alias"] = "<b>x</b> & y"
    text = O.render_answer(mi)
    assert "<b>" not in text and "&amp;" not in text and "&lt;" not in text and "Synthetic packaging" in text


def test_rendering_and_the_result_hash_are_deterministic_across_processes_and_hash_seeds():
    code = "import json;from nasha_lab.growth import ops_explanation_eval as E, ops_explanation as O;mi=E.IN['gap'];r=O.explain(mi,lambda m:O.reference_output(m),audit_complete=True);print(json.dumps([r['envelope']['rendered_explanation'],r['envelope']['accepted_result_sha256']]))"
    outs = {subprocess.run([sys.executable, "-c", code], cwd=LAB, env={**os.environ, "PYTHONPATH": str(LAB), "PYTHONHASHSEED": seed}, capture_output=True, text=True, check=True).stdout for seed in ("0", "1", "123")}
    assert len(outs) == 1


# ============================================================ result envelope and pipeline
def test_every_envelope_status_validates_against_the_published_result_schema_and_the_cross_field_invariants():
    mi, miss = E.IN["gap"], E.IN["miss"]
    results = {
        "ACCEPTED": run(mi, O.reference_output(mi), audit_complete=True),
        "AUDIT_PENDING": run(mi, O.reference_output(mi)),
        "ABSTAINED": run(miss, O.reference_output(miss), audit_complete=True),
        "REJECTED": run(mi, E.edit(lambda o: E.claim(o, "c3").update(claimed_difference=1))(mi)),
        "FAILED": O.explain(mi, lambda m: (_ for _ in ()).throw(RuntimeError("boom"))),
    }
    v = jsv("result-envelope.schema.json")
    for status, r in results.items():
        env = r["envelope"]
        assert env["status"] == status and not list(v.iter_errors(env)), (status, list(v.iter_errors(env))[:1])
        assert O.result_invariants(env) == [], status
    assert results["REJECTED"]["envelope"]["model_output"] is None and results["REJECTED"]["envelope"]["accepted_result_sha256"] is None, "a rejected output is not shown, not even partly"
    assert results["REJECTED"]["envelope"]["rendered_explanation"] == O.REJECTED_TEXT and results["FAILED"]["envelope"]["rendered_explanation"] == O.FAILED_TEXT


def test_validation_codes_are_emitted_in_the_lower_case_form_the_published_result_schema_requires():
    r = run(E.IN["gap"], E.edit(lambda o: E.claim(o, "c3").update(claimed_difference=1))(E.IN["gap"]))
    assert r["verdict"]["codes"] == ["incorrect_difference"] and r["envelope"]["validation_codes"] == ["incorrect_difference"]


def test_a_refused_input_never_reaches_the_candidate():
    calls = []
    for key in ("tampered", "poisoned", "poisoned2", "extra", "reordered", "dangling", "dup", "neg"):
        r = O.explain(E.IN[key], lambda m: calls.append(1) or O.reference_output(m))
        assert r["envelope"]["status"] == "REJECTED" and "input_refused" in r["envelope"]["validation_codes"] and r["record"]["refused_before_provider"] is True, key
    assert calls == [], "the provider was never called for an inadmissible input"


def test_provider_failures_are_failures_nothing_is_substituted_and_no_content_is_shown():
    mi = E.IN["gap"]
    for exc, code in ((TimeoutError(), "provider_timeout"), (RuntimeError("boom"), "provider_error"), (ConnectionError("x"), "provider_error")):
        r = O.explain(mi, lambda m, exc=exc: (_ for _ in ()).throw(exc))
        assert r["envelope"]["status"] == "FAILED" and r["envelope"]["validation_codes"] == [code] and r["envelope"]["model_output"] is None and r["envelope"]["rendered_explanation"] == O.FAILED_TEXT


def test_the_labelled_deterministic_replay_is_separate_never_live_and_equals_a_perfect_models_explanation():
    mi = E.IN["gap"]
    rep = O.deterministic_replay(mi, audit_complete=True)["envelope"]
    assert rep["mode"] == "DETERMINISTIC_REPLAY" and rep["provider"] is None and rep["status"] == "ACCEPTED"
    perfect = run(mi, O.reference_output(mi), audit_complete=True)["envelope"]
    assert rep["rendered_explanation"] == perfect["rendered_explanation"] and rep["accepted_result_sha256"] == perfect["accepted_result_sha256"]
    assert O.deterministic_replay(E.IN["miss"], True)["envelope"]["status"] == "ABSTAINED"


def test_a_scripted_double_can_never_produce_a_live_model_result():
    mi = E.IN["gap"]
    good = O.reference_output(mi)
    meta = dict(name="ollama", model=O.APPROVED_MODEL, digest=O.APPROVED_DIGEST, runtime_profile_sha256="a" * 64, actual_model_calls=1, prompt_tokens=100, completion_tokens=50, estimated_usage=False, latency_ms=1000)
    trusted = E.TRUSTED_RIGHT
    r = O.explain(mi, lambda m: good, "LIVE_LLM", trusted_record_hashes=trusted)
    assert r["envelope"]["status"] == "FAILED" and r["envelope"]["validation_codes"] == ["provider_provenance_missing"], "live mode without provider evidence is refused"
    for bad in (dict(meta, digest="0" * 64), dict(meta, model="qwen2.5:14b-instruct"), dict(meta, estimated_usage=True), dict(meta, actual_model_calls=0), {k: v for k, v in meta.items() if k != "latency_ms"}):
        assert O.explain(mi, lambda m, b=bad: (good, b), "LIVE_LLM", trusted_record_hashes=trusted)["envelope"]["status"] == "FAILED"
    ok = O.explain(mi, lambda m: (good, meta), "LIVE_LLM", audit_complete=True, trusted_record_hashes=trusted)["envelope"]
    assert ok["status"] == "ACCEPTED" and ok["mode"] == "LIVE_LLM" and not O.result_invariants(ok), "structurally complete provenance is accepted; its AUTHENTICITY is the host's job (trusted runtime registry), not this pure module's"
    assert O.explain(mi, lambda m: (good, meta), "DETERMINISTIC_REPLAY")["envelope"]["validation_codes"] == ["mode_mismatch"], "a replay cannot carry provider metadata"
    assert O.explain(mi, lambda m: good, "CACHED_REPLAY")["envelope"]["status"] == "FAILED", "no cross-request cache in this release"


def test_audit_incomplete_results_are_pending_never_accepted():
    mi = E.IN["gap"]
    assert run(mi, O.reference_output(mi))["envelope"]["status"] == "AUDIT_PENDING"
    assert run(E.IN["miss"], O.reference_output(E.IN["miss"]))["envelope"]["status"] == "AUDIT_PENDING"


def test_the_result_hash_binds_the_snapshot_the_claims_the_rendered_text_and_the_revisions():
    mi = E.IN["gap"]
    h = run(mi, O.reference_output(mi), audit_complete=True)["envelope"]["accepted_result_sha256"]
    other = run(E.IN["budget"], O.reference_output(E.IN["budget"]), audit_complete=True)["envelope"]["accepted_result_sha256"]
    assert h != other and len(h) == 64
    assert O.accepted_result_sha256(mi, O.reference_output(mi), "different text") != h


# ============================================================ evidence recording (reuses the recording vocabulary of the model-live battery)
def test_the_record_keeps_the_complete_raw_output_its_hash_and_the_per_claim_verdicts():
    mi = E.IN["gap"]
    bad = E.edit(lambda o: E.claim(o, "c3").update(claimed_difference=59))(mi)
    r = run(mi, json.dumps(bad))
    rec = r["record"]
    assert json.loads(rec["raw_output"]) == bad and rec["raw_chars"] == len(json.dumps(bad)) and len(rec["raw_sha256"]) == 64
    assert [c["ok"] for c in rec["claim_verdicts"]] == [True, True, False, True] and rec["codes"] == ["incorrect_difference"] and rec["snapshot_sha256"] == mi["snapshot_sha256"]
    assert rec["validator_revision"] == O.VALIDATOR_REVISION and "facts" not in json.dumps(rec), "the record carries hashes and the candidate's output, not a copy of the tenant snapshot"


# ============================================================ tenant isolation
def test_zero_cross_tenant_disclosures_across_every_cross_tenant_case_and_both_directions():
    a, b = E.IN["gap"], E.base("budget-risk", "B")
    ra = run(a, O.reference_output(a), audit_complete=True)["envelope"]["rendered_explanation"]
    rb = run(b, O.reference_output(b), audit_complete=True)["envelope"]["rendered_explanation"]
    assert "packaging" in ra and "towels" not in ra and "towels" in rb and "packaging" not in rb
    for c in (c for c in E.CASES if c["group"] == "cross-tenant"):
        got = E.run_case(c)
        assert got["status"] == "REJECTED", c["id"]
    # tenant B's complete valid answer, submitted for tenant A's analysis, is rejected whole, with nothing of it rendered
    r = O.explain(a, lambda m: O.reference_output(b))
    assert r["envelope"]["status"] == "REJECTED" and "towels" not in json.dumps(r["envelope"]) and r["envelope"]["model_output"] is None


# ============================================================ authorization invariants (this module cannot approve, execute, mutate or call anything)
def test_the_module_is_pure_it_imports_no_database_network_workflow_or_weir_code():
    tree = ast.parse(SRC.read_text())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add(("." * n.level) + (n.module or "") if n.level else n.module.split(".")[0])
    assert mods <= {"hashlib", "html", "json", "re", "datetime", "pathlib", ".", "."}, mods
    src = SRC.read_text()
    for forbidden in ("psycopg", "urllib", "requests", "socket", "subprocess", "mcp_weir", "launch_workflow", "weir_", "open(", "os.environ"):
        assert forbidden not in src, forbidden
    assert [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level] == [None], "the only repository import is model_boundary (itself pure)"


def test_no_envelope_or_output_can_carry_an_action_approval_tool_or_effect_field():
    banned = {"approve", "approval", "tool", "tool_calls", "action", "effect", "purchase", "email", "side_effects", "recommendation", "decision"}
    def keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k.lower(); yield from keys(v)
        elif isinstance(o, list):
            for x in o:
                yield from keys(x)
    for sch in ("model-output.schema.json", "result-envelope.schema.json"):
        def sk(s):
            if isinstance(s, dict):
                for k, v in s.get("properties", {}).items():
                    yield k.lower(); yield from sk(v)
                for kk in ("items", "anyOf", "oneOf", "allOf", "then", "else", "if"):
                    x = s.get(kk)
                    for y in (x if isinstance(x, list) else [x] if x else []):
                        yield from sk(y)
        assert not (set(sk(O.SCHEMAS[sch])) & banned), sch
    for key in ("gap", "budget", "nogap", "miss"):
        env = run(E.IN[key], O.reference_output(E.IN[key]), audit_complete=True)["envelope"]
        assert not (set(keys(env)) & banned)
    for c in (c for c in E.CASES if c["group"] == "injection" and "tool" in c["id"] or "approve" in c["id"]):
        assert E.run_case(c)["status"] == "REJECTED"


def test_the_prohibited_effects_list_is_a_constant_of_the_input_and_cannot_be_altered():
    for bad in ([], ["PURCHASE"], ["PURCHASE", "INVENTORY_MUTATION", "SUPPLIER_CONTACT", "APPROVAL", "FINANCIAL_MUTATION"], ["PURCHASE", "INVENTORY_MUTATION", "SUPPLIER_CONTACT", "APPROVAL", "FINANCIAL_MUTATION", "ARBITRARY_TOOL", "SEND_EMAIL"]):
        mi = E.rehash(dict(copy.deepcopy(E.IN["gap"]), prohibited_effects=bad))
        assert "input_invalid" in O.check_input(mi)


def test_the_task_is_a_fixed_constant_an_unsupported_task_is_refused():
    mi = E.rehash(dict(copy.deepcopy(E.IN["gap"]), task="APPROVE_PURCHASE_ORDER"))
    assert "input_invalid" in O.check_input(mi)


# ============================================================ the milestone gates, stated as one assertion each
def test_gate_zero_accepted_invalid_claims():
    assert E.metrics()["accepted_invalid_claims"] == 0


def test_gate_the_committed_evidence_equals_a_fresh_run():
    r = subprocess.run([sys.executable, "tools/ops_explanation_eval.py", "--check"], cwd=LAB, env={**os.environ, "PYTHONPATH": str(LAB)})
    assert r.returncode == 0, "results/ops-explanation/m-ops-contract-2-offline-matrix.json is stale: run tools/ops_explanation_eval.py"


def test_negative_control_a_behaviour_neutral_edit_is_not_flagged_as_a_killed_mutant():
    mod = mutated_module('PROFILE = "ops-explanation-v1-milestone-profile"', 'PROFILE = "renamed-but-identical-behaviour"')
    a, b = E.run_cases(O), E.run_cases(mod)
    assert [(x["got"], x["exact"]) for x in a] == [(x["got"], x["exact"]) for x in b], "an equivalent mutant must leave every verdict unchanged, or the mutation harness proves nothing"


def test_the_published_schema_alone_would_accept_defects_that_the_semantic_validator_rejects():
    """Contract finding, pinned: JSON Schema validity is necessary, not sufficient (the specification says so; these are the concrete cases)."""
    v = jsv("model-output.schema.json"); mi = E.IN["gap"]
    wrong = E.edit(lambda o: E.claim(o, "c3").update(claimed_difference=61))(mi)
    dup = E.edit(lambda o: E.claim(o, "c2").update(claim_id="c1"))(mi)
    as_float = json.loads(json.dumps(O.reference_output(mi)).replace('"claimed_difference": 60', '"claimed_difference": 60.0'))
    for name, out in (("wrong arithmetic", wrong), ("duplicate claim ids", dup), ("an integral float", as_float)):
        assert not list(v.iter_errors(out)), f"the schema alone accepts {name}"
    assert E.run_case(next(c for c in E.CASES if c["id"] == "diff-plus-one"))["status"] == "REJECTED"
    assert E.run_case(next(c for c in E.CASES if c["id"] == "structure-duplicate-claim-ids"))["status"] == "REJECTED"
    assert E.run_case(next(c for c in E.CASES if c["id"] == "diff-as-float-text"))["status"] == "REJECTED"
