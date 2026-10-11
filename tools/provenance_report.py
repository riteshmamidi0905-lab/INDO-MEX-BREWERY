#!/usr/bin/env python3
"""Asset provenance and public-use blocker report from visuals/NASHA-VISUAL-MANIFEST.csv (Sprint 16). Read-only. Groups raster assets by generation tool,
rights status and stage, and lists what blocks public use. It never asserts clearance: a missing/unverified provider term is a blocker.
  python3 tools/provenance_report.py            print report        python3 tools/provenance_report.py selftest"""
import csv, collections, sys
M = "visuals/NASHA-VISUAL-MANIFEST.csv"
def classify(tool):
    t = (tool or "").lower()
    if "openai" in t: return "OpenAI image generation (per founder; model not recorded)"
    if "figma" in t or "gemini" in t: return "Figma generate_image (gemini-3.1-flash-image)"
    if not t or t in ("n/a", "none"): return "none (not generated)"
    return tool
def report(rows):
    out = []; by = collections.defaultdict(list)
    for r in rows:
        if r["kind"] != "raster" and "AI" not in (r["concept_or_real"] or "") and r["status"] not in ("INTEGRATED-PROVISIONAL", "CANDIDATE GENERATED (not integrated)"): continue
        by[classify(r["tool"])].append(r)
    for tool, rs in sorted(by.items()):
        out.append(f"## {tool}: {len(rs)} manifest rows")
        out.append("  rights: " + str(dict(collections.Counter(r["rights_status"] for r in rs))))
        out.append("  status: " + str(dict(collections.Counter(r["status"] for r in rs))))
        out.append("  commercial-use status: " + str(dict(collections.Counter((r["commercial_use_status"] or "blank")[:40] for r in rs))))
    blockers = [r for r in rows if r["rights_status"] == "PROVISIONAL-LOCAL-ONLY"]
    out.append(f"\nPUBLIC-USE BLOCKERS: {len(blockers)} integrated/provisional AI assets are PROVISIONAL-LOCAL-ONLY (provider terms not verified from primary sources; no attorney review).")
    for r in blockers: out.append(f"  {r['id']}: {r['title']} | source {r['source_file']} | replace: {r['replacement_plan'][:90]}")
    return "\n".join(out)
def selftest():
    rows = [dict(id="A", title="t", kind="raster", status="INTEGRATED-PROVISIONAL", concept_or_real="concept (AI)", rights_status="PROVISIONAL-LOCAL-ONLY", tool="OpenAI image generation", commercial_use_status="UNVERIFIED", source_file="x", replacement_plan="replace")]
    assert "PUBLIC-USE BLOCKERS: 1" in report(rows); print("selftest ok")
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest()
    else: print(report(list(csv.DictReader(open(M, encoding="utf-8")))))
