# RB-STALE-SOURCE: Stale, superseded or untrusted source

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: STALE_SOURCE. Alert rules: AR-15, AR-18.

## Detection
AR-15: the trust gateway flagged the supplier-portal result (STALE, INJECTION_SUSPECTED, SCHEMA_MISMATCH, ...). AR-18: a non-authoritative source matched a policy question and was excluded.

## Triage
- Was the flagged source CITED? Check the proposal citations: any SUPERSEDED/UNVERIFIED path in the citations is a containment failure (SEV2).
- Is the supplier portal publishing old data? (STALE means as_of older than 30 days.)

## Containment
Non-authoritative sources are excluded or labelled and never cited as authority; tainted untrusted values cannot become draft or mutation arguments.

## Recovery
Refresh the source or register the document status correctly in the decision register. No run recovery is needed.

## Rollback
Not version-related.

## Escalation
SEV4; SEV2 if a stale source was cited.

AR-27 (authority rules v2): a superseded, historical or unverified source CONTRADICTS the current authoritative answer. The current source governed and the contradiction is recorded; check that the stale document is still needed.
