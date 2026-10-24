"""Milestone 5 evidence: two businesses on one platform. Runs the real evaluations (supplier held-out vs dev, financial held-out vs dev, generalisation, authorisation matrix with policy-widening mutants), records the supplier research
tiers and the model-execution status, drives a fresh fitness-studio launch through the SAME HTTP API, and compares what the two tenants share. Deterministic fields only (no ids, timestamps), so two exports of the same code are
identical. Called by export_growth_evidence.py; also runnable alone: python tools/m5_evidence.py"""
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

from fastapi.testclient import TestClient  # noqa: E402

from nasha_lab.growth import (api as GA, authz_eval as AZ, demo as DM, financial_eval as FE, financial_heldout as FH, industry_eval as IE, industry_profiles as PF, schema as SC, supplier_eval as SE,  # noqa: E402
                              supplier_heldout as SH, supplier_intel as SI)

AS_OF = date(2026, 10, 23)
A, B = "tenant-nasha", "tenant-fit"
DATA = LAB / "nasha_lab" / "growth" / "data" / "real_suppliers.json"


def model_status():
    p = LAB / "results" / "model-validation" / "live.json"
    live = json.loads(p.read_text()) if p.exists() else None
    return dict(model_execution_recorded=bool(live and live.get("executed")), harness="tools/live_model_validation.py", live_test="tests/test_growth_model_live.py (skipped here; reported unverified by the release gate)",
                last_probe=None if not live else {k: live.get(k) for k in ("executed", "runtime_base_url", "runtime_reachable", "reason")},
                decision_needed=None if live and live.get("executed") else (live or {}).get("decision_needed"),
                note="No language model produced any output in this repository. The offline provider is a heuristic, scripted boundary cases are test doubles, and nothing here is presented as model behaviour.")


def supplier_research():
    d = json.loads(DATA.read_text())
    tiers = {}
    for s in d["suppliers"]:
        t = SI.evidence_tier(dict(sources=[dict(kind=k, url=u, claim=c, access=("search_snippet" if k != "encyclopedia" else "search_snippet")) for k, u, c in s["sources"]], website_url=None, verification_status="lead_unverified"))
        tiers[t] = tiers.get(t, 0) + 1
    return dict(researched_on=d["researched_on"], method=d["method"], suppliers=len(d["suppliers"]), shortlisted=sum(bool(s["shortlist"]) for s in d["suppliers"]), verified_from_primary_page=0,
                evidence_tiers=tiers, blocked_hosts=d["blocked_hosts"], blocked_host_count=len(d["blocked_hosts"]),
                records=[dict(name=s["name"], category=s["category"], service_area=s["service_area"], shortlisted=bool(s["shortlist"]), sources=[dict(kind=k, url=u) for k, u, _ in s["sources"]], limitations=s["limitations"]) for s in d["suppliers"]],
                note="Primary-source verification was impossible in this environment (the network proxy refuses every supplier host). Every record is a research lead with its evidence tier shown; none is marked verified, no contact was made, no price recorded.")


def evaluations():
    se = SE.run_eval(); sm = SE.run_mutants(); ho = SH.run()
    dev = dict(dedupe={k: se["dedupe"][k] for k in ("cases", "precision", "recall")} if "dedupe" in se else None)
    fe = FE.run_cases(); fm = FE.run_mutants(); fh = FH.run()
    ge = IE.run_cases(); gm = IE.run_mutants()
    return dict(
        supplier=dict(development=se, development_mutants=[dict(name=m["name"], killed=m["killed"]) for m in sm["mutants"]], held_out=ho,
                      note="The held-out set was written after the rules were frozen (commit %s) and was not used to tune them. It reports its misses; it is small and author-labelled, so it supports no general-accuracy claim." % SH.FROZEN_AT),
        financial=dict(development=dict(cases=len(fe), correct=sum(c["ok"] for c in fe), mutants=[dict(name=m["name"], killed=m["killed"]) for m in fm["mutants"]]),
                       held_out=dict(cases=len(fh), correct=sum(c["ok"] for c in fh), fields_checked=sum(c["fields"] for c in fh), details=[dict(name=c["name"], ok=c["ok"]) for c in fh]),
                       note="Expected values were worked by hand before the code ran against them."),
        generalisation=dict(cases=len(ge), correct=sum(bool(v) for v in ge.values()), names=sorted(ge), mutants=[dict(name=m["name"], removes=m["removes"], killed=m["killed"]) for m in gm["mutants"]]))


