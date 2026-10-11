#!/usr/bin/env python3
"""Website validation for website/dist. Run from repo root: python3 tools/validate_site.py (exit 1 on failure).
Static checks: internal links and anchors, HTML semantics (lang, title, one h1, heading order, alt text, labels, landmarks),
no third-party resources or trackers, noindex, prohibited claims, rights-register coverage, fonts licensed, performance budget,
and that the committed real-browser QA result (website/qa/results/latest.json) has no violations and is not stale versus dist/."""
import csv, glob, hashlib, json, os, re, sys
from html import unescape as html_unescape
from html.parser import HTMLParser
D="website/dist"; fails=[]
def fail(m): fails.append(m); print("FAIL",m)
class P(HTMLParser):
    def __init__(s): super().__init__(); s.tags=[]; s.ids=set(); s.links=[]; s.heads=[]; s.imgs=[]; s.title=""; s._t=False; s.attrs=[]; s.text=[]; s.inscript=False; s.labels=set(); s.inputs=[]; s.buttons=[]; s._b=None; s.svg=False
    def handle_starttag(s,t,a):
        a=dict(a); s.tags.append(t); s.attrs.append((t,a))
        if "id" in a: s.ids.add(a["id"])
        if t=="a" and "href" in a: s.links.append(a["href"])
        if t in("link",) and "href" in a: s.links.append(a["href"])
        if t=="script": s.inscript=True; s.links.append(a.get("src","")) if "src" in a else None
        if t=="img": s.imgs.append(a)
        if re.fullmatch(r"h[1-6]",t): s.heads.append(int(t[1]))
        if t=="svg": s.svg=True
        if t=="title" and not s.svg: s._t=True
        if t=="label": s.labels.add(a.get("for",""))
        if t=="input": s.inputs.append(a)
        if t=="svg" and a.get("role")=="img" and not a.get("aria-labelledby") and not a.get("aria-label"): fail(f"{s.f}: role=img svg without accessible name")
    def handle_endtag(s,t):
        if t=="svg": s.svg=False
        if t=="title": s._t=False
        if t=="script": s.inscript=False
    def handle_data(s,d):
        if s._t: s.title+=d
        elif not s.inscript: s.text.append(d)
# ---- protected-material gate: nothing but web-necessary assets in dist ----
ALLOWED_EXT={".html",".css",".js",".woff2",".txt",".avif",".webp",".jpg"}
for x in glob.glob(D+"/**/*",recursive=True):
    if os.path.isfile(x):
        ext=os.path.splitext(x)[1].lower(); rel=os.path.relpath(x,D)
        if ext not in ALLOWED_EXT: fail(f"dist file type not allowed (possible source/master leak): {rel}")
        if re.search(r"logo|master|exploration|rejected|attorney|trademark|\.psd|\.ai$|\.fig|\.sketch|\.eps",rel,re.I): fail(f"dist file name suggests protected material: {rel}")
if os.path.exists(D+"/brand") or os.path.exists(D+"/ip"): fail("dist contains brand/ or ip/ directory")
files=sorted(glob.glob(D+"/*.html"))
_beer=open(D+"/beer.html",encoding="utf-8").read() if os.path.exists(D+"/beer.html") else ""
_food=open(D+"/food.html",encoding="utf-8").read() if os.path.exists(D+"/food.html") else ""
if "Style-based concept visualization" not in _beer or "Not brewed yet" not in _beer: fail("beer page must label beers 'Not brewed yet' and 'Style-based concept visualization'")
if "not cooked or tested" not in _food: fail("food page must label dishes 'Proposed presentation · not cooked or tested'")
if "not sensory tested" not in _food.lower(): fail("pairings must say 'not sensory tested'")
if not files: fail("no website/dist/*.html (run python3 website/build.py)"); print("SITE:",len(fails),"fail"); sys.exit(1)
pages={}
for f in files:
    p=P(); p.f=f; p.feed(open(f,encoding="utf-8").read()); pages[os.path.basename(f)]=p
    h=open(f,encoding="utf-8").read()
    if not re.search(r'<html lang="en"',h): fail(f"{f}: missing html lang")
    if not p.title.strip() or len(p.title)>70: fail(f"{f}: title missing or too long")
    if p.heads.count(1)!=1: fail(f"{f}: needs exactly one h1 (has {p.heads.count(1)})")
    for a,b in zip(p.heads,p.heads[1:]):
        if b>a+1: fail(f"{f}: heading level jumps h{a} to h{b}")
    for i in p.imgs:
        if "alt" not in i: fail(f"{f}: img without alt")
    for lm in ("<main","<header","<footer",'<nav'):
        if lm not in h: fail(f"{f}: missing landmark {lm}>")
    if 'name="robots" content="noindex' not in h: fail(f"{f}: pre-launch pages must be noindex")
    if 'name="viewport"' not in h or 'name="description"' not in h: fail(f"{f}: missing viewport/description")
    for i in p.inputs:
        if i.get("type") not in ("hidden","submit","button") and i.get("id") not in p.labels and not re.search(r"<label[^>]*>[^<]*<input[^>]*"+re.escape(i.get("name","@@")),h): fail(f"{f}: input without label")
    if "href=\"#main\"" not in h: fail(f"{f}: missing skip link")
    # external resources and trackers
    if re.search(r'(src|href)=["\']https?://',h): fail(f"{f}: external URL in src/href (no third-party resources allowed pre-launch)")
    if re.search(r"google-analytics|gtag|googletagmanager|fbq\(|hotjar|segment\.com|doubleclick",h,re.I): fail(f"{f}: tracker reference")
    # prohibited claims
    t=" ".join(p.text)
    for pat,why in [(r"\bhalal\b","halal wording (D-54)"),(r"™|®","trademark symbol (no clearance)"),(r"\b(now open|opening soon|order now|book a table|reserve a table|buy tickets|buy now|add to cart)\b","commerce or open claim"),
                    (r"\b(award[- ]winning|best in austin|sold out|as seen)\b","unearned claim"),(r"\b(our brewery is|we brew|we serve|we are open)\b","present-tense operating claim"),
                    (r"\b(testimonial|\d+ (guests|customers|reviews))\b","fabricated social proof"),(r"\b(guarantee|proven|certified)\b","unsupported certainty")]:
        for m in re.finditer(pat,t,re.I):
            ctx=t[max(0,m.start()-40):m.end()+40]
            if re.search(r"\b(no|not|never|nothing|none|without|isn.?t|aren.?t)\b",ctx,re.I) and pat!=r"\bhalal\b": continue
            fail(f"{f}: {why}: …{ctx.strip()}…")
    if not re.search(r"in development|Illustrations show a concept|concept",t,re.I): fail(f"{f}: development/concept disclosure missing")
