"""Local QA for website/collections-dist: structure, link targets, alt text, disclosures, forbidden words, then axe-core in real Chromium at
desktop and mobile widths (dark and light) plus a horizontal-overflow check. Needs Playwright (python) and axe.min.js (path via AXE env or the
portfolio repo's node_modules). Exit 1 on any problem.     python3 website/tools/qa_collections.py"""
import json
import os
import re
import subprocess
import sys
import threading
import http.server
import socketserver
from pathlib import Path

DIST = Path(__file__).resolve().parents[1] / "collections-dist"
AXE = os.environ.get("AXE", "/home/user/riteshmamidi0905-lab.github.io/node_modules/axe-core/axe.min.js")
FORBIDDEN = re.compile(r"™|®|halal|\bbeef\b|\bpork\b|add to cart|buy now|checkout|\bPAAPI\b", re.I)


def static_checks():
    problems = []
    pages = sorted(DIST.glob("*.html"))
    for p in pages:
        t = p.read_text()
        if t.count("<h1") != 1:
            problems.append(f"{p.name}: expected one h1")
        if 'content="noindex, nofollow"' not in t:
            problems.append(f"{p.name}: missing noindex")
        if "role=\"note\"" not in t or "Concept stage" not in t:
            problems.append(f"{p.name}: missing concept disclosure")
        for m in re.finditer(r"<img [^>]*>", t):
            if not re.search(r'alt="[^"]{20,}"', m.group(0)):
                problems.append(f"{p.name}: image without a descriptive alt")
        for href in re.findall(r'(?:href|src|srcset)="([^":#]+?)"', t):
            if not href.startswith(("http", "data:")) and not (DIST / href).exists():
                problems.append(f"{p.name}: broken local reference {href}")
        vis = re.sub(r"<(script|style)[\s\S]*?</\1>|<[^>]+>", " ", t)
        vis = vis.replace("No beef and no pork on any menu", " ")      # the dietary policy statement itself is allowed
        if FORBIDDEN.search(vis):
            problems.append(f"{p.name}: forbidden wording {FORBIDDEN.search(vis).group(0)!r}")
    return problems


def browser_checks():
    from playwright.sync_api import sync_playwright
    os.chdir(DIST)
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), Q)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    axe = Path(AXE).read_text()
    out, problems = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"), args=["--no-sandbox"])
        for width, label in ((1280, "desktop"), (390, "mobile")):
            for scheme in ("dark", "light"):
                ctx = b.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
                for f in sorted(DIST.glob("*.html")):
                    pg = ctx.new_page()
                    errs = []
                    pg.on("console", lambda m, errs=errs: errs.append(m.text) if m.type == "error" else None)
                    pg.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
                    pg.goto(f"http://127.0.0.1:{port}/{f.name}", wait_until="load")
                    pg.add_script_tag(content=axe)
                    res = pg.evaluate("axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}}).then(r=>r.violations.map(v=>({id:v.id,n:v.nodes.length})))")
                    ov = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    out.append({"page": f.name, "width": width, "scheme": scheme, "axe_violations": res, "overflow_px": ov, "console_errors": errs})
                    if res:
                        problems.append(f"{f.name} {label} {scheme}: axe {res}")
                    if ov > 0:
                        problems.append(f"{f.name} {label} {scheme}: horizontal overflow {ov}px")
                    if errs:
                        problems.append(f"{f.name} {label} {scheme}: console errors {errs}")
                    pg.close()
                ctx.close()
        b.close()
    srv.shutdown()
    return out, problems


if __name__ == "__main__":
    sp = static_checks()
    res, bp = browser_checks()
    (DIST / "qa-results.json").write_text(json.dumps(res, indent=1))
    pr = sp + bp
    print(f"static problems: {len(sp)}; browser runs: {len(res)}; browser problems: {len(bp)}")
    for x in pr:
        print(" -", x)
    sys.exit(1 if pr else 0)
