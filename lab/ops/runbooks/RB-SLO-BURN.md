# RB-SLO-BURN: SLO burn-rate alert

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: SLO_BURN. Alert rules: BR-1, BR-2.

## Detection
A multi-window burn-rate alert fired: both the long and the short window burn faster than the threshold (BR-1: 6x over 60/10 runs; BR-2: 3x over 120/20 runs). DESIGN TARGETS, windows counted in runs.

## Triage
- Which SLO? Use its owner classes (slo-design-targets.json) to find the underlying incident class and open that runbook.

## Containment
Per the underlying class.

## Recovery
Per the underlying class.

## Rollback
Per the underlying class.

## Escalation
BR-1 pages (SEV2), BR-2 tickets (SEV3); SLO-5 (safety) is SEV1 on any violation.
