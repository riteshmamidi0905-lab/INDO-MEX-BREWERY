"""Growth OS web interface, driven in a real browser against the real API, PostgreSQL and THE WEIR (two synthetic tenants). Every assertion about state is made against the API/database, not the page's own claims.
Skipped with an explicit reason when no Chromium or PostgreSQL is available."""
import glob
import os
import socket
import threading
import time

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
sync_api = pytest.importorskip("playwright.sync_api", reason="INTEGRATION UNAVAILABLE: playwright not installed")
uvicorn = pytest.importorskip("uvicorn")
import requests as _rq  # noqa: E402  (requests is used only to talk to the localhost test server)

CH = os.environ.get("CHROMIUM_PATH") or (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome") or [None])[0]
AXE = os.environ.get("AXE_PATH") or (glob.glob("/usr/local/lib/python3*/dist-packages/axe_playwright_python/axe.min.js") or [None])[0]
if not CH:
    pytest.skip("INTEGRATION UNAVAILABLE: no Chromium executable (set CHROMIUM_PATH)", allow_module_level=True)

from nasha_lab.growth import api as GA, demo as DM, service as SV  # noqa: E402


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    try:
        import pixeltable_pgserver as pg
        srv = pg.get_server(str(tmp_path_factory.mktemp("pgdata")), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    envs = DM.build(tmp_path_factory.mktemp("ui"), srv.get_uri(), schema="growth_ui", with_warehouse=False)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = uvicorn.Server(uvicorn.Config(GA.create_growth_app(envs), host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True); th.start()
    for _ in range(100):
        try:
            if _rq.get(f"http://127.0.0.1:{port}/v1/health", timeout=1).ok:
                break
        except Exception:  # noqa: BLE001
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", envs
    server.should_exit = True; th.join(5)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CH, args=["--no-sandbox"])
        yield b
        b.close()


def login(browser, base, user, tenant="tenant-nasha", vp=(1280, 900)):
    ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]})
    pg = ctx.new_page(); pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e))); pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
    pg.goto(base + "/app"); pg.wait_for_selector("#login-form")
    pg.select_option("#l-tenant", tenant); pg.select_option("#l-user", user); pg.click("button[type=submit]"); pg.wait_for_selector("#app:not([hidden])")
    pg.wait_for_selector("#main h1")
    return pg


def token(envs, tenant, user):
    return {"Authorization": "Bearer " + envs[tenant].authority.login(user, f"{tenant}-{user}-dev-passcode")}


def get(base, envs, tenant, user, path):
    return _rq.get(f"{base}/v1/tenants/{tenant}{path}", headers=token(envs, tenant, user)).json()


def go(pg, h, sel="#main h1"):
    pg.evaluate(f"location.hash='{h}'"); pg.wait_for_timeout(250); pg.wait_for_selector(sel); pg.wait_for_load_state("networkidle")


def test_login_screen_hides_the_app_and_a_wrong_passcode_is_refused(server, browser):
    base, _ = server
    pg = browser.new_context().new_page(); pg.goto(base + "/app"); pg.wait_for_selector("#login-form")
    assert pg.is_hidden("#app") and pg.is_visible("#login")
    pg.fill("#l-pass", "wrong"); pg.click("button[type=submit]"); pg.wait_for_timeout(500)
    assert "failed" in pg.inner_text("#l-err").lower() and pg.is_hidden("#app")


def test_dashboard_numbers_equal_the_api(server, browser):
    base, envs = server
    pg = login(browser, base, "sam"); go(pg, "#/dashboard", ".kpi")
    d = get(base, envs, "tenant-nasha", "sam", "/dashboard")
    kpis = [x.inner_text() for x in pg.query_selector_all(".kpi b")]
    assert kpis[0] == str(d["lead_total"]) and kpis[3] == str(d["approvals_pending"])
    assert not pg.errors


def test_crm_create_account_through_the_form_and_viewer_is_read_only(server, browser):
    base, envs = server
    pg = login(browser, base, "sam"); go(pg, "#/crm/accounts", "#f")
    pg.fill("#f input[name=name]", "UI Test Catering"); pg.click("#f button"); pg.wait_for_timeout(700)
    assert "UI Test Catering" in pg.inner_text("#tbl")
    assert any(a["name"] == "UI Test Catering" for a in get(base, envs, "tenant-nasha", "sam", "/accounts?limit=50")["items"])
    v = login(browser, base, "vic"); go(v, "#/crm/accounts", "#tbl")
    assert v.query_selector("#f") is None and "read-only" in v.inner_text("#crm-body")


