#!/usr/bin/env python3
"""Sprint-3 repository validation. Run from repo root: python3 tools/validate_repo.py   (exit 1 on failure; warnings do not fail)
Checks: dietary audit; CSV/JSON well-formedness; duplicate decision IDs; customer-discovery responses empty (no synthetic data); T1 sheets still blank;
prohibited 'it happened' claims; broken backticked internal file references; market observations have source and date."""
import csv, glob, json, os, re, subprocess, sys
fails=[]; warns=[]
def fail(m): fails.append(m); print("FAIL",m)
def warn(m): warns.append(m); print("WARN",m)
# 1 diet audit
r=subprocess.run([sys.executable,"tools/diet_audit.py"],capture_output=True,text=True)
print(r.stdout.strip().splitlines()[-2] if r.stdout.strip() else "")
if r.returncode!=0: fail("diet_audit reported unmarked beef/pork in current-product files:\n"+r.stdout)
# 2 CSV/JSON
for f in glob.glob("research/**/*.csv",recursive=True):
    rows=list(csv.reader(open(f)));
    if not rows: fail(f"empty csv {f}"); continue
    n=len(rows[0])
    for i,row in enumerate(rows[1:],2):
        if len(row)!=n: fail(f"{f}: line {i} has {len(row)} columns, header has {n}")
for f in glob.glob("research/**/*.json",recursive=True):
    try: json.load(open(f))
    except Exception as e: fail(f"bad json {f}: {e}")
# 3 decision IDs
ids=re.findall(r"^\| (D-\d+) \|",open("docs/decisions/DECISIONS.md").read(),re.M)
dup={x for x in ids if ids.count(x)>1}
if dup: fail(f"duplicate decision IDs: {sorted(dup)}")
print(f"decision rows: {len(ids)}, latest {ids[-1]}")
# 4 no synthetic/real interview data unless intended
rows=list(csv.reader(open("research/customer-discovery/responses.csv")))
if len(rows)>1: warn(f"responses.csv has {len(rows)-1} rows: confirm these are REAL interviews (never synthetic)")
else: print("responses.csv: header only (no interview data), as expected")
# 5 T1 sheets blank
for f in sorted(glob.glob("food/t1-test-sheets/0[1-6]-*.md")):
    t=open(f).read()
    if "Result: KEEP / REWORK / CUT / HOLD" in t and "Result: KEEP / REWORK / CUT / HOLD   Reason: ______" not in t: fail(f"{f}: outcome line altered (sheet may have been filled)")
    if re.search(r"\| \*\*Average\*\* \| [0-9]",t): fail(f"{f}: average score filled in")
# 6 prohibited claims
BAD=re.compile(r"customers preferred|tested well|pilot batch produced|market survey found|attorney confirmed|architect estimates|supplier confirmed|our food cost is|GLS-0[12] demonstrates|production-ready|is now validated",re.I)
SKIP={"tools/validate_repo.py"}
for f in (x for x in glob.glob("**/*.md",recursive=True) if "node_modules" not in x):
    if f in SKIP or f.startswith(".git") or f.startswith("phase-one/"): continue
    for i,l in enumerate(open(f),1):
        if BAD.search(l) and not re.search(r"never|do not|don't|prohibited|not claim|must not|no .* has|until|before|only after|unless",l,re.I): warn(f"{f}:{i}: possible unperformed-event claim: {l.strip()[:110]}")
# 7 halal wording
for f in (x for x in glob.glob("**/*.md",recursive=True) if "node_modules" not in x):
    if f.startswith("phase-one/"): continue
    for i,l in enumerate(open(f),1):
        if re.search(r"\bhalal\b",l,re.I) and not re.search(r"not|no |never|without|review|claim|unresolved|decision|policy|positioning|sourcing|certif|question|policy",l,re.I): warn(f"{f}:{i}: 'halal' without a not-claimed qualifier: {l.strip()[:110]}")
# 8 broken references
allfiles={os.path.basename(p) for p in glob.glob("**/*",recursive=True) if os.path.isfile(p)}
missing=set()
for f in (x for x in glob.glob("**/*.md",recursive=True) if "node_modules" not in x):
    for m in re.findall(r"`([A-Za-z0-9_./\-]+\.(?:md|py|csv|png|json|webp))`",open(f).read()):
        if os.path.exists(m) or os.path.exists(os.path.join(os.path.dirname(f),m)): continue
        if os.path.basename(m) in allfiles: continue
        missing.add((f,m))
