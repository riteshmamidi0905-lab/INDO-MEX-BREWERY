"""Reproducible dashboard screenshots + accessibility checks (Milestone 5). SYNTHETIC / OFFLINE.
Renders lab/results/ops/dashboard.html (the source of truth; `python -m nasha_lab.ops dashboard` regenerates it from the committed JSON) in headless Chromium at
desktop (1280 px) and phone (390 px) widths in light and dark colour schemes, writes full-page PNGs and dashboard_checks.json (horizontal overflow, axe-core violations,
first Tab stop). Needs `playwright` and `axe-playwright-python` and an installed Chromium (PLAYWRIGHT_BROWSERS_PATH); it never runs `playwright install`.

  python -m nasha_lab.ops.render_dashboard [--out DIR] [--png]      default: write dashboard_checks.json only; --png also writes the four PNGs (git-ignored)
"""
import argparse
import json
import os

from .util import RESULTS_DIR, dump_json

HTML = os.path.join(RESULTS_DIR, "dashboard.html")
COMBOS = [("light-desktop", "light", 1280, 800), ("light-phone", "light", 390, 844), ("dark-desktop", "dark", 1280, 800), ("dark-phone", "dark", 390, 844)]


def chromium_path():
    """NASHA_CHROMIUM, else the newest chromium-*/chrome-linux/chrome under PLAYWRIGHT_BROWSERS_PATH (the installed playwright package may expect a newer build than the one provisioned), else None (playwright's default)."""
    if os.environ.get("NASHA_CHROMIUM"): return os.environ["NASHA_CHROMIUM"]
    import glob
    found = sorted(glob.glob(os.path.join(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"), "chromium-*", "chrome-linux", "chrome")))
    return found[-1] if found else None


def render(out_dir=RESULTS_DIR, png=False, html=HTML):
    from playwright.sync_api import sync_playwright
    from axe_playwright_python.sync_playwright import Axe
    checks = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path(), args=["--no-sandbox"])
        for name, scheme, w, h in COMBOS:
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, device_scale_factor=1); page = ctx.new_page(); page.goto("file://" + os.path.abspath(html))
            sw = page.evaluate("document.documentElement.scrollWidth"); res = Axe().run(page)
            checks[name] = dict(scrollWidth=sw, viewport=w, horizontal_scroll=sw > w, axe=dict(violations=[v["id"] for v in res.response["violations"]], passes=len(res.response["passes"])))
            if name == "light-desktop":
                page.keyboard.press("Tab"); checks["first_tab_focus"] = page.evaluate("(()=>{const e=document.activeElement;return (e.className||e.tagName).toString()+':'+(e.textContent||'').trim().slice(0,40)})()")
            if png:
                os.makedirs(out_dir, exist_ok=True); page.screenshot(path=os.path.join(out_dir, f"dashboard-{name}.png"), full_page=True)
            ctx.close()
        browser.close()
    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=RESULTS_DIR); ap.add_argument("--png", action="store_true"); ap.add_argument("--html", default=HTML); ap.add_argument("--checks-to", default=None)
    a = ap.parse_args(argv); checks = render(a.out, a.png, a.html)
    dump_json(a.checks_to or os.path.join(a.out, "dashboard_checks.json"), checks); print(json.dumps(checks, indent=1)); return checks


if __name__ == "__main__":
    main()
