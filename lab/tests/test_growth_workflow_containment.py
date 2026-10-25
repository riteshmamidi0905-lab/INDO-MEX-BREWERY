"""Containment in the governed procurement workflow (Phase 2 targeted hardening). Run 40141457239 showed the model-backed path ending in the deterministic fallback; these tests pin what the workflow guarantees WHATEVER an agent returns:
model output is verified before use; rejected or failed output can never become an approved action; the fallback is labelled and explained; THE WEIR still holds the write and a different owner decides; tool calls stay on the read-only
allowlist; and the audit trail keeps the evidence (rejected claim text, comparison set, usage, telemetry). The agents here are SCRIPTED doubles, not models."""
import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
from nasha_lab.growth import agent_research as AR, service as SV  # noqa: E402
from test_growth_launch import AS_OF, SCHEMA, FakeAgent, dsn, make, project, q, tok, world  # noqa: E402,F401


class ModelLike(FakeAgent):
    provider = "ollama"                                       # makes the workflow treat the double like a model-backed agent (extra provenance is recorded for model runs only)


def real_pair(world):
    s = SV.GrowthService(world["dsn"], SCHEMA, "tenant-nasha", "ana")
    d = s.supplier_directory(AS_OF, project(world)); s.close()
    docs = AR.supplier_documents(d)
    by_ref = {}
    for sup in d:
        for p in sup["products"]:
            if p["unit_price_cents"] is not None and p.get("ingredient_ref"):
                by_ref.setdefault(p["ingredient_ref"], []).append((float(p["unit_price_cents"]), sup, p))
    ref = sorted((r for r, v in by_ref.items() if len({x[1]["id"] for x in v}) >= 3), key=lambda r: (-len(by_ref[r]), r))[0]
    rows = sorted(by_ref[ref], key=lambda x: (x[0], x[1]["name"]))
    return d, docs, rows


def result(docs, sup, claims, tool_calls=None, limitations=("l",)):
    did = f"supplier-{sup['id']}"
    return dict(mode=AR.MODE_MODEL, provider="ollama", run_id="scripted", report=dict(title="t", answer="a", claims=claims, limitations=list(limitations)), verification=dict(ok=True, groundedness=1.0, citation_validity=1.0),
                evidence={"e1": dict(doc_id=did, title=sup["name"], text=docs[did][1])}, tool_calls=tool_calls if tool_calls is not None else [dict(tool="search_corpus", status="ok")],
                usage=dict(calls=2, prompt_tokens=100, completion_tokens=20, estimated=False), models=["scripted-model"], event_counts={}, telemetry={"state": "completed"}, quarantined=[])


def baseline_hash(world):
    wf = make(world); r = wf.run(tok(wf, "ana"), project(world), 4); h = wf.status(r["corr_id"])["proposal_hash"]; wf.close(); return h


def no_record_yet(world, corr):
    return not q(world, "SELECT 1 FROM audit_log WHERE action='procurement.record' AND entity_id=%s", (corr,))


def held_and_decided_by_a_different_owner(world, wf, r):
    assert r["status"] == "AWAITING_APPROVAL" and r["side_effects"] == dict(orders_placed=0, suppliers_contacted=0, emails_sent=0) and no_record_yet(world, r["corr_id"])
    assert wf.decide(r["corr_id"], tok(wf, "ana"), True).get("failure") == "ROLE_DENIED", "the requester's role cannot approve"
    assert wf.decide(r["corr_id"], tok(wf, "ada"), True)["status"] == "EXECUTED", "a different owner can, through THE WEIR"


