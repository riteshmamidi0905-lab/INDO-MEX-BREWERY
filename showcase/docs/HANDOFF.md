# Handoff to the founder and Claude Code

All new source and documentation is under `showcase/` in `/workspace/enterprise-showcase`, local branch `codex/enterprise-showcase-foundation`. Base: `88f6ff4f12c7a713ce8ab005d92f77531cc67e23`. The original checkout, supporting platform checkout and portfolio audit checkout were left without tracked changes. Nothing was pushed, merged, deployed, purchased or published. Claude Code's branch was only fetched/read.

## Implemented

An additive business domain extension with relational schemas, a configurable fictional 15-agent registry, review-task records, source-linked operating events, balanced financial journals, canonical export, read-only tenant tools, an existing-platform Tool adapter through the actual THE WEIR Gateway, a PostgreSQL migration for new schemas, and architecture/audit/playbook documentation. It reuses the existing hospitality simulator and current menu. Meridian is a separate synthetic membership fixture and store, not a renamed brewery catalog.

The NASHA full scenario covers May 9, 2025–October 24, 2026. At the 35,000-order volume setting, modeled net sales are $988,636.79. Fictional compensation and simplified operating costs total $2,448,612.72, producing a $1,459,975.93 loss and $1,540,024.07 cash after assumed $3 million opening capital. These are transaction-derived fictional results, not real revenue, profitability or company funding.

## Validation evidence

- Initial repository: `bash tools/validate_all.sh` returned `ALL CHECKS PASSED` after missing Python packages were installed. This is the repository runner's reported outcome; its security helper pipes some subcommands without preserving every underlying exit status, so it does not prove that all dependency audits are clean.
- Initial static site: actual build in a scratch copy completed, producing 12 HTML pages. Chromium loaded all 12 with HTTP 200, one H1 each and zero page errors. This was a smoke check, not the complete historical accessibility/performance suite. The original browser runner hardcodes a browser installation path absent from this machine; the smoke check used installed `/usr/bin/chromium` without editing it.
- Foundation suite: **18 passed**, zero failed, zero skipped. Covers deterministic replay/seed sensitivity; salary and records; financial identity; overwrite refusal; invalid configs; six deliberate corruptions; grants, tenant routing and cross-tenant foreign keys; real WEIR and pinned platform Tool; forbidden actions; real PostgreSQL reconciliation, constraints, and tenant filtering of tables and aggregate view under a non-superuser role. RuntimeDirWarning from the embedded database helper is non-fatal.
- Full scenario was generated and checked; complete canonical export and counts are retained outside the checkout in `/workspace/.brewery-setup/`. Test outputs there include `showcase-tests.xml` and `showcase-tests.log`. These files are local execution evidence; no remote CI run was created.
- Existing Phase 2 real-model, full lab, portfolio and broader platform suites were not rerun or modified. Their historical results were not represented as new test results.

## Safe reuse

Review/cherry-pick only the additive `showcase/` directory; no existing implementation was replaced. Start at `showcase/config.py`, `schema.sql`, `scenario.py` and `service.py`. Use a fresh output filename per build. Do not connect to production databases or treat an in-process TenantPrincipal as user authentication. Reuse existing governed/Growth modules for any future inventory, CRM or consequential workflow, and keep THE WEIR approvals ahead of effects.

The current branch's changes are intentionally uncommitted for review. Supporting repositories were inspected at exact revisions noted in AUDIT.md. Setup instructions are saved in the environment draft separately from these source files; publishing the environment remains a user action. Fresh-task restoration has not been tested.

## Remaining work

The immersive Headquarters and department UI, animated avatars, authenticated HTTP host routing, live agent task execution, per-department source views beyond the foundation, actual provider integration, authoritative role/session binding, deployed PostgreSQL storage, and external CRM are not implemented here. No paid visual assets were generated. A server mounting the read adapter must create a separate bound Service/upstream/gateway session/Tool for each authenticated principal; do not register a global mutable tenant selector.

Business creation has a reusable fixture/config/export spine and documented workflow; a complete guided business-creation product remains future work. The PostgreSQL migration is independently tested but is not wired as the runtime fixture backend. No automated CI workflow was changed. No external secrets or integrations are required to review and run this foundation.
