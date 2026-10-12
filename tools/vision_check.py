#!/usr/bin/env python3
"""Vision layer guard (Sprint 25). ASSUME FOR VISION. VERIFY BEFORE IMPLEMENTATION.
Checks that the vision layer (vision/) stays separate from the frozen Blueprint and from evidence:
assumption register shape, asset classes, no vision asset treated as real/validated, vision figures on the site are labelled, no prices or logo claims.
Usage: python3 tools/vision_check.py [check|selftest]"""
import csv, glob, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "vision")
CLASSES = {"REAL", "FOUNDER PROTOTYPE", "VISION", "CONCEPT", "RESEARCH REFERENCE"}
SUBCLASSES = {"VISION PLACE", "VISION FOOD", "VISION BEER", "VISION NA", "CONCEPT ILLUSTRATION", "(none)", "(none registered)"}
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
    return errs


def selftest():
    assert not [e for e in re.findall(BAD_TEXT[0][0], "plain text")], "false positive"
    assert re.search(BAD_TEXT[2][0], "costs $12"), "price pattern broken"
    assert re.search(BAD_TEXT[0][0], "NASHA™"), "tm pattern broken"
    print("vision_check selftest ok")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "selftest": selftest(); sys.exit(0)
    e = check()
    for x in e: print("FAIL", x)
    print("VISION:", "OK" if not e else f"{len(e)} problem(s)")
    sys.exit(1 if e else 0)