def _journey(c, envs):
    FIT = f"/v1/tenants/{B}"
    H = lambda u: {"Authorization": "Bearer " + envs[B].authority.login(u, f"{B}-{u}-dev-passcode")}
    steps = []
    def step(n, label, role, ok, result, **kw):
        steps.append(dict(n=n, label=label, role=role, ok=bool(ok), result=result, **kw))
    body = dict(name="Pilates annex", industry="Fitness", location="Cedar Park, TX", concept="A small reformer pilates annex for existing members, used to test the add-on before a larger build.", budget_cents=9_000_000)
    refused = c.post(f"{FIT}/projects", json=body, headers=H("ana")).status_code
    p = c.post(f"{FIT}/projects", json=body, headers=H("ada")); pid = p.json()["id"]
    step(1, "Create the studio's launch project with a start-up budget", "OWNER", p.status_code == 201 and refused == 403, "created at stage 'idea'; an analyst's attempt is refused (403)")
    req = dict(ref="equip.spin-bike", name="Spin bike", kind="equipment", qty=6, unit="each", recurrence="one_time")
    viewer = c.post(f"{FIT}/projects/{pid}/requirements", json=req, headers=H("vic")).status_code
    r1 = c.post(f"{FIT}/projects/{pid}/requirements", json=req, headers=H("ana")); c.post(f"{FIT}/projects/{pid}/requirements", json=dict(ref="svc.towel-service", name="Towel service (per pickup)", kind="service", qty=1, unit="pickup", recurrence="per_week"), headers=H("ana"))
    c.put(f"{FIT}/requirements/{r1.json()['id']}", json={"qty": 4}, headers=H("ana"))
    step(2, "State equipment and service requirements (no recipes)", "ANALYST", viewer == 403 and r1.status_code == 201, "4 spin bikes (one-time) and weekly towel pickups; a viewer's attempt is refused (403)")
    for k, v in (("weekly_orders", 40), ("capex_equipment_cents", 600_000), ("working_capital_months", 1), ("contingency_pct", 5)):
        c.put(f"{FIT}/projects/{pid}/assumptions/{k}", json=dict(label=k.replace("_", " ").title(), value=v, unit="x", basis="synthetic_assumption"), headers=H("ana"))
    pv = c.post(f"{FIT}/projects/{pid}/scenarios/preview", json={}, headers=H("ana")).json()["results"]
    sc = c.post(f"{FIT}/projects/{pid}/scenarios", json=dict(name="Base", overrides={}), headers=H("ana"))
    step(3, "Calculate the financial scenario from stored assumptions", "ANALYST", sc.status_code == 201, f"start-up requirement ${pv['startup']['total_requirement_cents'] / 100:,.2f} against a $90,000.00 budget; formulas shown with worked values",
         total_requirement_cents=pv["startup"]["total_requirement_cents"], budget_cents=pv["startup"]["budget_cents"])
    run = c.post(f"{FIT}/projects/{pid}/procurement", json={"period_weeks": 2}, headers=H("ana")); rid = run.json()["corr_id"]
    det = c.get(f"{FIT}/procurement/runs/{rid}", headers=H("ana")).json()["business"]
    step(4, "Generate a procurement recommendation from requirements and supplier quotes", "ANALYST", run.status_code == 202 and det["recommendation"]["total_cost_cents"] == 4 * 94_500 + 2 * 23_500,
         f"planned spend ${det['recommendation']['total_cost_cents'] / 100:,.2f} (4 bikes at the cheapest quote + 2 weeks of pickups); research mode: {det['research']['mode_label']}; no recipe was used",
         total_cost_cents=det["recommendation"]["total_cost_cents"], model_backed=det["research"].get("model_backed", False), needs_from=det["recommendation"].get("needs_from"))
    own = c.post(f"{FIT}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H("ana")).status_code
    stage_before = c.get(f"{FIT}/projects/{pid}", headers=H("vic")).json()["stage"]
    step(5, "Hold the recommendation for a different person's approval", "THE WEIR", own == 403 and stage_before == "idea", "held; the requesting analyst cannot approve (403); the project stage has not moved")
    done = c.post(f"{FIT}/procurement/runs/{rid}/decision", json={"approve": True, "comment": "Reviewed the quotes."}, headers=H("ada"))
    replay = c.post(f"{FIT}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H("omar")).status_code
    step(6, "Record the human authorisation decision", "OWNER", done.json()["status"] == "EXECUTED" and replay == 409, "approved once and recorded; a second approval is refused (409); nothing was ordered")
    stage = c.get(f"{FIT}/projects/{pid}", headers=H("vic")).json()["stage"]
    step(7, "Move the project state in the same transaction", "system", stage == "roadmap", f"stage is now '{stage}'")
    hist = c.get(f"{FIT}/projects/{pid}/history", headers=H("vic")).json()["items"]; ver = c.get(f"{FIT}/audit/verify", headers=H("ada")).json()
    step(8, "Preserve an auditable history", "any role", ver["chain_valid"] is True and hist[0]["action"] == "project.create", f"{len(hist)} recorded changes in order; the tenant's audit hash chain verifies")
    cross = c.get(f"/v1/tenants/{A}/projects/{pid}/history", headers={"Authorization": "Bearer " + envs[A].authority.login("ada", f"{A}-ada-dev-passcode")}).status_code
    step(9, "Keep the journey invisible to the other business", "other tenant", cross == 404, "the flagship's request for this project's history returns 404")
    return dict(project="Pilates annex (created for this walkthrough in the Meridian Fitness tenant)", steps=steps, all_steps_ok=all(s["ok"] for s in steps))


def shared_architecture(dsn, schema):
    import psycopg
    rows = {}
    with psycopg.connect(dsn, autocommit=True) as con:
        con.execute(f"SET search_path TO {schema}")
        for t in sorted(SC.ALL_TENANT_TABLES):
            try:
                r = dict(con.execute(f"SELECT tenant_id, count(*) FROM {t} GROUP BY tenant_id").fetchall())
            except Exception:  # noqa: BLE001
                con.rollback(); continue
            rows[t] = {A: int(r.get(A, 0)), B: int(r.get(B, 0))}
        policies = con.execute("SELECT count(*) FROM pg_policies WHERE schemaname=%s", (schema,)).fetchone()[0]
    both = sorted(t for t, v in rows.items() if v[A] and v[B])
    pa, pb = PF.PROFILES["hospitality"], PF.PROFILES["fitness"]
    differing = sorted(k for k in pa if pa[k] != pb[k])
    return dict(tables_in_schema=len(rows), tables_used_by_both_businesses=len(both), tables_both=both, row_counts=rows, rls_policies=policies,
                code_paths_shared=["service.py (authorisation POLICY)", "launch.py (projects, requirements, scenarios)", "procurement.py", "launch_workflow.py (THE WEIR flow)", "financials.py", "supplier_intel.py", "audit (hash-chained per tenant)"],
                configuration_that_differs=differing, profile_keys=dict(hospitality=pa["needs"], fitness=pb["needs"]), migrations=sorted(SC.MIGRATIONS) if hasattr(SC, "MIGRATIONS") else None,
                note="Everything in 'code_paths_shared' runs unchanged for both tenants. The only industry-specific inputs are the profile fields listed in 'configuration_that_differs', the seed data, and the supplier classification vocabulary.")


def collect():
    ev = evaluations()
    with tempfile.TemporaryDirectory(prefix="m5-evidence-") as tmp:
        import pixeltable_pgserver as pg
        srv = pg.get_server(str(Path(tmp) / "pg"), cleanup_mode="stop"); dsn = srv.get_uri()
        try:
            envs = DM.build(Path(tmp) / "d", dsn, schema="m5_evidence", with_warehouse=False)
            try:
                import agentplatform  # noqa: F401
                app = GA.create_growth_app(envs, agent_dsn=dsn, as_of=AS_OF)
            except ImportError:
                app = GA.create_growth_app(envs, as_of=AS_OF)
            with TestClient(app) as c:
                journey = _journey(c, envs)
                rows = []
                for t in (A, B):
                    h = {"Authorization": "Bearer " + envs[t].authority.login("vic", f"{t}-vic-dev-passcode")}
                    pid = c.get(f"/v1/tenants/{t}/projects", headers=h).json()["items"][0]["id"]; sid = c.get(f"/v1/tenants/{t}/suppliers", headers=h).json()["items"][0]["id"]
                    rows += AZ.run(c, envs, t, pid, sid)
                base = AZ.summary(rows); muts = []
                for name, (action, role) in AZ.MUTANTS.items():
                    with AZ.widened(action, role):
                        mrows = []
                        for t in (A, B):
                            h = {"Authorization": "Bearer " + envs[t].authority.login("vic", f"{t}-vic-dev-passcode")}
                            pid = c.get(f"/v1/tenants/{t}/projects", headers=h).json()["items"][0]["id"]; sid = c.get(f"/v1/tenants/{t}/suppliers", headers=h).json()["items"][0]["id"]
                            mrows += AZ.run(c, envs, t, pid, sid)
                    s = AZ.summary(mrows); muts.append(dict(name=name, widens=f"{action} to {role}", killed=bool(s["wrong"]), first_catch=(s["wrong"] or [None])[0]))
                authz = dict(operations=sorted(AZ.EXPECTED), roles=AZ.USERS, summary={k: v for k, v in base.items()}, mutants=muts, note="Every (operation, role) pair is exercised in BOTH businesses against a table written from the intended policy.")
            arch = shared_architecture(dsn, "m5_evidence")
        finally:
            srv.cleanup()
    return dict(model=model_status(), supplier_research=supplier_research(), evaluations=ev, authorization=authz, journey=journey, architecture=arch)


if __name__ == "__main__":
    d = collect()
    print("journey ok:", d["journey"]["all_steps_ok"], "| authz:", d["authorization"]["summary"]["correct"], "/", d["authorization"]["summary"]["checks"], "| mutants killed:", sum(m["killed"] for m in d["authorization"]["mutants"]),
          "| shared tables:", d["architecture"]["tables_used_by_both_businesses"], "| model executed:", d["model"]["model_execution_recorded"])
