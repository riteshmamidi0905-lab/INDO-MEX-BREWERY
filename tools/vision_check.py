#!/usr/bin/env python3
"""Vision layer guard (Sprint 25). ASSUME FOR VISION. VERIFY BEFORE IMPLEMENTATION.
Checks that the vision layer (vision/) stays separate from the frozen Blueprint and from evidence:
assumption register shape, asset classes, no vision asset treated as real/validated, vision figures on the site are labelled, no prices or logo claims.
Usage: python3 tools/vision_check.py [check|selftest]"""
import csv, glob, hashlib, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "vision")
CLASSES = {"REAL", "FOUNDER PROTOTYPE", "VISION", "CONCEPT", "RESEARCH REFERENCE"}
SUBCLASSES = {"VISION PLACE", "VISION FOOD", "VISION BEER", "VISION NA", "CONCEPT ILLUSTRATION", "VISION BOARD", "(none)", "(none registered)"}
AS_COLS = ["id", "area", "assumption", "why_chosen", "blueprint_unknown_it_temporarily_resolves", "visual_experience_effect", "implementation_gate", "changeable"]
FLAG_COLS = ["id", "area", "what_is_being_referenced", "caution", "reviewer_needed", "needed_before", "severity", "status"]
BAD_TEXT = [(r"™|®", "trademark symbol (D-66)"), (r"\bhalal\b", "halal wording (D-54)"), (r"\$\s?\d", "a price or dollar amount"),
            (r"official logo|final logo", "logo claim (D-66)"), (r"\b(?:actual|verified|validated) (?:site|cost|recipe|demand)\b", "vision promoted to fact")]


