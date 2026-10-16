# RB-RETRIEVAL: Retrieval unavailable or abstaining unexpectedly

SYNTHETIC / SIMULATED OPERATION runbook for the NASHA AI lab. NOT PRODUCTION DEPLOYED: there is no on-call rotation, pager or real incident behind it. Incident classes: RETRIEVAL_UNAVAILABLE, RETRIEVAL_ABSTAIN_ANOMALY. Alert rules: AR-14, AR-17, AR-22.

## Detection
AR-14: the policy retrieval tool itself failed. AR-17: retrieval abstained on an INVENTORY or POLICY event, where the clean baseline is to find an authoritative source. AR-22: the lexical fallback served the answer.

## Triage
- Expected vs anomalous: DATA_QUALITY events abstain by design (no authoritative procedure exists) and are excluded from AR-17. A retrieval miss on DATA_QUALITY events is therefore NOT detectable by AR-17 (a measured limitation).
- Did the corpus version change? Compare the corpus hash in the version id.
- Is the retriever process up? With ResilientKB in front, AR-22 tells you the primary is down.

## Containment
Fail closed: abstain with INSUFFICIENT VERIFIED EVIDENCE and list the missing policy as an uncertainty; no policy claim is made without a citation. With ResilientKB the lexical retriever (BM25) answers through the same status-aware code.

## Recovery
Restore the index or retriever; `request_more_evidence`. Verified (retrieval_miss; GAP-04 fallback experiment).

## Rollback
If a corpus rebuild caused it, re-point to the previous corpus version (`NASHA_CORPUS_VERSION`) and re-run the gate.

## Escalation
SEV2 for AR-14 (policy checks are down); SEV3 otherwise.