def test_pipeline_illegal_move_is_refused_by_the_backend_and_a_legal_move_is_applied(server, browser):
    base, envs = server
    pg = login(browser, base, "ada"); go(pg, "#/pipeline", ".board")
    opps = get(base, envs, "tenant-nasha", "ada", "/opportunities?limit=50")["items"]
    new = next(o for o in opps if o["stage"] == "new")
    pg.select_option(f"[data-opp='{new['id']}']", "won"); pg.wait_for_selector(".toast.bad")
    assert "illegal stage transition" in pg.inner_text(".toast.bad") and get(base, envs, "tenant-nasha", "ada", "/opportunities?limit=50")["items"][0]["stage"] in ("new", "qualified", "proposal", "negotiation", "won", "lost")
    assert next(o for o in get(base, envs, "tenant-nasha", "ada", "/opportunities?limit=50")["items"] if o["id"] == new["id"])["stage"] == "new"
    pg.wait_for_timeout(300); go(pg, "#/pipeline", ".board")
    pg.select_option(f"[data-opp='{new['id']}']", "qualified"); pg.wait_for_selector(".toast.ok"); pg.wait_for_timeout(600)
    assert next(o for o in get(base, envs, "tenant-nasha", "ada", "/opportunities?limit=50")["items"] if o["id"] == new["id"])["stage"] == "qualified"


def test_qualification_flow_in_the_browser_requester_cannot_approve_owner_can_and_the_crm_changes(server, browser):
    base, envs = server
    h = token(envs, "tenant-nasha", "sam"); u = base + "/v1/tenants/tenant-nasha"
    acc = _rq.post(u + "/accounts", json={"name": "Browser Flow Co"}, headers=h).json()["id"]
    con = _rq.post(u + "/contacts", json={"account_id": acc, "full_name": "Browser Flow", "email": "browser.flow@example.invalid"}, headers=h).json()["id"]
    _rq.put(f"{u}/contacts/{con}/consent", json={"status": "opt_in"}, headers=h)
    pick = _rq.post(u + "/leads", json={"contact_id": con, "source": "synthetic-referral", "signals": {"budget_confirmed": True, "decision_maker": True, "timeline_days": 20, "fit": 0.9, "engagement": 0.8}}, headers=h).json()["id"]
    pg = login(browser, base, "sam"); go(pg, "#/workflows", "#q"); pg.select_option("#q select", pick)
    runs_before = len(get(base, envs, "tenant-nasha", "sam", "/workflows/runs?limit=50")["items"])
    pg.click("#q button"); pg.wait_for_selector("#main h1 em"); pg.wait_for_selector("#main .timeline")
    assert "AWAITING" in pg.inner_text("#main").upper() and pg.query_selector("#ap") is None and "Only an owner may approve" in pg.inner_text("#main")
    run = pg.evaluate("location.hash.split('/')[2]")
    lead = get(base, envs, "tenant-nasha", "sam", f"/workflows/runs/{run}")["lead_id"]
    assert len(get(base, envs, "tenant-nasha", "sam", "/workflows/runs?limit=50")["items"]) == runs_before + 1
    assert next(l for l in get(base, envs, "tenant-nasha", "sam", "/leads?limit=50")["items"] if l["id"] == lead)["status"] == "new", "nothing changed before the human decided"
    ow = login(browser, base, "ada"); ow.on("dialog", lambda d: d.accept("looks right"))
    go(ow, f"#/workflows/{run}", "#ap")
    assert not ow.is_disabled("#ap")
    ow.click("#ap"); ow.wait_for_selector(".toast.ok"); ow.wait_for_timeout(800)
    assert get(base, envs, "tenant-nasha", "ada", f"/workflows/runs/{run}")["state"] == "EXECUTED"
    assert next(l for l in get(base, envs, "tenant-nasha", "ada", "/leads?limit=50")["items"] if l["id"] == lead)["status"] in ("qualified", "disqualified")
    ow.wait_for_selector("text=CRM updated")
    assert "CRM updated" in ow.inner_text("#main") and ow.query_selector("#ap") is None, "an executed run exposes no approval action"


def test_marketing_cannot_start_qualification_and_the_denial_is_audited_and_visible(server, browser):
    base, envs = server
    pg = login(browser, base, "mia"); go(pg, "#/workflows", "#main h1")
    assert pg.query_selector("#q") is None and "THE WEIR denies" in pg.inner_text("#main")
    lead = get(base, envs, "tenant-nasha", "mia", "/leads?limit=1")["items"][0]["id"]
    r = _rq.post(f"{base}/v1/tenants/tenant-nasha/workflows/lead-qualification", json={"lead_id": lead}, headers=token(envs, "tenant-nasha", "mia"))
    assert r.status_code == 403
    ow = login(browser, base, "ada"); go(ow, "#/security", ".tablewrap")
    runs = get(base, envs, "tenant-nasha", "ada", "/workflows/runs?limit=50")["items"]
    assert any(x["state"] == "BLOCKED" and x["requester"] == "mia" for x in runs)


