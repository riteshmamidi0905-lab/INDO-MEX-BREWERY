#!/usr/bin/env python3
"""Validate the Founder Vision Preview (website/family-dist): private, noindex, self-contained, family-safe copy, honest, accessible markup.
No internal project language may appear in visible text. Usage: python3 tools/validate_family.py"""
import csv, glob, os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "website/family-dist")
fails = []
def fail(m): fails.append(m)

NAV = ["Home", "Food", "Beer", "The Court", "The Experience", "Our Story"]
INTERNAL = [r"\bevidence\b", r"\bscores?\b", r"\bvalidat\w*", r"\bgates?\b", r"provenance", r"\baudit\w*", r"\bsprint\b", r"\bVP-\d+", r"\bD-\d+", r"decision register", r"repository", r"blueprint",
            r"diligence", r"\binvest\w*", r"\bQA\b", r"lighthouse", r"hypothes\w*", r"pre-capital", r"\bMVP\b", r"data room", r"assumption", r"\bcapital\b", r"\bnoindex\b", r"\bunverified\b"]
CLAIMS = [(r"™|®", "trademark symbol"), (r"\bhalal\b", "halal wording"), (r"\b(beef|pork|lard|bacon|gelatin)\b", "beef, pork or hidden derivative wording (D-54)"),
          (r"\b(now open|opening soon|order now|book a table|reserve|reservations?|buy tickets|add to cart|pre-?order)\b", "commerce or open claim"),
          (r"\b(award[- ]winning|best in austin|world[- ]class|guarantee\w*|proven|certified|verified|trademark(ed)?|cleared)\b", "unearned claim"),
          (r"\b(our customers|our guests say|testimonials?|reviews?)\b", "fabricated social proof"),
          (r"\b(we serve|we brew|we are open|our brewery is open)\b", "present-tense operating claim")]

class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.text = []; s.h = []; s.imgs = []; s.links = []; s.ids = set(); s.skip = 0; s.nav = []; s.in_nav = False; s.in_a = False; s.meta = {}; s.title = ""; s.in_title = False; s.tags = set(); s.srcs = []
    def handle_starttag(s, t, a):
        a = dict(a); s.tags.add(t)
        if t in ("script", "style"): s.skip += 1
        if t == "title": s.in_title = True
        if t == "meta" and a.get("name"): s.meta[a["name"]] = a.get("content", "")
        if t in ("h1", "h2", "h3"): s.h.append(int(t[1]))
        if t == "img": s.imgs.append(a)
        if t == "a" and a.get("href") is not None: s.links.append(a["href"]); s.in_a = True
        if t == "nav" and a.get("aria-label") == "Main": s.in_nav = True
        if "id" in a: s.ids.add(a["id"])
        for k in ("src", "srcset", "href"):
            if k in a: s.srcs.append(a[k])
    def handle_endtag(s, t):
        if t in ("script", "style"): s.skip -= 1
        if t == "title": s.in_title = False
        if t == "nav": s.in_nav = False
        if t == "a": s.in_a = False
    def handle_data(s, d):
        if s.in_title: s.title += d
        if s.skip: return
        if s.in_nav and s.in_a and d.strip(): s.nav.append(d.strip())
        s.text.append(d)

