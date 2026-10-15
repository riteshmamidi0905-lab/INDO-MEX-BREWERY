"""Experiment observability: turn run traces into comparable records (planner, model, prompt, retriever, tokens, latency, retries, review time, outcome).
Local compute only: no API charge exists, so no dollar figure is invented. Tokens, calls and milliseconds are reported as measured."""
import json


def run_record(events):
    meta = next((e for e in events if e["kind"] == "run_meta"), {})
    llm = [e for e in events if e["kind"] == "llm_call" and e.get("ok")]
    prop = next((e for e in events if e["kind"] == "proposal"), None); dec = next((e for e in events if e["kind"] == "human_decision"), None); fin = next((e for e in reversed(events) if e["kind"] == "final"), None)
    tools = [e for e in events if e["kind"] in ("tool_call", "tool_error")]
    pol = [e for e in events if e["kind"] == "policy_retrieved"]
    return dict(planner_type=meta.get("planner_type"), planner_version=meta.get("planner_version"), model=meta.get("model"), prompt_version=meta.get("prompt_version"), retriever=meta.get("retriever_type"),
                embedding_model=meta.get("embedding_model"), llm_calls=len(llm), prompt_tokens=sum(e.get("prompt_tokens", 0) for e in llm), completion_tokens=sum(e.get("completion_tokens", 0) for e in llm),
                llm_ms=round(sum(e.get("ms", 0) for e in llm), 1), tool_calls=len(tools), tool_errors=sum(1 for e in tools if e["kind"] == "tool_error"), tool_ms=round(sum(e.get("ms", 0) or 0 for e in tools if e["kind"] == "tool_call"), 1),
                schema_failures=sum(1 for e in events if e["kind"] == "schema_failure"), retries=sum(1 for e in events if e["kind"] == "schema_failure" and e.get("attempt", 0) < 2),
                guardrail_overrides=sum(1 for e in events if e["kind"] == "guardrail_override"), retrieval_scores=[s for e in pol for s in e.get("scores", []) if s is not None][:6],
                human_review_s=round(dec["ts"] - prop["ts"], 3) if dec and prop else None, action=prop["action"] if prop else None, outcome=fin["outcome"] if fin else None,
                cost_note="LOCAL COMPUTE: NO API CHARGE")


def summarize(store, run_ids=None):
    ids = run_ids or [r[0] for r in store.con.execute("SELECT run_id FROM agent_runs").fetchall()]
    return {rid: run_record(store.events(rid)) for rid in ids}