def test_pricing_studio_computes_scenarios_through_the_engine_and_a_viewer_cannot(server, browser):
    base, envs = server
    pg = login(browser, base, "ana"); go(pg, "#/pricing", "#p-form")
    pg.select_option("#p-prod", label=next(o for o in pg.eval_on_selector_all("#p-prod option", "els=>els.map(e=>e.textContent)") if o.startswith("Tandoori Lamb Tacos")))
    pg.click("#p-form button.pri"); pg.wait_for_selector("#p-out table"); text = pg.inner_text("#p-out")
    assert "10% discount" in text and "cost +20%" in text and "planning assumptions" in text and "assumed value" in text
    assert "69.4%" in text, "(1850-566.08)/1850 = 69.4%: the base row must show the engine's margin from the stored cost"
    v = login(browser, base, "vic"); go(v, "#/pricing", "#p-form")
    assert v.is_disabled("#p-form button.pri") and "may view products but not run" in v.inner_text("#main")


def test_the_two_tenants_do_not_leak_into_each_other_in_the_ui(server, browser):
    base, envs = server
    a = login(browser, base, "sam"); go(a, "#/crm/accounts", "#tbl")
    names_a = a.inner_text("#tbl")
    b = login(browser, base, "sam", tenant="tenant-fit"); go(b, "#/crm/accounts", "#tbl")
    names_b = b.inner_text("#tbl")
    assert "Larkspur Analytics" in names_a and "Kestrel Logistics" in names_b and "Kestrel" not in names_a and "Larkspur" not in names_b and "UI Test Catering" not in names_b
    assert "Meridian Fitness" in b.inner_text("#who")


def test_every_screen_is_keyboard_reachable_and_has_no_serious_axe_violations(server, browser):
    base, envs = server
    pg = login(browser, base, "ada")
    assert pg.evaluate("document.querySelector('a.skip').getAttribute('href') === '#main' && document.body.querySelector('a, button, input, select') === document.querySelector('a.skip')"), "the skip link comes first"
    pg.evaluate("document.querySelector('a.skip').focus()"); assert pg.evaluate("document.querySelector('a.skip').getBoundingClientRect().top >= 0"), "the skip link becomes visible on focus"
    pg.evaluate("document.querySelector('#nav a').focus()")
    for _ in range(2):
        pg.keyboard.press("Tab")
    assert pg.evaluate("document.activeElement.closest('#nav') !== null"), "the sidebar navigation is reachable and ordered by keyboard"
    pg.keyboard.press("Enter"); pg.wait_for_timeout(400); assert pg.evaluate("location.hash") in ("#/business", "#/research", "#/suppliers", "#/crm", "#/pipeline", "#/dashboard")
    for h in ("#/business", "#/research", "#/suppliers", "#/financial", "#/procurement", "#/roadmap", "#/marketing", "#/dashboard", "#/crm/leads", "#/pipeline", "#/pricing", "#/workflows", "#/security", "#/settings"):
        go(pg, h); pg.wait_for_timeout(500)
        assert pg.evaluate("document.querySelectorAll('#main h1').length") == 1
        assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), h
        if AXE:
            pg.add_script_tag(path=AXE)
            res = pg.evaluate("axe.run(document,{runOnly:['wcag2a','wcag2aa','wcag21aa']}).then(r=>r.violations.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,t:v.nodes.slice(0,2).map(n=>n.target.join(' '))})))")
            bad = [v for v in res if v["impact"] in ("serious", "critical")]
            assert not bad, (h, bad)
    pg.click("#signout"); assert pg.is_visible("#login") and pg.is_hidden("#app")


def test_business_and_engineering_views_use_the_same_records_and_a_blocked_run_has_no_approval_action(server, browser):
    base, envs = server
    pg = login(browser, base, "ada")
    runs = get(base, envs, "tenant-nasha", "ada", "/workflows/runs?limit=50")["items"]
    blocked = next(r for r in runs if r["state"] == "BLOCKED" and r["failure"].startswith("TOOL_DENIED"))
    go(pg, f"#/workflows/{blocked['id']}", "#main .timeline")
    biz = pg.inner_text("#main")
    assert blocked["prospect"] in biz and blocked["organization"] in biz and "does not have permission" in biz and "No CRM changes were made" in biz
    assert blocked["id"] not in biz and blocked["lead_id"] not in biz and "TOOL_DENIED" not in biz and "E4:lead.signals" not in biz, "no raw identifiers in the business view"
    assert pg.query_selector("#ap") is None and pg.query_selector("#rj") is None, "a blocked workflow exposes no approval action"
    assert pg.evaluate("document.querySelector('.vt [data-v=business]').getAttribute('aria-pressed')") == "true"
    pg.click(".vt [data-v=engineering]"); pg.wait_for_selector("text=Engineering record")
    eng = pg.inner_text("#main")
    assert blocked["id"] in eng and blocked["lead_id"] in eng and "TOOL_DENIED" in eng and "E4:lead.signals" in eng, "engineering view shows the same record with ids and evidence keys"
    assert pg.evaluate("localStorage.getItem('growth.view')") == "engineering"
    pg.click(".vt [data-v=business]")


