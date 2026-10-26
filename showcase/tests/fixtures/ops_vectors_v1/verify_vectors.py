"""Independent verifier for the NASHA Operations explanation golden-vector package (v1). Standard library ONLY: it imports nothing from the repository and shares no code with the reference implementation, so agreement is evidence, not tautology.
Run from anywhere:  python3 verify_vectors.py [path-to-package-dir]     Exit 0 and 'ALL VECTORS VERIFIED' on success; otherwise lists every failure."""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

D = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
FAIL = []


def check(ok, what):
    if not ok:
        FAIL.append(what)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(name):
    return json.loads((D / name).read_text(encoding="utf-8"))


# ---------- my own strict JSON + canonical form (canonical-json.v1)
class Strict(Exception):
    pass


def _pairs(p):
    d = {}
    for k, v in p:
        if k in d:
            raise Strict("duplicate_key")
        d[k] = v
    return d


def _const(n):
    raise Strict("non_finite_number")


def _flt(t):
    raise Strict("non_integer_number")


def depth(v, d=1):
    if isinstance(v, dict):
        return max([d] + [depth(x, d + 1) for x in v.values()])
    if isinstance(v, list):
        return max([d] + [depth(x, d + 1) for x in v])
    return d


def strict(raw):
    if isinstance(raw, bytes):
        if len(raw) > 12288:
            raise Strict("oversize")
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise Strict("invalid_utf8")
    elif len(raw.encode("utf-8")) > 12288:
        raise Strict("oversize")
    try:
        v = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_const, parse_float=_flt)
    except Strict:
        raise
    except ValueError:
        raise Strict("not_json")
    if depth(v) > 8:
        raise Strict("too_deep")
    return v


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


# ---------- manifest
for line in (D / "MANIFEST.sha256").read_text().splitlines():
    h, name = line.split("  ", 1)
    check(sha((D / name).read_bytes()) == h, f"manifest: {name} differs")

ident = load("identifiers.json")
TEN = ident["tenants"]

# ---------- canonical json
cj = load("canonical_json.json")
for p in cj["positive"]:
    c = canon(strict(p["input_json_text"]))
    check(c.decode() == p["canonical_text"] and c.hex() == p["canonical_hex"] and sha(c) == p["sha256"], f"canonical: {p['name']}")
for n in cj["negative"]:
    if "raw_text" in n:
        raw = n["raw_text"]
    elif "raw_hex" in n:
        raw = bytes.fromhex(n["raw_hex"])
    else:
        r = n["recipe"]
        raw = " " * r["prefix_spaces"] + r["then"] if "prefix_spaces" in r else r["open"] * r["depth"] + r["close"] * r["depth"]
    try:
        strict(raw); got = None
    except Strict as e:
        got = str(e)
    check(got == n["expect"], f"canonical negative {n['name']}: got {got}, expected {n['expect']}")

# ---------- record hashes
V1 = ident["record_hash_v1_preimage_keys"]
rh = load("record_hashes.json")
for v in rh["v0_published_example"]:
    check(list(sorted(v["preimage"])) == sorted(ident["record_hash_v0_preimage_keys"]) and sha(canon(v["preimage"])) == v["sha256"] == v["published_record_sha256"], f"record v0 {v['fact_id']}")
for v in rh["v1_live"]:
    check(sorted(v["preimage"]) == sorted(V1) and v["preimage"]["profile"] == "record-hash.v1" and sha(canon(v["preimage"])) == v["sha256"] and v["equals_input_record_sha256"], f"record v1 {v['tenant']}/{v['scenario']}/{v['fact_id']}")
base = next(v for v in rh["v1_live"] if v["tenant"] == "nasha-brewery" and v["scenario"] == "count-gap" and v["fact_id"] == "fact:counted_units")
check(base["sha256"] == rh["v1_baseline_counted_fact"]["sha256"], "record v1 baseline pointer")
for s in rh["v1_sensitivity"]:
    pre = dict(base["preimage"])
    if s["changed_field"].startswith("profile"):
        del pre["profile"]
    else:
        pre[s["changed_field"]] = s["new_value"]
    check(sha(canon(pre)) == s["sha256"] and s["sha256"] != base["sha256"], f"sensitivity {s['changed_field']}")
a = {(v["tenant"], v["scenario"], v["fact_id"]): v["sha256"] for v in rh["v1_live"]}
check(a[("nasha-brewery", "count-gap", "fact:counted_units")] != a[("meridian-fitness", "count-gap", "fact:counted_units")], "v1 is tenant-scoped")

# ---------- scenarios: snapshot hash, record hashes, required reasons
def snapshot(mi):
    return sha(canon({k: mi[k] for k in ("as_of", "entities", "facts", "comparison_groups", "completeness")}))


