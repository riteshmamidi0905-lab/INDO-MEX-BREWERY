"""Operations explanation (M-OPS-1, OFFLINE): a PURE validator and deterministic renderer for the closed claim grammar of Codex's Phase 5 specification, restricted to its initial scenario.
Source of truth: the published JSON schemas vendored byte-for-byte in lab/contracts/ops_explanation (pinned by hash; this module refuses to load if any differs). The model, if one is ever used, may only select claim OBJECTS from a typed snapshot;
this module recomputes every claim from the snapshot and renders the explanation from server-owned templates. NO model-written text can reach the rendered explanation (the grammar has no free-text field and the renderer reads only the validated snapshot).
Scope of this milestone profile (narrower than the specification, which also allows optional price/comparison claims): an ANSWER is exactly OBSERVE(expected_units) + OBSERVE(counted_units) + DIFFERENCE(expected - counted) + LIMITATION(CAUSE_NOT_ESTABLISHED).
COMPARISON, EXTREMUM, SCOPED_ABSENCE and the other fields/limitations are valid in the schema and DEFERRED here: a claim of those kinds is rejected (fail closed). One false, unsupported or unexpected claim rejects the WHOLE output: there is no partial acceptance.
Contract alignment (approved baseline D1-D8): canonical-json.v1; tenant-scoped record-hash.v1 (record-hash.v0, the legacy 4-key form of the published example, exists ONLY for golden-vector verification and is never accepted for a live snapshot; no input, model output or caller chooses the profile);
lower-case diagnostics from one explicit table that also fixes whether a code makes a result REJECTED (the input or output is at fault) or FAILED (infrastructure or configuration is at fault); source provenance and staleness are checked at admission, before any provider call.
Nothing here calls a model, a database, the network, THE WEIR or the workflow; it neither reads nor writes any store. It is not the governed procurement workflow and cannot change a proposal, an approval or a hash."""
import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path

from . import model_boundary as MB

VALIDATOR_REVISION = "ops-validator-v1.1-m-ops-contract-1"
RENDERER_REVISION = "ops-renderer-v2.0-tenant-scoped-labels"
HISTORICAL_RENDERER_REVISION_V1 = "ops-renderer-v1.0-m-ops-1"      # M-OPS-1 / golden vectors v1 / frozen case set v1 only; unreachable from explain()
PROFILE = "ops-explanation-v1-milestone-profile"
CANONICAL_JSON_PROFILE = "canonical-json.v1"
DIAGNOSTICS_VERSION = "ops-diagnostics.v1"
OUTPUT_VERSION, INPUT_VERSION, RESULT_VERSION = "ops-explanation-output.v1", "ops-explanation-input.v1", "ops-explanation-result.v1"
MAX_OUTPUT_BYTES, MAX_INPUT_BYTES, MAX_RENDERED_CHARS = 12288, 16384, 2000
APPROVED_MODEL, APPROVED_DIGEST = "qwen2.5:7b-instruct", "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"

CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contracts" / "ops_explanation"
PINNED = {   # sha256 of the vendored upstream files (codex/phase5-integration-specification @ b064414; equal to that directory's MANIFEST.sha256)
    "contracts/model-input.schema.json": "3668b2f080546ca0f1ee5baa4ad9509939efd7a9fad53bc71f8cf336cc71deb0",
    "contracts/model-output.schema.json": "5414cd904bd2b109be24be52d5ba6d348b7a09d9b0e1829a19fcb06c8bffbccc",
    "contracts/request-envelope.schema.json": "6ff220a6c64b21a64c8020adb9089ffa0b2d71eb92cc0e92f79e5e1fb911245d",
    "contracts/result-envelope.schema.json": "7796703418002374f9208b8367bbcc36b2a22312e4286534162bd180e6af0fff",
    "examples/model-input.json": "d66ce7c118a2347e09fb7579ef82dd547ee4205d785392a55efc3717402ba941",
    "examples/model-output.json": "ac6a7968ab228cf51e91da00667d9a836c78ba1193b541455f0d07dbd6cdbb80",
    "prompt-candidate.json": "16f30b537c473fe8a3ed47a53d1c45f2b77aaae72106620599937d851ad4e77d",
    "execution-profile-candidate.json": "f713b9c35b8d65faf1caf38edb54d246bc3f0d4dee074ed1fbb4aa597aa87a8f",
}


class ContractMismatch(RuntimeError):
    """A vendored contract differs from the pinned upstream bytes, or uses a schema keyword this validator does not implement. Never silently continue."""


def _load_contracts():
    out = {}
    for rel, want in PINNED.items():
        data = (CONTRACT_DIR / rel).read_bytes()
        if hashlib.sha256(data).hexdigest() != want:
            raise ContractMismatch(f"{rel} differs from the pinned upstream contract")
        out[rel] = json.loads(data)
    return out


_C = _load_contracts()
SCHEMAS = {Path(k).name: v for k, v in _C.items() if k.startswith("contracts/")}


# ------------------------------------------------------------------ strict JSON, canonical form, hashes
class StrictJSONError(ValueError):
    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}"); self.code, self.detail = code, detail


def _pairs(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise StrictJSONError("duplicate_key", k)
        seen[k] = v
    return seen


def _no_const(name):
    raise StrictJSONError("non_finite_number", name)


def _no_float(text):
    raise StrictJSONError("non_integer_number", text)


def parse_strict(raw, max_bytes=MAX_OUTPUT_BYTES):
    """Bytes or str -> value. Rejects invalid UTF-8, oversize, duplicate object keys, NaN/Infinity, any non-integer number (including 60.0), and nesting deeper than 8."""
    if isinstance(raw, (bytes, bytearray)):
        if len(raw) > max_bytes:
            raise StrictJSONError("oversize", str(len(raw)))
        try:
            raw = bytes(raw).decode("utf-8", errors="strict")
        except UnicodeDecodeError as e:
            raise StrictJSONError("invalid_utf8", str(e))
    elif isinstance(raw, str):
        if len(raw.encode("utf-8", errors="surrogatepass")) > max_bytes:
            raise StrictJSONError("oversize", str(len(raw)))
    else:
        raise StrictJSONError("not_json_text", type(raw).__name__)
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_no_const, parse_float=_no_float)
    except StrictJSONError:
        raise
    except (ValueError, RecursionError) as e:
        raise StrictJSONError("not_json", str(e)[:80])
    if _depth(value) > 8:
        raise StrictJSONError("too_deep")
    return value


