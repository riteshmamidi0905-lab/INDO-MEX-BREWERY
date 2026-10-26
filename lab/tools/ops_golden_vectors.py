"""Generate the versioned golden-vector package for the NASHA Operations explanation contract (lab/contracts/ops_explanation_vectors/v1/).
Deterministic: running it twice yields byte-identical files; `--check` exits non-zero if the committed package differs from a fresh run. The vectors are produced by THIS repository's reference implementation and are meant to be verified INDEPENDENTLY:
the package ships `verify_vectors.py`, a standard-library-only verifier that imports nothing from the repository, and Codex is expected to verify them with its own implementation before any integration. Nothing here calls a model."""
import copy
import hashlib
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from nasha_lab.growth import ops_explanation as O, ops_explanation_eval as E  # noqa: E402

OUT = LAB / "contracts" / "ops_explanation_vectors" / "v1"
TENANTS = {"nasha-brewery": "00000000-0000-4000-8000-0000000000a1", "meridian-fitness": "00000000-0000-4000-8000-0000000000b2"}      # PLACEHOLDER scope ids: the host assigns real ones
ANALYSIS, WORKFLOW = "00000000-0000-4000-8000-000000000001", "run-0000000001"
ALIAS = {"nasha-brewery": "Synthetic packaging", "meridian-fitness": "Synthetic towels"}
SCEN = ["count-gap", "budget-risk", "no-gap", "missing-count"]