def v1_hash(f, scope):
    p = f["provenance"]
    return sha(canon(dict(profile="record-hash.v1", tenant_scope_id=scope, source_kind=p["source_kind"], source_ref=p["source_ref"], record_id=p["record_id"], source_revision=p["source_revision"], subject_id=f["subject_id"],
                          inventory_item_id=f["inventory_item_id"], field=f["field"], availability=f["availability"], value=f["value"], unit=f["unit"], as_of=f["as_of"])))


def reasons(mi):
    items = [e for e in mi["entities"] if e["kind"] == "INVENTORY_ITEM"]
    if len(items) != 1:
        return ["INSUFFICIENT_SCOPE"]
    it = items[0]["id"]
    ex = [f for f in mi["facts"] if f["subject_id"] == it and f["field"] == "expected_units"]
    co = [f for f in mi["facts"] if f["subject_id"] == it and f["field"] == "counted_units"]
    if len(ex) > 1 or len(co) > 1:
        return ["INSUFFICIENT_SCOPE"]
    r = set(); both = ex + co
    if not ex or not co or any(f["availability"] == "MISSING" for f in both):
        r.add("MISSING_REQUIRED_EVIDENCE")
    if any(f["availability"] == "CONFLICTING" for f in both):
        r.add("CONFLICTING_EVIDENCE")
    if both and any(f["unit"] != "UNITS" or f["inventory_item_id"] != it for f in both):
        r.add("INCOMPATIBLE_UNITS")
    return sorted(r)


sc = load("scenarios.json")
by = {}
for s in sc["scenarios"]:
    mi = s["model_input"]; by[(s["tenant"], s["scenario"])] = mi
    check(snapshot(mi) == mi["snapshot_sha256"] == s["snapshot_sha256"], f"snapshot {s['tenant']}/{s['scenario']}")
    check(sha(canon(mi)) == s["model_input_canonical_sha256"], f"input canonical sha {s['tenant']}/{s['scenario']}")
    check(mi["tenant_scope_id"] == TEN[s["tenant"]] and all(f["provenance"]["record_sha256"] == v1_hash(f, mi["tenant_scope_id"]) for f in mi["facts"]), f"record hashes {s['tenant']}/{s['scenario']}")
    check(reasons(mi) == s["required_abstention_reasons"], f"required reasons {s['tenant']}/{s['scenario']}")
pe = sc["published_example"]
check(pe["matches"] and pe["snapshot_sha256"] == pe["recomputed_snapshot_sha256"], "published example snapshot hash")

# ---------- rendered strings (my own templates)
rd = load("rendered.json")


def units(n):
    return f"{n} unit" if abs(n) == 1 else f"{n} units"


def answer(alias, e, c):
    d = e - c
    rel = f"The counted quantity is {units(d)} below expected." if d > 0 else f"The counted quantity is {units(-d)} above expected." if d < 0 else "The counted quantity equals the expected quantity."
    return f"In this synthetic snapshot, the expected quantity of {html.escape(alias)} is {units(e)} and the counted quantity is {units(c)}. {rel} These scenario assumptions do not establish a physical root cause."


TXT = {"MISSING_REQUIRED_EVIDENCE": "A required count is missing from this synthetic snapshot.", "CONFLICTING_EVIDENCE": "The recorded counts conflict in this synthetic snapshot.",
       "INCOMPATIBLE_UNITS": "The recorded counts are not in compatible units or for the same item.", "INSUFFICIENT_SCOPE": "This synthetic snapshot does not cover the scope needed for an explanation.", "UNSUPPORTED_TASK": "This request is not a supported explanation task."}
for r in rd["answers"]:
    check(answer(r["alias"], r["expected"], r["counted"]) == r["text"], f"rendered answer {r['name']}")
for r in rd["abstentions"]:
    check(" ".join(TXT[k] for k in rd["abstention_order"] if k in r["required_reasons"]) + " No explanation is given." == r["text"], f"rendered abstention {r['required_reasons']}")
check(all(len(r["text"]) <= 2000 for r in rd["answers"] + rd["abstentions"]), "rendered length bound")

# ---------- diagnostics
dg = load("diagnostics.json")
codes = [c["code"] for c in dg["codes"]]
check(all(re.fullmatch(r"[a-z][a-z0-9:_-]{0,95}", c) for c in codes) and len(set(codes)) == len(codes), "diagnostic codes are lower-case, valid and unique")
check(all(c["status"] == ("FAILED" if c["class_"] in dg["failed_classes"] else "REJECTED") for c in dg["codes"]), "diagnostic status follows class")
check({"source_provenance_missing", "provider_provenance_missing", "incorrect_difference", "duplicate_key", "invalid_utf8", "non_integer_number", "schema_invalid", "provider_truncated"} <= set(codes), "required diagnostics present")
CLS = {c["code"]: c["class_"] for c in dg["codes"]}

