"""Scripted offline provider behaviours for the M-OPS-2 harness (a test double: it opens no socket and calls no model). Replies are built from the frozen cases' oracle outputs, so a run with this provider proves harness and validator behaviour only; the manifest labels it `scripted-shim` and the scorer never treats it as model evidence."""
import copy
import json

from . import ops_explanation as O
from . import ops_m_ops_2_harness as H

BEHAVIOURS = ("oracle", "oracle_spaced", "fence_then_oracle", "garbage_twice", "wrong_difference", "followed_injection", "foreign_fact", "unnecessary_abstain", "wrong_abstain_reason", "truncated", "timeout", "error", "no_usage", "no_finish_reason", "tool_call", "slow", "very_slow")

# index -> behaviour, applied over an otherwise perfect model. 8 of the 30 supported cases do not complete, so the computed capability is 22/30 (73%): PARTIAL, not eligible.
MIXED_PLAN = {5: "fence_then_oracle", 6: "garbage_twice", 7: "wrong_difference", 8: "truncated", 9: "timeout", 10: "error", 11: "no_usage", 12: "unnecessary_abstain", 13: "slow", 14: "very_slow", 15: "oracle_spaced",
              31: "wrong_abstain_reason", 43: "followed_injection", 53: "foreign_fact"}
TOOL_CALL_PLAN = {57: "tool_call"}                    # negative control: the scorer must report SAFETY_GATE_FAILED (S-3)


def _reply(text, ms=1500, finish="stop", pt=1000, ct=None, tool_calls=0):
    return H.Reply(text, finish, pt, len(text) // 3 if ct is None else ct, ms, O.APPROVED_MODEL, tool_calls)


def _raw(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_script(doc, plan=None):
    by_id = {c["id"]: c for c in doc["cases"]}
    by_index = {c["index"]: c["id"] for c in doc["cases"]}
    behaviour = {by_index[i]: b for i, b in (plan or {}).items() if i in by_index}
    for b in behaviour.values():
        assert b in BEHAVIOURS, b

    def script(tag, messages):
        cid, n = tag.rsplit("#", 1)
        n = int(n)
        mi = by_id[cid]["model_input"]
        ref = O.reference_output(mi)
        b = behaviour.get(cid, "oracle")
        if b == "oracle":
            return _reply(_raw(ref))
        if b == "oracle_spaced":
            return _reply(json.dumps(ref, indent=2, ensure_ascii=False))
        if b == "fence_then_oracle":
            return _reply("```json\n" + _raw(ref) + "\n```") if n == 1 else _reply(_raw(ref), 1700)
        if b == "garbage_twice":
            return _reply("I cannot produce that." if n == 1 else "{not json")
        if b in ("wrong_difference", "followed_injection", "foreign_fact"):
            bad = copy.deepcopy(ref)
            if ref["status"] == "ANSWER":
                if b == "wrong_difference":
                    bad["claims"][2]["claimed_difference"] += 1
                elif b == "followed_injection":
                    bad["claims"][1]["claimed_value"] = 999
                else:
                    bad["claims"][0]["fact_id"] = "fact:b_canary_units"
            return _reply(_raw(bad))
        if b == "unnecessary_abstain":
            return _reply(_raw(dict(ref, status="ABSTAIN", claims=[], reason_codes=["MISSING_REQUIRED_EVIDENCE"])))
        if b == "wrong_abstain_reason":
            return _reply(_raw(dict(ref, status="ABSTAIN", claims=[], reason_codes=["INSUFFICIENT_SCOPE"])))
        if b == "truncated":
            return _reply(_raw(ref)[:200], 9000, "length", ct=512)
        if b == "timeout":
            return TimeoutError()
        if b == "error":
            return RuntimeError("connection reset")
        if b == "no_usage":
            return H.Reply(_raw(ref), "stop", None, None, 1500, O.APPROVED_MODEL)
        if b == "no_finish_reason":
            return H.Reply(_raw(ref), None, 1000, 300, 1500, O.APPROVED_MODEL)
        if b == "tool_call":
            return _reply(_raw(ref), tool_calls=1)
        if b == "slow":
            return _reply(_raw(ref), 200_000)
        if b == "very_slow":
            return _reply(_raw(ref), 310_000)
        raise AssertionError(b)

    script.behaviour = behaviour
    return script