PLACEHOLDERS={"ARC-02-C-edited-crop.png","ARC-01_v03_approved.png"}  # future/placeholder file names, not real files yet
for f,m in sorted(missing):
    if os.path.basename(m) in PLACEHOLDERS: continue
    warn(f"unresolved reference in {f}: {m}")
# 9 observations
o=list(csv.DictReader(open("research/market-survey/observations.csv")))
for r in o:
    if not r["source_url"] or not r["capture_date"] or not r["price_type"]: fail(f"observation {r['obs_id']} missing source/date/price_type")
print(f"market observations (long form): {len(o)} price rows; confidences: {sorted({r['confidence'] for r in o})}")

# 10 financial assumption register: no value without class+ref; allowed classes
ALLOWED={"founder_assumption","benchmark_T3","benchmark_T1","observation_LOW","interview_real","popup_real","supplier_quote","vendor_quote","architect_estimate","professional_advice","calculated","illustrative"}
a=list(csv.DictReader(open("business/model/assumptions-template.csv")))
filled=[r for r in a if (r["value"] or "").strip()]
for r in filled:
    if r["source_class"] not in ALLOWED or not (r["source_ref"] or "").strip(): fail(f"assumption {r['id']} has a value without a valid source_class/source_ref")
    if r["source_class"]=="illustrative": warn(f"assumption {r['id']} is ILLUSTRATIVE; must not appear in investor outputs")
ids_a=[r["id"] for r in a]
if len(ids_a)!=len(set(ids_a)): fail("duplicate assumption ids")
print(f"assumptions register: {len(a)} variables, {len(filled)} with values")
# 11 readiness register consistency
import os as _os
if _os.path.exists("docs/readiness/readiness.csv"):
    rd=list(csv.DictReader(open("docs/readiness/readiness.csv")))
    for r in rd:
        ev=int(r["evidence_0_5"]); de=int(r["design_0_5"])
        if not _os.path.exists((r["evidence_ref"] or "").split(";")[0].strip()): fail(f"readiness {r['area']}: evidence_ref file missing")
        if ev>=3 and r["primary_or_external_evidence"].strip().lower()!="yes": fail(f"readiness {r['area']}: evidence {ev}>=3 requires primary/external evidence = yes")
        if ev>2 and not r["evidence_ref"].strip(): fail(f"readiness {r['area']}: evidence>2 needs a reference")
    td=sum(int(r["design_0_5"]) for r in rd); te=sum(int(r["evidence_0_5"]) for r in rd); n=5*len(rd)
    print(f"readiness: design completeness {td}/{n} = {100*td/n:.0f}% ; evidence-backed readiness {te}/{n} = {100*te/n:.0f}% across {len(rd)} areas")

# 14 Sprint-5 structured data
TL=list(csv.DictReader(open("validation/traction-event-log.csv")))
bad=[r for r in TL if (r.get("data_source","").strip().lower() not in ("real","dry_run"))]
if bad: fail(f"traction-event-log.csv has {len(bad)} rows without data_source real/dry_run (synthetic data must never be saved)")
print(f"traction event log: {len(TL)} rows ({sum(1 for r in TL if r['data_source'].strip().lower()=='real')} real)")
AS=list(csv.DictReader(open("ip/founder-asset-register.csv")))
OKSTAT={"NOT_ESTABLISHED","NOT_CREATED","UNKNOWN","ESTABLISHED_FOR_ACCESS_ONLY","OWNED_DOCUMENTED"}
for r in AS:
    if r["ownership_status"] not in OKSTAT: fail(f"asset {r['asset_id']}: invalid ownership_status {r['ownership_status']}")
    if r["ownership_status"]=="OWNED_DOCUMENTED" and not os.path.exists((r["evidence_ref"] or "").strip()): fail(f"asset {r['asset_id']}: OWNED_DOCUMENTED needs an existing evidence_ref file")
print(f"founder asset register: {len(AS)} assets, owned-documented: {sum(1 for r in AS if r['ownership_status']=='OWNED_DOCUMENTED')}")
WR=list(csv.DictReader(open("ip/website-asset-rights-register.csv")))
for r in WR:
    if not (r["licence"] or "").strip() or not (r["status"] or "").strip(): fail(f"website asset {r['asset_id']}: missing licence/status")