def test_workflow_center_lists_business_language_not_identifiers(server, browser):
    base, envs = server
    pg = login(browser, base, "ada"); go(pg, "#/workflows", ".tablewrap")
    txt = pg.inner_text("#main")
    for needle in ("Dana Whitfield", "Larkspur Analytics", "Awaiting approval", "Completed", "Blocked", "Rejected", "Needs more information", "Corporate catering inquiry"):
        assert needle.lower() in txt.lower(), needle
    import re
    assert not re.search(r"\b(wf-[0-9a-f]{6,}|lead-[0-9a-f]{6,}|ap_[0-9a-f]+)\b", txt)
    go(pg, "#/security", ".tablewrap"); sec = pg.inner_text("#main")
    assert "after approval by" in sec and not re.search(r"\b(wf-[0-9a-f]{6,}|lead-[0-9a-f]{6,})\b", sec)


def test_awaiting_run_shows_scoring_factors_and_an_owner_other_than_the_requester_can_decide(server, browser):
    base, envs = server
    runs = get(base, envs, "tenant-nasha", "ada", "/workflows/runs?limit=50")["items"]
    aw = next(r for r in runs if r["state"] == "AWAITING_APPROVAL" and r["prospect"] == "Dana Whitfield")
    sam = login(browser, base, "sam"); go(sam, f"#/workflows/{aw['id']}", "#main .timeline")
    t = sam.inner_text("#main")
    assert "Budget" in t and "Decision maker" in t and "Timeline" in t and "75" in t and "Only an owner may approve" in t and sam.query_selector("#ap") is None
    ada = login(browser, base, "ada"); go(ada, f"#/workflows/{aw['id']}", "#main .timeline")
    assert ada.query_selector("#ap") is not None and ada.query_selector("#rj") is not None


def test_lead_search_and_status_filter_narrow_the_list_without_new_requests(server, browser):
    base, envs = server
    pg = login(browser, base, "ada"); go(pg, "#/crm/leads", "#srch"); pg.wait_for_selector("#tbl tbody tr")
    total = pg.locator("#tbl tbody tr").count()
    pg.fill("#srch", "Larkspur"); assert pg.locator("#tbl tbody tr").count() == 1 and "Dana Whitfield" in pg.inner_text("#tbl")
    pg.fill("#srch", ""); pg.select_option("#stf", "converted")
    n = pg.locator("#tbl tbody tr").count()
    assert 0 < n < total and all("converted" in r.lower() for r in pg.locator("#tbl tbody tr").all_inner_texts())
    assert f"{n} of {total}" in pg.inner_text("#cnt")


# ---------------------------------------------------------------- the launch journey screens
def _api(base, envs, tenant, user, method, path, **kw):
    return _rq.request(method, f"{base}/v1/tenants/{tenant}{path}", headers=token(envs, tenant, user), **kw)


def test_my_business_shows_the_project_the_stage_tracker_and_labelled_assumptions_and_no_ids_in_business_view(server, browser):
    base, envs = server
    pg = login(browser, base, "ada"); go(pg, "#/business", ".track")
    txt = pg.inner_text("#main")
    assert "NASHA — The Courtyard" in txt and "synthetic assumption" in txt.lower() and "synthetic case study" in txt.lower() and "fusion" not in txt.lower()
    proj = _api(base, envs, "tenant-nasha", "ada", "GET", "/projects").json()["items"][0]
    assert proj["id"] not in txt
    pg.click(".vt [data-v=engineering]"); pg.wait_for_selector("text=Engineering record"); assert proj["id"] in pg.inner_text("#main")
    pg.click(".vt [data-v=business]")
    b = login(browser, base, "ada", tenant="tenant-fit"); go(b, "#/business", ".track")
    assert "Second studio location" in b.inner_text("#main") and "Courtyard" not in b.inner_text("#main")