def test_a_false_superlative_from_a_model_is_rejected_and_the_labelled_fallback_still_needs_a_human(world):  # noqa: F811
    d, docs, rows = real_pair(world)
    not_lowest = rows[-1]                                                    # the most expensive supplier called the lowest
    claim = f"{not_lowest[1]['name']} quotes the lowest {not_lowest[2]['name'].split(' (')[0]} price at {AR.money(not_lowest[0])} per {not_lowest[2]['unit']}."
    wf = make(world, agent=ModelLike(result(docs, not_lowest[1], [dict(text=claim, evidence_ids=["e1"])])))
    r = wf.run(tok(wf, "ana"), project(world), 4)
    run = wf.status(r["corr_id"])
    assert run["agent_mode"] == "deterministic_fallback" and run["proposal_hash"] == baseline_hash(world), "the recommendation is the stored-quote computation, never the model's text"
    assert run["research"]["fallback_reason"] == "agent output failed verification" and "COMPARATIVE_FALSE" in run["research"]["rejected_agent_output"]["codes"]
    ev = {e["name"]: e for e in wf.trace(r["corr_id"]) if e.get("name") in ("agent_research", "agent_fallback")}
    assert ev["agent_fallback"]["mode"] == "deterministic_fallback" and ev["agent_fallback"]["reason"] == "agent output failed verification"
    a = ev["agent_research"]                                                 # audit evidence retained: the rejected claim text, the comparison set, usage and models
    assert a["rejected_claims"][0]["text"] == claim and a["rejected_claims"][0]["codes"] and a["comparisons"][0]["verdict"] == "false" and a["comparisons"][0]["set"] and a["usage"]["estimated"] is False and a["models"] == ["scripted-model"]
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_a_true_superlative_is_accepted_labelled_as_a_model_run_and_still_held_for_approval(world):  # noqa: F811
    d, docs, rows = real_pair(world)
    best = rows[0]
    claim = f"{best[1]['name']} quotes the lowest {best[2]['name'].split(' (')[0]} price at {AR.money(best[0])} per {best[2]['unit']}."
    wf = make(world, agent=ModelLike(result(docs, best[1], [dict(text=claim, evidence_ids=["e1"])])))
    r = wf.run(tok(wf, "ana"), project(world), 4)
    run = wf.status(r["corr_id"])
    assert run["agent_mode"] == "engine_model" and run["research"]["boundary"]["status"] == "accepted" and run["proposal_hash"] == baseline_hash(world)
    a = next(e for e in wf.trace(r["corr_id"]) if e.get("name") == "agent_research")
    assert a["comparisons"][0]["verdict"] == "verified" and a["comparisons"][0]["extreme"]["suppliers"] == [best[1]["name"]]
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_a_universal_absence_claim_from_a_model_is_rejected_not_accepted_as_a_finding(world):  # noqa: F811
    d, docs, rows = real_pair(world)
    wf = make(world, agent=ModelLike(result(docs, rows[0][1], [dict(text="No published prices were found for any of the suppliers.", evidence_ids=["e1"])])))
    r = wf.run(tok(wf, "ana"), project(world), 4)
    run = wf.status(r["corr_id"])
    assert run["agent_mode"] == "deterministic_fallback" and "ABSENCE_OVERGENERAL" in run["research"]["rejected_agent_output"]["codes"]
    ab = next(e for e in wf.trace(r["corr_id"]) if e.get("name") == "agent_research")["absences"][0]
    assert ab["kind"] == "universal" and ab["verdict"] == "overgeneral" and ab["suggestion"] == "No matching price was found in the searched records."
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_a_tool_outside_the_read_only_allowlist_voids_the_whole_output(world):  # noqa: F811
    d, docs, rows = real_pair(world)
    best = rows[0]
    claim = f"{best[1]['name']} quotes {best[2]['name'].split(' (')[0]} at {AR.money(best[0])} per {best[2]['unit']}."
    wf = make(world, agent=ModelLike(result(docs, best[1], [dict(text=claim, evidence_ids=["e1"])], tool_calls=[dict(tool="search_corpus", status="ok"), dict(tool="send_email", status="ok")])))
    r = wf.run(tok(wf, "ana"), project(world), 4)
    run = wf.status(r["corr_id"])
    assert run["agent_mode"] == "deterministic_fallback" and "TOOL_NOT_ALLOWED" in run["research"]["rejected_agent_output"]["codes"] and run["proposal_hash"] == baseline_hash(world)
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_failed_inference_falls_back_labelled_with_classified_telemetry_and_cannot_bypass_approval(world):  # noqa: F811
    tele = dict(run_id="r", state="failed", failure_class="verification_failed", usage=dict(calls=3, prompt_tokens=10, completion_tokens=5, estimated=False), models=["scripted-model"], call_latency_ms=[1.0], event_counts={}, provider_events=[], plan_fallback=None, tool_calls=[],
                verification=[dict(attempt=1, ok=False, unsupported_claims=["No published prices were found for any of the suppliers."], invalid_citations=[])])
    wf = make(world, agent=ModelLike(exc=AR.AgentUnavailable("the agent run ended failed: no claim survived verification", "verification_failed", telemetry=tele)))
    r = wf.run(tok(wf, "ana"), project(world), 4)
    run = wf.status(r["corr_id"])
    assert run["agent_mode"] == "deterministic_fallback" and "agent unavailable" in run["research"]["fallback_reason"] and run["proposal_hash"] == baseline_hash(world)
    fb = next(e for e in wf.trace(r["corr_id"]) if e.get("name") == "agent_fallback")
    cls = fb["agent_telemetry"]["unsupported_claim_classification"][0]
    assert fb["mode"] == "deterministic_fallback" and fb["agent_telemetry"]["usage"]["calls"] == 3 and cls["absence"]["kind"] == "universal" and cls["absence"]["verdict"] == "overgeneral"
    held_and_decided_by_a_different_owner(world, wf, r)
    wf.close()


