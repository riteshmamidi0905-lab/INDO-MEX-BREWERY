"""The governed workflow's rejection record (recording format 2), end to end with SCRIPTED agent doubles (no model): a rejected comparison - correct or incorrect - and an accepted one all leave a record that can be judged afterwards; the rejection still voids the model output
(no partial acceptance), the fallback recommendation is still the stored-quote computation, and THE WEIR still holds the write."""
import json

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
from nasha_lab.growth import agent_research as AR, launch_workflow as LW  # noqa: E402
from test_growth_launch import dsn, make, project, tok, world  # noqa: E402,F401
from test_growth_workflow_containment import ModelLike, baseline_hash, held_and_decided_by_a_different_owner, real_pair  # noqa: E402


def scripted(docs, rows, claims):
    ev = {f"e{n}": dict(doc_id=f"supplier-{s['id']}", title=s["name"], text=docs[f"supplier-{s['id']}"][1]) for n, (_, s, _) in enumerate(rows, 1)}
    return dict(mode=AR.MODE_MODEL, provider="ollama", run_id="scripted", report=dict(title="t", answer="a", claims=[dict(text=t, evidence_ids=list(ev)) for t in claims], limitations=["l"]), verification=dict(ok=True, groundedness=1.0, citation_validity=1.0),
                evidence=ev, tool_calls=[dict(tool="search_corpus", status="ok")], usage=dict(calls=2, prompt_tokens=100, completion_tokens=20, estimated=False), models=["scripted-model"], event_counts={}, telemetry={"state": "completed"}, quarantined=[])


def product(rows):
    return rows[0][2]["name"].split(" (")[0]


def listing(rows, called_lowest):
    parts = ", ".join(f"{s['name']} at {AR.money(c)} per {p['unit']}" for c, s, p in rows)
    return f"{product(rows)} is quoted by {parts}; of these stored quotes, {called_lowest['name']} holds the lowest."


def run_with(world, claims):  # noqa: F811
    d, docs, rows = real_pair(world)
    wf = make(world, agent=ModelLike(scripted(docs, rows, claims(rows))))
    r = wf.run(tok(wf, "ana"), project(world), 4)
    return wf, r, wf.status(r["corr_id"]), next(e for e in wf.trace(r["corr_id"]) if e.get("name") == "agent_research"), rows


def check_record(a, rows, text):
    assert a["recording_version"] == 2 and a["query"] and a["corpus_version"] and len(a["evidence_context"]) == len(rows)
    assert all(len(e["text_sha256"]) == 64 and "text" not in e for e in a["evidence_context"])
    rc = a["rejected_claims_full"][0]
    assert rc["text"] == text and rc["text_chars"] == len(text) and rc["codes"] and rc["evidence_ids"] and rc["cited_passages"] and "detail" in rc
    assert a["report_reviewed"]["claims"][0]["text"] == text and a["verification"]["ok"] is True
    cmp_ = next(c for c in a["comparisons"] if c["claim_full"] == text)
    assert cmp_["verdict"] == "false" and [x["supplier"] for x in cmp_["set_detail"]] == [s["name"] for _, s, _ in rows], "every stored quote compared, cheapest first"
    return rc, cmp_


def test_a_correct_listing_that_the_current_rule_rejects_is_recorded_completely_and_remains_rejected(world):  # noqa: F811
    wf, r, run, a, rows = run_with(world, lambda rows: [listing(rows, rows[0][1])])           # prices real, the supplier called lowest IS the lowest
    assert run["agent_mode"] == "deterministic_fallback" and "COMPARATIVE_FALSE" in run["research"]["rejected_agent_output"]["codes"], "verification was not loosened"
    assert run["proposal_hash"] == baseline_hash(world)
    rc, cmp_ = check_record(a, rows, listing(rows, rows[0][1]))
    assert cmp_["extreme"]["suppliers"] == [rows[0][1]["name"]] and rows[0][1]["name"] in rc["text"].split("lowest")[0].rsplit(";", 1)[-1], "the record shows the supplier called lowest is the true lowest"
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_an_incorrect_comparison_is_recorded_completely_and_the_record_shows_the_error(world):  # noqa: F811
    wf, r, run, a, rows = run_with(world, lambda rows: [listing(rows, rows[-1][1])])          # the dearest supplier called the lowest
    rc, cmp_ = check_record(a, rows, listing(rows, rows[-1][1]))
    assert cmp_["extreme"]["suppliers"] == [rows[0][1]["name"]] and rows[-1][1]["name"] in rc["text"].split("lowest")[0].rsplit(";", 1)[-1] and rows[-1][1]["name"] not in cmp_["extreme"]["suppliers"], "the record shows the supplier called lowest is not the true lowest"
    assert run["agent_mode"] == "deterministic_fallback" and run["proposal_hash"] == baseline_hash(world)
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_one_rejected_claim_still_voids_a_report_that_also_has_a_true_claim_no_partial_acceptance(world):  # noqa: F811
    def claims(rows):
        return [f"{rows[0][1]['name']} quotes the lowest {product(rows)} price at {AR.money(rows[0][0])} per {rows[0][2]['unit']}.", listing(rows, rows[-1][1])]
    wf, r, run, a, rows = run_with(world, claims)
    assert run["agent_mode"] == "deterministic_fallback" and a["boundary"]["accepted"] == 1 and len(a["rejected_claims_full"]) == 1
    shown = run["research"]["report"]
    assert run["research"]["rejected_agent_output"] is not None and "no agent run" in shown["title"], "the report shown is the labelled deterministic summary"
    assert not any(c["text"] == a["report_reviewed"]["claims"][0]["text"] for c in shown["claims"]), "the true claim of the rejected report was not carried over"
    wf.close()


def test_an_accepted_model_output_records_its_context_and_no_rejection(world):  # noqa: F811
    wf, r, run, a, rows = run_with(world, lambda rows: [f"{rows[0][1]['name']} quotes the lowest {product(rows)} price at {AR.money(rows[0][0])} per {rows[0][2]['unit']}."])
    assert run["agent_mode"] == "engine_model" and a["rejected_claims_full"] == [] and a["report_reviewed"] is None
    assert a["recording_version"] == 2 and a["query"] and len(a["evidence_context"]) == len(rows)
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_the_offline_agents_event_is_unchanged_no_recording_fields(world):  # noqa: F811
    wf = make(world); r = wf.run(tok(wf, "ana"), project(world), 4)
    assert not any("recording_version" in e or "rejected_claims_full" in e for e in wf.trace(r["corr_id"])), json.dumps([k for e in wf.trace(r["corr_id"]) for k in e if k.startswith("recording")])
    wf.close()