def _depth(v, d=1):
    if isinstance(v, dict):
        return max([d] + [_depth(x, d + 1) for x in v.values()])
    if isinstance(v, list):
        return max([d] + [_depth(x, d + 1) for x in v])
    return d


def canonical(value):
    """Keys sorted, no whitespace, ensure_ascii=False, integers only (the specification's canonicalization)."""
    def chk(v):
        if isinstance(v, float):
            raise StrictJSONError("non_integer_number", repr(v))
        if isinstance(v, dict):
            [chk(x) for x in v.values()]
        elif isinstance(v, list):
            [chk(x) for x in v]
    chk(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def snapshot_sha256(model_input):
    """Covers exactly {as_of, entities, facts, comparison_groups, completeness}; excludes the analysis identifiers and the hash itself."""
    return sha256_hex(canonical({k: model_input[k] for k in ("as_of", "entities", "facts", "comparison_groups", "completeness")}))


# ------------------------------------------------------------------ a small, closed JSON-Schema (2020-12 subset) validator that runs the PUBLISHED schemas
_ANNOTATIONS = {"$schema", "$id", "title", "description"}
_KEYWORDS = _ANNOTATIONS | {"type", "const", "enum", "pattern", "minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems", "uniqueItems", "items", "properties", "required", "additionalProperties", "anyOf", "oneOf", "allOf", "if", "then", "else", "format", "$ref"}
_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


def _is_datetime(s):
    if not isinstance(s, str) or not _RFC3339.match(s):
        return False
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _type_ok(t, v):
    if t == "object":
        return isinstance(v, dict)
    if t == "array":
        return isinstance(v, list)
    if t == "string":
        return isinstance(v, str)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "boolean":
        return isinstance(v, bool)
    if t == "null":
        return v is None
    raise ContractMismatch(f"unsupported schema type {t!r}")


def _eq(a, b):
    return type(a) is type(b) and a == b if not isinstance(a, (list, dict)) else json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def schema_errors(schema, value, root=None, path="$"):
    """-> list of (path, kind, message). kind is UNKNOWN_KEY for a property the closed schema does not allow, else SCHEMA_INVALID."""
    errs = []
    for k in schema:
        if k not in _KEYWORDS:
            raise ContractMismatch(f"unsupported schema keyword {k!r}")
    if "$ref" in schema:
        name = schema["$ref"]
        if name not in SCHEMAS:
            raise ContractMismatch(f"unresolvable $ref {name!r}")
        return schema_errors(SCHEMAS[name], value, SCHEMAS[name], path)
    for sub in schema.get("allOf", []):
        errs += schema_errors(sub, value, root, path)
    if "if" in schema:
        branch = "then" if not schema_errors(schema["if"], value, root, path) else "else"
        if branch in schema:
            errs += schema_errors(schema[branch], value, root, path)
    if "anyOf" in schema and not any(not schema_errors(s, value, root, path) for s in schema["anyOf"]):
        errs.append((path, "schema_invalid", "matches none of the allowed forms"))
    if "oneOf" in schema:
        n = sum(1 for s in schema["oneOf"] if not schema_errors(s, value, root, path))
        if n != 1:
            hit = [s for s in schema["oneOf"] if isinstance(value, dict) and s.get("properties", {}).get("kind", {}).get("const") == value.get("kind")]
            if n == 0 and hit:
                errs += schema_errors(hit[0], value, root, path)                 # report WHY the variant the claim declares was not matched (e.g. an unknown key)
            else:
                errs.append((path, "schema_invalid", f"matches {n} of the allowed forms, exactly one required"))
    if "type" in schema and not _type_ok(schema["type"], value):
        return errs + [(path, "schema_invalid", f"expected {schema['type']}")]
    if "const" in schema and not _eq(schema["const"], value):
        errs.append((path, "schema_invalid", "not the required constant"))
    if "enum" in schema and not any(_eq(e, value) for e in schema["enum"]):
        errs.append((path, "schema_invalid", "not an allowed value"))
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append((path, "schema_invalid", "does not match the required pattern"))
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append((path, "schema_invalid", "too short"))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append((path, "schema_invalid", "too long"))
        if schema.get("format") == "date-time" and not _is_datetime(value):
            errs.append((path, "schema_invalid", "not an RFC 3339 date-time"))
        elif schema.get("format") not in (None, "date-time"):
            raise ContractMismatch(f"unsupported format {schema['format']!r}")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append((path, "schema_invalid", "below the minimum"))
        if "maximum" in schema and value > schema["maximum"]:
            errs.append((path, "schema_invalid", "above the maximum"))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append((path, "schema_invalid", "too few items"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append((path, "schema_invalid", "too many items"))
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errs.append((path, "schema_invalid", "items are not unique"))
        if "items" in schema:
            for i, x in enumerate(value):
                errs += schema_errors(schema["items"], x, root, f"{path}[{i}]")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for r in schema.get("required", []):
            if r not in value:
                errs.append((path, "schema_invalid", f"missing required key {r!r}"))
        for k, v in value.items():
            if k in props:
                errs += schema_errors(props[k], v, root, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append((f"{path}.{k}", "unknown_key", "key not allowed by the closed schema"))
    return errs


# ------------------------------------------------------------------ record hash profiles (D2): the profile is a CONSTANT of the server, never read from the snapshot, the model output or the caller
LIVE_RECORD_HASH_PROFILE = "record-hash.v1"
HISTORICAL_RECORD_HASH_PROFILE = "record-hash.v0"
KNOWN_RECORD_HASH_PROFILES = (HISTORICAL_RECORD_HASH_PROFILE, LIVE_RECORD_HASH_PROFILE)
ADMISSIBLE_LIVE_RECORD_HASH_PROFILES = (LIVE_RECORD_HASH_PROFILE,)
V1_PREIMAGE_KEYS = ("profile", "tenant_scope_id", "source_kind", "source_ref", "record_id", "source_revision", "subject_id", "inventory_item_id", "field", "availability", "value", "unit", "as_of")


def record_preimage(profile, fact, tenant_scope_id):
    """The exact object whose canonical JSON is hashed. v0 (published example, historical): {subject_id, field, value, unit}. v1: the tenant-scoped, versioned form below (the profile string is part of the hashed bytes)."""
    if profile == HISTORICAL_RECORD_HASH_PROFILE:
        return {k: fact[k] for k in ("subject_id", "field", "value", "unit")}
    if profile == LIVE_RECORD_HASH_PROFILE:
        p = fact["provenance"]
        return dict(profile=LIVE_RECORD_HASH_PROFILE, tenant_scope_id=tenant_scope_id, source_kind=p["source_kind"], source_ref=p["source_ref"], record_id=p["record_id"], source_revision=p["source_revision"], subject_id=fact["subject_id"],
                    inventory_item_id=fact["inventory_item_id"], field=fact["field"], availability=fact["availability"], value=fact["value"], unit=fact["unit"], as_of=fact["as_of"])
    raise ContractMismatch(f"unknown record hash profile {profile!r}")


def record_sha256(profile, fact, tenant_scope_id):
    return sha256_hex(canonical(record_preimage(profile, fact, tenant_scope_id)))


# ------------------------------------------------------------------ diagnostics (D4, D5): one explicit table. class -> which side is at fault -> the result status.
DIAGNOSTICS = {
    # admission of the snapshot (nothing was sent to a provider)
    "input_refused": "admission", "input_invalid": "admission", "input_oversize": "admission", "input_poisoned": "admission", "duplicate_id": "admission", "noncanonical_order": "admission", "dangling_reference": "admission",
    # source provenance, checked at admission
    "source_hash_mismatch": "source", "source_provenance_missing": "source", "stale_snapshot": "source",
    # the candidate output as bytes / JSON
    "not_json": "parse", "not_json_text": "parse", "duplicate_key": "parse", "non_finite_number": "parse", "non_integer_number": "parse", "invalid_utf8": "parse", "oversize": "parse", "too_deep": "parse",
    # the candidate output against the published schema and the bindings
    "schema_invalid": "schema", "unknown_key": "schema", "binding_mismatch": "binding", "cross_tenant_reference": "binding",
    # the claims
    "unknown_evidence": "claim", "wrong_entity": "claim", "wrong_item": "claim", "wrong_fact": "claim", "field_mismatch": "claim", "unit_mismatch": "claim", "value_mismatch": "claim", "incorrect_difference": "claim", "unsupported_claim": "claim",
    "claim_set_mismatch": "claim", "deferred_claim_kind": "claim", "deferred_field": "claim", "deferred_limitation": "claim",
    # abstention and completeness
    "invented_completion": "abstention", "wrong_abstention_reason": "abstention",
    # infrastructure and configuration: the model output is not what failed
    "provider_timeout": "provider", "provider_error": "provider", "provider_truncated": "provider", "provider_provenance_missing": "provider", "mode_mismatch": "config", "mode_unsupported": "config", "record_hash_profile_unsupported": "config",
}
FAILED_CLASSES = ("provider", "config")
FLAGS = ("unnecessary_abstention",)                  # not errors: reported beside a verified abstention
LEGACY_UPPER = {c.upper(): c for c in DIAGNOSTICS} | {"MISSING_PROVENANCE": "source_provenance_missing", "PROVENANCE_MISSING": "provider_provenance_missing"}      # M-OPS-1 (commit 06fc273) spellings, for reading old records only


def status_for(codes):
    """FAILED when any code is an infrastructure or configuration fault; otherwise REJECTED. A code outside the table is a bug and raises."""
    for c in codes:
        if c not in DIAGNOSTICS:
            raise ContractMismatch(f"diagnostic code {c!r} is not in the table")
    return "FAILED" if any(DIAGNOSTICS[c] in FAILED_CLASSES for c in codes) else "REJECTED"


# ------------------------------------------------------------------ the milestone profile
OBSERVED_FIELDS = ("expected_units", "counted_units")
RULES = frozenset({"strict_parse", "schema", "duplicate_ids", "bindings", "foreign_refs", "snapshot_hash", "provenance", "entity", "field", "unit", "value", "availability", "arithmetic", "difference_facts",
                   "limitation", "claim_set", "deferred", "completeness", "abstention", "input_schema", "input_screen", "record_hash"})


def _by_id(items):
    return {x["id"]: x for x in items}


def _sorted_ok(items):
    ids = [x["id"] for x in items]
    return ids == sorted(ids)


def check_input(model_input, rules=RULES, now=None, max_age_seconds=None, trusted_record_hashes=None):
    """Everything about the server-built model input that must hold BEFORE a provider may see it. -> sorted list of codes ([] = admissible). Pure.
    Record hashes are verified under the LIVE profile (record-hash.v1) only. `trusted_record_hashes` maps "record_id|source_ref" to the hash the HOST read from the authoritative source; with `now` and `max_age_seconds` the snapshot age is bounded."""
    return _check_input(model_input, rules, now, max_age_seconds, trusted_record_hashes, LIVE_RECORD_HASH_PROFILE)


def _check_input(model_input, rules, now, max_age_seconds, trusted_record_hashes, profile):
    codes = set()
    try:
        size = len(canonical(model_input))
    except StrictJSONError as e:
        return [e.code]
    if size > MAX_INPUT_BYTES:
        codes.add("input_oversize")
    if "input_schema" in rules:
        errs = schema_errors(SCHEMAS["model-input.schema.json"], model_input)
        if errs:
            codes.add("input_invalid")
            return sorted(codes)
    ents, facts = model_input["entities"], model_input["facts"]
    if "input_schema" in rules:
        if len({e["id"] for e in ents}) != len(ents) or len({f["id"] for f in facts}) != len(facts):
            codes.add("duplicate_id")
        for coll in ("entities", "facts", "comparison_groups", "completeness"):
            if not _sorted_ok(model_input[coll]):
                codes.add("noncanonical_order")
        ent_ids = {e["id"] for e in ents}
        for f in facts:
            if f["subject_id"] not in ent_ids or f["inventory_item_id"] not in ent_ids:
                codes.add("dangling_reference")
            if f["availability"] == "PRESENT" and not (isinstance(f["value"], int) and f["value"] >= 0):
                codes.add("input_invalid")
            if f["availability"] != "PRESENT" and f["value"] is not None:
                codes.add("input_invalid")
        fact_ids = {f["id"] for f in facts}
        for g in model_input["comparison_groups"]:
            if not set(g["fact_ids"]) <= fact_ids:
                codes.add("dangling_reference")
    if "snapshot_hash" in rules and model_input["snapshot_sha256"] != snapshot_sha256(model_input):
        codes.add("source_hash_mismatch")
    if "record_hash" in rules and any(f["provenance"]["record_sha256"] != record_sha256(profile, f, model_input["tenant_scope_id"]) for f in facts):
        codes.add("source_hash_mismatch")                                    # a fact altered after its record hash was taken, a hash from another tenant, or a profile other than the pinned one (mixed profiles end here too)
    if "provenance" in rules:
        if max_age_seconds is not None and now is not None:
            age = (datetime.fromisoformat(now.replace("Z", "+00:00")) - datetime.fromisoformat(model_input["as_of"].replace("Z", "+00:00"))).total_seconds()
            if age > max_age_seconds or age < 0:
                codes.add("stale_snapshot")
        if trusted_record_hashes is not None:
            for f in facts:
                want = trusted_record_hashes.get(f["provenance"]["record_id"] + "|" + f["provenance"]["source_ref"])
                if want is None:
                    codes.add("source_provenance_missing")
                elif want != f["provenance"]["record_sha256"]:
                    codes.add("source_hash_mismatch")
    # untrusted text in the snapshot: a name that addresses the assistant is refused before any provider sees it (reuses the repository's directive screen)
    if "input_screen" in rules:
        strings = [e["alias"] for e in ents] + [f["provenance"]["source_ref"] for f in facts]
        if any(MB.directive_flags(x) or MB.INSTRUCTION_WORDS.search(x) for x in strings):
            codes.add("input_poisoned")
    return sorted(codes)


def required_reasons(model_input):
    """The abstention reasons the SNAPSHOT itself requires (deterministic). {} means a complete explanation is possible. Also returns the expected/counted facts when usable."""
    items = [e for e in model_input["entities"] if e["kind"] == "INVENTORY_ITEM"]
    if len(items) != 1:
        return {"INSUFFICIENT_SCOPE"}, None, None, None
    item = items[0]["id"]
    ex = [f for f in model_input["facts"] if f["subject_id"] == item and f["field"] == "expected_units"]
    co = [f for f in model_input["facts"] if f["subject_id"] == item and f["field"] == "counted_units"]
    if len(ex) > 1 or len(co) > 1:
        return {"INSUFFICIENT_SCOPE"}, item, None, None
    reasons = set()
    both = ex + co
    if not ex or not co or any(f["availability"] == "MISSING" for f in both):
        reasons.add("MISSING_REQUIRED_EVIDENCE")
    if any(f["availability"] == "CONFLICTING" for f in both):
        reasons.add("CONFLICTING_EVIDENCE")
    if both and any(f["unit"] != "UNITS" or f["inventory_item_id"] != item for f in both):
        reasons.add("INCOMPATIBLE_UNITS")
    return reasons, item, (ex[0] if ex else None), (co[0] if co else None)


def _claim_codes(c, facts, item, ex, co, foreign_ids, rules, seen_fields):
    """Codes for one claim, recomputed from the snapshot. Pure."""
    codes, kind = [], c["kind"]

    def fact(fid):
        if fid in facts:
            return facts[fid]
        codes.append("cross_tenant_reference" if fid in foreign_ids and "foreign_refs" in rules else "unknown_evidence")
        return None

    if kind in ("COMPARISON", "EXTREMUM", "SCOPED_ABSENCE"):
        return ["deferred_claim_kind"] if "deferred" in rules else []
    if kind == "OBSERVE":
        if c["field"] not in OBSERVED_FIELDS:
            codes.append("deferred_field") if "deferred" in rules else None
        f = fact(c["fact_id"])
        if f is not None:
            if "entity" in rules:
                if c["subject_id"] != f["subject_id"]:
                    codes.append("wrong_entity")
                if f["inventory_item_id"] != c["subject_id"] or c["subject_id"] != item:
                    codes.append("wrong_item")
            if "field" in rules and f["field"] != c["field"]:
                codes.append("field_mismatch")
            if "unit" in rules and c["unit"] != f["unit"]:
                codes.append("unit_mismatch")
            if "availability" in rules and f["availability"] != "PRESENT":
                codes.append("unsupported_claim")
            elif "value" in rules and c["claimed_value"] != f["value"]:
                codes.append("value_mismatch")
            if "claim_set" in rules and c["field"] in OBSERVED_FIELDS:
                want = ex if c["field"] == "expected_units" else co
                if want is None or c["fact_id"] != want["id"]:
                    codes.append("wrong_fact")
        seen_fields.append(c["field"])
    elif kind == "DIFFERENCE":
        e, o = fact(c["expected_fact_id"]), fact(c["counted_fact_id"])
        if e is not None and o is not None:
            if "difference_facts" in rules:
                if e["field"] != "expected_units" or o["field"] != "counted_units":
                    codes.append("field_mismatch")
                if not (c["subject_id"] == e["subject_id"] == o["subject_id"] == item) or e["inventory_item_id"] != o["inventory_item_id"]:
                    codes.append("wrong_item")
                if e["unit"] != "UNITS" or o["unit"] != "UNITS":
                    codes.append("unit_mismatch")
            if "availability" in rules and (e["availability"] != "PRESENT" or o["availability"] != "PRESENT"):
                codes.append("unsupported_claim")
            elif "arithmetic" in rules and c["claimed_difference"] != e["value"] - o["value"]:
                codes.append("incorrect_difference")
    elif kind == "LIMITATION":
        if "limitation" in rules:
            if c["code"] != "CAUSE_NOT_ESTABLISHED":
                codes.append("deferred_limitation") if "deferred" in rules else None
            for fid in c["fact_ids"]:
                if fid not in facts:
                    codes.append("cross_tenant_reference" if fid in foreign_ids and "foreign_refs" in rules else "unknown_evidence")
            if not codes and (ex is None or co is None or set(c["fact_ids"]) != {ex["id"], co["id"]}):
                codes.append("unsupported_claim")
    return codes


def validate_output(raw, model_input, rules=RULES, foreign_scopes=(), foreign_ids=(), trusted_record_hashes=None, now=None, max_age_seconds=None):
    """Judge an untrusted candidate output against the authorized snapshot. Pure; never raises on bad input (returns REJECTED with codes).
    -> dict(status ANSWER_VERIFIED | ABSTAIN_VERIFIED | REJECTED, codes[sorted], flags[], claims[per-claim], required_reasons[], output|None). Record hashes are verified under record-hash.v1 only."""
    return _validate(raw, model_input, rules, foreign_scopes, foreign_ids, trusted_record_hashes, now, max_age_seconds, LIVE_RECORD_HASH_PROFILE)


def validate_historical_vector(raw, model_input, rules=RULES):
    """GOLDEN-VECTOR VERIFICATION ONLY: the same judgement with the legacy record-hash.v0 of Codex's published example. It is not reachable from `explain` and its result is marked historical; a v0 snapshot is never accepted for a live explanation."""
    v = _validate(raw, model_input, rules, (), (), None, None, None, HISTORICAL_RECORD_HASH_PROFILE)
    v["historical_vector"] = True
    return v


def _validate(raw, model_input, rules, foreign_scopes, foreign_ids, trusted_record_hashes, now, max_age_seconds, profile):
    out = dict(status="REJECTED", codes=[], flags=[], claims=[], required_reasons=[], output=None)
    codes = set()
    foreign_scopes, foreign_ids = set(foreign_scopes), set(foreign_ids)
    in_codes = _check_input(model_input, rules, now, max_age_seconds, trusted_record_hashes, profile)
    if in_codes:
        out["codes"] = sorted({"input_refused"} | set(in_codes)); return out
    if not isinstance(raw, (str, bytes, bytearray, dict, list)):
        out["codes"] = ["not_json_text"]; return out                          # neither text nor an already-parsed JSON value
    # 1. strict parse, schema, bindings
    try:
        data = parse_strict(raw) if isinstance(raw, (str, bytes, bytearray)) and "strict_parse" in rules else (raw if not isinstance(raw, (str, bytes, bytearray)) else json.loads(raw))
    except StrictJSONError as e:
        out["codes"] = [e.code]; return out
    except Exception:                                                          # noqa: BLE001 - a mutant with strict parsing off may be handed malformed text; it must still produce a verdict
        out["codes"] = ["not_json"]; return out
    if "schema" in rules:
        errs = schema_errors(SCHEMAS["model-output.schema.json"], data)
        if errs:
            out["codes"] = sorted({k for _, k, _ in errs}); out["errors"] = [dict(path=p, kind=k, message=m) for p, k, m in errs[:12]]; return out
    if not isinstance(data, dict) or not isinstance(data.get("claims", []), list):
        out["codes"] = ["schema_invalid"]; return out
    out["output"] = data
    if "bindings" in rules:
        for k in ("analysis_id", "tenant_scope_id", "workflow_id", "snapshot_id", "snapshot_sha256"):
            if data.get(k) != model_input.get(k):
                codes.add("binding_mismatch")
        if data.get("schema_version") != OUTPUT_VERSION:
            codes.add("binding_mismatch")
    if "foreign_refs" in rules and (data.get("tenant_scope_id") in foreign_scopes or data.get("snapshot_sha256") in foreign_scopes):
        codes.add("cross_tenant_reference")
    claims = data.get("claims", [])
    if "duplicate_ids" in rules and len({c.get("claim_id") for c in claims if isinstance(c, dict)}) != len(claims):
        codes.add("duplicate_id")
    # 3-8. claims, completeness, abstention
    reasons, item, ex, co = required_reasons(model_input)
    out["required_reasons"] = sorted(reasons)
    facts = _by_id(model_input["facts"])
    status = data.get("status")
    if status == "ABSTAIN":
        given = set(data.get("reason_codes", []))
        if "abstention" in rules:
            if reasons and given != reasons:
                codes.add("wrong_abstention_reason")
            if not reasons:
                out["flags"].append("unnecessary_abstention")                 # safe, but not a useful answer; counted against usefulness, never as an error
        out["status"] = "ABSTAIN_VERIFIED" if not codes else "REJECTED"
        out["codes"] = sorted(codes); return out
    if "completeness" in rules and reasons:
        codes.add("invented_completion")                                      # an ANSWER where the snapshot cannot support one
    per, seen_fields, kinds = [], [], []
    for c in claims:
        kinds.append(c["kind"])
        cc = _claim_codes(c, facts, item, ex, co, foreign_ids, rules, seen_fields)
        per.append(dict(claim_id=c["claim_id"], kind=c["kind"], ok=not cc, codes=sorted(set(cc)))); codes.update(cc)
    if "claim_set" in rules:
        want = ["DIFFERENCE", "LIMITATION", "OBSERVE", "OBSERVE"]
        if sorted(kinds) != want and not {"COMPARISON", "EXTREMUM", "SCOPED_ABSENCE"} & set(kinds):
            codes.add("claim_set_mismatch")
        if sorted(f for f in seen_fields) != sorted(OBSERVED_FIELDS) and "OBSERVE" in kinds:
            codes.add("claim_set_mismatch")
    out["claims"] = per
    out["codes"] = sorted(codes)
    out["status"] = "ANSWER_VERIFIED" if not codes else "REJECTED"
    return out


# ------------------------------------------------------------------ deterministic renderer (server-owned templates; reads ONLY the validated snapshot)
ABSTAIN_TEXT = {
    "MISSING_REQUIRED_EVIDENCE": "A required count is missing from this synthetic snapshot.",
    "CONFLICTING_EVIDENCE": "The recorded counts conflict in this synthetic snapshot.",
    "INCOMPATIBLE_UNITS": "The recorded counts are not in compatible units or for the same item.",
    "INSUFFICIENT_SCOPE": "This synthetic snapshot does not cover the scope needed for an explanation.",
    "UNSUPPORTED_TASK": "This request is not a supported explanation task.",
}
ABSTAIN_ORDER = list(ABSTAIN_TEXT)
UNNECESSARY_TEXT = "The AI declined to explain this snapshot, although the counts are complete. The deterministic Operations output is unaffected."
REJECTED_TEXT = "The AI-generated explanation did not pass verification and is not shown. The deterministic Operations output is unaffected."
FAILED_TEXT = "The AI explanation could not be produced. The deterministic Operations output is unaffected."


def _units(n):
    return f"{n} unit" if abs(n) == 1 else f"{n} units"


# ---- renderer v2 (D-R2): the displayed item label comes ONLY from this server-owned table, keyed by (authorized tenant scope, inventory item id). The snapshot's alias is never read for wording.
GENERIC_ITEM_LABEL = "the inventory item"
TRUSTED_DISPLAY_LABELS = {      # PLACEHOLDER tenant scope ids (the golden vectors' and the M-OPS-2 case set's); the host replaces this table with its own authoritative mapping
    ("00000000-0000-4000-8000-0000000000a1", "item:packaging"): "Synthetic packaging",
    ("00000000-0000-4000-8000-0000000000b2", "item:packaging"): "Synthetic towels",
}


class RendererAuthorizationError(RuntimeError):
    """The scope the host authorized for this request is not the snapshot's tenant scope. It is never turned into a generic label: explain() reports REJECTED input_refused + cross_tenant_reference."""


def display_label(model_input, item_id, authorized_tenant_scope=None, labels=None):
    """-> the trusted label for (authorized scope, item id), or exactly GENERIC_ITEM_LABEL when the server table has none. Never the alias, the item id, source text or any sanitized copy of them."""
    scope = model_input["tenant_scope_id"]
    if authorized_tenant_scope is not None and authorized_tenant_scope != scope:
        raise RendererAuthorizationError("the authorized tenant scope does not match the snapshot")
    return (TRUSTED_DISPLAY_LABELS if labels is None else labels).get((scope, item_id), GENERIC_ITEM_LABEL)


def _answer_text(label, e, c):
    d = e - c
    if d > 0:
        rel = f"The counted quantity is {_units(d)} below expected."
    elif d < 0:
        rel = f"The counted quantity is {_units(-d)} above expected."
    else:
        rel = "The counted quantity equals the expected quantity."
    text = f"In this synthetic snapshot, the expected quantity of {html.escape(label)} is {_units(e)} and the counted quantity is {_units(c)}. {rel} These scenario assumptions do not establish a physical root cause."
    assert len(text) <= MAX_RENDERED_CHARS
    return text


def render_answer(model_input, authorized_tenant_scope=None, labels=None):
    """The explanation for a VERIFIED answer (renderer v2), computed from the snapshot's numbers and the server's label table (never from the candidate's claimed values, never from the alias)."""
    _, item, ex, co = required_reasons(model_input)
    return _answer_text(display_label(model_input, item, authorized_tenant_scope, labels), ex["value"], co["value"])


def _render_answer_historical_v1(model_input):
    """Renderer v1.0 (prints the escaped alias). KEPT ONLY to reproduce golden vectors v1 and case set v1 byte for byte; explain() cannot reach it and nothing falls back to it."""
    _, item, ex, co = required_reasons(model_input)
    return _answer_text(_by_id(model_input["entities"])[item]["alias"], ex["value"], co["value"])


def render_abstention(verdict):
    if "unnecessary_abstention" in verdict["flags"]:
        return UNNECESSARY_TEXT
    return " ".join(ABSTAIN_TEXT[r] for r in ABSTAIN_ORDER if r in verdict["required_reasons"]) + " No explanation is given."


# ------------------------------------------------------------------ result envelope (ops-explanation-result.v1) and the pipeline
def provider_ok(p):
    return (isinstance(p, dict) and p.get("name") == "ollama" and p.get("model") == APPROVED_MODEL and p.get("digest") == APPROVED_DIGEST and isinstance(p.get("actual_model_calls"), int) and p["actual_model_calls"] >= 1
            and p.get("estimated_usage") is False and isinstance(p.get("runtime_profile_sha256"), str) and not schema_errors(SCHEMAS["result-envelope.schema.json"]["properties"]["provider"], p))


def accepted_result_sha256(model_input, output, rendered, renderer_revision=None):
    return sha256_hex(canonical(dict(schema_version=OUTPUT_VERSION, analysis_id=model_input["analysis_id"], snapshot_sha256=model_input["snapshot_sha256"], claims=output["claims"], rendered_explanation=rendered,
                                     validator_revision=VALIDATOR_REVISION, renderer_revision=renderer_revision or RENDERER_REVISION)))


def make_envelope(model_input, status, mode, codes=(), output=None, rendered="", provider=None, audit_complete=False, accepted_hash=None):
    for c in codes:
        if c not in DIAGNOSTICS:
            raise ContractMismatch(f"diagnostic code {c!r} is not in the table")
    if codes and status in ("REJECTED", "FAILED") and status != status_for(codes):
        raise ContractMismatch(f"status {status} contradicts the diagnostics {sorted(codes)}")
    env = dict(schema_version=RESULT_VERSION, analysis_id=model_input["analysis_id"], workflow_id=model_input["workflow_id"], tenant_scope_id=model_input["tenant_scope_id"], status=status, mode=mode, model_output=output,
               rendered_explanation=rendered, validation_codes=sorted({c.lower() for c in codes}), provider=provider, audit_complete=audit_complete, accepted_result_sha256=accepted_hash, cached_from_analysis_id=None)
    errs = schema_errors(SCHEMAS["result-envelope.schema.json"], env)
    if errs:
        raise ContractMismatch(f"server-built result violates the published result schema: {errs[:3]}")
    return env


def result_invariants(env):
    """The cross-field rules the specification adds to the result schema (section 5.4). -> list of violations ([] = holds)."""
    bad, s, m = [], env["status"], env["mode"]
    if s == "ACCEPTED" and not (env["model_output"] and env["model_output"]["status"] == "ANSWER" and not env["validation_codes"] and env["audit_complete"] and env["rendered_explanation"] and env["accepted_result_sha256"]):
        bad.append("ACCEPTED requires a valid ANSWER, no validation codes, complete audit, rendered text and a result hash")
    if s == "ABSTAINED" and not (env["model_output"] and env["model_output"]["status"] == "ABSTAIN" and env["audit_complete"]):
        bad.append("ABSTAINED requires a valid ABSTAIN and complete audit")
    if s == "REJECTED" and (env["model_output"] is not None or env["accepted_result_sha256"] is not None):
        bad.append("REJECTED carries no public model output and no accepted hash")
    if s in ("REJECTED", "FAILED", "CANCELLED", "INTERRUPTED") and env["accepted_result_sha256"] is not None:
        bad.append("a non-accepted result has no accepted hash")
    if m == "LIVE_LLM" and s in ("ACCEPTED", "ABSTAINED", "AUDIT_PENDING") and not provider_ok(env["provider"]):
        bad.append("LIVE_LLM requires approved model identity and actual, non-estimated model use (PROVENANCE_MISSING)")
    if m == "DETERMINISTIC_REPLAY" and env["provider"] is not None:
        bad.append("DETERMINISTIC_REPLAY requires provider null")
    if m == "CACHED_REPLAY" and s in ("ACCEPTED", "ABSTAINED", "AUDIT_PENDING") and env["cached_from_analysis_id"] is None:
        bad.append("CACHED_REPLAY requires the originating analysis")
    return bad


class ProviderTruncated(Exception):
    """Raised by a host adapter when the provider stopped at its token limit: the output is incomplete because of configuration or capacity, not because the model made an invalid claim. -> FAILED provider_truncated."""


def explain(model_input, candidate, mode="DETERMINISTIC_REPLAY", audit_complete=False, foreign_scopes=(), foreign_ids=(), rules=RULES, trusted_record_hashes=None, now=None, max_age_seconds=None, record_hash_profile=LIVE_RECORD_HASH_PROFILE, authorized_tenant_scope=None, display_labels=None):
    """Renderer v2 pipeline (the only one reachable by callers). `authorized_tenant_scope` is the scope the HOST authorized for this request: when given and different from the snapshot's, the result is REJECTED input_refused + cross_tenant_reference before any provider call (never a generic-label fallback). `display_labels` is the HOST's (scope, item id) -> label table; it defaults to TRUSTED_DISPLAY_LABELS and can never come from the snapshot, the model or a request field."""
    return _explain(model_input, candidate, mode, audit_complete, foreign_scopes, foreign_ids, rules, trusted_record_hashes, now, max_age_seconds, record_hash_profile, authorized_tenant_scope, display_labels, False)


def explain_historical_v1(model_input, candidate, mode="DETERMINISTIC_REPLAY", audit_complete=False, foreign_scopes=(), foreign_ids=(), rules=RULES, trusted_record_hashes=None, now=None, max_age_seconds=None, record_hash_profile=LIVE_RECORD_HASH_PROFILE):
    """Reproduces renderer v1.0 results ONLY to regenerate/verify golden vectors v1 and case set v1 (historical evidence). Not used by any pipeline; a test fails if production code references it."""
    return _explain(model_input, candidate, mode, audit_complete, foreign_scopes, foreign_ids, rules, trusted_record_hashes, now, max_age_seconds, record_hash_profile, None, None, True)


def _explain(model_input, candidate, mode, audit_complete, foreign_scopes, foreign_ids, rules, trusted_record_hashes, now, max_age_seconds, record_hash_profile, authorized_tenant_scope, display_labels, historical_v1):
    """Run one explanation. `record_hash_profile` is the HOST's pin; anything other than record-hash.v1 (v0, unknown) is FAILED record_hash_profile_unsupported before the snapshot is even read. `candidate(model_input)` returns raw output text/bytes/dict, or (raw, provider_metadata), or (raw, provider_metadata, finish_reason); it is NOT called when the input is refused.
    Admission (before any provider call) checks the snapshot, the record hashes under the pinned record-hash.v1, the host's trusted record hashes (REQUIRED for LIVE_LLM) and, when `now` and `max_age_seconds` are given, staleness.
    A finish_reason other than "stop" (or a raised ProviderTruncated) is FAILED, never an ordinary rejection. A failure is a failure: nothing is substituted. The labelled deterministic alternative is `deterministic_replay`. -> dict(envelope, verdict, record)."""
    record = dict(validator_revision=VALIDATOR_REVISION, renderer_revision=HISTORICAL_RENDERER_REVISION_V1 if historical_v1 else RENDERER_REVISION, profile=PROFILE, snapshot_sha256=model_input.get("snapshot_sha256"), refused_before_provider=False, raw_output=None, raw_chars=None, raw_sha256=None)
    if record_hash_profile != LIVE_RECORD_HASH_PROFILE:
        return _failed(model_input if isinstance(model_input, dict) else {}, mode, "record_hash_profile_unsupported", record)
    if authorized_tenant_scope is not None and (not isinstance(model_input, dict) or model_input.get("tenant_scope_id") != authorized_tenant_scope):
        record["refused_before_provider"] = True
        codes = ["input_refused", "cross_tenant_reference"]
        return dict(envelope=_safe_envelope(model_input, "REJECTED", mode, codes, rendered=REJECTED_TEXT), verdict=dict(status="REJECTED", codes=sorted(codes), flags=[], claims=[], required_reasons=[], output=None), record=record)
    in_codes = check_input(model_input, rules, now, max_age_seconds, trusted_record_hashes)
    if mode == "LIVE_LLM" and trusted_record_hashes is None:
        in_codes = sorted(set(in_codes) | {"source_provenance_missing"})       # a live explanation needs the host's own record hashes; the snapshot's self-consistency is not enough
    if in_codes:
        record["refused_before_provider"] = True
        env = _safe_envelope(model_input, "REJECTED", mode, ["input_refused"] + in_codes, rendered=REJECTED_TEXT)
        return dict(envelope=env, verdict=dict(status="REJECTED", codes=sorted(["input_refused"] + in_codes), flags=[], claims=[], required_reasons=[], output=None), record=record)
    try:
        got = candidate(model_input)
    except TimeoutError:
        return _failed(model_input, mode, "provider_timeout", record)
    except ProviderTruncated:
        return _failed(model_input, mode, "provider_truncated", record)
    except Exception:                                                          # noqa: BLE001 - any provider failure is a FAILED result; it never becomes an answer
        return _failed(model_input, mode, "provider_error", record)
    finish = None
    if isinstance(got, tuple) and len(got) == 3:
        got, finish = (got[0], got[1]), got[2]
    raw, meta = (got if isinstance(got, tuple) and len(got) == 2 else (got, None))
    if finish not in (None, "stop"):
        return _failed(model_input, mode, "provider_truncated" if finish == "length" else "provider_error", dict(record, finish_reason=finish))
    if isinstance(raw, (str, bytes, bytearray)):
        b = raw.encode("utf-8", errors="replace") if isinstance(raw, str) else bytes(raw)
        record.update(raw_output=b[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), raw_chars=len(b), raw_sha256=sha256_hex(b))
    elif isinstance(raw, (dict, list)):
        try:
            b = canonical(raw); record.update(raw_output=b[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), raw_chars=len(b), raw_sha256=sha256_hex(b))
        except StrictJSONError:
            pass
    if mode == "LIVE_LLM" and not provider_ok(meta):
        return _failed(model_input, mode, "provider_provenance_missing", record)
    if mode == "DETERMINISTIC_REPLAY" and meta is not None:
        return _failed(model_input, mode, "mode_mismatch", record)
    if mode not in ("LIVE_LLM", "DETERMINISTIC_REPLAY"):
        return _failed(model_input, mode if mode in ("CACHED_REPLAY",) else "DETERMINISTIC_REPLAY", "mode_unsupported", record)
    v = validate_output(raw, model_input, rules, foreign_scopes, foreign_ids, trusted_record_hashes, now, max_age_seconds)
    record.update(codes=v["codes"], claim_verdicts=v["claims"], flags=v["flags"], required_reasons=v["required_reasons"])
    if v["status"] == "REJECTED":
        env = make_envelope(model_input, status_for(v["codes"]), mode, v["codes"], rendered=REJECTED_TEXT)
    elif v["status"] == "ABSTAIN_VERIFIED":
        env = make_envelope(model_input, "ABSTAINED" if audit_complete else "AUDIT_PENDING", mode, (), v["output"], render_abstention(v), meta, audit_complete)
    else:
        text = _render_answer_historical_v1(model_input) if historical_v1 else render_answer(model_input, authorized_tenant_scope, display_labels)
        env = make_envelope(model_input, "ACCEPTED" if audit_complete else "AUDIT_PENDING", mode, (), v["output"], text, meta, audit_complete, accepted_result_sha256(model_input, v["output"], text, HISTORICAL_RENDERER_REVISION_V1 if historical_v1 else None))
    return dict(envelope=env, verdict=v, record=record)


def _safe_envelope(model_input, status, mode, codes, rendered):
    """Envelope for a refused input, whose identifiers may themselves be invalid: only well-formed identifiers are echoed."""
    base = {k: model_input.get(k) for k in ("analysis_id", "workflow_id", "tenant_scope_id")} if isinstance(model_input, dict) else {}
    ok = {k: (v if isinstance(v, str) and not schema_errors(SCHEMAS["model-input.schema.json"]["properties"][k], v) else None) for k, v in base.items()}
    stub = dict(analysis_id=ok.get("analysis_id") or "00000000-0000-4000-8000-000000000000", workflow_id=ok.get("workflow_id") or "run-0000000000", tenant_scope_id=ok.get("tenant_scope_id") or "00000000-0000-4000-8000-000000000000")
    return make_envelope(stub, status, mode, codes, rendered=rendered)


def _failed(model_input, mode, code, record):
    m = mode if mode in ("LIVE_LLM", "DETERMINISTIC_REPLAY", "CACHED_REPLAY") else "DETERMINISTIC_REPLAY"
    env = _safe_envelope(model_input, "FAILED", m, [code], rendered=FAILED_TEXT)
    return dict(envelope=env, verdict=dict(status="FAILED", codes=[code], flags=[], claims=[], required_reasons=[], output=None), record=dict(record, codes=[code]))


# ------------------------------------------------------------------ deterministic reference (the oracle for tests and the explicitly-labelled replay)
def reference_output(model_input):
    """The correct output for a snapshot, computed by the server: what a perfect model would return. Used as the test oracle and for the labelled DETERMINISTIC_REPLAY."""
    base = {k: model_input[k] for k in ("analysis_id", "tenant_scope_id", "workflow_id", "snapshot_id", "snapshot_sha256")}
    reasons, item, ex, co = required_reasons(model_input)
    if reasons:
        return dict(schema_version=OUTPUT_VERSION, **base, status="ABSTAIN", claims=[], reason_codes=[r for r in ABSTAIN_ORDER if r in reasons])
    return dict(schema_version=OUTPUT_VERSION, **base, status="ANSWER", reason_codes=[], claims=[
        dict(claim_id="c1", kind="OBSERVE", subject_id=item, fact_id=ex["id"], field="expected_units", claimed_value=ex["value"], unit="UNITS"),
        dict(claim_id="c2", kind="OBSERVE", subject_id=item, fact_id=co["id"], field="counted_units", claimed_value=co["value"], unit="UNITS"),
        dict(claim_id="c3", kind="DIFFERENCE", subject_id=item, operation="EXPECTED_MINUS_COUNTED", expected_fact_id=ex["id"], counted_fact_id=co["id"], claimed_difference=ex["value"] - co["value"], unit="UNITS"),
        dict(claim_id="c4", kind="LIMITATION", code="CAUSE_NOT_ESTABLISHED", fact_ids=sorted([ex["id"], co["id"]]))])


def deterministic_replay(model_input, audit_complete=False, authorized_tenant_scope=None, display_labels=None):
    """The explicitly labelled, scripted path (mode DETERMINISTIC_REPLAY, provider null). It is NOT a model result and is never counted as one."""
    return explain(model_input, lambda mi: reference_output(mi), "DETERMINISTIC_REPLAY", audit_complete, authorized_tenant_scope=authorized_tenant_scope, display_labels=display_labels)


# ------------------------------------------------------------------ snapshot builder for the published Phase 4 scenarios (test and replay support; the facts are hypothetical scenario assumptions)
SCENARIOS = {   # copied from Codex's Phase 4 showcase/workforce.py SCENARIOS (read-only); only the fields this milestone uses
    "count-gap": dict(expected=100, counted=40, target=120),
    "budget-risk": dict(expected=100, counted=20, target=120),
    "no-gap": dict(expected=100, counted=100, target=120),
    "missing-count": dict(expected=100, counted=None, target=120),
}


def build_model_input(scenario, tenant_scope_id, analysis_id, workflow_id, item_alias="Synthetic packaging", item_id="item:packaging", snapshot_id="snapshot:scenario-v1", as_of="2026-10-25T00:00:00Z"):
    sc = SCENARIOS[scenario]
    facts = []
    for field in ("counted_units", "expected_units", "target_units"):
        val = sc[field.replace("_units", "")]
        fact = dict(id=f"fact:{field}", subject_id=item_id, field=field, availability="PRESENT" if val is not None else "MISSING", value=val, unit="UNITS", as_of=as_of,
                    provenance=dict(source_kind="SCENARIO_ASSUMPTION", source_ref=f"scenario://{scenario}/v1/{field}", record_id=f"scenario:{scenario}", record_sha256="0" * 64, source_revision=f"{scenario}:v1"), inventory_item_id=item_id)
        fact["provenance"]["record_sha256"] = record_sha256(LIVE_RECORD_HASH_PROFILE, fact, tenant_scope_id)
        facts.append(fact)
    mi = dict(schema_version=INPUT_VERSION, analysis_id=analysis_id, tenant_scope_id=tenant_scope_id, workflow_id=workflow_id, snapshot_id=snapshot_id, snapshot_sha256="0" * 64, task="EXPLAIN_SYNTHETIC_INVENTORY_DISCREPANCY", as_of=as_of,
              entities=[dict(id=item_id, kind="INVENTORY_ITEM", alias=item_alias)], facts=sorted(facts, key=lambda f: f["id"]), comparison_groups=[], completeness=[],
              prohibited_effects=["PURCHASE", "INVENTORY_MUTATION", "SUPPLIER_CONTACT", "APPROVAL", "FINANCIAL_MUTATION", "ARBITRARY_TOOL"])
    mi["snapshot_sha256"] = snapshot_sha256(mi)
    return mi