print(f"website asset rights register: {len(WR)} rows")
IV=list(csv.DictReader(open("investor/investor-universe-schema.csv")))
for r in IV:
    if not (r["evidence_source_url"] or "").strip() or not (r["source_type"] or "").strip() or not (r["access_date"] or "").strip(): fail(f"investor row {r['investor_id']}: needs public evidence_source_url, source_type, access_date")
if IV: warn(f"investor universe has {len(IV)} rows: confirm public professional information only and no outreach claimed")
print(f"investor universe: {len(IV)} rows")
# no claims of investor contact / traction in strategy docs
for f in ["investor/CAPITAL-LADDER-AND-INVESTOR-STRATEGY.md","validation/MOBILE-MVP-STRATEGY.md","marketing/MARKETING-AND-BUILD-IN-PUBLIC-FOUNDATION.md"]:
    t=open(f).read()
    if not re.search(r"No investor has been identified|No marketing has been done|NOT validated|No permit, cost",t): fail(f"{f}: missing honesty disclaimer")
# 12 Track A docs must carry a status/label near the top
TRACKA=["concept/INDO-MEX-BREWERY-MASTER-CONCEPT.md","brand/BRAND-ARCHITECTURE-V1.md","experience/GUEST-EXPERIENCE-ARCHITECTURE-V1.md","architecture/SPATIAL-VISION-V1.md","visuals/VISUAL-WORLD-AND-BRIEFS-V1.md","food/MENU-STORYTELLING-V1.md","beer/BEER-BRAND-EXPERIENCE-V1.md","business/BUSINESS-MODEL-MAP-V1.md","business/FINANCIAL-MODEL-ARCHITECTURE-V1.md","investor/INVESTOR-STORY-ARCHITECTURE-V1.md","investor/DATA-ROOM-MAP.md","website/WEBSITE-IA-AND-EXPERIENCE-V1.md","docs/decisions/BREWERY-SCALE-DECISION-ANALYSIS.md","validation/MOBILE-MVP-STRATEGY.md","validation/TRACTION-METRICS.md","investor/CAPITAL-LADDER-AND-INVESTOR-STRATEGY.md","ip/IP-OWNERSHIP-FRAMEWORK.md","marketing/MARKETING-AND-BUILD-IN-PUBLIC-FOUNDATION.md","docs/decisions/ATTORNEY-QUESTIONS.md","brand/NASHA-BRAND-STRATEGY.md","brand/NASHA-IDENTITY-SYSTEM.md","website/DESIGN-SYSTEM.md","visuals/NASHA-VISUAL-AUDIT-AND-GENERATION-QUEUE.md","ip/NASHA-TRADEMARK-ATTORNEY-PACKAGE.md","marketing/NASHA-DOMAIN-AND-HANDLE-INVENTORY.md"]
LABELS=re.compile(r"\[(CONCEPT|PROPOSED|DESIGN|STRUCTURE|PLAN|ANALYSIS|FOUNDER VISION)\]|`\[(CONCEPT|PROPOSED|DESIGN|STRUCTURE|PLAN|ANALYSIS)\]`")
for f in TRACKA:
    if not os.path.exists(f): fail(f"missing Track A document {f}"); continue
    head="".join(open(f).readlines()[:6])
    if not LABELS.search(head): fail(f"{f}: no Track A status label (CONCEPT/PROPOSED/DESIGN/STRUCTURE/PLAN/ANALYSIS) in the first lines")
# 13 investor-facing docs must not contain return/valuation claims
for f in glob.glob("investor/*.md")+["business/FINANCIAL-MODEL-ARCHITECTURE-V1.md"]:
    for i,l in enumerate(open(f),1):
        if re.search(r"\b(IRR|ROI|valuation of|expected return|guaranteed)\b",l) and not re.search(r"no |not |never|until|without",l,re.I): warn(f"{f}:{i}: return/valuation wording: {l.strip()[:100]}")
# 14 website (Sprint 6): static + real-browser QA result checks
r=subprocess.run([sys.executable,"tools/validate_site.py"],capture_output=True,text=True)
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
if r.returncode!=0: fail("validate_site failed:\n"+r.stdout)
print(f"\nSUMMARY: {len(fails)} fail, {len(warns)} warn")
sys.exit(1 if fails else 0)
