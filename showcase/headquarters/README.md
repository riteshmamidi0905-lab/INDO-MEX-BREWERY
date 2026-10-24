# NASHA AI Headquarters — Phase 3

A cinematic, interactive **local review application** on the preserved Enterprise Showcase foundation. All businesses, employees and operating results remain synthetic. Engineering evidence is actual source and mounted execution reports. No live agent activity is fabricated.

## Start the existing workspace

Run from `/workspace/enterprise-showcase` on `codex/enterprise-headquarters-phase3`:

```bash
source /workspace/.brewery-venv/bin/activate
export PYTHONPATH="$PWD/showcase:$PWD/lab${PYTHONPATH:+:$PYTHONPATH}"
# Choose a NEW frontend output directory; the build refuses overwrites.
python showcase/headquarters/build.py --out /workspace/.nasha-hq/web-review
python -m showcase.hq \
  --nasha /workspace/.brewery-setup/nasha-final.db \
  --meridian /workspace/.nasha-hq/meridian-existing.db \
  --web /workspace/.nasha-hq/web-review \
  --state /workspace/.nasha-hq/review-runtime \
  --foundation-report /workspace/.brewery-setup/showcase-tests.xml \
  --phase3-report /workspace/.nasha-hq/evidence/phase3-tests.xml \
  --port 8765
```

The current review server uses `/workspace/.nasha-hq/web-final` and `/workspace/.nasha-hq/runtime` on port 8765. If it is still running, use it rather than starting a conflicting server. It binds **127.0.0.1 only**. In a browser with access to that local/forwarded port, enter the code from `/workspace/.nasha-hq/runtime/access-code`. The file is owner-only and the code is regenerated on server startup. Do not paste it into chat or commit it. Localhost preview support depends on the host product; the screenshots are independently viewable artifacts.

No production identity, real contacts, external CRM, provider API, Redis daemon or paid visual assets are needed. Existing Python/WEIR dependencies are already installed in this workspace. The frontend has no npm/bundler dependency: its build checks local entry assets, copies only local files, and writes a SHA-256 manifest into the output directory. It does not modify the source tree or database fixtures.

Both fixture files are retained foundation outputs. NASHA points to the original full scenario; Meridian is an unchanged byte-for-byte copy of the previously validated separate membership fixture. The business periods/volumes differ and the interface displays each stored period. No dataset is regenerated during startup. If a fixture is unavailable in another workspace, recover the actual retained artifact; do not silently substitute sample metrics or rebuild it from memory.

## Explore

- **Headquarters:** cinematic original SVG atrium, business selection, operating totals and connected departments.
- **Executive Floor:** stored business idea/configuration, leadership organization, actual modeled losses and opening-capital reconciliation.
- **Engineering Studio:** actual Python/SQL, read-only tenant controls, PostgreSQL migration, immutable GitHub source links and mounted JUnit results.
- **Data Engineering:** source-to-journal pipeline, row counts, schema inspection and read-time quality checks.
- **Finance:** journal-derived totals, monthly revenue/expenses/cash, transaction type/month/search filters, pagination, provenance inspection and explicitly scoped JSON export.
- **Operations:** stored queued tasks, event ledger, actual THE WEIR read decisions and audit-chain status. No approval request is invented.
- **Product:** existing project/task records and a separately labeled editorial product roadmap.
- **CRM:** existing fictional stakeholder cohorts and linked movement; no individual customers or nonexistent partners invented.
- **People:** all 15 fictional personas, searchable roles/departments, symbolic original avatars, salary assumptions, permissions and queued review counts.
- **Business Creation:** three-step user-guided idea/model/blueprint draft and JSON download. No LLM, tenant provisioning or database mutation occurs.
- **Engineering Playbook:** source-linked architecture, audit, historical handoff and playbook plan. Historical plans are displayed as historical plans.

Keyboard: use the skip link, Tab/Shift+Tab, Escape to close dialogs, and Ctrl/Cmd+K for department search. Reduced-motion preferences are respected; an additional motion control is available. Mobile navigation has an explicit toggle. Monthly chart amounts are also available in an exact, keyboard-accessible table.

## Validation

```bash
PYTHONPATH=showcase:lab python -m pytest -q showcase/tests \
  --junitxml=/workspace/.nasha-hq/evidence/phase3-tests.xml
node --check showcase/headquarters/ui/app.js
python showcase/headquarters/browser_smoke.py \
  --code-file /workspace/.nasha-hq/runtime/access-code \
  --out /workspace/.nasha-hq/evidence
```

The browser runner uses installed `/usr/bin/chromium`, Python Playwright, and the existing locked `website/qa/node_modules/axe-core/axe.min.js`. If these are unavailable, install the existing documented development dependencies rather than disabling checks. It fails if axe-core is missing. It does not relax the application's CSP. Read [HANDOFF.md](HANDOFF.md) for verified outcomes, security boundaries and outstanding integration work.
