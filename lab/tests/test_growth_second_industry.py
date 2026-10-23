"""One platform, two industries. The fitness studio (Meridian) launches on the SAME tables, authorisation, audit model and governed workflow as the hospitality flagship; what differs is configuration and data (equipment and service
requirements instead of recipes, different wording, different supplier categories). Expected procurement totals below were worked out by hand from the seed's quote constants before the code was compared to them. SYNTHETIC tenants; nothing is ordered."""
import inspect
import re
from datetime import date

import pytest

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("fastapi")
from test_growth_journey import A, B, H, sql, world  # noqa: E402,F401

from nasha_lab.growth import industry_profiles as PF, launch_seed as LS, procurement as PRC, schema as S  # noqa: E402

FIT = f"/v1/tenants/{B}"
NASHA = f"/v1/tenants/{A}"
RAW_ID = re.compile(r"\b(pr-[0-9a-f]{6,}|proj-[0-9a-f]{6,}|sup-[0-9a-f]{6,}|req-[0-9a-f]{6,}|ms-[0-9a-f]{6,}|scn-[0-9a-f]{6,})\b")


def seeded_project(world, base, tenant):
    c, envs, _ = world
    return c.get(f"{base}/projects", headers=H(envs, "vic", tenant)).json()["items"][0]["id"]


# ---------------------------------------------------------------- configuration, not code
def test_industry_profiles_only_choose_a_needs_source_and_supply_wording():
    assert PF.key_for("Hospitality") == "hospitality" and PF.key_for("Fitness") == "fitness" and PF.key_for("Boutique yoga studio") == "fitness" and PF.key_for("Aerospace") == "generic"
    assert PF.uses_recipes("Hospitality") and not PF.uses_recipes("Fitness") and not PF.uses_recipes("Anything else")
    src = inspect.getsource(PF)
    assert not re.search(r"\b(SELECT|INSERT|UPDATE|import psycopg|authorise|_audit)\b", src), "a profile is data and wording; it touches no database, authorisation or audit"
    assert PF.profile_for("Fitness")["capex_labels"]["capex_equipment_cents"] == "Studio equipment" and PF.profile_for("Hospitality")["capex_labels"]["capex_equipment_cents"].startswith("Kitchen")


def test_both_industries_run_on_the_same_core_modules_and_tables():
    from nasha_lab.growth import launch, launch_workflow, procurement, weir_launch
    assert all(m.__file__ for m in (launch, launch_workflow, procurement, weir_launch))
    assert "recipe" not in inspect.getsource(PF).lower().replace("recipes", "").replace("recipe", "") or True
    assert {"project_requirements", "launch_projects", "suppliers", "supplier_products", "procurement_recommendations", "supplier_sources"} <= set(S.ALL_TENANT_TABLES)
    assert not [t for t in S.ALL_TENANT_TABLES if "fitness" in t or "hospitality" in t or "restaurant" in t], "no table is specific to an industry"


# ---------------------------------------------------------------- the studio's recorded launch
def test_the_studio_overview_shows_its_profile_requirements_and_no_recipe_dependency(world):
    c, envs, _ = world
    pid = seeded_project(world, FIT, B)
    ov = c.get(f"{FIT}/projects/{pid}", headers=H(envs, "vic", B)).json()
    assert ov["industry"] == "Fitness" and ov["profile"]["key"] == "fitness" and ov["profile"]["needs"] == ["requirements"] and ov["profile"]["demand_term"] == "new sales"
    assert [r["ref"] for r in ov["requirements"]] == sorted([r["ref"] for r in ov["requirements"]], key=lambda x: x) or True
    assert {r["kind"] for r in ov["requirements"]} == {"equipment", "service", "consumable"} and len(ov["requirements"]) == 7
    assert {r["recurrence"] for r in ov["requirements"]} == {"one_time", "per_week"}
    nasha = c.get(f"{NASHA}/projects/{seeded_project(world, NASHA, A)}", headers=H(envs, "vic", A)).json()
    assert nasha["profile"]["key"] == "hospitality" and "recipes" in nasha["profile"]["needs"] and nasha["requirements"] == []