def test_suppliers_screen_labels_leads_fixtures_and_missing_prices_and_the_shortlist_is_saved_through_the_api(server, browser):
    base, envs = server
    pg = login(browser, base, "ana"); go(pg, "#/suppliers", "#slist .sup")
    t = pg.inner_text("#main")
    tl = t.lower(); assert "Farm to Table LLC" in t and "lead, not verified" in tl and "no published prices" in tl and "synthetic fixture" in tl and "no supplier has been contacted" in tl and "official website: not verified" in tl
    assert "@" not in t.replace("@example", ""), "no e-mail addresses are displayed"
    pg.select_option("#sver", "lead_unverified"); assert pg.locator("#slist .sup").count() == 12
    sup = next(s for s in _api(base, envs, "tenant-nasha", "ana", "GET", "/suppliers").json()["items"] if s["name"] == "Brothers Produce")
    pid = _api(base, envs, "tenant-nasha", "ana", "GET", "/projects").json()["items"][0]["id"]
    pg.select_option(f"[data-sl='{sup['id']}']", "preferred"); pg.wait_for_selector(".toast.ok")
    ov = _api(base, envs, "tenant-nasha", "ana", "GET", f"/projects/{pid}").json()
    assert next(s for s in ov["shortlist"] if s["supplier_id"] == sup["id"])["status"] == "preferred"
    v = login(browser, base, "vic"); go(v, "#/suppliers", "#slist .sup")
    assert v.locator("[data-sl]").count() == 0, "a viewer cannot change the shortlist"


def test_financial_plan_calculates_on_the_server_from_stored_data_and_labels_everything_as_simulated(server, browser):
    base, envs = server
    pg = login(browser, base, "ana"); go(pg, "#/financial", "#fres .kpi")
    assert "not actual business performance" in pg.inner_text("#main").lower()
    pid = _api(base, envs, "tenant-nasha", "ana", "GET", "/projects").json()["items"][0]["id"]
    api0 = _api(base, envs, "tenant-nasha", "ana", "POST", f"/projects/{pid}/scenarios/preview", json={}).json()["results"]
    assert pg.inner_text("#fres .kpi b").replace(",", "") == f"${api0['revenue_cents'] / 100:.2f}"
    pg.fill("#ctl input[name=price_change_pct]", "10"); pg.click("#ctl button.pri"); pg.wait_for_timeout(700)
    api1 = _api(base, envs, "tenant-nasha", "ana", "POST", f"/projects/{pid}/scenarios/preview", json={"price_change_pct": 0.1}).json()["results"]
    assert pg.inner_text("#fres .kpi b").replace(",", "") == f"${api1['revenue_cents'] / 100:.2f}" and api1["revenue_cents"] != api0["revenue_cents"]
    t = pg.inner_text("#fres")
    assert "Break-even" in t and "Price sensitivity" in t and "Scenario comparison" in t and "Unit economics by product" in t
    pg.once("dialog", lambda d: d.accept("UI saved scenario")); pg.click("#svs"); pg.wait_for_selector(".toast.ok"); pg.wait_for_timeout(500)
    assert any(s["name"] == "UI saved scenario" for s in _api(base, envs, "tenant-nasha", "ana", "GET", f"/projects/{pid}").json()["scenarios"])
    v = login(browser, base, "vic"); go(v, "#/financial", "#fres .kpi"); assert v.query_selector("#svs") is None and v.query_selector("form.mini") is None


def test_procurement_screens_show_agent_research_two_person_approval_and_no_action_on_blocked_runs(server, browser):
    base, envs = server
    runs = _api(base, envs, "tenant-nasha", "ada", "GET", "/procurement/runs?limit=50").json()["items"]
    by = {r["state"]: r for r in runs}
    assert {"EXECUTED", "REJECTED", "AWAITING_APPROVAL", "BLOCKED"} <= set(by)
    pg = login(browser, base, "ada"); go(pg, "#/procurement", ".tablewrap")
    low = pg.inner_text("#main").lower(); assert "completed" in low and "rejected" in low and "blocked" in low
    go(pg, f"#/procurement/{by['AWAITING_APPROVAL']['id']}", "#main .timeline")
    t = pg.inner_text("#main")
    assert "Research brief" in t and "Recommended quotes by supplier" in t and "Inventory planning" in t and "No order" in t and by["AWAITING_APPROVAL"]["id"] not in t
    assert pg.query_selector("#ap") is not None and pg.query_selector("#rj") is not None, "an owner other than the requester may decide"
    ana = login(browser, base, "ana"); go(ana, f"#/procurement/{by['AWAITING_APPROVAL']['id']}", "#main .timeline")
    assert ana.query_selector("#ap") is None and "Only an owner may approve" in ana.inner_text("#main")
    go(pg, f"#/procurement/{by['BLOCKED']['id']}", "#main .timeline")
    assert pg.query_selector("#ap") is None and pg.query_selector("#rj") is None and "Nothing was recorded" in pg.inner_text("#main")
    go(pg, f"#/procurement/{by['EXECUTED']['id']}", "#main .timeline")
    assert pg.query_selector("#ap") is None and "Recommendation recorded" in pg.inner_text("#main")
    pg.click(".vt [data-v=engineering]"); pg.wait_for_selector("text=Engineering record")
    assert by["EXECUTED"]["id"] in pg.inner_text("#main") and "engine" in pg.inner_text("#main").lower()
    pg.click(".vt [data-v=business]")