def dumps(o):
    return json.dumps(o, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def scenario_input(scenario, tenant):
    return O.build_model_input(scenario, TENANTS[tenant], ANALYSIS, WORKFLOW, item_alias=ALIAS[tenant])


def identifiers():
    return dict(vector_package="ops-golden-vectors.v1", canonical_json=O.CANONICAL_JSON_PROFILE, record_hash=dict(live=O.LIVE_RECORD_HASH_PROFILE, historical_golden_vector_only=O.HISTORICAL_RECORD_HASH_PROFILE),
                record_hash_v1_preimage_keys=list(O.V1_PREIMAGE_KEYS), record_hash_v0_preimage_keys=["subject_id", "field", "value", "unit"],
                snapshot_hash="sha256 of canonical-json.v1 of {as_of, entities, facts, comparison_groups, completeness}; collections sorted by id, referenced id arrays sorted (Codex specification 5.2)",
                diagnostics=O.DIAGNOSTICS_VERSION, validator_revision=O.VALIDATOR_REVISION, renderer_revision=O.RENDERER_REVISION, milestone_profile=O.PROFILE,
                schema_versions=dict(input=O.INPUT_VERSION, output=O.OUTPUT_VERSION, result=O.RESULT_VERSION),
                contract_pin_set=dict(id="codex-phase5-spec@b064414b0773681c9b2af046e1458ce0c1c7f343", files=O.PINNED), limits=dict(max_output_bytes=O.MAX_OUTPUT_BYTES, max_input_bytes=O.MAX_INPUT_BYTES, max_rendered_chars=O.MAX_RENDERED_CHARS, max_json_depth=8),
                approved_model=dict(name=O.APPROVED_MODEL, digest=O.APPROVED_DIGEST), tenants=TENANTS, analysis_id=ANALYSIS, workflow_id=WORKFLOW)


def canonical_json():
    pos = []
    for name, text in [("empty-object", "{}"), ("key-order", '{"b":1,"a":2,"c":{"z":1,"y":[3,2,1]}}'), ("unicode-not-escaped", '{"name":"Z\\u00fcrich \\u2713","emoji":"\\ud83d\\ude00"}'), ("integer-extremes", '{"max":1000000000,"min":-1000000000,"zero":0}'),
                       ("booleans-null-array-order", '{"t":true,"f":false,"n":null,"a":[null,true,"x",1]}'), ("string-escapes", '{"s":"q\\" b\\\\ n\\n t\\t c\\u0001 d\\u007f"}'), ("non-ascii-key-order", '{"\\u00e9":1,"z":2,"a":3}'),
                       ("whitespace-insensitive", ' { "a" : 1 ,\n "b" : [ 1 , 2 ] } ')]:
        value = O.parse_strict(text); c = O.canonical(value)
        pos.append(dict(name=name, input_json_text=text, canonical_text=c.decode("utf-8"), canonical_hex=c.hex(), sha256=O.sha256_hex(c)))
    neg = []
    for name, raw in [("duplicate-key", '{"a":1,"a":2}'), ("nan", '{"a":NaN}'), ("infinity", '{"a":Infinity}'), ("negative-infinity", '{"a":-Infinity}'), ("fraction", '{"a":1.5}'), ("integral-float", '{"a":60.0}'),
                      ("exponent", '{"a":1e2}'), ("not-json", "hello"), ("empty-string", ""), ("two-documents", "{}{}"), ("trailing-comma", '{"a":1,}')]:
        try:
            O.parse_strict(raw); code = None
        except O.StrictJSONError as e:
            code = e.code
        neg.append(dict(name=name, raw_text=raw, expect=code))
    for name, raw in [("invalid-utf8", b"\xff\xfe{}")]:
        try:
            O.parse_strict(raw); code = None
        except O.StrictJSONError as e:
            code = e.code
        neg.append(dict(name=name, raw_hex=raw.hex(), expect=code))
    for name, recipe, raw in [("oversize", dict(prefix_spaces=O.MAX_OUTPUT_BYTES + 1, then="{}"), " " * (O.MAX_OUTPUT_BYTES + 1) + "{}"), ("too-deep", dict(open="[", close="]", depth=20), "[" * 20 + "]" * 20)]:
        try:
            O.parse_strict(raw); code = None
        except O.StrictJSONError as e:
            code = e.code
        neg.append(dict(name=name, recipe=recipe, expect=code))
    return dict(positive=pos, negative=neg, note="canonical-json.v1 = UTF-8, keys sorted by code point, separators (',',':'), ensure_ascii=false, integers only. Negative cases must be refused at strict parse with the stated lowercase diagnostic code.")


def record_hashes():
    ex = json.load(open(O.CONTRACT_DIR / "examples" / "model-input.json"))
    v0 = []
    for f in ex["facts"]:
        pre = O.record_preimage(O.HISTORICAL_RECORD_HASH_PROFILE, f, ex["tenant_scope_id"]); c = O.canonical(pre)
        v0.append(dict(fact_id=f["id"], preimage=pre, canonical_text=c.decode(), sha256=O.sha256_hex(c), published_record_sha256=f["provenance"]["record_sha256"], matches_published=O.sha256_hex(c) == f["provenance"]["record_sha256"]))
    v1 = []
    for tenant in TENANTS:
        for scen in SCEN:
            mi = scenario_input(scen, tenant)
            for f in mi["facts"]:
                pre = O.record_preimage(O.LIVE_RECORD_HASH_PROFILE, f, mi["tenant_scope_id"]); c = O.canonical(pre)
                v1.append(dict(tenant=tenant, scenario=scen, fact_id=f["id"], preimage=pre, canonical_text=c.decode(), sha256=O.sha256_hex(c), equals_input_record_sha256=O.sha256_hex(c) == f["provenance"]["record_sha256"]))
    base = scenario_input("count-gap", "nasha-brewery"); f0 = next(f for f in base["facts"] if f["field"] == "counted_units")
    sens = []
    for key, newval in [("tenant_scope_id", TENANTS["meridian-fitness"]), ("source_kind", "SYNTHETIC_RECORD"), ("source_ref", "scenario://count-gap/v1/other"), ("record_id", "scenario:other"), ("source_revision", "count-gap:v2"), ("subject_id", "item:other"),
                        ("inventory_item_id", "item:other"), ("field", "expected_units"), ("availability", "CONFLICTING"), ("value", 41), ("unit", "USD_CENTS_PER_UNIT"), ("as_of", "2026-10-26T00:00:00Z")]:
        pre = dict(O.record_preimage(O.LIVE_RECORD_HASH_PROFILE, f0, base["tenant_scope_id"])); pre[key] = newval
        sens.append(dict(changed_field=key, new_value=newval, sha256=O.sha256_hex(O.canonical(pre))))
    pre = dict(O.record_preimage(O.LIVE_RECORD_HASH_PROFILE, f0, base["tenant_scope_id"])); del pre["profile"]
    sens.append(dict(changed_field="profile (removed)", new_value=None, sha256=O.sha256_hex(O.canonical(pre))))
    return dict(v0_published_example=v0, v1_live=v1, v1_baseline_counted_fact=dict(tenant="nasha-brewery", scenario="count-gap", fact_id=f0["id"], sha256=f0["provenance"]["record_sha256"]), v1_sensitivity=sens,
                rules=["record-hash.v0 exists only to verify the published example; a live snapshot carrying v0 hashes is refused (verdict vectors: record-hash-v0-is-never-admissible-for-a-live-snapshot).",
                       "The profile is a server constant, never read from the snapshot, the model output or the caller; mixed profiles fail closed (record-hash-mixed-profiles-fail-closed).",
                       "v1 sensitivity: changing ANY preimage field, or removing the profile string, changes the hash; the v1 value of the same facts differs between tenants."])


def scenarios():
    items = []
    for tenant in TENANTS:
        for scen in SCEN:
            mi = scenario_input(scen, tenant); reasons, item, ex, co = O.required_reasons(mi)
            items.append(dict(tenant=tenant, scenario=scen, model_input=mi, snapshot_sha256=mi["snapshot_sha256"], model_input_canonical_sha256=O.sha256_hex(O.canonical(mi)), required_abstention_reasons=sorted(reasons)))
    ex = json.load(open(O.CONTRACT_DIR / "examples" / "model-input.json"))
    return dict(scenarios=items, published_example=dict(snapshot_sha256=ex["snapshot_sha256"], recomputed_snapshot_sha256=O.snapshot_sha256(ex), matches=O.snapshot_sha256(ex) == ex["snapshot_sha256"]))


def rendered():
    ans = []
    for name, alias, e, c in [("shortfall", "Synthetic packaging", 100, 40), ("shortfall-singular-unit", "Synthetic packaging", 2, 1), ("surplus", "Synthetic packaging", 100, 150), ("surplus-singular-unit", "Synthetic packaging", 100, 101),
                              ("equal", "Synthetic packaging", 100, 100), ("zero-counted", "Synthetic packaging", 100, 0), ("alias-with-markup-is-escaped", "<b>x</b> & y", 100, 40)]:
        mi = E.base("count-gap"); mi["entities"][0]["alias"] = alias
        for f in mi["facts"]:
            if f["field"] == "expected_units":
                f["value"] = e
            if f["field"] == "counted_units":
                f["value"] = c
        ans.append(dict(name=name, alias=alias, expected=e, counted=c, text=O.render_answer(mi)))
    ab = []
    for reasons in [["MISSING_REQUIRED_EVIDENCE"], ["CONFLICTING_EVIDENCE"], ["INCOMPATIBLE_UNITS"], ["INSUFFICIENT_SCOPE"], ["MISSING_REQUIRED_EVIDENCE", "CONFLICTING_EVIDENCE"], ["MISSING_REQUIRED_EVIDENCE", "INCOMPATIBLE_UNITS"]]:
        ab.append(dict(required_reasons=reasons, text=O.render_abstention(dict(flags=[], required_reasons=reasons))))
    return dict(answers=ans, abstentions=ab, unnecessary_abstention=O.UNNECESSARY_TEXT, rejected=O.REJECTED_TEXT, failed=O.FAILED_TEXT,
                abstention_order=O.ABSTAIN_ORDER, answer_template="In this synthetic snapshot, the expected quantity of {alias} is {E} and the counted quantity is {C}. {relation} These scenario assumptions do not establish a physical root cause.",
                relation_templates=dict(below="The counted quantity is {D} below expected.", above="The counted quantity is {D} above expected.", equal="The counted quantity equals the expected quantity."), unit_phrase="'1 unit' when the absolute value is 1, otherwise '{n} units'; alias is HTML-escaped")


def envelopes():
    out = []
    mi = scenario_input("count-gap", "nasha-brewery"); miss = scenario_input("missing-count", "nasha-brewery")
    trusted = {f["provenance"]["record_id"] + "|" + f["provenance"]["source_ref"]: f["provenance"]["record_sha256"] for f in mi["facts"]}
    meta = dict(name="ollama", model=O.APPROVED_MODEL, digest=O.APPROVED_DIGEST, runtime_profile_sha256="a" * 64, actual_model_calls=1, prompt_tokens=100, completion_tokens=50, estimated_usage=False, latency_ms=1000)
    wrong = O.reference_output(mi); [c.update(claimed_difference=61) for c in wrong["claims"] if c["kind"] == "DIFFERENCE"]
    good, abst = O.reference_output(mi), O.reference_output(miss)

    def add(name, model_input, candidate, mode="DETERMINISTIC_REPLAY", audit_complete=False, **kw):
        res = O.explain(model_input, (lambda m: candidate) if not callable(candidate) else candidate, mode, audit_complete, **kw)
        desc = dict(name=name, model_input=("scenario:" + model_input_name(model_input)), mode=mode, audit_complete=audit_complete, candidate=(candidate if not callable(candidate) else "<provider failure>"), options={k: v for k, v in kw.items() if k != "trusted_record_hashes"} | ({"trusted_record_hashes": "host map of record_id|source_ref -> record_sha256 for the input's facts"} if "trusted_record_hashes" in kw else {}),
                    expected_envelope=res["envelope"], expected_verdict_status=res["verdict"]["status"], expected_verdict_codes=res["verdict"]["codes"])
        out.append(desc)

    def model_input_name(x):
        return "count-gap/nasha-brewery" if x is mi else "missing-count/nasha-brewery"

    add("accepted-answer", mi, good, audit_complete=True)
    add("audit-pending-answer", mi, good)
    add("abstained-missing-count", miss, abst, audit_complete=True)
    add("audit-pending-abstain", miss, abst)
    add("rejected-wrong-difference", mi, wrong)
    add("rejected-input-refused-live-without-trusted-hashes", mi, good, "LIVE_LLM")
    add("live-accepted-with-provider-evidence", mi, (good, meta), "LIVE_LLM", True, trusted_record_hashes=trusted)
    add("failed-provider-timeout", mi, lambda m: (_ for _ in ()).throw(TimeoutError()))
    add("failed-provider-error", mi, lambda m: (_ for _ in ()).throw(RuntimeError("x")))
    add("failed-provider-truncated-finish-reason-length", mi, (good, meta, "length"), "LIVE_LLM", False, trusted_record_hashes=trusted)
    add("failed-provider-truncated-exception", mi, lambda m: (_ for _ in ()).throw(O.ProviderTruncated()))
    add("failed-provider-provenance-missing", mi, good, "LIVE_LLM", False, trusted_record_hashes=trusted)
    add("failed-mode-mismatch-replay-carrying-provider-metadata", mi, (good, meta))
    add("failed-record-hash-profile-v0-pinned", mi, good, record_hash_profile="record-hash.v0")
    add("failed-record-hash-profile-unknown", mi, good, record_hash_profile="record-hash.v9")
    return dict(envelopes=out, note="Envelopes are built to ops-explanation-result.v1 (published schema). validation_codes are lower-case. A non-text candidate is shown as its JSON value.")


def diagnostics():
    rows = [dict(code=c, class_=cls, status=("FAILED" if cls in O.FAILED_CLASSES else "REJECTED"), m_ops_1_spelling=next((u for u, v in O.LEGACY_UPPER.items() if v == c and u != c.upper()), c.upper())) for c, cls in sorted(O.DIAGNOSTICS.items())]
    return dict(version=O.DIAGNOSTICS_VERSION, codes=rows, flags=list(O.FLAGS), failed_classes=list(O.FAILED_CLASSES),
                disambiguation={"source_provenance_missing": "the HOST's trusted record hash for a fact is absent (source side; REJECTED at admission, before any provider call)", "provider_provenance_missing": "a live result lacks evidence of the approved model identity and actual, non-estimated use (provider side; FAILED)"},
                rules=["REJECTED: the input or the candidate output is at fault. FAILED: infrastructure or configuration is at fault; the model's output was not judged.", "A provider that stopped at its token limit (finish_reason 'length' or ProviderTruncated) is FAILED provider_truncated. Truncated JSON without that signal is indistinguishable from a bad answer and stays REJECTED not_json: the host MUST pass finish_reason.",
                       "Schema enums (reason_codes, LIMITATION.code, status, kind, availability, units) keep their published upper-case spelling; only diagnostics are lower-case."],
                reserved_for_deferred_claim_kinds=["incorrect_comparison", "invalid_comparison_scope", "incomplete_comparison_set", "incorrect_extremum", "omitted_tie", "unsupported_absence", "price_mismatch", "price_class_mismatch"])


def verdicts():
    inputs, cases = {}, []
    for c in E.CASES:
        mi = E.input_for(c); key = c["mi"] or "gap"
        inputs[key] = mi
        raw = c["out"](mi)
        if isinstance(raw, dict):
            raw = json.dumps(raw, sort_keys=True)
        entry = dict(id=c["id"], group=c["group"], input=key)
        if isinstance(raw, str):
            entry["output_text"] = raw if len(raw) < 14000 else None
            if len(raw) >= 14000:
                entry["output_recipe"] = dict(prefix_spaces=len(raw) - len(raw.lstrip(" ")), then=raw.lstrip(" "))
        elif isinstance(raw, (bytes, bytearray)):
            entry["output_hex"] = bytes(raw).hex()
        else:
            entry["output_non_text"] = repr(raw)
        kw = c["kw"]
        opts = {}
        if kw == "TRUSTED_RIGHT":
            opts["trusted_record_hashes"] = "right"
        elif kw == "TRUSTED_WRONG":
            opts["trusted_record_hashes"] = "one-hash-wrong"
        else:
            opts = {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in kw.items()}
            if "trusted_record_hashes" in opts:
                opts["trusted_record_hashes"] = "empty"
        got = E.run_case(c)
        entry.update(options=opts, expected_status=got["status"], expected_codes=got["codes"], expected_flags=sorted(got["flags"]), matches_matrix_expectation=E.judge(c, got)[0])
        cases.append(entry)
    return dict(inputs=inputs, cases=cases, trusted_record_hashes_options={"right": "record_id|source_ref -> record_sha256 of the 'gap' input's own facts", "one-hash-wrong": "same, with the first entry replaced by 64 zeros", "empty": "{}"},
                note="Verdicts are validate_output(output, input, **options) with the live profile. A non-text output is a Python value that is neither text nor JSON-like (diagnostic not_json_text).")


def amara_payload(tenant, scenario_id, scenarios_):
    """Transcription of codex/amara-readonly-operations@cb71397 showcase/showcase/operations.py::explain (pure), for adapter expectations. Their digest() is sha256 of canonical JSON (sorted keys, (',',':'), ensure_ascii=False)."""
    def digest(o):
        return O.sha256_hex(json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    sc = scenarios_[scenario_id]
    records = [dict(id=f"{tenant}:{scenario_id}:{field}", field=field, value=sc[field], unit="units", source=f"workforce.py:SCENARIOS/{scenario_id}/{field}", classification="SYNTHETIC_SCENARIO_ASSUMPTION") for field in ("expected", "counted")]
    for r in records:
        r["sha256"] = digest(r)
    missing = sc["counted"] is None
    diff = None if missing else sc["expected"] - sc["counted"]
    if missing:
        text = "The counted quantity is missing. No discrepancy can be established. Verify a count before drawing a conclusion."
    elif diff > 0:
        text = f"The scenario expects {sc['expected']} units and records {sc['counted']} counted units: a shortfall of {diff} units. These supplied assumptions do not establish a cause."
    elif diff < 0:
        text = f"The scenario records a surplus of {-diff} units. The supplied assumptions do not establish a cause."
    else:
        text = "Expected and counted quantities match. There is no discrepancy in this scenario snapshot; this does not establish that inventory is correct elsewhere."
    return dict(status="ABSTAINED" if missing else "EXPLAINED", explanation=text, difference=diff, records=records, snapshot_sha256=digest(dict(tenant=tenant, scenario_id=scenario_id, records=records)), renderer_revision="amara-readonly.v1")


def amara_adapter():
    out = []
    for tenant in TENANTS:
        for scen in SCEN:
            am = amara_payload(tenant, scen, O.SCENARIOS)
            mi = scenario_input(scen, tenant)
            ours = O.deterministic_replay(mi, True)["envelope"]
            out.append(dict(tenant=tenant, scenario=scen, amara_current=am, expected_model_input_snapshot_sha256=mi["snapshot_sha256"], expected_model_input=mi, shared_renderer_text=ours["rendered_explanation"], shared_renderer_status=ours["status"],
                            text_differs_from_amara=ours["rendered_explanation"] != am["explanation"]))
    return dict(source="Amara payload transcribed from codex/amara-readonly-operations@cb71397 showcase/showcase/operations.py; scenario values from workforce.py SCENARIOS (count-gap 100/40, budget-risk 100/20, no-gap 100/100, missing-count 100/None)",
                field_map={"expected": "expected_units", "counted": "counted_units"}, unit_map={"units": "UNITS"}, classification_map={"SYNTHETIC_SCENARIO_ASSUMPTION": "SCENARIO_ASSUMPTION"},
                id_rule="Amara id '{tenant}:{scenario}:{field}' carries the tenant NAME; the contract uses an opaque tenant_scope_id UUID, supplied by the host (the vectors use placeholders). fact ids are 'fact:{field}_units'.",
                source_ref_template="scenario://{scenario}/v1/{field}_units", record_id_template="scenario:{scenario}", source_revision_template="{scenario}:v1", item=dict(id="item:packaging (nasha-brewery) / item:towels is NOT used: the vectors use item:packaging with a per-tenant alias", aliases=ALIAS),
                hash_differences="Amara record sha256 = digest(record incl. id, source, classification); the contract uses record-hash.v1 over the tenant-scoped preimage. Amara snapshot_sha256 = digest({tenant, scenario_id, records}); the contract snapshot hash covers {as_of, entities, facts, comparison_groups, completeness}.",
                missing_in_amara=["as_of", "entities (item identity and alias)", "availability", "inventory_item_id", "target_units fact (optional)", "analysis_id / workflow_id / snapshot_id", "tenant_scope_id UUID"],
                d7_renderer_status="PENDING CODEX: Amara's wording differs from the shared renderer for shortfall, surplus, equal and missing-count; the shared strings are in rendered.json and shared_renderer_text below. Either side adopts the other's templates only through a version bump of both vector sets.",
                items=out)


FILES = dict(identifiers=identifiers, canonical_json=canonical_json, record_hashes=record_hashes, scenarios=scenarios, rendered=rendered, envelopes=envelopes, diagnostics=diagnostics, verdicts=verdicts, amara_adapter=amara_adapter)


def build():
    return {f"{k}.json": dumps(fn()) for k, fn in FILES.items()}


def manifest(files, verifier_bytes, readme_bytes):
    allf = dict(files); allf["verify_vectors.py"] = verifier_bytes.decode(); allf["README.md"] = readme_bytes.decode()
    return "".join(f"{hashlib.sha256(v.encode()).hexdigest()}  {k}\n" for k, v in sorted(allf.items()))


def main():
    files = build()
    verifier, readme = (OUT / "verify_vectors.py").read_bytes(), (OUT / "README.md").read_bytes()
    mf = manifest(files, verifier, readme)
    if "--check" in sys.argv:
        ok = all((OUT / k).exists() and (OUT / k).read_text() == v for k, v in files.items()) and (OUT / "MANIFEST.sha256").exists() and (OUT / "MANIFEST.sha256").read_text() == mf
        sys.exit(0 if ok else 1)
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in files.items():
        (OUT / k).write_text(v)
    (OUT / "MANIFEST.sha256").write_text(mf)
    print(f"wrote {len(files)} vector files + manifest to {OUT}")


if __name__ == "__main__":
    main()
