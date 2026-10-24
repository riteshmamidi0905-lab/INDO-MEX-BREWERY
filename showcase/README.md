# NASHA AI Enterprise Showcase foundation

**FULLY SYNTHETIC BUSINESS DEMONSTRATION.** No brewery, revenue, customers, salaries, contracts or workforce here are real. Actual engineering evidence is recorded separately from fictional operating events. This is a foundation, not the immersive finished product.

New code lives entirely under `showcase/`, on local branch `codex/enterprise-showcase-foundation`, based on the observed `career/master-directive-phase0` commit `88f6ff4f12c7a713ce8ab005d92f77531cc67e23`. No existing source file, model experiment, production portfolio or data set was edited. No push, merge, deployment or publication was performed.

## Run locally

From the repository root, with Python 3.12 and Node 24 supplied by the cloud image:

```bash
python3 -m venv --system-site-packages /workspace/.brewery-venv
source /workspace/.brewery-venv/bin/activate
pip install -e ./showcase -r showcase/requirements-test.txt
export PYTHONPATH="$PWD/showcase:$PWD/lab${PYTHONPATH:+:$PYTHONPATH}"
python -m pytest -q showcase/tests
# Each build requires a NEW filename. Existing files are never overwritten.
python -m showcase build --database /tmp/nasha-showcase-v1.db
python -m showcase check --database /tmp/nasha-showcase-v1.db
python -m showcase export --database /tmp/nasha-showcase-v1.db > /tmp/nasha-showcase-v1.json
python -m showcase build --database /tmp/meridian-showcase-v1.db --tenant meridian-fitness --industry fitness --orders 120
```

The lab is intentionally used directly from this checkout (`PYTHONPATH=lab`); this extension does not install the entire model/retrieval stack or download model weights. A persistent API, Redis, external credentials and a paid LLM are unnecessary for these deterministic checks. PostgreSQL tests start and stop their own local embedded server. `requirements-test.txt` pins both upstream integration revisions to the existing lab CI. Fresh-install package dependencies resolve through their normal verified sources.

## Working foundation

- Configurable 15-person fictional workforce, departments, salary assumptions, permissions and queued review tasks. No persona runs continuously or claims completed business work.
- Version-1 relational model for businesses, departments, agents, projects, tasks, events, transactions, line items, stakeholders, journals and engineering evidence.
- NASHA fixture reuses `nasha_lab.enterprise_sim.generate` and the current versioned concept menu. Date window is May 9, 2025 through October 24, 2026 inclusive. Parent simulator covers whole months; this extension retains only in-window orders and their lines/refunds.
- Integer-cent, double-entry cash-basis demonstration with event-to-transaction-to-journal reconciliation. Fictional $3 million opening capital is an explicit assumption; 35% operating costs and prorated fictional annual salaries are assumptions, not validated commercial economics. Tax, depreciation, accruals, individual supplier invoices and demand forecasting are not modeled here.
- Model sales arise from a 35,000-order volume assumption. Full run: **$988,636.79 net revenue**, **$2,448,612.72 expenses**, **-$1,459,975.93 net income**, **$1,540,024.07 ending cash**. No target revenue is used in dashboard calculations. The loss follows from the chosen workforce/cost assumptions and is preserved.
- Canonical logical export and SHA-256 event provenance. Hash chains detect accidental changes when validated; a privileged database writer can rewrite a whole chain. This is not a signed immutable audit claim.
- Tenant-bound read-only domain tools use the real production platform's `Tool` API through the real THE WEIR gateway. There is no new planner, framework or LLM loop. Role checks remain behind the gateway.
- Optional new PostgreSQL schema migration with composite tenant foreign keys, forced RLS and an invoker-security finance view. No existing schema is altered. Runtime fixture storage remains SQLite; PG portability/constraints are independently tested, not deployed.

Read [audit](docs/AUDIT.md), [architecture](docs/ARCHITECTURE.md), [engineering playbook plan](docs/PLAYBOOK.md) and [handoff](docs/HANDOFF.md). The current user directive is preserved verbatim at [USER-DIRECTIVE.txt](docs/USER-DIRECTIVE.txt); no earlier prompts were invented.