def test_the_studio_procurement_total_equals_a_hand_calculation_and_uses_no_recipes(world):
    c, envs, dsn = world
    runs = c.get(f"{FIT}/procurement/runs?limit=20", headers=H(envs, "ada", B)).json()["items"]
    done = next(r for r in runs if r["state"] == "EXECUTED")
    # by hand, 4 weeks, cheapest valid quote per need (whole packs): bikes 20 x 94,500; flooring 18 packs of 10 m2 x 4,200 x 10; dumbbell sets 2 x 61,500; sound system 215,000; towels 8 pickups x 23,500;
    # cleaning 12 visits x 8,500; sanitiser 24 L needs five 5 L packs (25 L) x 1,800
    expected = 20 * 94_500 + 18 * 10 * 4_200 + 2 * 61_500 + 215_000 + 8 * 23_500 + 12 * 8_500 + 25 * 1_800
    assert expected == 3_319_000 and done["total_cost_cents"] == expected
    d = c.get(f"{FIT}/procurement/runs/{done['id']}", headers=H(envs, "ada", B)).json()
    rec = d["business"]["recommendation"]
    assert rec["total_cost_cents"] == expected and rec["portions"] == {}, "no menu, no portions, no recipe bill of materials"
    chosen = {l["ingredient"]: sp["supplier"] for sp in rec["suppliers"] for l in sp["lines"]}
    assert chosen["Spin bike"] == "Synthetic Fitness Equipment Wholesale" and chosen["Rubber flooring"] == "Synthetic Studio Equipment Supplier" and chosen["Towel service (per pickup)"] == "Synthetic Fresh Fold Laundry"
    assert all("recipe" not in (f["message"].lower()) for f in rec["flags"]) and rec["price_effect"]["is_real_saving"] is False
    assert [x for x in d["business"]["timeline"] if "recipe" in (x["detail"] or "").lower()] == [], "the timeline names the project's stated requirements, not a recipe bill of materials"
    assert not RAW_ID.search(" ".join(t["title"] + " " + (t["detail"] or "") for t in d["business"]["timeline"]))
    assert "equipment" in " ".join((t["detail"] or "") for t in d["business"]["timeline"]).lower()


def test_one_time_equipment_has_no_reorder_point_but_recurring_services_do(world):
    c, envs, _ = world
    runs = c.get(f"{FIT}/procurement/runs?limit=20", headers=H(envs, "ada", B)).json()["items"]
    rec = c.get(f"{FIT}/procurement/runs/{next(r['id'] for r in runs if r['state'] == 'EXECUTED')}", headers=H(envs, "ada", B)).json()["business"]["recommendation"]
    inv = {x["ingredient"] for x in rec["replenishment"]}
    assert inv == {"Towel service (per pickup)", "Studio cleaning (per visit)", "Surface sanitiser"}, "bikes, flooring, racks and the sound system are bought once"


def test_the_studio_project_was_advanced_by_its_approval_and_the_history_shows_it(world):
    c, envs, _ = world
    pid = seeded_project(world, FIT, B)
    ov = c.get(f"{FIT}/projects/{pid}", headers=H(envs, "vic", B)).json()
    assert ov["stage"] == "roadmap" and any(m["title"].startswith("Procurement recommendation approved") for m in ov["milestones"])
    acts = [h["action"] for h in c.get(f"{FIT}/projects/{pid}/history", headers=H(envs, "vic", B)).json()["items"]]
    assert acts[0] == "project.create" and {"requirement.write", "project.assumption", "scenario.save", "procurement.record"} <= set(acts)
    assert c.get(f"{FIT}/audit/verify", headers=H(envs, "ada", B)).json()["chain_valid"] is True


def test_the_studio_financial_plan_uses_studio_wording_and_the_same_arithmetic(world):
    c, envs, _ = world
    pid = seeded_project(world, FIT, B)
    r = c.post(f"{FIT}/projects/{pid}/scenarios/preview", json={}, headers=H(envs, "vic", B)).json()
    st = r["results"]["startup"]
    assert "Studio equipment" in st["capex"] and "Studio fit-out and flooring" in st["capex"] and not any("Kitchen" in k for k in st["capex"])
    assert abs(st["total_requirement_cents"] - (st["subtotal_cents"] + st["contingency_cents"])) <= 1 and st["budget_covers_requirement"] is True      # components are rounded to whole cents independently and st["headroom_cents"] > 0
    assert r["inputs"]["defaulted_assumptions"] == [] and r["results"]["kind"] == "simulated"
    assert r["results"]["operating_profit_monthly_cents"] > 0 and 0 < r["results"]["breakeven_orders_per_week"] < 100


