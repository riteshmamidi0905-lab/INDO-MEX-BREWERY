# Security demonstration scenarios (all executed, see the evidence JSON)

| Scenario | What is attempted | Control that stops it | Outcome (executed) | POs created | Steps recorded |
|---|---|---|---|---|---|
| `approved_draft_po` | Discrepancy to approved DRAFT purchase order | A flagged inventory discrepancy becomes a draft purchase order only after a different, authorised human approves the exact call. | EXECUTED | 1 | 24 |
| `unauthorised_role_blocked` | A role without the procurement tool is blocked by THE WEIR | The quality-lead policy does not contain the write tool at all, so no approval is even requested. | BLOCKED · TOOL_DENIED | 0 | 21 |
| `expired_approval` | An approval that expires before the human decides is refused | Approvals have a 15-minute lifetime enforced by the gateway store; a late approval creates nothing. | EXPIRED · APPROVAL_EXPIRED | 0 | 22 |
| `modified_after_approval` | A proposal changed after approval cannot use that approval | The approval is bound to the exact call hash, so a 50% larger quantity needs a new approval. | REAPPROVAL_REQUIRED · REAPPROVAL_REQUIRED | 0 | 23 |
| `prompt_injection_in_supplier_note` | An instruction hidden in supplier text is treated as data | The note is labelled untrusted, flagged, excluded from claims, and the proposal is unchanged. | AWAITING_APPROVAL | 0 | 21 |
| `replayed_approval_and_duplicate_request` | Replays and duplicates create nothing new | A used approval is single-use and a repeated request with the same idempotency key returns the original run. | DENIED · APPROVAL_REPLAY | 1 | 25 |
| `malformed_agent_output` | Malformed model output fails safe | Schema validation with two bounded retries, then abstention; no proposal and no approval request. The model here is a scripted test double, not a real language model. | ABSTAINED · MALFORMED_AGENT_OUTPUT | 0 | 18 |
| `cross_tenant_blocked` | Tenant B's identity cannot act in tenant A | Each tenant has its own signing secret, warehouse, ledger, approval store and memory; a token from another tenant fails signature verification. | DENIED · AUTH_DENIED | 0 | 3 |

All 8 scenarios matched their expected outcome when exported; external transmissions: 0 in every one; audit chain valid in every one. Source: `lab/tools/export_portfolio_evidence.py`. Tests: `lab/tests/test_governed_workflow.py` (59 passed at export).
