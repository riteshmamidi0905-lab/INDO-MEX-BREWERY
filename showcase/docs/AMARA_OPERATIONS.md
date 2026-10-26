# Amara — read-only Operations room

Branch `codex/amara-readonly-operations` starts at documentation commit `b064414b0773681c9b2af046e1458ce0c1c7f343`, which preserves the Phase 4 implementation at `2d745575929301af33ad1deee09b3221147866a9`. Phase 3, Phase 4 and specification branch tips are retained. No model, shared platform, portfolio or existing branch was changed.

## Product experience

Enter the existing authenticated Headquarters and open Operations. Amara presents four existing Phase 4 scenarios, a deterministic explanation, supporting records and hashes, the selected business scope, real THE WEIR read activity and explicit authorization limits. Missing count abstains; balanced count limits the absence claim to the supplied snapshot. Source/gateway failure removes the explanation and offers retry. Model inference is unavailable, not silently substituted. Desktop and mobile use the existing graphite/teal design, native accessible selects/details and reduced-motion support.

## Architecture and boundaries

`operations.py` is a pure renderer over existing `workforce.SCENARIOS`, not an agent framework or new scenario generator. Inputs are expected/count quantities only; no costs, procurement quantities or financial decisions enter the explanation. Server-derived tenant scope is included in every evidence ID and fingerprint. Both businesses use the existing separate foundation stores; inventory values are shared demonstration assumptions from Phase 4, **not** independent measured stock fixtures or values inferred from transactions.

The existing `/api/view/operations` authenticated read accepts one allowlisted `scenario` selector. The same selector is refused on other departments; browser tenant/reviewer selectors are not accepted. `HeadquartersUpstream` runs the pure renderer inside the existing `showcase__read` WEIR route under Amara's department principal. Existing per-tenant gateway locks/store and session authorization apply. Audit integrity failure refuses the Operations read. Source fixtures are opened read-only. Runtime gateway audit writes are expected; there is no business mutation.

The UI shows actual gateway decision/call records, not invented model or ToolExecutor activity. Historical reads are scoped to the selected tenant and can include department reads by this local reviewer. Call IDs are local gateway identifiers, not globally unique workflow IDs. Record/snapshot hashes fingerprint exact assumptions but are not signed attestations of measured inventory. No new workflow or approval is created by selecting a scenario.

For this read-only review, run the host **without `--workforce-state`**. The unchanged optional Phase 4 simulated procurement workspace remains separately available when explicitly enabled; it is not used or invoked by this experience. No grant, approval or supplier communication is issued here.

## Local preview

From the isolated worktree, using the existing environment and existing fixture paths:

```bash
python3 showcase/headquarters/build.py --out /tmp/amara-web-new
PYTHONPATH=showcase:lab /workspace/.brewery-venv/bin/python -m showcase.hq \
  --nasha /workspace/.brewery-setup/nasha-final.db \
  --meridian /workspace/.nasha-hq/meridian-existing.db \
  --web /tmp/amara-web-new --state /tmp/amara-runtime-new --port 8774
```

Use the fresh owner-only access code file identified by the host, never a URL credential. Bind remains loopback-only. Choose an unused port/output directory if the review host is running. Open Operations after sign-in. No external assets or provider endpoint is needed.

## Validation and evidence

83 automated tests passed (foundation, Headquarters, governed workforce, workforce HTTP and new Operations tests). New coverage checks arithmetic, abstention, unauthenticated access, forbidden selectors, tenant-bound evidence, unchanged fixture bytes fail-closed source errors and rejection of an invalid gateway audit chain. Frontend build copied nine reviewed local assets; JavaScript syntax and Git whitespace checks passed.

`headquarters/amara_smoke.py` exercises real Chromium sign-in, evidence/activity disclosure, scenario changes, both businesses, 390px reflow, keyboard focus, missing count and source failure/retry. Two axe audits cover desktop expanded evidence and mobile Meridian. Six screenshots plus JSON results are outside Git at `/workspace/.nasha-hq/amara-review/screenshots/`. The existing broader Headquarters browser regression also passed all 11 departments and both businesses with zero page errors or axe violations. Test XML/logs are in its parent directory. These contain no access codes/cookies. Browser failure testing intercepts the local response; it does not disable the real gateway.

Run the same script with `--base`, `--code-file` and `--out` pointing to the local review instance. Automated accessibility checks do not replace manual assistive-technology review. PostgreSQL deployment tests and model-live are outside this change; neither was run.

## Intentionally deferred Phase 5 requirements

The preserved Phase 5 specification remains authoritative for **future model-assisted integration**. This is tangible deterministic product progress, not implementation or acceptance of that contract. No `LLMProvider`, async inference adapter, model prompt execution, model output claim parser/semantic gate, inference cache, timeout/retry/cancellation lifecycle, target-specific model evaluation, durable identity migration, signing-key/nonce migration or model sidecar workflow ledger was added. Those require separate implementation and evaluation authorization. No new wrapper around ToolExecutor is needed for pure arithmetic already inside the authorized department read; no per-agent tool execution is claimed.

This preview uses the existing local access-code reviewer and process-scoped sessions, not production SSO or durable multi-user identities. WEIR's current local audit chain provides tamper detection, not external notarization. Candidate model status remains REQUIRES_REVIEW; Claude's reported model-live results are not treated as approved. No live endpoint, paid service, fallback provider or autonomous external action is configured.