def test_roadmap_status_changes_are_saved_by_owner_and_unavailable_to_a_viewer(server, browser):
    base, envs = server
    pg = login(browser, base, "ada"); go(pg, "#/roadmap", "[data-ms]")
    ms = _api(base, envs, "tenant-nasha", "ada", "GET", "/projects").json()["items"][0]["id"]
    ov = _api(base, envs, "tenant-nasha", "ada", "GET", f"/projects/{ms}").json()
    todo = next(m for m in ov["milestones"] if m["status"] == "todo")
    pg.select_option(f"[data-ms='{todo['id']}']", "doing"); pg.wait_for_selector(".toast.ok"); pg.wait_for_timeout(500)
    assert next(m for m in _api(base, envs, "tenant-nasha", "ada", "GET", f"/projects/{ms}").json()["milestones"] if m["id"] == todo["id"])["status"] == "doing"
    v = login(browser, base, "vic"); go(v, "#/roadmap", ".track"); assert v.locator("[data-ms]").count() == 0


def test_on_a_phone_the_navigation_is_collapsed_behind_a_keyboard_operable_menu_and_content_starts_in_the_first_screen(server, browser):
    base, _ = server
    pg = login(browser, base, "ana", vp=(390, 844))
    btn = pg.locator("#menubtn")
    assert btn.is_visible() and btn.get_attribute("aria-expanded") == "false" and not pg.locator("#nav").is_visible()
    assert pg.locator("#main h1").bounding_box()["y"] < 400                      # the page title is on the first screen, not below a full navigation list
    btn.focus(); pg.keyboard.press("Enter")
    assert btn.get_attribute("aria-expanded") == "true" and pg.locator("#nav").is_visible() and pg.locator("#nav a[data-k=suppliers]").is_visible()
    pg.locator("#nav a[data-k=suppliers]").click(); pg.wait_for_selector("#slist .sup")
    assert btn.get_attribute("aria-expanded") == "false" and not pg.locator("#nav").is_visible()   # choosing a destination closes the menu
    assert not pg.evaluate("document.documentElement.scrollWidth>innerWidth+1")
    wide = login(browser, base, "ana", vp=(1280, 900))
    assert not wide.locator("#menubtn").is_visible() and wide.locator("#nav").is_visible()


def test_supplier_comparison_shows_data_categories_sources_and_never_ranks_across_them(server, browser):
    base, envs = server
    pg = login(browser, base, "ana"); go(pg, "#/suppliers", "#cmp table")
    t = pg.inner_text("#cmp").lower()
    assert "compare quotes" in t and "never compared with each other" in t and "synthetic quotation" in t and "lowest in category" in t and "no published price" in t
    assert pg.locator("#cmp tbody tr").count() == 8 and pg.locator("#cmpall").count() == 1
    pg.click("#cmpall"); assert pg.locator("#cmp tbody tr").count() > 8
    card = pg.locator("#slist .sup", has_text="Brothers Produce")
    assert "rule-based" in card.inner_text().lower() and "names the project area" in card.inner_text().lower()
    card.locator("summary", has_text="Public sources").click()
    txt = card.inner_text().lower()
    assert "search-result snippet only (page not opened)" in txt and "not an official website, a price or a verification" in txt and "restaurant365" in txt
    assert "official website: not verified" in txt


