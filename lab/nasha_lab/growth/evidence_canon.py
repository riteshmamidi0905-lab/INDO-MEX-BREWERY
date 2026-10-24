"""Canonical form of an evidence document, and a business digest of a procurement plan.

Why two forms. Operational records carry generated identifiers (supplier, run, approval, correlation ids), clock times and durations, and hashes computed over those identifiers. They are TRUE provenance of the execution that
produced a document and must be kept as they are. They are not outcomes. So that two independent executions of the same business inputs can be compared for the outcome only, `canonical_view` projects a document by
exactly three stated rules and nothing else:
  1. an identifier (pattern ID below) inside a string is replaced by "<id>"                       (identity of a record, not a result)
  2. a key in VOLATILE_KEYS is removed                                                          (a time, a duration, a version, or a hash computed over identifiers)
  3. nothing is sorted, rounded or dropped otherwise                                              (an ordering or number that differs between executions therefore shows up as a difference)
`business_digest` is a hash over the content of a recommendation that a user would read (what is bought, from whom by NAME, in what quantity, at what cost), so a recommendation can be compared across databases even though the
operational proposal hash (which includes supplier ids and is what THE WEIR binds an approval to) legitimately differs. Pure; no I/O."""
import hashlib
import json
import re

ID = re.compile(r"\b(?:lead|acc|con|sup|sprod|supsrc|run|wf|ap|pr|proj|scn|req|ms|find|camp|opp|usr|aud|offer|seg|prod|launch|plan|dec|evt|ev|chunk|doc)[-_][0-9a-f]{6,}\b|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
# Keys removed from the canonical view, with the reason each is not an outcome.
VOLATILE_KEYS = {
    "generated_at": "wall-clock time of the export", "generated_seconds": "duration of the export", "ts": "event time", "expires": "approval expiry (epoch seconds)", "created_at": "record time",
    "tool_ms_max": "measured latency", "tool_ms_median": "measured latency", "ms": "measured latency", "latency_ms": "measured latency", "elapsed_s": "duration",
    "commit": "source commit the document was produced from (provenance of the code, not of the result)", "postgres": "server version", "python": "interpreter version",
    "call_hash": "hash over a tool call whose arguments contain generated ids", "proposal_hash": "hash over a proposal whose lines contain generated supplier ids (use business_digest to compare the content)",
}


def mask(s):
    return ID.sub("<id>", s)


def canonical_view(o):
    if isinstance(o, dict):
        return {k: canonical_view(v) for k, v in o.items() if k not in VOLATILE_KEYS}
    if isinstance(o, list):
        return [canonical_view(v) for v in o]
    if isinstance(o, str):
        return mask(o)
    return o


def canonical_sha256(o):
    return hashlib.sha256(json.dumps(canonical_view(o), sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def business_digest(plan):
    """plan: a procurement.plan() result. Hash of what is bought, from which supplier (by name), in what quantity and at what cost, plus the per-supplier and grand totals. Order of the items is part of the content
    (they are produced in a defined order), so an unstable ordering changes the digest."""
    lines = [dict(ingredient=i["ingredient"], ref=i.get("ingredient_ref"), need=i["need_qty"], supplier=(i["chosen"] or {}).get("supplier"), packs=(i["chosen"] or {}).get("packs"), buy=(i["chosen"] or {}).get("buy_qty"),
                  cost=(i["chosen"] or {}).get("cost_cents"), price_class=(i["chosen"] or {}).get("price_class")) for i in plan["items"]]
    totals = [dict(supplier=t["supplier"], cost=t["cost_cents"], items=t["items"]) for t in plan["supplier_totals"]]
    blob = json.dumps(dict(lines=lines, totals=totals, total=plan["total_cost_cents"], weeks=plan["period_weeks"]), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