files = sorted(glob.glob(D + "/*.html"))
if len(files) != 6: fail(f"expected 6 pages, found {len(files)}")
pages = {}
for f in files:
    h = open(f, encoding="utf-8").read(); n = os.path.basename(f); p = P(); p.feed(h); pages[n] = p
    if '<html lang="en"' not in h: fail(f"{n}: html lang")
    if not p.title.strip() or len(p.title) > 70: fail(f"{n}: title")
    if p.h.count(1) != 1: fail(f"{n}: needs one h1")
    for a, b in zip(p.h, p.h[1:]):
        if b > a + 1: fail(f"{n}: heading jump h{a} to h{b}")
    for tag in ("main", "header", "footer", "nav"):
        if tag not in p.tags: fail(f"{n}: missing <{tag}>")
    if "noindex" not in p.meta.get("robots", ""): fail(f"{n}: must be noindex")
    if 'href="#main"' not in h: fail(f"{n}: skip link")
    if p.nav != NAV: fail(f"{n}: main navigation must be exactly {NAV}, got {p.nav}")
    for i in p.imgs:
        if not (i.get("alt") and len(i["alt"]) > 20): fail(f"{n}: image without meaningful alt")
        if not re.search(r"\d+", i.get("width", "")) or not re.search(r"\d+", i.get("height", "")): fail(f"{n}: img lacks width/height")
    if re.search(r'(src|href)=["\']https?://', h) or "//cdn" in h: fail(f"{n}: external URL")
    if re.search(r"google-analytics|gtag|fbq\(|hotjar|segment\.com|doubleclick", h, re.I): fail(f"{n}: tracker")
    t = re.sub(r"\s+", " ", " ".join(p.text))
    for pat in INTERNAL:
        for m in re.finditer(pat, t, re.I): fail(f"{n}: internal project language in visible text: ...{t[max(0, m.start()-25):m.end()+25]}...")
    for pat, why in CLAIMS:
        for m in re.finditer(pat, t, re.I): fail(f"{n}: {why}: ...{t[max(0, m.start()-30):m.end()+30]}...")
    if "founder's vision" not in t or "concept in development" not in t or "working name" not in t: fail(f"{n}: footer concept notice missing")
    if len(h.encode()) > 60000: fail(f"{n}: html too large")
    for l in p.links:
        if not l or l.startswith(("data:", "mailto:")): continue
        path, _, frag = l.partition("#")
        if path and not os.path.exists(os.path.join(D, path)): fail(f"{n}: broken link {l}")
        if path in ("labs.html", "investor.html", "craft.html", "evening.html", "space.html", "experience.html") and path == "labs.html": fail(f"{n}: internal page linked")
    for rel in re.findall(r'images/[A-Za-z0-9_.-]+', h):
        if not os.path.exists(os.path.join(D, rel)): fail(f"{n}: missing image {rel}")
css = open(D + "/family.css", encoding="utf-8").read(); js = open(D + "/family.js", encoding="utf-8").read()
if "prefers-reduced-motion" not in css: fail("css lacks prefers-reduced-motion")
if re.search(r"https?://|@import", css): fail("css has an external reference")
if re.search(r"fetch\(|XMLHttpRequest|https?://", js): fail("js makes network requests or has absolute URLs")
if len(css) > 40000 or len(js) > 4000: fail("css or js too large")
ALLOWED = {".html", ".css", ".js", ".woff2", ".txt", ".avif", ".webp", ".jpg"}
man = {r["id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "visuals/NASHA-VISUAL-MANIFEST.csv"), encoding="utf-8"))}
for f in glob.glob(D + "/**/*", recursive=True):
    if os.path.isfile(f):
        ext = os.path.splitext(f)[1]
        if ext not in ALLOWED: fail(f"disallowed file type {f}")
        if "/images/" in f:
            vid = os.path.basename(f).rsplit("-", 2)[0]
            if vid not in man: fail(f"image {os.path.basename(f)} not in the visual manifest")
            elif man[vid]["rights_status"] not in ("PROVISIONAL-LOCAL-ONLY", "OWNED-BY-PROJECT-AI-ASSISTED"): fail(f"{vid}: unapproved rights status")
for lic in ("LICENSE-Inter.txt", "LICENSE-InstrumentSerif.txt"):
    if not os.path.exists(os.path.join(D, "fonts", lic)): fail(f"missing {lic}")
big = [f for f in glob.glob(D + "/images/*") if os.path.getsize(f) > 450000]
if big: fail(f"oversized image derivatives: {[os.path.basename(b) for b in big][:3]}")
for f in files:
    if len(open(f, encoding="utf-8").read()) < 800: fail(f"{f}: nearly empty")
print(f"FAMILY: {len(files)} pages, {len(glob.glob(D + '/**/*', recursive=True))} entries, {len(fails)} fail")
for m in fails[:40]: print("FAIL", m)
sys.exit(1 if fails else 0)