def test_adding_a_public_source_and_the_duplicate_warning_work_through_the_real_api(server, browser):
    base, envs = server
    pg = login(browser, base, "ana"); go(pg, "#/suppliers", "#slist .sup")
    card = pg.locator("#slist .sup", has_text="Hill Country Dairies")
    card.locator("summary", has_text="Add a public source").click()
    f = card.locator("form.srcf")
    f.locator("[name=url]").fill("https://example.test/ui-added-source"); f.locator("[name=observed_on]").fill("2026-10-23"); f.locator("[name=claim]").fill("Listed in a trade directory as a dairy distributor.")
    f.locator("button").click(); pg.wait_for_selector(".toast", timeout=8000); assert "source added" in pg.inner_text(".toast").lower(), pg.inner_text(".toast"); pg.wait_for_selector("#slist .sup")
    sup = next(s for s in _api(base, envs, "tenant-nasha", "ana", "GET", "/suppliers").json()["items"] if s["name"] == "Hill Country Dairies")
    assert any(s["url"] == "https://example.test/ui-added-source" and s["access"] == "search_snippet" for s in sup["sources"])
    pg.locator("summary", has_text="Add a supplier record").click()
    ns = pg.locator("#ns")
    ns.locator("[name=name]").fill("Brothers Produce Inc."); ns.locator("[name=category]").fill("Produce"); ns.locator("[name=service_area]").fill("Texas"); ns.locator("[name=source_url]").fill("https://example.test/dup")
    ns.locator("button").click()
    pg.wait_for_function("[...document.querySelectorAll('.toast')].some(t=>t.innerText.toLowerCase().includes('duplicate'))", timeout=8000)
    assert not [s for s in _api(base, envs, "tenant-nasha", "ana", "GET", "/suppliers").json()["items"] if s["name"] == "Brothers Produce Inc."]
    v = login(browser, base, "vic"); go(v, "#/suppliers", "#slist .sup"); assert v.locator("form.srcf").count() == 0, "a viewer cannot add a source"


def test_financial_plan_shows_startup_costs_formulas_break_even_grid_and_limitations_from_stored_data(server, browser):
    base, envs = server
    pg = login(browser, base, "ana"); go(pg, "#/financial", "#fres .kpi")
    pid = _api(base, envs, "tenant-nasha", "ana", "GET", "/projects").json()["items"][0]["id"]
    st = _api(base, envs, "tenant-nasha", "ana", "POST", f"/projects/{pid}/scenarios/preview", json={}).json()["results"]["startup"]
    t = pg.inner_text("#fres")
    assert "Start-up costs" in t and "budget does not cover the plan" in t.lower() and f"${st['total_requirement_cents'] / 100:,.2f}" in t and "Contingency" in t and "Working capital" in t
    assert "Break-even orders per week" in t and "not reachable" in t or "Break-even orders per week" in t
    assert "What this model does not know" in t and "assumptions, not measurements" in t
    pg.locator("summary", has_text="Formulas").click(); ft = pg.inner_text("#fres details").lower()
    assert "contribution" in ft and "fixed costs / contribution per unit" in ft and "contingency %" in ft
    pg.fill("#ctl input[name=capex_buildout_cents]", "170000"); pg.click("#ctl button.pri"); pg.wait_for_timeout(700)
    st2 = _api(base, envs, "tenant-nasha", "ana", "POST", f"/projects/{pid}/scenarios/preview", json={"capex_buildout_cents": 17_000_000}).json()["results"]["startup"]
    assert st2["total_requirement_cents"] < st["total_requirement_cents"] and f"${st2['total_requirement_cents'] / 100:,.2f}" in pg.inner_text("#fres")


def test_my_business_shows_the_journey_from_records_and_a_readable_audit_history(server, browser):
    base, envs = server
    pg = login(browser, base, "ada"); go(pg, "#/business", ".journey")
    t = pg.inner_text("#main")
    assert "The launch journey" in t and "Market research" in t and "Human approval" in t and "Project history" in t and "Approved and recorded" in t
    assert pg.locator(".journey li").count() == 7 and "done" in pg.inner_text(".journey").lower()
    assert "audit #" not in t, "the business view carries no engineering identifiers"
    assert not __import__("re").search(r"\b(proj|sup|asm|ms|scn|pr)-[0-9a-f]{6,}\b", t)
    pg.click(".vt [data-v=engineering]"); pg.wait_for_selector("text=audit #")
    pg.click(".vt [data-v=business]")


def test_procurement_detail_states_that_no_language_model_ran_and_lists_what_remains_uncertain(server, browser):
    base, envs = server
    runs = _api(base, envs, "tenant-nasha", "ada", "GET", "/procurement/runs?limit=50").json()["items"]
    rid = next(r["id"] for r in runs if r["state"] == "AWAITING_APPROVAL")
    pg = login(browser, base, "ada"); go(pg, f"#/procurement/{rid}", "#main .timeline")
    t = pg.inner_text("#main")
    assert "No language model was used for this brief" in t and "What remains uncertain" in t and "Effect of the supplier choice" in t and "synthetic" in t.lower()
    assert "not a language model" in t.lower() or "offline heuristic" in t.lower()


