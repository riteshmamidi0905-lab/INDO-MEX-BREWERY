#!/usr/bin/env python3
"""Export RECORDED Growth OS evidence for the portfolio: the capability tracker, a stage-transition matrix and cross-tenant probes actually executed against PostgreSQL, and the control-mutation results.
Nothing is hand-written; the script exits non-zero if any recorded expectation fails. Output: lab/portfolio/growth-os-evidence.json.   cd lab && python3 tools/export_growth_evidence.py"""
import importlib.util
import itertools
import json
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
import psycopg  # noqa: E402
from nasha_lab.governed import tenants as T  # noqa: E402
from nasha_lab.growth import financials as F, schema as S, seed as SD, service as SV, testing as TT  # noqa: E402
from nasha_lab.warehouse import pg_hardening as H  # noqa: E402

SCHEMA = "growth_export"
ORACLE = {("new", "qualified"), ("new", "lost"), ("qualified", "proposal"), ("qualified", "lost"), ("proposal", "negotiation"), ("proposal", "lost"), ("negotiation", "won"), ("negotiation", "lost"), ("negotiation", "proposal")}


def main():
    import pixeltable_pgserver as pg
    tmp = Path(tempfile.mkdtemp(prefix="growth-evidence-"))
    srv = pg.get_server(str(tmp / "pg"), cleanup_mode="stop"); dsn = srv.get_uri()
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'CREATE SCHEMA "{SCHEMA}"')
    H.migrate(dsn, SCHEMA, specs=S.migrations(SCHEMA))
    users = [("ada", "Ada (synthetic owner)", "OWNER"), ("sam", "Sam (synthetic sales)", "SALES"), ("mia", "Mia (synthetic marketing)", "MARKETING"), ("vic", "Vic (synthetic viewer)", "VIEWER")]
    SV.provision(dsn, SCHEMA, "tenant-nasha", "NASHA — The Courtyard (synthetic hospitality brand)", "hospitality", users)
    SV.provision(dsn, SCHEMA, "tenant-fit", "Meridian Fitness (synthetic studio)", "fitness", users)
    a_env, _ = T.default_pair(tmp / "wh")
    a, b = SV.GrowthService(dsn, SCHEMA, "tenant-nasha", "ada"), SV.GrowthService(dsn, SCHEMA, "tenant-fit", "ada")
    SD.seed_nasha(a, a_env.warehouse); SD.seed_fitness(b)
    # ---- stage matrix (each pair attempted on a fresh opportunity)
    acc = a.read("SELECT id FROM accounts LIMIT 1")[0][0]
    stages = ["new", "qualified", "proposal", "negotiation", "won", "lost"]
    matrix, ok_all = [], True
    for frm, to in itertools.product(stages, stages):
        if frm == to:
            continue
        oid = a._id("opp")
        with TT.audited(a, "opportunities", oid):
            a.con.execute("INSERT INTO opportunities (tenant_id,id,account_id,name,stage,amount_cents) VALUES (%s,%s,%s,'probe',%s,1)", (a.tenant, oid, acc, frm))
        try:
            with TT.audited(a, "opportunities", oid):
                a.con.execute("UPDATE opportunities SET stage=%s WHERE tenant_id=%s AND id=%s", (to, a.tenant, oid))
            allowed, msg = True, ""
        except psycopg.errors.CheckViolation as e:
            allowed, msg = False, str(e).splitlines()[0]
        matrix.append(dict(frm=frm, to=to, allowed=allowed, database_message=msg, oracle_allowed=((frm, to) in ORACLE)))
        ok_all &= allowed == ((frm, to) in ORACLE)
    # ---- isolation probes
    tables = ["accounts", "contacts", "leads", "segments", "products", "prices", "audit_log", "entity_versions"]
    probes = []
    nosetting = psycopg.connect(SV.app_dsn(dsn), autocommit=True); nosetting.execute(f'SET search_path TO "{SCHEMA}", pg_catalog, public')
    for t in tables:
        own_a = a.con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        own_b = b.con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        key = "seq" if t == "audit_log" else "id" if t != "entity_versions" else "entity_id"
        ids_b = [r[0] for r in b.con.execute(f"SELECT {key} FROM {t}")]
        a_sees_b = a.con.execute(f"SELECT count(*) FROM {t} WHERE tenant_id=%s", ("tenant-fit",)).fetchone()[0]
        a_sees_b_ids = a.con.execute(f"SELECT count(*) FROM {t} WHERE {key} = ANY(%s) AND tenant_id <> %s", (ids_b, "tenant-nasha")).fetchone()[0]
        none = nosetting.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        probes.append(dict(table=t, tenant_a_rows=own_a, tenant_b_rows=own_b, a_sees_b_rows=a_sees_b, a_sees_b_by_id=a_sees_b_ids, no_tenant_setting_rows=none))
        ok_all &= a_sees_b == 0 and a_sees_b_ids == 0 and none == 0 and own_a > 0 and own_b > 0
    attempts = []
    for label, sql, params, exc in [
        ("insert a row for the other tenant", "INSERT INTO accounts (tenant_id,id,name,kind) VALUES ('tenant-fit','acc-forged','forged','business')", (), psycopg.errors.InsufficientPrivilege),
        ("reference the other tenant's account in a contact", "INSERT INTO contacts (tenant_id,id,account_id,full_name,email) VALUES ('tenant-nasha','con-x',%s,'x','x@example.invalid')", (b.read("SELECT id FROM accounts LIMIT 1")[0][0],), psycopg.errors.ForeignKeyViolation),
        ("create a tenant from the application role", "INSERT INTO tenants (tenant_id,name,vertical) VALUES ('tenant-evil','x','y')", (), psycopg.errors.InsufficientPrivilege),
        ("delete from the audit log", "DELETE FROM audit_log", (), psycopg.errors.InsufficientPrivilege)]:
        try:
            a.con.execute(sql, params); res = "ALLOWED (failure)"; ok_all = False
        except exc as e:
            res = f"refused: {type(e).__name__}"
        attempts.append(dict(attempt=label, result=res))
    # ---- audit guard: a raw, unaudited mutation of every guarded table is refused by the database
    guard = []
    for tbl, sql in [("accounts", "INSERT INTO accounts (tenant_id,id,name,kind) VALUES ('tenant-nasha','raw-1','Raw','business')"), ("products", "INSERT INTO products (tenant_id,id,name,kind,unit_cost_cents) VALUES ('tenant-nasha','raw-2','Raw','dish',1)"),
                     ("leads", "UPDATE leads SET score=1 WHERE tenant_id='tenant-nasha'"), ("contacts", "UPDATE contacts SET job_title='x' WHERE tenant_id='tenant-nasha'"), ("opportunities", "UPDATE opportunities SET amount_cents=amount_cents+1 WHERE tenant_id='tenant-nasha' AND stage='new'")]:
        try:
            a.con.execute(sql); res = "ACCEPTED (failure)"; ok_all = False
        except psycopg.errors.IntegrityConstraintViolation as e:
            res = "refused: no audit evidence in this transaction" if "no audit evidence" in str(e) else "refused: " + str(e).splitlines()[0]
        guard.append(dict(table=tbl, statement_kind=sql.split()[0], result=res))
    # ---- control mutants (the same probes/mutants the test suite runs)
    spec = importlib.util.spec_from_file_location("gmut", LAB / "tests/test_growth_mutations.py")
    gm = importlib.util.module_from_spec(spec); sys.modules["gmut"] = gm; spec.loader.exec_module(gm)
    mutants = []
    for i, (name, probe, sql, patch) in enumerate(gm.MUTANTS):
        sc = f"growth_exp_m{i}"; gm.build(dsn, sc)
        for st in (sql.split("; ") if sql else []):
            gm.admin(dsn, sc, st)
        if patch:
            with patch():
                held = probe(dsn, sc)
        else:
            held = probe(dsn, sc)
        mutants.append(dict(mutant=name, probe=probe.__name__, killed=(held is False)))
        ok_all &= held is False
    # ---- governed lead-qualification workflow: recorded runs on the real THE WEIR gateway, hand-oracle evaluation and the 8 workflow-level mutants
    spec = importlib.util.spec_from_file_location("gwe", LAB / "tests/test_growth_workflow_eval.py")
    gwe = importlib.util.module_from_spec(spec); sys.modules["gwe"] = gwe; spec.loader.exec_module(gwe)
    W = gwe.World(dsn, "growth_exp_wf", tmp / "wfroot"); wf = W.wf["tenant-nasha"]
    lead, contact = W.lead()
    before = dict(status=W.status(lead), qualification_audit_rows=W.applied(lead))
    r = wf.run(W.tok("sam"), lead, idempotency_key="export-happy", request_id="req-export-1")
    held = dict(status=r["status"], approval_id=r["approval_id"], recommendation_status=r["recommendation"]["proposed_status"], score=r["recommendation"]["score"], lead_status_while_held=W.status(lead), qualification_audit_rows=W.applied(lead))
    self_approve = wf.decide(r["corr_id"], W.tok("sam"), True)
    d = wf.decide(r["corr_id"], W.tok("ada"), True, "evidence reviewed")
    replay = wf.decide(r["corr_id"], W.tok("ada"), True)
    arow = W.sql("SELECT actor, detail FROM audit_log WHERE action='lead.qualification_applied' AND entity_id=%s", (lead,))
    happy = dict(corr_id=r["corr_id"], tenant="tenant-nasha", before=before, held=held, requester_self_approval=dict(status=self_approve["status"], failure=self_approve.get("failure")),
                 approved=dict(status=d["status"], side_effects=d["side_effects"]), replay_after_execution=dict(status=replay["status"], failure=replay.get("failure")),
                 lead_after=dict(status=W.status(lead), score=W.sql("SELECT score FROM leads WHERE id=%s", (lead,))[0][0]), audit=dict(actor=arow[0][0], approved_by=arow[0][1]["approved_by"], approval_matches=arow[0][1]["approval"] == r["approval_id"], rows=len(arow)),
                 emails_or_messages_created=W.sql("SELECT count(*) FROM activities WHERE contact_id=%s", (contact,))[0][0], trace=wf.trace(r["corr_id"]))
    ok_all &= happy["lead_after"]["status"] == "qualified" and happy["audit"]["rows"] == 1 and happy["emails_or_messages_created"] == 0 and happy["approved"]["status"] == "EXECUTED" and happy["held"]["lead_status_while_held"] == "new"
    viewer = wf.run(W.tok("vic"), W.lead()[0]); sup, _ = W.lead(suppress_directly=True); supp = wf.run(W.tok("sam"), sup)
    l2, _ = W.lead(); r2 = wf.run(W.tok("sam"), l2); rej = wf.decide(r2["corr_id"], W.tok("ada"), False, "not convinced")
    other, _ = W.lead(tenant="tenant-meridian"); xt = wf.run(W.tok("sam"), other)
    refusals = [dict(case="viewer starts a qualification", status=viewer["status"], failure=viewer.get("failure")), dict(case="suppressed contact", status=supp["status"], failure=supp.get("failure")),
                dict(case="human rejects the proposal", status=rej["status"], lead_status=W.status(l2)), dict(case="lead id from another tenant", status=xt["status"], failure=xt.get("failure"))]
    ok_all &= viewer["status"] != "AWAITING_APPROVAL" and supp.get("failure") == "SUPPRESSED_CONTACT" and rej["status"] == "REJECTED" and W.status(l2) == "new" and xt["status"] == "DENIED"
    oracle_rows = []
    for name, sg, score, status in gwe.ORACLE:
        lx, _ = W.lead(sg); rec = wf.run(W.tok("sam"), lx)["recommendation"]
        oracle_rows.append(dict(case=name, expected_score=score, expected_status=status, proposed_score=rec["score"], proposed_status=rec["proposed_status"], match=(rec["score"], rec["proposed_status"]) == (score, status)))
        ok_all &= oracle_rows[-1]["match"]
    W.close()
    wf_mutants = []
    for i, (name, probe, sql, patch) in enumerate(gwe.MUTANTS):
        Wm = gwe.World(dsn, f"growth_exp_wm{i}", tmp / f"wm{i}")
        for st in (sql.split("; ") if sql else []):
            Wm.sql(st)
        with patch():
            held_m = probe(Wm)
        Wm.close()
        wf_mutants.append(dict(mutant=name, probe=probe.__name__, killed=(held_m is False)))
        ok_all &= held_m is False
    workflow = dict(name="governed_lead_qualification", happy_path=happy, refusals=refusals, oracle_evaluation=oracle_rows, mutants=wf_mutants)
    # ---- launch workspace: recorded agent-assisted procurement run, refusals, financial scenario, supplier honesty, launch mutants
    spec = importlib.util.spec_from_file_location("gle", LAB / "tests/test_growth_launch_eval.py")
    gle = importlib.util.module_from_spec(spec); sys.modules["gle"] = gle; spec.loader.exec_module(gle)
    from nasha_lab.growth import agent_research as AR  # noqa: E402
    try:
        import agentplatform  # noqa: F401
        agent = AR.SupplierResearchAgent(dsn, "tenant-nasha", tmp / "lab-agent")
    except ImportError:
        agent = None
    L = gle.Lab(dsn, tmp / "launchroot", agent=agent)
    lw = L.wf
    r1 = lw.run(L.tok("ana"), L.pid, 4, idempotency_key="export-proc-1", request_id="req-export-proc")
    held = dict(status=r1["status"], agent_mode=r1["agent_mode"], total_cost_cents=r1["total_cost_cents"], recorded_while_held=L.recorded(r1["corr_id"]))
    analyst_try = lw.decide(r1["corr_id"], L.tok("ana"), True); maker = None
    own = lw.run(L.tok("ada"), L.pid, 2); maker = lw.decide(own["corr_id"], L.tok("ada"), True)
    done = lw.decide(r1["corr_id"], L.tok("ada"), True, "reviewed")
    replay = lw.decide(r1["corr_id"], L.tok("omar"), True)
    run1 = lw.status(r1["corr_id"]); sales = lw.run(L.tok("sam"), L.pid, 2); vic = lw.run(L.tok("vic"), L.pid, 2)
    audit = L.sql("SELECT actor, detail FROM audit_log WHERE action='procurement.record' AND entity_id=%s", (r1["corr_id"],))
    s_an = SV.GrowthService(dsn, L.schema, "tenant-nasha", "ana")
    prev = s_an.preview_scenario(L.pid); cmp = F.compare([("Stored assumptions", prev["inputs"]), ("Prices +5%", s_an.scenario_inputs(L.pid, {"price_change_pct": 0.05})), ("Ingredient costs +20%", s_an.scenario_inputs(L.pid, {"cost_change_pct": 0.2}))])
    directory = s_an.supplier_directory(gle.AS_OF, L.pid); offers = s_an.offer_economics()
    ov = s_an.project_overview(L.pid)
    grid = []
    base_orders = next(a["value"] for a in ov["assumptions"] if a["key"] == "weekly_orders")
    for pc in (-0.10, -0.05, 0.0, 0.05, 0.10):
        for cc in (0.0, 0.10, 0.20, 0.30):
            for oc in (-0.20, -0.10, 0.0, 0.10, 0.20):
                r_ = F.compute(s_an.scenario_inputs(L.pid, {"price_change_pct": pc, "cost_change_pct": cc, "weekly_orders": base_orders * (1 + oc)}))
                grid.append(dict(price_change_pct=round(100 * pc), cost_change_pct=round(100 * cc), orders_change_pct=round(100 * oc), weekly_orders=round(base_orders * (1 + oc)), revenue_cents=r_["revenue_cents"], gross_margin=r_["gross_margin"],
                                 contribution_margin=r_["contribution_margin"], operating_profit_monthly_cents=r_["operating_profit_monthly_cents"], breakeven_orders_per_week=r_["breakeven_orders_per_week"], payback_months=r_["payback_months"]))
    s_an.close()
    by_status = {}
    for sp in directory:
        by_status[sp["verification_status"]] = by_status.get(sp["verification_status"], 0) + 1
    launch_mut = []
    for name, probe, sql, patch in gle.MUTANTS:
        lab_m = gle.Lab(dsn, tmp / "lm", agent=None)
        try:
            if sql:
                for (cn,) in lab_m.sql("SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass AND contype='c' AND pg_get_constraintdef(oid) LIKE %s", (f'"{lab_m.schema}".suppliers', "%contact_channel%")):
                    lab_m.sql(f'ALTER TABLE "{lab_m.schema}".suppliers DROP CONSTRAINT "{cn}"')
            with (patch() if patch else __import__("contextlib").nullcontext()):
                killed = probe(lab_m) is False
        finally:
            lab_m.close()
        launch_mut.append(dict(mutant=name, probe=probe.__name__, killed=killed)); ok_all &= killed
    ok_all &= held["status"] == "AWAITING_APPROVAL" and held["recorded_while_held"] == 0 and done["status"] == "EXECUTED" and len(audit) == 1 and replay["failure"] == "APPROVAL_REPLAY" and analyst_try["failure"] == "ROLE_DENIED" and maker["failure"] == "MAKER_CHECKER" and sales["status"] == "BLOCKED"
    ok_all &= all(sp["verification_status"] in ("synthetic_fixture", "lead_unverified") for sp in directory) and not any(sp["verified_on"] for sp in directory)
    items_ = sorted([i for i in run1["items"]["items"] if i["chosen"]], key=lambda i: -i["chosen"]["cost_cents"])[:14]
    walk = dict(project=dict(name=ov["name"], industry=ov["industry"], location=ov["location"], concept=ov["concept"], budget_cents=ov["budget_cents"], launch_target=ov["launch_target"], stage=ov["stage"], basis=ov["basis"],
                             assumptions=[dict(label=a["label"], value=a["value"], unit=a["unit"], basis=a["basis"]) for a in ov["assumptions"]], milestones=[dict(title=m["title"], phase=m["phase"], due=m["due"], status=m["status"]) for m in ov["milestones"]]),
                findings=[dict(topic=f["topic"], finding=f["finding"], source_kind=f["source_kind"], source_url=f["source_url"], retrieved_on=f["retrieved_on"], confidence=f["confidence"], limitation=f["limitation"]) for f in ov["findings"]],
                suppliers=[dict(name=sp["name"], category=sp["category"], service_area=sp["service_area"], verification_status=sp["verification_status"], freshness=sp["freshness"], source_kind=sp["source_kind"], source_url=sp["source_url"], website_verified=bool(sp["website_url"]),
                                contact=sp["contact_channel"], priced_items=sp["priced_products"], price_classes=sorted({p["price_class"] for p in sp["products"]})) for sp in directory],
                financial_grid=grid, base_weekly_orders=base_orders,
                procurement_lines=[dict(ingredient=i["ingredient"], need=i["need_qty"], unit=i["unit"], supplier=i["chosen"]["supplier"], buy_qty=i["chosen"]["buy_qty"], cost_cents=i["chosen"]["cost_cents"], lead_days=i["chosen"]["lead_days"], next_best=i["runner_up"]) for i in items_],
                agent_claims=[c["text"] for c in run1["research"]["report"]["claims"]], flags=[f["message"] for f in run1["items"]["flags"]], replenishment=run1["items"]["replenishment"][:8])
    launch = dict(name="governed_procurement_recommendation", walkthrough=walk, agent_mode=run1["agent_mode"], model_tested=False, note="The agent is the Production AI Agent Platform engine with its offline heuristic provider (deterministic; not a language model). No language-model provider was run.",
                  held=held, refusals=[dict(case="analyst tries to approve", failure=analyst_try.get("failure")), dict(case="owner tries to approve their own request", failure=maker.get("failure")), dict(case="sales requests a recommendation", status=sales["status"], failure=sales.get("failure")),
                                       dict(case="viewer requests a recommendation", status=vic["status"], failure=vic.get("failure")), dict(case="approval used a second time", failure=replay.get("failure"))],
                  approved=dict(status=done["status"], side_effects=done["side_effects"]), audit=dict(actor=audit[0][0], approved_by=audit[0][1]["approved_by"], approval_matches=audit[0][1]["approval"] == r1["approval_id"], rows=len(audit)),
                  research=dict(mode=run1["research"]["mode"], claims=len(run1["research"]["report"]["claims"]), rejected=bool(run1["research"]["rejected_agent_output"]), platform_verification=run1["research"].get("verification")),
                  recommendation=dict(period_weeks=run1["items"]["period_weeks"], total_cost_cents=run1["items"]["total_cost_cents"], suppliers=[dict(supplier=t["supplier"], cost_cents=t["cost_cents"], items=t["items"]) for t in run1["items"]["supplier_totals"]], flags=[f["kind"] for f in run1["items"]["flags"]]),
                  trace=lw.trace(r1["corr_id"]), financial=dict(kind="simulated", results={k: prev["results"][k] for k in ("units_per_month", "revenue_cents", "gross_margin", "contribution_margin", "fixed_costs_monthly_cents", "operating_profit_monthly_cents", "breakeven_units_per_month", "payback_months")},
                  sensitivity_price=prev["sensitivity"]["price"], compare=cmp, inputs_hash=prev["inputs_hash"], defaulted_assumptions=prev["inputs"]["defaulted_assumptions"]),
                  suppliers=dict(by_verification_status=by_status, real_leads=[dict(name=sp["name"], status=sp["verification_status"], source_url=sp["source_url"], prices_published=sp["priced_products"], contact=sp["contact_channel"], verified_on=sp["verified_on"]) for sp in directory if sp["source_kind"] == "search_result"], external_verification="INCOMPLETE"),
                  offers=[dict(name=o["name"], discount_pct=o["discount_pct"], margin_before=o["margin_before"], margin_after=o["margin_after"], uplift=o["breakeven_volume_uplift"]) for o in offers], mutants=launch_mut)
    L.close()
    caps = json.loads((LAB / "nasha_lab/growth/capabilities.json").read_text())
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=LAB).stdout.strip()
    ver = a.verify_audit(), b.verify_audit()
    out = dict(schema="growth-os-evidence/1", commit=commit, synthetic=True, pushed=False, notice="Synthetic tenants and data. NASHA Growth OS is a working name; this is a foundation, not a commercial product. Recorded from probes executed against PostgreSQL when exported.",
               postgres=a.con.execute("SHOW server_version").fetchone()[0], tenants=[dict(id="tenant-nasha", vertical="hospitality"), dict(id="tenant-fit", vertical="fitness")],
               tables=S.ALL_TENANT_TABLES, stage_matrix=matrix, isolation_probes=probes, privilege_attempts=attempts, mutants=mutants, audit_guard=guard, workflow=workflow, launch=launch, audit_chains_valid=dict(nasha=ver[0][0], fit=ver[1][0]),
               capabilities=caps["capabilities"], status_rules=caps["rules"], all_expectations_met=ok_all)
    (LAB / "portfolio/growth-os-evidence.json").write_text(json.dumps(out, indent=1, default=str))
    a.close(); b.close(); nosetting.close(); srv.cleanup()
    print("written; all expectations met:", ok_all, f"{len(matrix)} stage pairs, {len(probes)} tables probed, {sum(m['killed'] for m in mutants)}/{len(mutants)} control mutants and {sum(m['killed'] for m in wf_mutants)}/{len(wf_mutants)} workflow mutants and {sum(m['killed'] for m in launch_mut)}/{len(launch_mut)} launch mutants killed")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
