# Phase 4 — governed AI workforce demonstration

This extends the preserved Phase 3 application. It does **not** restart the project, replace its agent platform, regenerate business fixtures, call a live model, or send orders. The mode is explicitly **DETERMINISTIC_REPLAY**.

## Implemented workflow

Inventory discrepancy → Operations analysis → Procurement proposal → Finance assessment → THE WEIR authorization hold → authenticated human approval/rejection → separately recorded **SIMULATED DRAFT_NOT_SENT**.

Three existing fictional personas participate: Amara Brooks (Operations), Arjun Mehta (Procurement), Maya Desai (Finance). Their actual structured tool executions are recorded. The remaining personas remain configured and inactive. No model accuracy/reliability score is invented.

The current foundation fixtures do not contain the warehouse `scn_procurement_reco` / supplier-quote / inventory tables required by the older full `GovernedProcurement` upstream. Rather than fabricate those tables inside historical fixtures, this adapter uses explicitly labeled scenario count/cost/budget inputs and reuses the existing security, tool-execution, ledger and trace components. Available modeled cash is read from the selected business's original finance summary.

## Run in this workspace

```bash
cd /workspace/enterprise-showcase
source /workspace/.brewery-venv/bin/activate
export PYTHONPATH="$PWD/showcase:$PWD/lab${PYTHONPATH:+:$PYTHONPATH}"
# Use a NEW output directory. Existing Phase 3 web builds are preserved.
python showcase/headquarters/build.py --out /workspace/.nasha-hq/web-phase4-review
python -m showcase.hq \
 --nasha /workspace/.brewery-setup/nasha-final.db \
 --meridian /workspace/.nasha-hq/meridian-existing.db \
 --web /workspace/.nasha-hq/web-phase4-review \
 --state /workspace/.nasha-hq/phase4-review-runtime \
 --workforce-state /workspace/.nasha-hq/phase4-review-workflows \
 --foundation-report /workspace/.brewery-setup/showcase-tests.xml \
 --phase3-report /workspace/.nasha-hq/phase4-evidence/all-tests.xml \
 --port 8767
```

The report argument retains its original CLI name for compatibility; its displayed filename identifies the actual mounted Phase 4 combined JUnit report. No old report is overwritten. Existing installed dependencies supply the actual platform, THE WEIR and identity/ledger modules; no paid or additional framework dependency is introduced.

The server binds to loopback. Read the owner-only access-code file in the selected `--state` directory through your local terminal; never paste the code into chat or a URL. On this workspace the final review server's paths are recorded in HANDOFF.md. A separate original Phase 3 server may remain on port 8765; do not stop it to run the new review host on 8767.

Open Operations Center. Select one of four explicit scenarios (normal discrepancy, over-budget, balanced count, missing count). Start the workflow. Inspect each agent's inputs/outputs/tool calls, the actual policy events, proposed hypothetical cost, source-derived cash and budget. Approve or reject only the exact displayed action. The approved result is a draft in a new workflow ledger, not an actual purchase, stock update or historical expense. Rejection, finance blocking, missing inputs and expiry leave no draft.

Workflow history belongs to the current authenticated review session and selected business. A new login cannot inherit another session's approval authority. Host restart deliberately requires a new login; existing pending workflows cannot be taken over by a new session. Inspect retained stores with trusted local tooling rather than weakening this boundary.

## Reproduce validation

```bash
PYTHONPATH=showcase:lab python -m pytest -q showcase/tests \
 --junitxml=/workspace/.nasha-hq/phase4-evidence/all-tests.xml
node --check showcase/headquarters/ui/app.js
python showcase/workforce/browser_workforce.py \
 --port 8767 --code-file /workspace/.nasha-hq/phase4-runtime/access-code \
 --out /workspace/.nasha-hq/phase4-evidence
python showcase/headquarters/browser_smoke.py \
 --port 8767 --code-file /workspace/.nasha-hq/phase4-runtime/access-code \
 --out /workspace/.nasha-hq/phase4-evidence/phase3-regression
```

Browser prerequisites are unchanged: existing Python Playwright, `/usr/bin/chromium`, and the locked existing website QA axe-core package. No expensive model evaluation is invoked. Unit tests use isolated temporary fixtures and workflow ledgers; the retained NASHA/Meridian financial fixtures are fingerprinted and unchanged.

Read [PLAYBOOK.md](PLAYBOOK.md) for state transitions, tool contracts, authorization boundaries and recovery. Read [HANDOFF.md](HANDOFF.md) for actual outcomes and remaining integration blockers.