def rows(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check():
    errs = []
    a = rows(os.path.join(V, "data/VISION-ASSUMPTIONS.csv"))
    if list(a[0].keys()) != AS_COLS: errs.append("VISION-ASSUMPTIONS.csv columns changed")
    ids = [r["id"] for r in a]
    if len(set(ids)) != len(ids): errs.append("duplicate vision assumption ids")
    for r in a:
        if not re.fullmatch(r"V-\d\d", r["id"]): errs.append(f"{r['id']}: id format")
        for c in AS_COLS:
            if not r[c].strip(): errs.append(f"{r['id']}: empty {c}")
        if r["changeable"] not in ("Yes", "No"): errs.append(f"{r['id']}: changeable must be Yes or No")
    if len(a) > 40: errs.append("vision assumption register is flooded with small decisions (max 40)")
    f = rows(os.path.join(V, "data/VISION-CULTURAL-FLAGS.csv"))
    if list(f[0].keys()) != FLAG_COLS: errs.append("VISION-CULTURAL-FLAGS.csv columns changed")
    m = rows(os.path.join(V, "data/VISION-ASSET-MANIFEST.csv"))
    proto = os.path.join(ROOT, "visuals/FOUNDER-PROTOTYPE-MEDIA.csv")
    nproto = len(rows(proto)) if os.path.exists(proto) else 0
    for r in m:
        if r["asset_class"] not in CLASSES: errs.append(f"{r['asset_id']}: unknown asset class {r['asset_class']}")
        if r["subclass"] not in SUBCLASSES: errs.append(f"{r['asset_id']}: unknown subclass {r['subclass']}")
        if r["asset_class"] == "VISION" and re.search(r"VALIDATED|REAL|PROTOTYPE", r["status"]): errs.append(f"{r['asset_id']}: vision asset has a real or validated status")
        if r["asset_id"].startswith("VP-") and r["status"] != "PROMPT READY — NOT GENERATED":
            if not os.path.exists(os.path.join(ROOT, "visuals/vision")): errs.append(f"{r['asset_id']}: marked generated but visuals/vision/ does not exist")
        if r["asset_class"] in ("REAL", "FOUNDER PROTOTYPE") and r["status"] not in ("EMPTY", "DOES NOT EXIST") and nproto == 0:
            errs.append(f"{r['asset_id']}: real or prototype asset claimed but the founder prototype register is empty")
    # vision text hygiene
    for p in glob.glob(os.path.join(V, "*.md")) + glob.glob(os.path.join(V, "data/*.csv")):
        t = open(p, encoding="utf-8").read()
        for pat, why in BAD_TEXT:
            for mm in re.finditer(pat, t, re.I):
                ctx = t[max(0, mm.start() - 220):mm.end() + 30]
                if re.search(r"\b(no|not|never|without|nor)\b", ctx, re.I): continue
                errs.append(f"{os.path.relpath(p, ROOT)}: {why}: …{ctx.strip()}…")
    for need in ("VISION FLAGSHIP — NOT CONSTRUCTION DESIGN", "ASSUME FOR VISION"):
        if need not in open(os.path.join(V, "README.md"), encoding="utf-8").read() + open(os.path.join(V, "VISION-WORLD-BIBLE.md"), encoding="utf-8").read():
            errs.append(f"vision docs lack required phrase: {need}")
    # site: every vision figure is labelled and registered
    man = {r["asset_id"] for r in m}
    for p in glob.glob(os.path.join(ROOT, "website/dist/*.html")):
        h = open(p, encoding="utf-8").read()
        for mm in re.finditer(r'<figure[^>]*data-vision="([^"]+)"[^>]*>(.*?)</figure>', h, re.S):
            vid, inner = mm.group(1), mm.group(2)
            if vid not in man: errs.append(f"{os.path.basename(p)}: vision figure {vid} not in VISION-ASSET-MANIFEST.csv")
            if 'class="tag"' not in inner or "Vision" not in inner: errs.append(f"{os.path.basename(p)}: vision figure {vid} lacks a Vision label")
    # the frozen blueprint must not be edited by vision work
    fz = os.path.join(ROOT, "docs/company/data/blueprint-freeze.csv")
    t = open(fz, encoding="utf-8").read()
    if "FROZEN" not in t: errs.append("blueprint-freeze.csv no longer says FROZEN")
    try:
        d = subprocess.run(["git", "diff", "--quiet", "8e46d7b", "--", "docs/company/data/blueprint-freeze.csv"], cwd=ROOT).returncode
        if d == 1: errs.append("blueprint-freeze.csv changed since the freeze record 8e46d7b (vision work must not edit Blueprint v1.0)")
    except Exception:
        pass
    # Round 2 architecture freeze (founder-confirmed): VP-01..VP-04 files must not change
    fzp = os.path.join(V, "production/ROUND2-FREEZE.csv")
    if os.path.exists(fzp):
        for fr in rows(fzp):
            fpath = os.path.join(ROOT, fr["file"])
            if not os.path.exists(fpath): errs.append(f"Round 2 freeze: {fr['id']} file missing")
            elif hashlib.sha256(open(fpath, "rb").read()).hexdigest() != fr["sha256"]: errs.append(f"Round 2 freeze: {fr['id']} changed after the freeze (accepted images are never altered)")
    else:
        errs.append("ROUND2-FREEZE.csv missing")
    # Sprint 26 production system
    PD = os.path.join(V, "production")
    audit = rows(os.path.join(PD, "VP-AUDIT.csv"))
    want = [f"VP-{i:02d}" for i in range(1, 15)]
    if [r["id"] for r in audit] != want: errs.append("VP-AUDIT.csv must hold VP-01..VP-14 in order")
    ALLOWED_VP = {"VISION PLACE", "VISION FOOD — NOT COOKED PRODUCT", "VISION BEER — NOT BREWED PRODUCT", "VISION NA — NOT TESTED PRODUCT"}
    for r in audit:
        for c, v in r.items():
            if c != "audit_note" and not (v or "").strip(): errs.append(f"{r['id']}: empty field {c}")
        if r["asset_class"] not in ALLOWED_VP: errs.append(f"{r['id']}: asset class {r['asset_class']}")
        if re.search(r"™|®|reading NASHA|text NASHA", r["final_prompt"]): errs.append(f"{r['id']}: prompt asks for a trademark symbol or readable name")
    RC = "REFERENCE CORRECTIONS — VP-01 IS THE STYLE/ARCHITECTURE MASTER, BUT DO NOT COPY THESE KNOWN INACCURACIES:"
    for r in audit:
        rc = r.get("reference_corrections", "")
        if not rc: errs.append(f"{r['id']}: reference_corrections missing")
        elif not rc.startswith("n/a") and not rc.startswith(RC): errs.append(f"{r['id']}: reference_corrections must start with the standard header")
        if r["id"] == "VP-01" and not rc.startswith("n/a"): errs.append("VP-01 is the master and must not carry reference corrections")
        if r["id"] in ("VP-02", "VP-04") and "stone-edged channel" not in rc: errs.append(f"{r['id']}: court image lacks the water-channel correction")
        if r["id"] in ("VP-05", "VP-06", "VP-07", "VP-08", "VP-09", "VP-10", "VP-11", "VP-12") and "channel" in rc and not rc.startswith("n/a"): errs.append(f"{r['id']}: food or drink image must not carry the water-channel correction")
    lock = open(os.path.join(PD, "GLOBAL-LOCK-BLOCK.txt"), encoding="utf-8").read()
    for need in ("SIX", "no readable name", "Children never hold", "NO string lights", "No copper-clad tanks", "fictional future"):
        if need not in lock: errs.append(f"GLOBAL-LOCK-BLOCK.txt lacks: {need}")
    neg = open(os.path.join(PD, "GLOBAL-NEGATIVES.txt"), encoding="utf-8").read()
    for need in ("sombreros", "Taj Mahal", "elephant", "neon", "copper", "sports bar", "luxury hotel", "string lights", "black studio", "mandalas", "trademark symbols", "children near beer"):
        if need not in neg: errs.append(f"GLOBAL-NEGATIVES.txt lacks: {need}")
    prov = rows(os.path.join(PD, "IMAGE-PROVENANCE.csv"))
    PROV_COLS = ["id", "generation_date", "prompt_version", "asset_class", "source", "edit_status", "website_use", "blueprint_relation", "known_inaccuracies", "supersedes", "file", "sha256", "review_status"]
    if list(prov[0].keys()) != PROV_COLS: errs.append("IMAGE-PROVENANCE.csv columns changed")
    for r in prov:
        if r["review_status"] != "NOT GENERATED":
            fp = os.path.join(ROOT, r["file"]) if r["file"] else ""
            if not fp or not os.path.exists(fp): errs.append(f"{r['id']}: provenance names a missing file")
            elif hashlib.sha256(open(fp, "rb").read()).hexdigest() != r["sha256"]: errs.append(f"{r['id']}: file SHA-256 differs from provenance")
            if not r["generation_date"] or not r["edit_status"]: errs.append(f"{r['id']}: provenance incomplete")
    return errs

def apply_register(prov, man, vp, rel, sha, date, edit, inaccuracies):
    """Pure update of the provenance and manifest rows for an accepted-for-review generated image."""
    hit = [r for r in prov if r["id"] == vp]
    if not hit: raise ValueError(f"unknown asset {vp}")
    hit[0].update({"generation_date": date, "file": rel, "sha256": sha, "edit_status": edit, "known_inaccuracies": inaccuracies or "(none recorded yet)", "review_status": "GENERATED — PENDING REVIEW"})
    for r in man:
        if r["asset_id"] == vp: r["status"] = "GENERATED — PENDING REVIEW (not integrated)"
    return prov, man


def register(argv):
    vp, src = argv[0], argv[1]
    def opt(n, d=""):
        return argv[argv.index(n) + 1] if n in argv else d
    date, edit = opt("--date"), opt("--edit")
    if not date or not edit: sys.exit("register needs --date YYYY-MM-DD and --edit (use 'none' if unedited)")
    if not os.path.isfile(src): sys.exit("file not found")
    ext = os.path.splitext(src)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"): sys.exit("image must be png, jpg or webp")
    try:
        from PIL import Image
        w, h = Image.open(src).size
        if w < 1536: print(f"WARNING: width {w}px is below 1536; the hero may look soft")
        if abs(w / h - 1.5) > 0.12: print(f"WARNING: aspect {w}x{h} is not close to 3:2; crops may cut the subject")
    except ImportError:
        pass
    dest_dir = os.path.join(ROOT, "visuals/vision"); os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{vp}-{date}{ext}")
    shutil.copyfile(src, dest)
    sha = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    pp = os.path.join(V, "production/IMAGE-PROVENANCE.csv"); mp = os.path.join(V, "data/VISION-ASSET-MANIFEST.csv")
    prov, man = rows(pp), rows(mp)
    prov, man = apply_register(prov, man, vp, os.path.relpath(dest, ROOT), sha, date, edit, opt("--inaccuracies"))
    for path, data in ((pp, prov), (mp, man)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(data[0].keys()), quoting=csv.QUOTE_ALL); wr.writeheader(); wr.writerows(data)
    print(f"registered {vp}: {os.path.relpath(dest, ROOT)} sha256 {sha[:12]}…  (class unchanged; not yet integrated into the website; review it against the success criteria)")


def selftest():
    assert not [e for e in re.findall(BAD_TEXT[0][0], "plain text")], "false positive"
    assert re.search(BAD_TEXT[2][0], "costs $12"), "price pattern broken"
    assert re.search(BAD_TEXT[0][0], "NASHA™"), "tm pattern broken"
    prov = [{"id": "VP-01", "review_status": "NOT GENERATED"}]; man = [{"asset_id": "VP-01", "status": "PROMPT READY — NOT GENERATED"}]
    p, m = apply_register(prov, man, "VP-01", "visuals/vision/VP-01-2026-01-01.png", "ab" * 32, "2026-01-01", "none", "")
    assert p[0]["review_status"] == "GENERATED — PENDING REVIEW" and "not integrated" in m[0]["status"], "register update broken"
    try:
        apply_register(prov, man, "VP-99", "x", "y", "d", "e", ""); raise SystemExit("unknown id accepted")
    except ValueError:
        pass
    print("vision_check selftest ok")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "selftest": selftest(); sys.exit(0)
    if cmd == "register": register(sys.argv[2:]); sys.exit(0)
    e = check()
    for x in e: print("FAIL", x)
    print("VISION:", "OK" if not e else f"{len(e)} problem(s)")
    sys.exit(1 if e else 0)