import csv as _csv
MAN={r["id"]:r for r in _csv.DictReader(open("visuals/NASHA-VISUAL-MANIFEST.csv",encoding="utf-8"))}
for fn,p in pages.items():
    h=open(os.path.join(D,fn),encoding="utf-8").read()
    for m in re.finditer(r'<figure class="fig[^"]*" data-vid="([^"]+)"[^>]*>(.*?)</figure>',h,re.S):
        vid,inner=m.group(1),m.group(2)
        if vid not in MAN: fail(f"{fn}: figure {vid} not in visual manifest"); continue
        r=MAN[vid]
        if r["status"].startswith("NOT GENERATED"): fail(f"{fn}: unbuilt planned asset {vid} used on a page")
        if "class=\"tag\"" not in inner or "Concept" not in inner: fail(f"{fn}: figure {vid} lacks a concept label")
        if "<img" in inner:
            im=re.search(r"<img[^>]*>",inner).group(0)
            if not re.search(r'width="\d+" height="\d+"',im): fail(f"{fn}: {vid} img lacks width/height")
            if not re.search(r'alt="[^"]{25,}"',im): fail(f"{fn}: {vid} alt text missing or too short")
            if "Concept visualization" not in re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",html_unescape(r["alt_text"]))) and "Concept visualization" not in r["alt_text"]: fail(f"{fn}: {vid} alt should say it is a concept visualization")
            lazy="loading=\"lazy\"" in im
            if fn=="index.html" and vid=="NV-HERO-01":
                if lazy or "fetchpriority=\"high\"" not in im: fail("hero image must be eager with fetchpriority high")
            elif not lazy: fail(f"{fn}: {vid} below-the-fold image must be lazy")
            if "image/avif" not in inner or "image/webp" not in inner or "(max-width: 700px)" not in inner: fail(f"{fn}: {vid} needs avif+webp sources and a mobile composition")
        if r["rights_status"] not in ("PROVISIONAL-LOCAL-ONLY","OWNED-BY-PROJECT-AI-ASSISTED"): fail(f"{fn}: {vid} has unapproved rights status {r['rights_status']}")
names={os.path.basename(x) for x in glob.glob(D+"/**/*",recursive=True) if os.path.isfile(x)}
for fn,p in pages.items():
    for l in p.links:
        if not l or l.startswith(("data:","mailto:")): continue
        path,_,frag=l.partition("#")
        if path and not os.path.exists(os.path.join(D,path)): fail(f"{fn}: broken link {l}")
        elif frag and (pages[path or fn].ids if (path or fn) in pages else set()) and frag not in pages[path or fn].ids: fail(f"{fn}: missing anchor {l}")
        elif frag and (path or fn) in pages and frag not in pages[path or fn].ids: fail(f"{fn}: missing anchor {l}")
css=open(D+"/styles.css").read()
for u in re.findall(r"url\(\"?([^)\"]+)",css):
    if u.startswith("http"): fail("css external url "+u)
    elif not os.path.exists(os.path.join(D,u)): fail("css missing "+u)
