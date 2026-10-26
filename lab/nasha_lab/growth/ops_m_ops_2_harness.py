"""M-OPS-2 controlled evaluation harness (frozen design v1.0, commit ae6e0ec): provider adapters, resource/integrity preflight, case runner and evidence writer.

NOTHING HERE RUNS A MODEL BY ITSELF. The runner takes a provider object: `OllamaProvider` (loopback HTTP, only reached by the manual workflow) or `ScriptedProvider` (offline shim, no network). Scoring is a different program (`tools/ops_m_ops_2_score.py`, standard library only, imports nothing from this repository).
The harness has no handle to any workflow, database, approval or procurement object, sends no tools, and never lets a model output reach anything but the pure validator and the shared renderer."""
import hashlib
import json
import os
import shutil
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from . import ops_explanation as O

LAB = Path(__file__).resolve().parents[2]
CASESET = LAB / "contracts" / "ops_explanation_m_ops_2" / "v1" / "caseset.json"
CASESET_SHA_FILE = CASESET.with_name("CASESET.sha256")
VECTORS = LAB / "contracts" / "ops_explanation_vectors" / "v1"
PROMPT = O.CONTRACT_DIR / "prompt-candidate.json"
PROFILE_FILE = O.CONTRACT_DIR / "execution-profile-candidate.json"
UPSTREAM = O.CONTRACT_DIR / "UPSTREAM.sha256"

FROZEN_CASESET_SHA256 = "df0bb15ae47425018a347b0bcee7bceab5df7b8c4848fc2054976caea05c58e6"
FROZEN_PROMPT_SHA256 = "16f30b537c473fe8a3ed47a53d1c45f2b77aaae72106620599937d851ad4e77d"
FROZEN_VECTOR_IDENTITY = "14f526e71a5e76eb7f7287e7e313934d9cf32c0c0af6cf0ca8cd21fca2e59e2f"
FROZEN_TOTAL_CASES = 60
EVIDENCE_VERSION = "ops-m-ops-2-evidence.v1"
CASE_EVIDENCE_VERSION = "ops-m-ops-2-case-evidence.v1"

# --- the frozen execution configuration (design section 2). The evaluation deadline is a deliberate, documented deviation from the candidate profile's 150 s call limit.
CONFIG = dict(model=O.APPROVED_MODEL, model_digest=O.APPROVED_DIGEST, temperature=0, seed=7, max_tokens=512, response_format="json_object", tools=[], tool_choice=None, stream=False, record_hash_profile=O.LIVE_RECORD_HASH_PROFILE,
              max_generations_per_case=2, max_repairs_per_case=1, transport_retries=0, call_timeout_s=300, profile_call_limit_s=150, max_age_seconds=86400, now="2026-10-25T12:00:00Z", prompt_sha256=FROZEN_PROMPT_SHA256, caseset_sha256=FROZEN_CASESET_SHA256)
RUNTIME_PROFILE_SHA256 = hashlib.sha256(O.canonical({k: v for k, v in CONFIG.items() if k != "now"})).hexdigest()
REPAIRABLE = frozenset({"not_json", "not_json_text", "duplicate_key", "non_finite_number", "non_integer_number", "invalid_utf8", "oversize", "too_deep", "schema_invalid", "unknown_key"})

# --- thresholds (documented, measured or derived; every one is a parameter so a test can prove the check fails closed)
GIB = 1024 ** 3
MIB = 1024 ** 2
THRESHOLDS = {
    "offline": dict(min_free_disk_bytes=1 * GIB, min_available_memory_bytes=1024 * MIB),         # the shim dry run writes a few MB; the margin protects the rest of the machine
    "suite": dict(min_free_disk_bytes=4 * GIB, min_available_memory_bytes=2048 * MIB),            # the complete local suite left ~0.76 GB free from 3.8 GB: its scratch peak is ~3.0 GB, so start with >= 4 GiB
    "live": dict(min_free_disk_bytes=13 * GIB, min_available_memory_bytes=8750 * MIB),            # model-live's own heuristic for a 7B model: 0.7 GB/B + 8 GB disk, 0.75 GB/B + 3.5 GB memory (run 4 peaked at 6.2 GB RSS)
}