def test_the_research_question_names_the_ingredients_and_does_not_depend_on_the_model(world):  # noqa: F811
    from nasha_lab.growth import launch_workflow as LW
    s = SV.GrowthService(world["dsn"], SCHEMA, "tenant-nasha", "ana")
    from nasha_lab.growth import procurement as PRC
    c = s.procurement_context(project(world)); d = s.supplier_directory(AS_OF, project(world)); s.close()
    plan = PRC.plan(d, c["scenario"], 4, AS_OF, c["requirements"], c["use_recipes"])
    qtext = LW.research_query(plan)
    assert qtext == LW.research_query(plan), "stable for a given plan"
    names = [i["ingredient"] for i in sorted(plan["items"], key=lambda i: (-((i.get("chosen") or {}).get("cost_cents") or 0), i["ingredient_ref"]))[:LW.QUERY_ITEMS]]
    assert all(n in qtext for n in names) and "published prices" not in qtext and "Cite the supplier records" in qtext


@pytest.mark.parametrize("weeks", [1, 2, 4, 8])
def test_the_offline_engines_grounded_answer_fits_the_boundarys_size_limit_for_every_period(world, weeks):  # noqa: F811
    """Regression: a 2-week plan once produced a grounded 8-claim answer of 1,542 characters and was refused as MALFORMED by the (unchanged) 1,500-character limit, so the labelled fallback replaced a good answer. The run now asks for a bounded report."""
    from nasha_lab.growth import model_boundary as MB
    agent = AR.SupplierResearchAgent(world["dsn"], "tenant-nasha", world["root"] / f"fit{weeks}", provider="offline")
    wf = make(world, agent=agent)
    r = wf.run(tok(wf, "ana"), project(world), weeks)
    run = wf.status(r["corr_id"])
    ev = next(e for e in wf.trace(r["corr_id"]) if e.get("name") in ("agent_research", "agent_fallback"))
    assert run["agent_mode"] == "engine_offline_heuristic" and run["research"]["boundary"]["status"] == "accepted", (weeks, ev)
    assert 0 < len(run["research"]["report"]["answer"]) <= MB.MAX_ANSWER_CHARS and len(run["research"]["report"]["claims"]) <= MB.MAX_CLAIMS
    wf.close()


def test_the_report_size_limit_itself_is_unchanged():
    from nasha_lab.growth import model_boundary as MB
    assert MB.MAX_ANSWER_CHARS == 1500 and MB.MAX_CLAIMS == 12 and MB.MAX_CLAIM_CHARS == 400
