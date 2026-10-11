---
name: nasha-evidence-audit
description: Audit whether a NASHA claim, score change, capability status or sprint statement is supported by evidence. Use before committing anything that changes readiness scores, tool status, website copy or research findings.
---
# NASHA evidence audit

Input: a claim, a diff, or a status change. Output: VERDICT (SUPPORTED / CAUTION / REJECT) with file:line references and the smallest fix.

1. Classify the claim: IDEA, RESEARCH (T1 web summary / T2 page read / T0 primary quoted), PROTOTYPE (physical cook), TEST (scored real rows), VALIDATED, or OPERATING BUSINESS. NASHA does not exist: nothing is OPERATING.
2. Find the source. Run `python3 tools/nasha_search.py q "<key words>" --evidence` and `python3 tools/nasha_search.py decision D-NN`. A claim with no ledger row (research/VERIFICATION-LEDGER.md) or results row (food/t1-results/t1-results.csv) is unsupported.
3. Scores: evidence readiness (4/95) moves only for a satisfied criterion backed by a real artefact; design completeness (43/95) only per the existing scoring rules. Tools, research and AI images never raise evidence. Run `python3 tools/validate_repo.py`.
4. Tool status words: INSTALLED (install ok) < TESTED (one representative op, synthetic counts) < OPERATIONAL (used on real NASHA work). Check docs/tools/NASHA-CAPABILITY-MATRIX.md.
5. Hard rules: D-54 (no beef/pork; `python3 tools/diet_audit.py`), D-66 (no logo/monogram/icon, no TM symbols), D-74 (frozen thresholds), name status SELECTED_BY_FOUNDER, LEGAL CLEARANCE PENDING; no claim of tested food, brewed beer, guests, sales or professional approval.
6. If agents disagree, record the disagreement; do not merge into "truth".
