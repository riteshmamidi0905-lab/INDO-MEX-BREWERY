#!/usr/bin/env python3
"""D-54 consistency check: no beef/pork in CURRENT-PRODUCT files unless the line is marked as superseded/rejected/historical/policy text.
Run from repo root: python3 tools/diet_audit.py   (exit code 1 if an unmarked occurrence is found)"""
import re, sys, glob
TERMS=r"\b(beef|pork|bacon|lard|carnitas|carne asada|gelatin|brisket|chorizo|barbacoa|sausage|ham)\b"
SCOPE=["food/*.md","food/t1-test-sheets/*.md","beer/*.md","beer/pilot-briefs/*.md","business/*.md","experience/*.md","architecture/MASTER-PLAN-PHASE2.md","brand/BRAND-SYSTEM-V0.md","PROJECT-ROADMAP.md","visuals/generation-batch-01/*.md"]
OK=re.compile(r"SUPERSEDED|REJECTED|HISTORICAL|RESEARCH-ONLY|D-54|no beef|No beef|no pork|No pork|not serve beef|~~|policy|Policy|beef-free|pork-free|derivative|Lard|lard-free|No beef, no pork|barbacoa taco|jackfruit|rennet|bones|bases|stock|gelatin",re.I)
bad=0; seen=0
for pat in SCOPE:
    for f in sorted(glob.glob(pat)):
        for i,l in enumerate(open(f),1):
            if re.search(TERMS,l,re.I):
                seen+=1
                if not OK.search(l): bad+=1; print(f"UNMARKED {f}:{i}: {l.strip()[:140]}")
print(f"checked scope; {seen} marked/policy occurrences, {bad} unmarked")
sys.exit(1 if bad else 0)