js=open(D+"/app.js").read()
if re.search(r"fetch\(|XMLHttpRequest|https?://",js): fail("app.js makes network requests or has absolute URLs")
if "prefers-reduced-motion" not in css: fail("css lacks prefers-reduced-motion")
# fonts licensed
for f in glob.glob(D+"/fonts/*.woff2"):
    fam="Inter" if "inter" in f else "InstrumentSerif"
    if not os.path.exists(f"{D}/fonts/LICENSE-{fam}.txt"): fail(f"font {f} has no licence file in dist")
prov=[r for r in csv.DictReader(open("ip/website-asset-rights-register.csv")) if r["status"]=="provisional-local-only"]
print(f"provisional-rights images (blocked from public launch until cleared): {len(prov)}")
for f in files:
    if prov and 'name="robots" content="noindex' not in open(f,encoding="utf-8").read(): fail(f"{f}: provisional-rights images present, page must stay noindex")
    t=open(f,encoding="utf-8").read()
    if "temporary typographic placeholder" not in t: fail(f"{f}: footer must disclose the temporary typographic wordmark")
    if 'rel="icon" href="data:,"' not in t: fail(f"{f}: favicon must stay empty until a logo is approved")
# rights register coverage
reg={r["name"]:r for r in csv.DictReader(open("ip/website-asset-rights-register.csv"))}
allfiles=[os.path.relpath(x,D).replace(os.sep,"/") for x in glob.glob(D+"/**/*",recursive=True) if os.path.isfile(x)]
for rel in allfiles:
    key=rel if not rel.startswith("fonts/") else None
    if rel.startswith("images/"): ok=any(rel.split("/")[1].startswith(n+"-") for n in reg)
    elif rel.startswith("fonts/"): ok=any(rel.split("/")[1] in n for n in reg)
    else: ok=rel in reg
    if not ok: fail(f"asset {rel} not covered by ip/website-asset-rights-register.csv (run website/build.py)")
for r in reg.values():
    if r["status"]=="in use" and not (r["licence"] and r["creation_method"]): fail(f"rights row {r['asset_id']} incomplete")
# performance budget (gzip-free raw bytes of HTML+CSS+JS per page, fonts counted separately)
for f in files:
    b=os.path.getsize(f)+os.path.getsize(D+"/styles.css")+os.path.getsize(D+"/app.js")
    if b>150_000: fail(f"{f}: HTML+CSS+JS {b} bytes exceeds 150 KB budget")
    b=0
    if b>150_000: fail(f"{f}: HTML+CSS+JS {b} bytes exceeds 150 KB budget")
fb=sum(os.path.getsize(x) for x in glob.glob(D+"/fonts/*.woff2"))
if fb>200_000: fail(f"fonts {fb} bytes exceed 200 KB budget")
# QA results present, clean, and not stale
qp="website/qa/results/latest.json"
if not os.path.exists(qp): fail("no QA results; run: cd website/qa && npm i && node run-qa.mjs")
else:
    q=json.load(open(qp)); s=q["summary"]
    if s["axeViolations"] or s["overflowFailures"] or s["consoleIssues"]: fail(f"QA result has issues: {s}")
    if s["maxCls"]>0.1 or s["maxLcpMs"]>2500: fail(f"QA performance over budget: {s}")
    if s["homeInitialBytes"]>450_000: fail(f"home initial transfer {s['homeInitialBytes']} bytes exceeds 450 KB budget")
    if q["slow"].get("heroReadyMs",1e9)>6000: fail(f"hero not ready within 6 s on the slow profile: {q['slow']}")
    for pg,v in q["imagesBlocked"].items():
        if v["overflow"] or v["withAlt"]!=v["imgs"]: fail(f"image-failure test failed on {pg}: {v}")
    h=hashlib.sha256(b"".join(open(os.path.join(D,f),"rb").read() for f in sorted(os.listdir(D)) if re.search(r"\.(html|css|js)$",f))).hexdigest()[:16]
    if q.get("distHash")!=h: fail("QA results are stale: dist changed since run-qa.mjs (rerun build and QA)")
    if set(q["pages"])!=set(pages): fail("QA result covers different pages than dist")
    mq=q.get("manual")
    if not mq: fail("QA lacks manual-review aids (focus, text spacing, 200% zoom)")
    else:
        for pg,x in mq["focus"].items():
            if x["withoutVisibleOutline"]: fail(f"{pg}: focusable elements without a visible focus outline: {x['sample']}")
        for pg,x in mq["textSpacing"].items():
            if x["overflowX"]: fail(f"{pg}: text-spacing override (WCAG 1.4.12) causes horizontal overflow")
        for pg,x in mq["zoom200"].items():
            if x["overflowX"]: fail(f"{pg}: 200% zoom reflow overflows horizontally")
    if not q["interaction"]["firstTabIsSkipLink"]: fail("QA: skip link is not first tab stop")
print(f"SITE: {len(files)} pages, {len(allfiles)} files, {len(fails)} fail")
sys.exit(1 if fails else 0)