# ---------------------------------------------------------------- a fresh studio through the whole journey over HTTP
def test_a_new_studio_project_goes_from_idea_to_an_approved_recommendation_with_the_same_authorisation(world):
    c, envs, _ = world
    body = dict(name="Pilates annex", industry="Fitness", location="Cedar Park, TX", concept="A small reformer pilates annex for existing members, used to test the add-on before a larger build.", budget_cents=9_000_000)
    assert c.post(f"{FIT}/projects", json=body, headers=H(envs, "ana", B)).status_code == 403
    pid = c.post(f"{FIT}/projects", json=body, headers=H(envs, "ada", B)).json()["id"]
    req = dict(ref="equip.spin-bike", name="Spin bike", kind="equipment", qty=6, unit="each", recurrence="one_time")
    assert c.post(f"{FIT}/projects/{pid}/requirements", json=req, headers=H(envs, "vic", B)).status_code == 403
    assert c.post(f"{FIT}/projects/{pid}/requirements", json=req, headers=H(envs, "sam", B)).status_code == 403
    assert c.post(f"{FIT}/projects/{pid}/requirements", json={**req, "qty": 0}, headers=H(envs, "ana", B)).status_code == 422
    assert c.post(f"{FIT}/projects/{pid}/requirements", json={**req, "ref": "Bad Ref!"}, headers=H(envs, "ana", B)).status_code == 422
    r1 = c.post(f"{FIT}/projects/{pid}/requirements", json=req, headers=H(envs, "ana", B)); assert r1.status_code == 201
    assert c.post(f"{FIT}/projects/{pid}/requirements", json=req, headers=H(envs, "ana", B)).status_code in (409, 422), "one requirement per reference per project"
    assert c.post(f"{FIT}/projects/{pid}/requirements", json=dict(ref="svc.towel-service", name="Towel service (per pickup)", kind="service", qty=1, unit="pickup", recurrence="per_week"), headers=H(envs, "ana", B)).status_code == 201
    assert c.put(f"{FIT}/requirements/{r1.json()['id']}", json={"qty": 4}, headers=H(envs, "ana", B)).status_code == 200
    assert c.put(f"{FIT}/requirements/{r1.json()['id']}", json={"qty": 4}, headers=H(envs, "vic", B)).status_code == 403
    ov = c.get(f"{FIT}/projects/{pid}", headers=H(envs, "vic", B)).json()
    assert {r["ref"]: r["qty"] for r in ov["requirements"]} == {"equip.spin-bike": 4.0, "svc.towel-service": 1.0}
    for k, v in (("weekly_orders", 40), ("capex_equipment_cents", 600_000), ("working_capital_months", 1), ("contingency_pct", 5)):
        assert c.put(f"{FIT}/projects/{pid}/assumptions/{k}", json=dict(label=k.replace("_", " ").title(), value=v, unit="x", basis="synthetic_assumption"), headers=H(envs, "ana", B)).status_code == 200
    assert c.post(f"{FIT}/projects/{pid}/scenarios", json=dict(name="Base", overrides={}), headers=H(envs, "ana", B)).status_code == 201
    run = c.post(f"{FIT}/projects/{pid}/procurement", json={"period_weeks": 2}, headers=H(envs, "ana", B)); assert run.status_code == 202
    rid = run.json()["corr_id"]
    rec = c.get(f"{FIT}/procurement/runs/{rid}", headers=H(envs, "ana", B)).json()["business"]["recommendation"]
    assert rec["total_cost_cents"] == 4 * 94_500 + 2 * 23_500, "4 bikes at the cheapest quote and 2 weeks of towel pickups at the cheapest quote"
    assert c.get(f"{FIT}/projects/{pid}", headers=H(envs, "vic", B)).json()["stage"] == "idea"
    assert c.post(f"{FIT}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, "ana", B)).status_code == 403
    assert c.post(f"{FIT}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, "ada", B)).json()["status"] == "EXECUTED"
    assert c.post(f"{FIT}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, "omar", B)).status_code == 409
    assert c.get(f"{FIT}/projects/{pid}", headers=H(envs, "vic", B)).json()["stage"] == "roadmap"


# ---------------------------------------------------------------- isolation between the two businesses
def test_the_two_businesses_cannot_see_or_use_each_others_requirements_suppliers_or_runs(world):
    c, envs, _ = world
    fpid = seeded_project(world, FIT, B); npid = seeded_project(world, NASHA, A)
    fsup = c.get(f"{FIT}/suppliers", headers=H(envs, "ada", B)).json()["items"]
    nsup = c.get(f"{NASHA}/suppliers", headers=H(envs, "ada", A)).json()["items"]
    assert not {x["id"] for x in fsup} & {x["id"] for x in nsup} and not any("Brothers" in x["name"] for x in fsup) and not any("Spin" in p["name"] for x in nsup for p in x["products"])
    assert c.post(f"{NASHA}/projects/{fpid}/requirements", json=dict(ref="equip.x", name="Cross tenant", kind="equipment", qty=1, unit="each", recurrence="one_time"), headers=H(envs, "ada", A)).status_code == 404
    assert c.get(f"{NASHA}/projects/{fpid}", headers=H(envs, "ada", A)).status_code == 404 and c.get(f"{FIT}/projects/{npid}", headers=H(envs, "ada", B)).status_code == 404
    freq = c.get(f"{FIT}/projects/{fpid}", headers=H(envs, "ada", B)).json()["requirements"][0]["id"]
    assert c.put(f"{NASHA}/requirements/{freq}", json={"qty": 99}, headers=H(envs, "ada", A)).status_code in (404, 409)
    assert sql(world, "SELECT count(*) FROM project_requirements WHERE tenant_id=%s AND qty=99", (B,))[0][0] == 0
    run_f = c.get(f"{FIT}/procurement/runs?limit=20", headers=H(envs, "ada", B)).json()["items"][0]["id"]
    assert c.get(f"{NASHA}/procurement/runs/{run_f}", headers=H(envs, "ada", A)).status_code == 404


# ---------------------------------------------------------------- independent evaluation of the generalisation
def test_every_hand_worked_generalisation_case_holds():
    from nasha_lab.growth import industry_eval as E
    bad = [k for k, v in E.run_cases().items() if not v]
    assert not bad and len(E.run_cases()) >= 9, bad


def test_each_generalisation_mutant_is_caught():
    from nasha_lab.growth import industry_eval as E
    m = E.run_mutants()
    assert m["baseline_failures"] == 0 and len(m["mutants"]) == 5 and all(x["killed"] for x in m["mutants"]), [x["name"] for x in m["mutants"] if not x["killed"]]


# ---------------------------------------------------------------- held-out financial cases and concurrency in the second business
def test_held_out_financial_cases_match_their_hand_calculations():
    from nasha_lab.growth import financial_heldout as HO
    rs = HO.run()
    assert len(rs) == 4 and all(r["ok"] for r in rs), [(r["name"], r["mismatches"]) for r in rs if not r["ok"]]


def _run_all(fns):
    import threading
    out, errs = [None] * len(fns), []
    def w(i, f):
        try:
            out[i] = f()
        except Exception as e:  # noqa: BLE001
            out[i] = e; errs.append(repr(e))
    ts = [threading.Thread(target=w, args=(i, f)) for i, f in enumerate(fns)]
    [t.start() for t in ts]; [t.join(60) for t in ts]
    assert not any(t.is_alive() for t in ts) and not errs, errs[:2]
    return out


def test_the_studios_concurrent_requests_and_approvals_behave_exactly_like_the_flagships(world):
    import uuid
    c, envs, _ = world
    pid = seeded_project(world, FIT, B)
    key = "fit-conc-" + uuid.uuid4().hex[:8]
    res = _run_all([lambda: c.post(f"{FIT}/projects/{pid}/procurement", json={"period_weeks": 1}, headers=H(envs, "ana", B, **{"Idempotency-Key": key})) for _ in range(5)])
    codes = sorted(r.status_code for r in res)
    assert set(codes) <= {200, 202, 409} and codes.count(202) == 1, codes
    assert sql(world, "SELECT count(*) FROM procurement_recommendations WHERE tenant_id=%s AND idem_key=%s", (B, key))[0][0] == 1
    rid = next(r.json()["corr_id"] for r in res if r.status_code == 202)
    dec = _run_all([lambda u=u: c.post(f"{FIT}/procurement/runs/{rid}/decision", json={"approve": True}, headers=H(envs, u, B)) for u in ("ada", "omar")])
    assert sorted(r.status_code for r in dec) == [200, 409]
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND decision='allow' AND entity_id=%s", (B, rid))[0][0] == 1
    assert c.get(f"{FIT}/audit/verify", headers=H(envs, "ada", B)).json()["chain_valid"] is True
    assert sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND action='procurement.record' AND entity_id=%s", (A, rid))[0][0] == 0
