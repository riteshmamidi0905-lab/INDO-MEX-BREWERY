# Phase 4 handoff — governed workforce

Branch: `codex/enterprise-governed-workforce-phase4`.
Base: verified Phase 3 commit `4750f2ec073f14d289e764335212594224b8a589`.

## Delivered

One end-to-end workflow: **inventory discrepancy → procurement decision**. Four explicit scenarios cover normal replenishment, finance/budget blocking, balanced count/no action, and missing data/failure.

Operations (Amara), Procurement (Arjun) and Finance (Maya) perform actual structured deterministic tool executions through the existing production platform ToolExecutor and real THE WEIR Gateway. Their inputs, outputs, calls, retries, policy decisions, durations and errors can be inspected in the Operations workspace. No other persona activity is fabricated.

Eligible proposals are held by THE WEIR. An authenticated initiating reviewer can approve or reject only the exact tenant/run/action/effect before expiry. Valid approval records a **SIMULATED DRAFT_NOT_SENT** in a new per-tenant procurement ledger. Nothing is transmitted, purchased, added to inventory or posted into the historical financial journals. Cost/budget/count inputs are hypothetical and labeled; available modeled cash comes from the selected foundation fixture.

The existing Headquarters gains workflow selection, start, history, review controls, agent record dialogs, finance implications, audit details and explicit terminal states. Its eleven departments, business switching, source explorer, financial views and blueprint wizard remain available. Phase 4 architecture/source documentation is accessible through the Engineering Studio/Playbook evidence menu. Original immutable source links remain valid; unpushed Phase 4 files are labeled local rather than linked to nonexistent remote files.

## Execution mode and upstream boundaries

**DETERMINISTIC_REPLAY only. No live model inference was performed or evaluated.** No approved showcase provider/model configuration is present. Claude Code's separate model-live evaluation was neither assumed to pass nor rerun.

This is a fixed domain adapter over existing ToolRegistry/ToolExecutor/Tracer, Gateway/Store, Authority, governed Ledger and trace Store, not a parallel agent framework. The older full warehouse workflow requires inventory/recommendation/quote tables absent from the immutable showcase fixtures; that integration remains a blocker rather than grounds to mutate or reconstruct historical data.

Preparation is a bounded request with three fixed stages. The interface displays completed recorded steps and supports refreshing recorded state; it does not claim live token streaming or fabricate intermediate animations.

## Validation outcomes

- **77 automated tests passed; zero failed, zero skipped.** Breakdown: original 37 foundation/Phase 3 tests, 31 workflow/security/recovery tests, and 9 authenticated HTTP integration tests. The embedded PostgreSQL helper emits one non-fatal runtime-directory warning.
- Security-negative coverage: absent authentication/CSRF, wrong origin, reviewer/session and tenant mismatches, unapproved direct calls, unknown role/tool/input, modified payload/action/proposal, wrong approval/run, expired approvals, repeated decisions, signed grant replay/cross-tenant signatures, missing or corrupt audit/trace records, and denied financial proposals.
- Recovery coverage: bounded read timeout, one permitted transient read retry, missing data failure, a lost write response reconciled to one existing draft, and failed writes requiring a new reviewed workflow. Duplicate approvals never produce a second draft.
- Deterministic replay compares actual stage inputs/outputs, not random IDs, timestamps or latency. Financial fixture fingerprints remain identical before/after execution.
- Browser: 8 grouped workflow checks passed for pending/approved/rejected outcomes, finance blocking, missing count, no-action abstention, Meridian isolation, agent inspection, mobile reflow and new-session non-inheritance. Zero page errors and zero automated axe violations on the audited workflow surface.
- Existing Phase 3 Chromium regression passed: all 11 departments across both businesses and original interactions; zero application page errors and zero automated axe violations on its five representative views.
- Frontend build and JavaScript syntax checks passed; nine local assets, no paid assets or new frontend dependency. No expensive model tests or external CI jobs ran.

Actual JUnit/JSON/logs and screenshots are in `/workspace/.nasha-hq/phase4-evidence/`. These are local evidence, not a published certification. The original Phase 3 reports and business fixtures were preserved.

## Local review

The Phase 4 review host uses port **8767**, built assets at `/workspace/.nasha-hq/web-phase4-v1`, host/session state at `/workspace/.nasha-hq/phase4-runtime`, and separate workflow state at `/workspace/.nasha-hq/phase4-workflows`. Its access code is owner-only in the host state directory. See README.md for startup and test commands. The original Phase 3 server on port 8765 is not replaced.

## Security limitations and remaining work

This remains a loopback-only local reviewer prototype, not enterprise SSO or verified human identity. A session-derived reviewer capability can initiate and approve a fictional agent's proposal; organizational multi-human separation of duties is not implemented. Role selection, tenant identity, effect and signer are server-controlled, never taken from request arguments.

Existing Authority signing keys/nonces and browser sessions are process-local. A new session cannot take over an old session's pending workflow after restart. Persistent records remain available to trusted local operators. Multi-worker durable authority/reviewer delegation and production identity are required before deployment. Hash-chain checks and required records fail closed in tested tampering cases; this is not protection against a privileged administrator rewriting every local store and anchor.

No actual supplier communication, general-purpose write tool, external provider, financial booking, public deployment or production portfolio integration is configured. Historical agent directory review tasks remain historical records; workflow executions live in their own stores rather than silently marking those tasks complete.

Recommended next phase: integrate an approved existing provider only after upstream reliability evidence is accepted, using this same constrained scenario and evaluation harness. First establish durable authenticated reviewer grants, approved separation-of-duties policy and restart/recovery semantics. Expand workflow count only after those boundaries are validated.

No push, merge, deployment, publication, paid service or upstream engineering branch modification was performed for Phase 4.
