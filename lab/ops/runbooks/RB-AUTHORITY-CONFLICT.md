# RB-AUTHORITY-CONFLICT: Contradictory authoritative sources

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: AUTHORITY_CONFLICT. Alert rules: AR-26.

## Detection
AR-26: authority rules v2 found two sources of the same tier (two AUTHORITATIVE, or two caveated with no authoritative one) that answer the same policy question in contradictory ways (rule R1 polarity or R2 numeric, see docs/KNOWLEDGE-AUTHORITY.md). The trace shows both document ids and the sentences that conflict.

## Triage
- Which two documents? Is one of them recently added or recently re-classified (for example a new CANONICAL entry in the document map)?
- Is one of them meant to supersede the other but not registered as such (missing `supersedes` / `superseded_by`)?
- Is it a false conflict (two sentences about different subjects that share question terms)? Record it; do not suppress the rule.

## Containment
The policy answer abstains (INSUFFICIENT VERIFIED EVIDENCE with reason AUTHORITY_CONFLICT) and cites neither source, so the planner escalates instead of choosing. No mutation follows from the conflicted answer.

## Recovery
The decision owner decides which source governs, then the register or document map is updated (mark the other SUPERSEDED, or correct the text). Re-run the event.

## Rollback
Not version-related, unless the conflicting document arrived with a corpus change: roll the corpus version back.

## Escalation
SEV3. SEV2 if an answer was given from either side of an unresolved conflict.
