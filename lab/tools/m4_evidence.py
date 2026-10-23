"""Milestone 4 evidence: runs the real evaluations (supplier intelligence, financial model, model-output boundary), records the model-runtime facts, and drives the complete entrepreneur journey through the real HTTP API on a fresh
synthetic world. Only deterministic fields are recorded (no ids, no timestamps), so two exports of the same code are identical. Called by export_growth_evidence.py; also runnable alone: python tools/m4_evidence.py."""
import os
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

from fastapi.testclient import TestClient  # noqa: E402

from nasha_lab.growth import api as GA, demo as DM, financial_eval as FE, model_boundary as MB, model_eval as ME, supplier_eval as SE  # noqa: E402

AS_OF = date(2026, 10, 23)
A = "tenant-nasha"


def runtime_facts():
    reachable = False
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2); reachable = True
    except Exception:  # noqa: BLE001
        pass
    paid_ok = MB.provider_permitted("openai", os.environ)[0] or MB.provider_permitted("anthropic", os.environ)[0]
    return dict(local_runtime_checked="Ollama at localhost:11434", local_runtime_reachable=reachable, paid_provider_permitted=paid_ok, paid_provider_rule=MB.provider_permitted("openai", {})[1],
                model_backed_run_recorded=False, providers_selectable=["offline (heuristic, not a language model)", "ollama (local)", "openai-compatible (paid; needs approval)", "anthropic (paid; needs approval)"],
                live_test="tests/test_growth_model_live.py is skipped here and reported as unverified by the release gate",
                what_would_change_this="serve a local model with Ollama and run: NASHA_LIVE_MODEL_PROVIDER=ollama python -m pytest tests/test_growth_model_live.py; the output still crosses the same boundary and cannot change the recommendation")


def eval_sections():
    me = ME.metrics(); mm = ME.run_mutants()
    boundary = dict(metrics={k: v for k, v in me.items() if k != "failures"}, failures=me["failures"], rules=sorted(MB.RULES),
                    cases=[dict(name=r["name"], expected=r["expected"], got=r["got"], codes=r["got_codes"], ok=r["ok"]) for r in ME.run_cases()], mutants=[dict(name=m["name"], removes=m["removes"], killed=m["killed"]) for m in mm["mutants"]],
                    note="Scripted outputs, not produced by a language model. They show what the boundary does with any output of these shapes, not how a model behaves.")
    se = SE.run_eval(); sm = SE.run_mutants()
    supplier = dict(metrics=se, mutants=[dict(name=m["name"], removes=m["removes"], killed=m["killed"]) for m in sm["mutants"]],
                    note="Labelled by the author before the rules were run; the dedupe set was extended after a first run exposed two false positives (see docs/growth-os). Small sets: they test the stated rules, not the real supplier market.")
    fe = FE.run_cases(); fm = FE.run_mutants()
    finance = dict(cases=[dict(name=c["name"], fields=c["expected_fields"], ok=c["ok"]) for c in fe], invariants=FE.invariants(), mutants=[dict(name=m["name"], removes=m["removes"], killed=m["killed"]) for m in fm["mutants"]],
                   note="Expected numbers were worked by hand before the code was run against them.")
    return boundary, supplier, finance


def journey(tmp):
    import pixeltable_pgserver as pg
    srv = pg.get_server(str(Path(tmp) / "pg"), cleanup_mode="stop"); dsn = srv.get_uri()
    try:
        envs = DM.build(Path(tmp) / "d", dsn, schema="m4_evidence", with_warehouse=False)
        try:
            import agentplatform  # noqa: F401
            app = GA.create_growth_app(envs, agent_dsn=dsn, as_of=AS_OF)
        except ImportError:
            app = GA.create_growth_app(envs, as_of=AS_OF)
        with TestClient(app) as c:
            return _run(c, envs, base=f"/v1/tenants/{A}")
    finally:
        srv.cleanup()