class PreflightFailed(RuntimeError):
    def __init__(self, report):
        super().__init__("preflight failed: " + ", ".join(c["name"] for c in report["checks"] if not c["ok"]))
        self.report = report


class DigestMismatch(RuntimeError):
    pass


class ProviderToolCall(RuntimeError):
    """The model asked for a tool although none was offered. It is never executed; the case is FAILED and gate S-3 is violated."""


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def file_sha256(path):
    return sha256_hex(Path(path).read_bytes())


# ------------------------------------------------------------------ providers
class Reply:
    def __init__(self, text, finish_reason, prompt_tokens, completion_tokens, latency_ms, model, tool_calls=0):
        self.text, self.finish_reason, self.prompt_tokens, self.completion_tokens, self.latency_ms, self.model, self.tool_calls = text, finish_reason, prompt_tokens, completion_tokens, latency_ms, model, tool_calls


def build_request(messages, config=CONFIG):
    """The one request body the evaluation ever sends. No `tools`, no `tool_choice`, no functions."""
    return dict(model=config["model"], messages=messages, temperature=config["temperature"], seed=config["seed"], max_tokens=config["max_tokens"], response_format={"type": config["response_format"]}, stream=False)


class OllamaProvider:
    kind = "ollama-live"

    def __init__(self, base_url="http://127.0.0.1:11434", config=CONFIG, opener=None, clock=time.monotonic):
        host = urlparse(base_url).hostname
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("the evaluation talks to a loopback Ollama only")
        self.base, self.config, self.opener, self.clock, self.requests = base_url.rstrip("/"), config, opener or urllib.request.urlopen, clock, 0
        self.attested_digest = None

    def _call(self, req, timeout):
        try:
            with self.opener(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (socket.timeout, TimeoutError):
            raise TimeoutError("provider call timed out")
        except urllib.error.URLError as e:
            if isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
                raise TimeoutError("provider call timed out")
            raise RuntimeError(f"provider unreachable: {type(e).__name__}")

    def attest(self):
        """Read the served digest from /api/tags (not from a prompt, not from the model's own claim). Raises DigestMismatch unless it is the approved one. Makes NO inference request."""
        tags = self._call(urllib.request.Request(self.base + "/api/tags"), 30)
        hit = next((m for m in tags.get("models", []) if self.config["model"] in (m.get("name"), m.get("model"))), None)
        digest = hit.get("digest") if hit else None
        if digest != self.config["model_digest"]:
            raise DigestMismatch(f"served digest {digest!r} is not the approved {self.config['model_digest']!r}")
        self.attested_digest = digest
        return digest

    def complete(self, messages, tag=""):
        if self.attested_digest is None:
            raise DigestMismatch("attest() must succeed before any inference")
        body = json.dumps(build_request(messages, self.config)).encode()
        req = urllib.request.Request(self.base + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"}, method="POST")
        t0 = self.clock(); self.requests += 1
        d = self._call(req, self.config["call_timeout_s"])
        ms = int((self.clock() - t0) * 1000)
        ch = (d.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        u = d.get("usage") or {}
        pt, ct = u.get("prompt_tokens"), u.get("completion_tokens")
        return Reply(msg.get("content") if isinstance(msg.get("content"), str) else "", ch.get("finish_reason"), pt if isinstance(pt, int) and not isinstance(pt, bool) else None, ct if isinstance(ct, int) and not isinstance(ct, bool) else None, ms, d.get("model"), len(msg.get("tool_calls") or []))


class ScriptedProvider:
    """Offline shim. Replies from a script keyed by (case id, attempt); never opens a socket. Results produced with it are labelled `scripted-shim` and can never be a model result."""
    kind = "scripted-shim"

    def __init__(self, script, digest=O.APPROVED_DIGEST, config=CONFIG):
        self.script, self.digest, self.config, self.requests, self.calls, self.attested_digest = script, digest, config, 0, [], None

    def attest(self):
        if self.digest != self.config["model_digest"]:
            raise DigestMismatch(f"served digest {self.digest!r} is not the approved one")
        self.attested_digest = self.digest
        return self.digest

    def complete(self, messages, tag=""):
        if self.attested_digest is None:
            raise DigestMismatch("attest() must succeed before any inference")
        self.requests += 1
        assert not any(k in build_request(messages, self.config) for k in ("tools", "tool_choice", "functions")), "tools must never be offered"
        r = self.script(tag, messages)
        self.calls.append(tag)
        if isinstance(r, BaseException):
            raise r
        return r


# ------------------------------------------------------------------ frozen inputs and preflight
def load_caseset(path=CASESET, sha_file=CASESET_SHA_FILE, frozen_sha=FROZEN_CASESET_SHA256):
    b = Path(path).read_bytes()
    got = sha256_hex(b)
    if got != frozen_sha:
        raise PreflightFailed(dict(checks=[dict(name="dataset_integrity", ok=False, observed=got, required=frozen_sha)]))
    doc = json.loads(b.decode("utf-8"))
    if doc["total"] != FROZEN_TOTAL_CASES or len(doc["cases"]) != FROZEN_TOTAL_CASES:
        raise PreflightFailed(dict(checks=[dict(name="dataset_integrity", ok=False, observed=len(doc["cases"]), required=FROZEN_TOTAL_CASES)]))
    return doc


def _check(name, ok, observed, required, detail=""):
    return dict(name=name, ok=bool(ok), observed=observed, required=required, detail=detail)


def vector_identity(vectors=VECTORS):
    """SHA-256 of MANIFEST.sha256, after checking that every listed file hashes to its entry."""
    lines = [ln.split("  ", 1) for ln in (vectors / "MANIFEST.sha256").read_text().splitlines() if ln.strip()]
    bad = [name for h, name in lines if sha256_hex((vectors / name).read_bytes()) != h]
    return file_sha256(vectors / "MANIFEST.sha256"), bad


def mem_available_bytes():
    with open("/proc/meminfo") as f:
        for ln in f:
            if ln.startswith("MemAvailable:"):
                return int(ln.split()[1]) * 1024
    raise RuntimeError("MemAvailable not found")


def run_preflight(purpose, out_dir, provider=None, base_url="http://127.0.0.1:11434", disk_free=None, mem_available=None, caseset_path=CASESET, frozen_caseset_sha=FROZEN_CASESET_SHA256, thresholds=None, config=CONFIG, prompt_path=PROMPT, vectors=VECTORS, profile_file=PROFILE_FILE):
    """Fail closed: every check is evaluated, the report lists all of them, and the caller must stop unless report['ok']. Nothing is deleted or modified to make a check pass."""
    th = dict(THRESHOLDS[purpose], **(thresholds or {}))
    out = Path(out_dir)
    checks = []
    probe = out if out.exists() else out.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    free = (disk_free or (lambda p: shutil.disk_usage(p).free))(probe)
    checks.append(_check("disk_free_bytes", free >= th["min_free_disk_bytes"], free, th["min_free_disk_bytes"], f"probed at {probe}; no file is deleted to recover space"))
    mem = (mem_available or mem_available_bytes)()
    checks.append(_check("memory_available_bytes", mem >= th["min_available_memory_bytes"], mem, th["min_available_memory_bytes"]))
    checks.append(_check("output_directory_unused", (not out.exists()) or (out.is_dir() and not any(out.iterdir())), str(out), "absent or empty", "an existing result is never overwritten or removed"))
    got = file_sha256(caseset_path) if Path(caseset_path).exists() else None
    checks.append(_check("dataset_integrity", got == frozen_caseset_sha, got, frozen_caseset_sha))
    side = CASESET_SHA_FILE.read_text().split()[0] if CASESET_SHA_FILE.exists() else None
    checks.append(_check("dataset_hash_file", side == frozen_caseset_sha, side, frozen_caseset_sha))
    ph = file_sha256(prompt_path)
    checks.append(_check("prompt_integrity", ph == config["prompt_sha256"], ph, config["prompt_sha256"]))
    pins = {ln.split("  ", 1)[1].strip(): ln.split("  ", 1)[0] for ln in UPSTREAM.read_text().splitlines() if "  " in ln}
    bad = sorted(k for k, v in pins.items() if (O.CONTRACT_DIR / k).exists() and file_sha256(O.CONTRACT_DIR / k) != v) + sorted(k for k, v in O.PINNED.items() if file_sha256(O.CONTRACT_DIR / k) != v)
    checks.append(_check("contract_pins", not bad and set(O.PINNED) <= set(pins), bad or "all pinned files match", "UPSTREAM.sha256 and PINNED"))
    ident, bad_vec = vector_identity(vectors)
    checks.append(_check("vector_package_pin", ident == FROZEN_VECTOR_IDENTITY and not bad_vec, ident if not bad_vec else bad_vec, FROZEN_VECTOR_IDENTITY))
    checks.append(_check("record_hash_profile_pin", config["record_hash_profile"] == O.LIVE_RECORD_HASH_PROFILE and O.ADMISSIBLE_LIVE_RECORD_HASH_PROFILES == (O.LIVE_RECORD_HASH_PROFILE,), config["record_hash_profile"], O.LIVE_RECORD_HASH_PROFILE))
    prof = json.loads(Path(profile_file).read_text())
    cfg_ok = (config["model"] == prof["model"] == O.APPROVED_MODEL and config["model_digest"] == prof["model_digest"] == O.APPROVED_DIGEST and config["temperature"] == 0 and config["seed"] == 7 and config["max_tokens"] == prof["output_tokens_per_call"]
              and config["tools"] == [] and config["tool_choice"] is None and prof["model_callable_tools"] == [] and config["max_generations_per_case"] == prof["max_http_generations_including_repairs"] == 2 and config["max_repairs_per_case"] == 1 and config["transport_retries"] == 0 and config["call_timeout_s"] <= 300)
    checks.append(_check("provider_configuration", cfg_ok, {k: config[k] for k in ("model", "temperature", "seed", "max_tokens", "tools", "max_generations_per_case", "call_timeout_s")}, "frozen design section 2"))
    if purpose == "live":
        try:
            host = urlparse(base_url).hostname
            checks.append(_check("provider_endpoint_loopback", host in ("127.0.0.1", "localhost", "::1"), host, "loopback"))
        except Exception as e:                                             # noqa: BLE001
            checks.append(_check("provider_endpoint_loopback", False, str(e), "loopback"))
    if provider is not None:
        try:
            checks.append(_check("model_digest", provider.attest() == config["model_digest"], provider.attested_digest, config["model_digest"], "read from the runtime's own model list before any inference"))
        except Exception as e:                                             # noqa: BLE001
            checks.append(_check("model_digest", False, f"{type(e).__name__}: {e}", config["model_digest"]))
    else:
        checks.append(_check("model_digest", False, "no provider supplied", config["model_digest"]))
    return dict(purpose=purpose, ok=all(c["ok"] for c in checks), thresholds=th, checks=checks)


# ------------------------------------------------------------------ prompts, trusted hashes, one case
def system_and_template():
    p = json.loads(PROMPT.read_text())
    return p["system"], p["user_template"]


def build_messages(model_input, repair_codes=None):
    system, template = system_and_template()
    assert template.count("{model_input_json}") == 1
    msgs = [dict(role="system", content=system), dict(role="user", content=template.replace("{model_input_json}", O.canonical(model_input).decode("utf-8")))]
    if repair_codes:
        msgs.append(dict(role="user", content="Your previous reply was rejected by the validator with: " + ", ".join(sorted(repair_codes)) + ". Return only the corrected JSON object for the same input."))
    return msgs


def trusted_hashes(model_input):
    """The host's own record hashes: RECOMPUTED under the pinned profile from the fact content, never copied from the snapshot's embedded hashes."""
    return {f["provenance"]["record_id"] + "|" + f["provenance"]["source_ref"]: O.record_sha256(O.LIVE_RECORD_HASH_PROFILE, f, model_input["tenant_scope_id"]) for f in model_input["facts"]}


def _raw_fields(text):
    b = (text or "").encode("utf-8", errors="replace")
    return dict(raw_output=b[:O.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), raw_bytes=len(b), raw_sha256=sha256_hex(b))


def run_case(case, provider, config=CONFIG, cfg_now=None):
    mi, tr = case["model_input"], trusted_hashes(case["model_input"])
    now = cfg_now or config["now"]
    attempts = []

    def call(msgs, kind):
        a = dict(n=len(attempts) + 1, kind=kind, finish_reason=None, prompt_tokens=None, completion_tokens=None, latency_ms=None, over_profile_call_limit=False, error=None, tool_calls=0, validator_status=None, validator_codes=[], **_raw_fields(""))
        attempts.append(a)
        try:
            r = provider.complete(msgs, tag=f"{case['id']}#{a['n']}")
        except BaseException as e:                                      # noqa: BLE001 - recorded, then re-raised for explain() to classify
            a["error"] = type(e).__name__
            raise
        a.update(finish_reason=r.finish_reason, prompt_tokens=r.prompt_tokens, completion_tokens=r.completion_tokens, latency_ms=r.latency_ms, tool_calls=r.tool_calls, over_profile_call_limit=(r.latency_ms or 0) > config["profile_call_limit_s"] * 1000, **_raw_fields(r.text))
        if r.tool_calls:
            a["error"] = "ProviderToolCall"
            raise ProviderToolCall()
        if (r.latency_ms or 0) > config["call_timeout_s"] * 1000:
            a["error"] = "TimeoutError"
            raise TimeoutError()
        return r

    def judge(text):
        v = O.validate_output(text, mi, trusted_record_hashes=tr, now=now, max_age_seconds=config["max_age_seconds"])
        return v["status"], v["codes"]

    def candidate(model_input):
        r = call(build_messages(model_input), "first")
        a = attempts[0]
        if r.finish_reason == "stop":
            a["validator_status"], a["validator_codes"] = judge(r.text)
        final = r
        if r.finish_reason == "stop" and a["validator_status"] == "REJECTED" and a["validator_codes"] and set(a["validator_codes"]) <= REPAIRABLE and config["max_repairs_per_case"] >= 1:
            final = call(build_messages(model_input, a["validator_codes"]), "repair")
            if final.finish_reason == "stop":
                attempts[1]["validator_status"], attempts[1]["validator_codes"] = judge(final.text)
        meta = dict(name="ollama", model=config["model"], digest=provider.attested_digest, runtime_profile_sha256=RUNTIME_PROFILE_SHA256, actual_model_calls=len(attempts), prompt_tokens=sum(x["prompt_tokens"] or 0 for x in attempts),
                    completion_tokens=sum(x["completion_tokens"] or 0 for x in attempts), estimated_usage=not all(isinstance(x["prompt_tokens"], int) and isinstance(x["completion_tokens"], int) for x in attempts), latency_ms=sum(x["latency_ms"] or 0 for x in attempts))
        return final.text, meta, final.finish_reason if final.finish_reason is not None else "missing_finish_reason"      # a reply without a finish reason is a provider failure, never a quiet "stop"

    res = O.explain(mi, candidate, "LIVE_LLM", audit_complete=False, trusted_record_hashes=tr, now=now, max_age_seconds=config["max_age_seconds"], record_hash_profile=config["record_hash_profile"])
    env, v, rec = res["envelope"], res["verdict"], res["record"]
    replay = O.deterministic_replay(mi)
    served = env["status"] in ("ACCEPTED", "AUDIT_PENDING", "ABSTAINED") and not env["validation_codes"]
    return dict(schema_version=CASE_EVIDENCE_VERSION, case_id=case["id"], index=case["index"], group=case["group"], category=case["category"], tenant=case["tenant"], label=case.get("label"), repeat_of=case.get("repeat_of"),
                snapshot_sha256=mi["snapshot_sha256"], record_hash_profile=config["record_hash_profile"], mode="LIVE_LLM", provider_kind=provider.kind, attempts=attempts, repair_used=any(a["kind"] == "repair" for a in attempts), request_tools_offered=False,
                envelope=env, validator=dict(status=v["status"], codes=v["codes"], flags=v.get("flags", []), required_reasons=v.get("required_reasons", []), claim_verdicts=v.get("claims", [])), validator_record=dict(rec, raw_output=None), result_invariant_violations=O.result_invariants(env),
                served_model_result=served, displayed_text=env["rendered_explanation"], displayed_text_sha256=sha256_hex(env["rendered_explanation"].encode()),
                deterministic_replay=dict(label="DETERMINISTIC_REPLAY", status=replay["envelope"]["status"], mode=replay["envelope"]["mode"], provider=None, rendered_explanation_sha256=sha256_hex(replay["envelope"]["rendered_explanation"].encode()), counted_as_model_success=False))


# ------------------------------------------------------------------ whole run and evidence
def _write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    Path(path).write_bytes(data)
    return sha256_hex(data)


def run_evaluation(out_dir, provider, purpose="offline", cases=None, preflight=None, config=CONFIG, environment=None, thresholds=None, disk_free=None, mem_available=None, ids=None):
    """Preflight (fail closed) -> every frozen case in index order -> evidence files + manifest + SHA256SUMS. Never overwrites: the output directory must be absent or empty."""
    pre = preflight or run_preflight(purpose, out_dir, provider=provider, thresholds=thresholds, disk_free=disk_free, mem_available=mem_available, config=config)
    if not pre["ok"]:
        raise PreflightFailed(pre)
    doc = load_caseset()
    todo = [c for c in (cases if cases is not None else doc["cases"]) if ids is None or c["id"] in ids]
    out = Path(out_dir)
    files, t0 = {}, time.time()
    files["preflight.json"] = _write_json(out / "preflight.json", pre)
    results = []
    for c in todo:
        ev = run_case(c, provider, config)
        results.append(ev)
        files[f"cases/{c['id']}.json"] = _write_json(out / "cases" / f"{c['id']}.json", ev)
    manifest = dict(schema_version=EVIDENCE_VERSION, kind="live-run" if provider.kind == "ollama-live" else "scripted-shim-dry-run", provider_kind=provider.kind, purpose=purpose, caseset_sha256=FROZEN_CASESET_SHA256, caseset_total=doc["total"], cases_run=len(todo), complete=len(todo) == doc["total"],
                    case_ids=[c["id"] for c in todo], prompt_sha256=config["prompt_sha256"], vector_identity=FROZEN_VECTOR_IDENTITY, contract_pin_set=doc["contract_pin_set"], validator_revision=O.VALIDATOR_REVISION, renderer_revision=O.RENDERER_REVISION, record_hash_profile=config["record_hash_profile"],
                    config={k: v for k, v in config.items()}, runtime_profile_sha256=RUNTIME_PROFILE_SHA256, model=config["model"], model_digest_attested=provider.attested_digest, provider_requests=provider.requests, environment=environment or {}, files=files, tools_offered=False,
                    workflow_fingerprint=dict(mode="structural", note="the harness holds no workflow, database, approval or procurement handle; see tests/test_ops_m_ops_2_harness.py::test_harness_imports_no_workflow_database_or_platform_module"), runner_wall_seconds=round(time.time() - t0, 3))
    mh = _write_json(out / "run-manifest.json", manifest)
    sums = "".join(f"{h}  {p}\n" for p, h in sorted({**files, "run-manifest.json": mh}.items()))
    (out / "SHA256SUMS").write_text(sums)
    return dict(manifest=manifest, results=results, out_dir=str(out))