# ---------- envelopes
en = load("envelopes.json")
for e in en["envelopes"]:
    env = e["expected_envelope"]; name = e["name"]
    check(re.fullmatch(r"[a-z][a-z0-9:_-]{0,95}", "x") and all(c in CLS for c in env["validation_codes"]), f"envelope {name}: codes in table")
    want = "FAILED" if any(CLS[c] in dg["failed_classes"] for c in env["validation_codes"]) else "REJECTED"
    if env["validation_codes"]:
        check(env["status"] == want, f"envelope {name}: status {env['status']} vs class {want}")
    if env["accepted_result_sha256"]:
        ref = e["model_input"].split(":", 1)[1].split("/")
        mi = by[(ref[1], ref[0])]
        txt = answer(mi["entities"][0]["alias"], next(f["value"] for f in mi["facts"] if f["field"] == "expected_units"), next(f["value"] for f in mi["facts"] if f["field"] == "counted_units"))
        check(env["rendered_explanation"] == txt, f"envelope {name}: rendered text")
        h = sha(canon(dict(schema_version="ops-explanation-output.v1", analysis_id=mi["analysis_id"], snapshot_sha256=mi["snapshot_sha256"], claims=env["model_output"]["claims"], rendered_explanation=txt,
                           validator_revision=ident["validator_revision"], renderer_revision=ident["renderer_revision"])))
        check(h == env["accepted_result_sha256"], f"envelope {name}: accepted_result_sha256")
    if env["status"] in ("REJECTED", "FAILED"):
        check(env["model_output"] is None and env["accepted_result_sha256"] is None, f"envelope {name}: nothing shown")
        check(env["rendered_explanation"] == (rd["rejected"] if env["status"] == "REJECTED" else rd["failed"]), f"envelope {name}: fixed message")

# ---------- verdicts (structure + the admission and strict-parse expectations I can recompute independently)
vd = load("verdicts.json")
PARSE = {"duplicate_key", "non_finite_number", "non_integer_number", "invalid_utf8", "oversize", "too_deep", "not_json"}
n_checked = 0
for c in vd["cases"]:
    check(c["input"] in vd["inputs"] and all(x in CLS for x in c["expected_codes"]) and c["matches_matrix_expectation"], f"verdict {c['id']}: structure")
    mi = vd["inputs"][c["input"]]
    adm = []
    if mi["snapshot_sha256"] != snapshot(mi):
        adm.append("snapshot")
    if all(isinstance(f.get("provenance"), dict) for f in mi["facts"]) and any(f["provenance"]["record_sha256"] != v1_hash(f, mi["tenant_scope_id"]) for f in mi["facts"]):
        adm.append("record")
    if "input_refused" not in c["expected_codes"] and c["expected_status"] != "REJECTED_X":
        check(not adm, f"verdict {c['id']}: input should pass hash admission")
    if adm and c["id"] not in ("injection-smuggled-key-in-the-input",):
        check("source_hash_mismatch" in c["expected_codes"] and "input_refused" in c["expected_codes"], f"verdict {c['id']}: hash defect must be refused as source_hash_mismatch")
    if "output_text" in c and c["output_text"] is not None and c["group"] == "structure":
        try:
            strict(c["output_text"]); got = None
        except Strict as e:
            got = str(e)
        if got in PARSE:
            check(c["expected_codes"] == [got], f"verdict {c['id']}: strict parse gives {got}")
            n_checked += 1
    if "output_hex" in c:
        try:
            strict(bytes.fromhex(c["output_hex"])); got = None
        except Strict as e:
            got = str(e)
        check(c["expected_codes"] == [got], f"verdict {c['id']}: bytes")
check(n_checked >= 5, "enough strict-parse verdicts recomputed")
check(len(vd["cases"]) >= 100, "verdict count")

# ---------- Amara adapter expectations
am = load("amara_adapter.json")
for it in am["items"]:
    a = it["amara_current"]
    dig = lambda o: sha(json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    ok = all(r["sha256"] == dig({k: v for k, v in r.items() if k != "sha256"}) for r in a["records"]) and a["snapshot_sha256"] == dig(dict(tenant=it["tenant"], scenario_id=it["scenario"], records=a["records"]))
    check(ok, f"amara digest {it['tenant']}/{it['scenario']}")
    mi = it["expected_model_input"]
    check(snapshot(mi) == it["expected_model_input_snapshot_sha256"] and mi["facts"][0]["provenance"]["record_sha256"] == v1_hash(mi["facts"][0], mi["tenant_scope_id"]), f"adapter input {it['tenant']}/{it['scenario']}")
    if it["shared_renderer_status"] in ("ACCEPTED",):
        exp = next(f["value"] for f in mi["facts"] if f["field"] == "expected_units"); cnt = next(f["value"] for f in mi["facts"] if f["field"] == "counted_units")
        check(it["shared_renderer_text"] == answer(mi["entities"][0]["alias"], exp, cnt), f"adapter text {it['tenant']}/{it['scenario']}")
    check(it["text_differs_from_amara"], f"amara/shared text difference recorded {it['scenario']}")

if FAIL:
    print("FAILURES:\n  " + "\n  ".join(FAIL)); sys.exit(1)
print("ALL VECTORS VERIFIED")