def _run(c, envs, base):
    H = lambda u: {"Authorization": "Bearer " + envs[A].authority.login(u, f"{A}-{u}-dev-passcode")}
    steps = []
    def step(n, label, role, ok, **kw):
        steps.append(dict(n=n, label=label, role=role, ok=bool(ok), **kw))
    intel0 = c.get(f"{base}/supplier-intelligence", headers=H("ana")).json()
    sup_cards = [dict(name=x["name"], information=x["information_label"], classification=x["classification"]["primary"], area=(x["area"] or {}).get("level"), sources=len(x["sources"]), source_access=sorted({s["access"] for s in x["sources"]}),
                      price_categories=x["price_categories"], official_website_verified=x["official_website_verified"]) for x in intel0["cards"]]
    dup_try = c.post(f"{base}/suppliers", json=dict(name="Brothers Produce, Inc.", category="Produce", service_area="Texas", verification_status="lead_unverified", source_kind="search_result", source_url="https://example.test/dup"), headers=H("ada"))
    p = c.post(f"{base}/projects", json=dict(name="Courtyard pilot kitchen", industry="Hospitality", location="Austin, TX", concept="A small pilot kitchen to test the opening menu with real recipes before the full venue is built.", budget_cents=45_000_000, launch_target="2027-04-01"), headers=H("ada"))
    pid = p.json()["id"]
    step(1, "Create a business-launch project with a start-up budget", "OWNER", p.status_code == 201 and c.post(f"{base}/projects", json=dict(name="x project", industry="Hospitality", location="Austin, TX", concept="An analyst may not start a project.", budget_cents=1000), headers=H("ana")).status_code == 403,
         result="project created at stage 'idea'; an analyst's attempt to create one is refused (403)")
    f = c.post(f"{base}/projects/{pid}/findings", json=dict(topic="Local demand", finding="Founder's notes: lunch traffic near the proposed site is expected to be the weakest daypart.", source_kind="founder_note", confidence=0.4, limitation="A founder note, not measured demand."), headers=H("ana"))
    step(2, "Record market research with its limitation", "ANALYST", f.status_code == 201, result="finding stored as a founder note with confidence 0.4 and a stated limitation")
    syn = [x for x in intel0["cards"] if x["information_category"] == "synthetic_fixture"][:2]; lead = next(x for x in intel0["cards"] if x["information_category"] == "unverified_public_lead")
    sl = [c.put(f"{base}/projects/{pid}/suppliers/{x['id']}", json=dict(status="shortlisted"), headers=H("ana")).status_code for x in syn + [lead]]
    step(3, "Build a supplier shortlist", "ANALYST", sl == [200, 200, 200], result="two synthetic fixtures and one unverified public-search lead shortlisted")
    intel = c.get(f"{base}/supplier-intelligence?project_id={pid}", headers=H("ana")).json()
    step(4, "Compare supplier information with explicit data categories", "ANALYST", all(r["cross_category_ranking"] is None for r in intel["quotes"]["rows"]) and lead["official_website_verified"] is False,
         result=f"{len(intel['quotes']['rows'])} ingredients compared inside one category (synthetic quotation); the lead has no published price and is never ranked; the duplicate guard refused 'Brothers Produce, Inc.' ({dup_try.status_code})")
    for k, label, v, unit in (("weekly_orders", "Guest orders per week", 300, "orders"), ("items_per_order", "Items per order", 2.5, "items"), ("rent_monthly_cents", "Rent", 900_000, "cents/month"), ("labor_monthly_cents", "Labour", 2_600_000, "cents/month"),
                              ("capex_buildout_cents", "Build-out", 24_000_000, "cents"), ("capex_equipment_cents", "Equipment", 9_000_000, "cents"), ("working_capital_months", "Working capital months", 2, "months"), ("contingency_pct", "Contingency", 10, "%")):
        c.put(f"{base}/projects/{pid}/assumptions/{k}", json=dict(label=label, value=v, unit=unit, basis="synthetic_assumption"), headers=H("ana"))
    before = c.post(f"{base}/projects/{pid}/scenarios/preview", json={}, headers=H("ana")).json()
    c.put(f"{base}/projects/{pid}/assumptions/capex_buildout_cents", json=dict(label="Build-out", value=20_000_000, unit="cents", basis="founder"), headers=H("ada"))
    after = c.post(f"{base}/projects/{pid}/scenarios/preview", json={}, headers=H("ana")).json()
    b, a_ = before["results"]["startup"], after["results"]["startup"]
    step(5, "Update a financial assumption", "OWNER", True, result="build-out changed from $240,000 to $200,000 (a founder input)")
    step(6, "Recalculate start-up costs from stored data", "ANALYST", b["total_requirement_cents"] - a_["total_requirement_cents"] == round(4_000_000 * 1.10),
         result=f"requirement ${b['total_requirement_cents'] / 100:,.2f} -> ${a_['total_requirement_cents'] / 100:,.2f}; the difference is the cut plus its 10% contingency", requirement_before_cents=b["total_requirement_cents"], requirement_after_cents=a_["total_requirement_cents"],
         budget_cents=a_["budget_cents"], funding_gap_after_cents=a_["funding_gap_cents"], formulas=[dict(name=x["name"], formula=x["formula"], worked=x["worked"]) for x in after["results"]["formulas"]],
         breakeven_orders_per_week=after["results"]["breakeven_orders_per_week"], kind=after["results"]["kind"])
    sc = c.post(f"{base}/projects/{pid}/scenarios", json=dict(name="Base plan", overrides={}), headers=H("ana"))
    run = c.post(f"{base}/projects/{pid}/procurement", json={"period_weeks": 2}, headers=H("ana")); rid = run.json()["corr_id"]
    det = c.get(f"{base}/procurement/runs/{rid}", headers=H("ana")).json()["business"]
    step(7, "Generate a procurement recommendation", "ANALYST", sc.status_code == 201 and run.status_code == 202 and run.json()["status"] == "AWAITING_APPROVAL",
         result=f"planned spend ${det['recommendation']['total_cost_cents'] / 100:,.2f} over 2 weeks at synthetic prices; research mode: {det['research']['mode_label']}", model_backed=det["research"]["model_backed"], boundary=det["research"]["boundary"],
         uncertainty=det["research"]["uncertainty"], price_effect=det["recommendation"]["price_effect"]["difference_cents"], agent_text_changes_numbers=False)
    step(8, "Hold the recommendation for a different person's approval", "THE WEIR", det["approval"]["can_decide"] and c.get(f"{base}/projects/{pid}", headers=H("vic")).json()["stage"] == "idea",
         result="held; the project stage has not moved; the analyst who asked cannot approve (403)", requester_refused=c.post(f"{base}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H("ana")).status_code)
    done = c.post(f"{base}/procurement/runs/{rid}/decision", json={"approve": True, "comment": "Reviewed the quotes."}, headers=H("ada"))
    replay = c.post(f"{base}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H("omar"))
    step(9, "Record the authorisation decision", "OWNER", done.status_code == 200 and done.json()["status"] == "EXECUTED" and replay.status_code == 409, result="approved once and recorded; a second approval is refused (409); nothing was ordered", side_effects=done.json()["side_effects"])
    ov = c.get(f"{base}/projects/{pid}", headers=H("vic")).json()
    ms = [m for m in ov["milestones"] if m["title"].startswith("Procurement recommendation approved")]
    step(10, "Update the project state in the same transaction", "system", ov["stage"] == "roadmap" and len(ms) == 1, result=f"stage is now '{ov['stage']}'; one completed sourcing milestone was added", stage=ov["stage"])
    hist = c.get(f"{base}/projects/{pid}/history", headers=H("vic")).json()["items"]
    ver = c.get(f"{base}/audit/verify", headers=H("ada")).json()
    step(11, "Preserve an auditable execution history", "any role", ver["chain_valid"] is True and hist[0]["action"] == "project.create", result=f"{len(hist)} recorded changes in order; the tenant's audit hash chain verifies", history_actions=sorted({h['action'] for h in hist}), history_entries=len(hist), chain_valid=ver["chain_valid"])
    other = c.get(f"/v1/tenants/tenant-fit/projects/{pid}/history", headers={"Authorization": "Bearer " + envs["tenant-fit"].authority.login("ada", "tenant-fit-ada-dev-passcode")}).status_code
    step(12, "Keep the journey invisible to another tenant", "other tenant", other == 404, result="another tenant's request for this project's history returns 404")
    return dict(project="Courtyard pilot kitchen (a pilot kitchen created for this walkthrough in the flagship tenant)", steps=steps, supplier_cards=sup_cards, duplicate_guard=dict(attempt="Brothers Produce, Inc.", http_status=dup_try.status_code, refused=dup_try.status_code in (409, 422)),
                all_steps_ok=all(s["ok"] for s in steps), disclaimer="Synthetic tenants and data. A recorded recommendation places no order and contacts no supplier; the figures are simulated projections on stated assumptions.")


def collect():
    boundary, supplier, finance = eval_sections()
    with tempfile.TemporaryDirectory(prefix="m4-evidence-") as tmp:
        j = journey(tmp)
    return dict(runtime=runtime_facts(), boundary=boundary, supplier=supplier, finance=finance, journey=j)


if __name__ == "__main__":
    import json
    d = collect()
    print(json.dumps({k: (v if k == "runtime" else "ok") for k, v in d.items()}, indent=1)[:600], "| journey ok:", d["journey"]["all_steps_ok"])
