"""Asset validation gate for the creative pipeline (step "Asset Validation" before any website integration).

For every PNG in visuals/concepts/: a provenance record exists, its recorded sha256 matches the file on disk, required provenance fields are
present, the status says LOCAL-ONLY, the image has plausible pixel size, and the SVG source contains no logo/trademark markers or the
forbidden words. Exit 1 on any problem.     python3 visuals/tools/validate_assets.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "visuals" / "concepts"
REQUIRED = ("asset", "svg_sha256", "png_sha256", "method", "authorship", "sources", "rights", "status")
FORBIDDEN = re.compile(r"™|®|\bTM\b|halal|\bbeef\b|\bpork\b", re.I)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def validate():
    problems = []
    prov_path = DIR / "PROVENANCE.json"
    if not prov_path.exists():
        return ["PROVENANCE.json is missing"]
    prov = {Path(r["asset"]).name: r for r in json.loads(prov_path.read_text())}
    pngs = sorted(DIR.glob("*.png"))
    if not pngs:
        problems.append("no PNG assets found")
    for png in pngs:
        name = png.stem
        r = prov.get(name)
        if not r:
            problems.append(f"{name}: no provenance record")
            continue
        for k in REQUIRED:
            if not r.get(k):
                problems.append(f"{name}: provenance field '{k}' is empty")
        if r.get("png_sha256") != sha(png):
            problems.append(f"{name}: PNG hash differs from the provenance record (file changed or stale record)")
        svg = DIR / f"{name}.svg"
        if not svg.exists() or r.get("svg_sha256") != sha(svg):
            problems.append(f"{name}: SVG missing or hash differs")
        else:
            if FORBIDDEN.search(svg.read_text()):
                problems.append(f"{name}: SVG contains a forbidden marker (trademark sign, halal, beef or pork)")
        if "LOCAL-ONLY" not in r.get("status", ""):
            problems.append(f"{name}: status must say LOCAL-ONLY until publication is approved")
        try:
            from PIL import Image
            w, h = Image.open(png).size
            if w < 800 or h < 800:
                problems.append(f"{name}: image is only {w}x{h}")
        except Exception as e:  # pragma: no cover
            problems.append(f"{name}: unreadable PNG ({e})")
    return problems


if __name__ == "__main__":
    pr = validate()
    print("asset validation:", "PASS" if not pr else f"{len(pr)} problem(s)")
    for x in pr:
        print(" -", x)
    sys.exit(1 if pr else 0)