def test_new_screens_have_no_serious_axe_violations_at_phone_width_with_every_section_expanded(server, browser):
    if not AXE:
        pytest.skip("INTEGRATION UNAVAILABLE: axe-core not installed")
    base, envs = server
    pg = login(browser, base, "ada", vp=(390, 844))
    rid = next(r["id"] for r in get(base, envs, "tenant-nasha", "ada", "/procurement/runs?limit=50")["items"] if r["state"] == "AWAITING_APPROVAL")
    for h in ("#/business", "#/suppliers", "#/financial", f"#/procurement/{rid}"):
        go(pg, h, "#main h1"); pg.wait_for_timeout(900)
        pg.evaluate("document.querySelectorAll('#main details').forEach(d=>d.open=true)")
        assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), ("horizontal overflow", h)
        pg.add_script_tag(path=AXE)
        res = pg.evaluate("axe.run(document,{runOnly:['wcag2a','wcag2aa','wcag21aa']}).then(r=>r.violations.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,t:v.nodes.slice(0,2).map(n=>n.target.join(' '))})))")
        bad = [v for v in res if v["impact"] in ("serious", "critical")]
        assert not bad, (h, bad)


# ---- Milestone 5: one app, two businesses --------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_workspace_switcher_opens_the_other_business_in_the_same_app_with_its_own_wording_and_requirements(server, browser):
    base, envs = server
    pg = login(browser, base, "ada"); go(pg, "#/business", ".hero-card")
    assert "NASHA" in pg.inner_text("#who") and pg.locator("[data-ws=tenant-nasha]").get_attribute("aria-pressed") == "true"
    assert "stated requirements" in pg.inner_text("#main").lower(), "hospitality keeps recipes and shows its extra requirements"
    pg.click("[data-ws=tenant-fit]"); pg.wait_for_function("document.querySelector('#who b').innerText.includes('Meridian')"); pg.wait_for_function("document.querySelector('#main').innerText.includes('Cedar Park')"); pg.wait_for_load_state("networkidle")
    t = pg.inner_text("#main").lower()
    assert "cedar park" in t and "fitness studio" in t and "spin bike" in t and "new sales" in t, "studio wording and its requirements are shown"
    assert "menu item" not in t and "recipe" not in t.replace("recipes and/or", ""), "no hospitality wording on the studio screen"
    assert pg.locator("[data-ws=tenant-fit]").get_attribute("aria-pressed") == "true" and not pg.errors
    reqs = get(base, envs, "tenant-fit", "ada", "/projects")
    assert reqs, "the studio project is served by the same API"


def test_a_requirement_added_through_the_form_is_saved_and_a_viewer_cannot_add_one(server, browser):
    base, envs = server
    pg = login(browser, base, "ada", tenant="tenant-fit"); go(pg, "#/business", ".hero-card")
    pg.evaluate("document.querySelector('#rq').closest('details').open=true")
    pg.fill("#rq input[name=ref]", "ui-rack"); pg.fill("#rq input[name=name]", "UI test dumbbell rack"); pg.fill("#rq input[name=qty]", "2"); pg.click("#rq button"); pg.wait_for_selector(".toast.ok")
    pg.wait_for_function("document.querySelector('#main').innerText.includes('UI test dumbbell rack')")
    v = login(browser, base, "vic", tenant="tenant-fit"); go(v, "#/business", ".hero-card")
    assert v.query_selector("#rq") is None and "ui test dumbbell rack" in v.inner_text("#main").lower()


def test_supplier_cards_show_the_evidence_tier_and_no_real_supplier_is_shown_as_verified(server, browser):
    base, _ = server
    pg = login(browser, base, "ada"); go(pg, "#/suppliers", "#slist .sup"); pg.wait_for_timeout(500)
    t = pg.inner_text("#slist").lower()
    assert "evidence:" in t and "official-domain search snippet" in t and "secondary" in t
    assert "verified from public sources" not in t, "no research lead is presented as verified"


def test_the_second_business_screens_have_no_serious_axe_violations_or_overflow_at_phone_width(server, browser):
    if not AXE:
        pytest.skip("INTEGRATION UNAVAILABLE: axe-core not installed")
    base, envs = server
    pg = login(browser, base, "ada", tenant="tenant-fit", vp=(390, 844))
    for h in ("#/business", "#/suppliers", "#/financial", "#/procurement", "#/roadmap"):
        go(pg, h, "#main h1"); pg.wait_for_timeout(900)
        pg.evaluate("document.querySelectorAll('#main details').forEach(d=>d.open=true)")
        assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), ("horizontal overflow", h)
        pg.add_script_tag(path=AXE)
        res = pg.evaluate("axe.run(document,{runOnly:['wcag2a','wcag2aa','wcag21aa']}).then(r=>r.violations.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,t:v.nodes.slice(0,2).map(n=>n.target.join(' '))})))")
        bad = [v for v in res if v["impact"] in ("serious", "critical")]
        assert not bad, (h, bad)
