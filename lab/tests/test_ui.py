import json, os, socket, threading, time
import pytest

pw = pytest.importorskip("playwright.sync_api", reason="INTEGRATION UNAVAILABLE: playwright not installed")
import uvicorn
from nasha_lab import api, agent, eval_agent as EA, identity as ID, knowledge, world as W

CHROME = os.environ.get("NASHA_CHROMIUM") or next((p for p in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",) if os.path.exists(p)), None)
pytestmark = pytest.mark.skipif(CHROME is None and not os.environ.get("NASHA_UI_PLAYWRIGHT_MANAGED"), reason="INTEGRATION UNAVAILABLE: no Chromium (set NASHA_CHROMIUM or install one with `playwright install chromium`)")


@pytest.fixture()
def server():
    w = W.build_world(1)[0]; svc = agent.AgentService(w, knowledge.default_kb(), authority=ID.Authority.dev())
    app = api.create_app(service=svc); s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")); t = threading.Thread(target=srv.run, daemon=True); t.start()
    for _ in range(100):
        try: socket.create_connection(("127.0.0.1", port), 0.2).close(); break
        except OSError: time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", svc, w
    srv.should_exit = True; t.join(5)


@pytest.fixture()
def page(server):
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch()
        pg = b.new_page(bypass_csp=True); pg.errors = []; pg.on("pageerror", lambda e: pg.errors.append(str(e))); pg.on("dialog", lambda d: d.accept())
        pg.goto(server[0] + "/review"); yield pg; b.close()


def login(page, who, pc):
    page.fill("#rid", who); page.fill("#pass", pc); page.click("#login button[type=submit]"); page.wait_for_selector("#who:not(:empty)")


def investigate(page, ev):
    page.click(f"button[aria-label='Investigate event {ev}']"); page.wait_for_selector("#runview:not([hidden])"); page.wait_for_function("document.getElementById('headline').textContent.length > 3")


def test_loads_without_errors_and_with_the_disclosure_banner(page):
    assert "SYNTHETIC DATA" in page.inner_text("header") and page.title() == "NASHA Lab Review Console"
    page.wait_for_selector("#events tr"); assert page.locator("#events tr").count() >= 9 and page.errors == []


def test_no_serious_accessibility_violations(page):
    from axe_playwright_python.sync_playwright import Axe
    login(page, "founder", ID.DEV_PASSCODES["founder"][1]); investigate(page, "EV-A1")
    res = Axe().run(page); bad = [v for v in res.response["violations"] if v["impact"] in ("serious", "critical", "moderate")]
    assert bad == [], [(v["id"], v["impact"], len(v["nodes"])) for v in bad]


def test_full_flow_sign_in_investigate_approve(page):
    login(page, "founder", ID.DEV_PASSCODES["founder"][1]); investigate(page, "EV-A1")
    assert "DRAFT_PURCHASE_RECOMMENDATION" in page.inner_text("#action") and page.locator("#claims tr").count() >= 2 and "D-" in page.inner_text("#cites")
    assert "release_draft" in page.inner_text("#muts") and "placing a purchase order" in page.inner_text("#nots")
    page.click("#approve"); page.wait_for_function("document.getElementById('final').textContent.includes('APPROVED_AND_EXECUTED_IN_SIMULATION')")
    assert "external actions performed: 0" in page.inner_text("#final") and page.locator("#approve").is_disabled()


def test_wrong_role_is_refused_visibly_and_the_run_stays_open(page):
    login(page, "alice", ID.DEV_PASSCODES["alice"][1]); investigate(page, "EV-C1")
    page.click("#approve"); page.wait_for_function("document.getElementById('status').textContent.includes('ROLE_NOT_PERMITTED')")
    assert page.locator("#approve").is_enabled() and "AWAITING_HUMAN" in page.inner_text("#runstatus")


def test_actions_need_sign_in(page):
    page.wait_for_selector("#events tr"); page.click("button[aria-label='Investigate event EV-B1']"); page.wait_for_selector("#runview:not([hidden])")
    page.click("#reject"); assert "Sign in first" in page.inner_text("#status")


def test_reject_executes_nothing(page, server):
    login(page, "bob", ID.DEV_PASSCODES["bob"][1]); investigate(page, "EV-B2"); page.click("#reject")
    page.wait_for_function("document.getElementById('final').textContent.includes('REJECTED_BY_HUMAN_NO_ACTION')")
    assert server[2].q("SELECT COUNT(*) n FROM review_queue")[0]["n"] == 0


def test_edit_quantity_returns_to_review(page):
    login(page, "alice", ID.DEV_PASSCODES["alice"][1]); investigate(page, "EV-A1"); page.fill("#qty", "25"); page.click("#edit")
    page.wait_for_function("document.getElementById('status').textContent.includes('review again')"); assert page.locator("#approve").is_enabled()


def test_supplier_controlled_text_is_rendered_as_text_never_as_markup(page, server):
    url, svc, w = server
    w.con.execute("INSERT INTO supplier_proposals VALUES('P-88','S01','<img src=x onerror=window.PWNED=1> chicken <script>window.PWNED=1</script> bouillon base','animal source unspecified','MISSING')")
    w.con.execute("INSERT INTO operational_incidents VALUES('EV-X8','POLICY_REVIEW','{\"proposal_id\": \"P-88\"}','2026-04-28')"); page.reload(); page.wait_for_selector("#events tr")
    login(page, "founder", ID.DEV_PASSCODES["founder"][1]); investigate(page, "EV-X8")
    assert page.evaluate("window.PWNED") is None and page.locator("#main img").count() == 0 and page.locator("#main script").count() == 0
    assert "untrusted" in page.inner_text("#claims").lower() or "withheld" in page.inner_text("#claims").lower()


def test_focus_moves_to_the_investigation_and_the_page_is_keyboard_operable(page):
    login(page, "founder", ID.DEV_PASSCODES["founder"][1]); page.focus("button[aria-label='Investigate event EV-A1']"); page.keyboard.press("Enter")
    page.wait_for_function("document.activeElement && document.activeElement.id === 'runview'")
    page.keyboard.press("Tab"); assert page.evaluate("document.activeElement.tagName") in ("SUMMARY", "BUTTON", "TEXTAREA", "INPUT", "A")


def test_no_horizontal_scroll_on_a_phone(server):
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch(); pg = b.new_page(viewport={"width": 375, "height": 800}, bypass_csp=True); pg.goto(server[0] + "/review"); pg.wait_for_selector("#events tr")
        login(pg, "founder", ID.DEV_PASSCODES["founder"][1]); investigate(pg, "EV-A1")
        assert pg.evaluate("document.documentElement.scrollWidth") <= 376; b.close()


def test_security_headers_on_the_review_page(server):
    import urllib.request
    r = urllib.request.urlopen(server[0] + "/review")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"] and r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["Cache-Control"] == "no-store"
