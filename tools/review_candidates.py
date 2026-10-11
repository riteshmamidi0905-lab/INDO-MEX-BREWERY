#!/usr/bin/env python3
"""Resume path for generated candidates (Sprint 10). When the founder drops full-resolution PNGs into visuals/archive/candidates/ (named
<CODE>-<name>-c<N>.png, for example A1-exterior-bluehour-c1.png), run:  python3 tools/review_candidates.py [--dir DIR]
It runs tools/visual_qa.py on every full-resolution file (thumbnails are skipped), writes qa-report.json and prints a table.
It NEVER accepts an image: acceptance needs the human gates in visuals/nasha-v3/IMAGE-QA.md (people, architecture, food, branding, culture, rights)."""
import argparse, glob, json, os, re, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="visuals/archive/candidates"); ap.add_argument("--min-width", default="1000")
a = ap.parse_args()
files = [f for f in sorted(glob.glob(os.path.join(a.dir, "*"))) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and "thumb" not in os.path.basename(f)]
if not files:
    print(f"No full-resolution candidates in {a.dir}. Thumbnails are not reviewable. Founder: download the PNGs from the 7-day URLs in visuals/nasha-v3/GENERATION-LOG.md."); sys.exit(0)
report = []
for f in files:
    r = subprocess.run([sys.executable, "tools/visual_qa.py", f, "--min-width", a.min_width], capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith(("WARN", "HARD FAIL", "RESULT"))]
    code = re.match(r"([A-Z]\d+)", os.path.basename(f)); report.append({"file": f, "code": code.group(1) if code else "?", "exit": r.returncode, "findings": lines})
    print(os.path.basename(f), "->", lines[-1] if lines else "no output")
json.dump(report, open(os.path.join(a.dir, "qa-report.json"), "w"), indent=1)
print("Wrote qa-report.json. Human gates (IMAGE-QA.md) still required before any ACCEPT; record decisions in visuals/nasha-v3/CANDIDATE-REVIEW.md.")
