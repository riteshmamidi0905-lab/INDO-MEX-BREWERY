#!/usr/bin/env python3
"""Build the portfolio integration package from the REAL evidence export (D-89 priority 4). Run tools/export_portfolio_evidence.py and tools/build_capability_matrix.py first.
Writes docs/portfolio-integration/*.md and lab/portfolio/evidence-manifest.json (sha256 of every artifact the website may consume)."""
import hashlib
import json
import subprocess
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
OUT = REPO / "docs/portfolio-integration"
ev = json.loads((LAB / "portfolio/nasha-governed-evidence.json").read_text())
cap = json.loads((LAB / "portfolio/capability-matrix.json").read_text())
OUT.mkdir(parents=True, exist_ok=True)
commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()

(OUT / "README.md").write_text(f"""# NASHA portfolio integration package (D-89)
For the portfolio team. **Everything here is derived from executed code; nothing is hand-written marketing.** Generated against local NASHA commit `{commit}` (not pushed). Synthetic data throughout; NASHA is a concept, not an operating business.

| File | Use |
|---|---|
| `lab/portfolio/nasha-governed-evidence.json` | Replayable timelines for {len(ev['scenarios'])} executed scenarios, measured metrics, architecture graph with per-component status. The website's player and architecture explorer read this file unchanged. |
| `lab/portfolio/capability-matrix.json` + `docs/engineering/D-89-CAPABILITY-MATRIX.md` | Implemented-and-tested / unverified / designed / blocked / not started, with code and test references. |
| `lab/portfolio/governed-api.openapi.json` | API contract (6 operations) for an "API explorer" panel; the API is tested but not deployed. |
| `lab/portfolio/evidence-manifest.json` | sha256 of each artifact above, for pinning. |
| `WORKFLOW-EXPLAINED.md`, `SECURITY-DEMO-SCENARIOS.md`, `INTERACTIVE-DEMO-SPECS.md`, `PROJECT-CONNECTIONS.md`, `LIMITATIONS.md` | Copy and specs. |

## Rules for the website
1. Never state a capability whose status in the matrix is not IMPLEMENTED_TESTED (or says what it is: blocked, designed, not integrated).
2. Show the commit and the "not pushed" flag until the commits are pushed, then update the evidence file by re-running the exporter.
3. Replays are recordings; no page may imply a live backend or a live model.
4. Reproduce: `cd lab && python3 tools/export_portfolio_evidence.py`.
""")

(OUT / "WORKFLOW-EXPLAINED.md").write_text("""# The end-to-end workflow, in plain terms
1. **Synthetic orders** are generated per tenant (seeded simulator) and loaded through a contract-checked warehouse pipeline.
2. **Recipes** (bills of materials) turn sold dishes into expected ingredient consumption.
3. **Inventory** counts and receipts (synthetic) are compared with expected consumption; a detector flags weeks where usage ran far above the site's own baseline. The detector never reads the injected truth; it is scored against it.
4. A **forecast** estimates the next days of ingredient demand; a rules-based recommender proposes a reorder from the cheapest valid (synthetic) supplier quote.
5. The **agent** retrieves evidence through THE WEIR (every read is a recorded tool call; supplier-written text is labelled untrusted), writes an explanation, and proposes a purchase. A validation gate drops any claim that cites missing evidence or a number not in that evidence, and rejects proposals that differ from the recommendation or exceed caps.
6. The proposal becomes a **write call that THE WEIR holds** for a human. Roles without the procurement tool in their policy are blocked outright.
7. A **different, authorised person approves** the exact call. The approval expires, works once, and is bound to the call (quantity, supplier, quote, amount, recommendation).
8. The upstream re-validates and the ledger creates a **DRAFT purchase order** (the only state its schema can store). Nothing is transmitted.
9. Every step carries one **correlation id**; the ledger's audit trail is hash-chained.
""")

rows = ["| Scenario | What is attempted | Control that stops it | Outcome (executed) | POs created | Steps recorded |", "|---|---|---|---|---|---|"]
for s in ev["scenarios"]:
    rows.append(f"| `{s['id']}` | {s['title']} | {s['claim']} | {s['outcome']}{' · ' + s['failure_class'] if s['failure_class'] else ''} | {s['purchase_orders_created']} | {len(s['steps'])} |")
(OUT / "SECURITY-DEMO-SCENARIOS.md").write_text("# Security demonstration scenarios (all executed, see the evidence JSON)\n\n" + "\n".join(rows) + f"\n\nAll {len(ev['scenarios'])} scenarios matched their expected outcome when exported; external transmissions: 0 in every one; audit chain valid in every one. Source: `lab/tools/export_portfolio_evidence.py`. Tests: `lab/tests/test_governed_workflow.py` ({ev['metrics']['governed_workflow_tests']['passed']} passed at export).\n")

(OUT / "INTERACTIVE-DEMO-SPECS.md").write_text("""# Interactive demo specifications (all client-side, recorded data)
1. **Trace player** (built in the portfolio candidate): tabs = scenarios; Play/Step/Reset; side panel shows the purchase-order counter, outcome, audit rows. Data: `scenarios[].steps`, `audit`, `purchase_orders_created`. Keyboard: arrow keys on tabs; live region announces steps.
2. **Architecture explorer** (built): nodes from `architecture.nodes`, edges from `architecture.edges`; filter by status; panel lists code and test paths.
3. **Attack gallery** (spec): one card per scenario with a one-line "attack → control → result" and a button that opens the player on that scenario.
4. **Metrics panel** (built as bars): `metrics.ops_ai_evaluation.by_category`, `metrics.governed_workflow_tests`; must show the caveat string verbatim.
5. **API explorer** (spec, not built): render `governed-api.openapi.json`; no "Try it" button, because no public backend exists.
6. **Approval-binding visualiser** (spec): show the call hash inputs (proposal id, reco id, inputs hash, quantity, supplier, quote, amount) and which field a tamper changed, using the `modified_after_approval` scenario. Do not invent hash values: use only fields present in the data.
Constraint: no demo may call a backend, a model or any external service.
""")

(OUT / "PROJECT-CONNECTIONS.md").write_text("""# How the three projects connect — actual integration status
| Project | Role in this system | Status |
|---|---|---|
| **NASHA Enterprise AI Lab** (this repository) | Synthetic business, data pipeline, scenario tables, Ops AI tools, governed workflow, API. | Implemented and tested. |
| **THE WEIR** (`mcp-weir`, separate repository, pinned commit) | Per-role default-deny policy, held writes, single-use call-bound approvals, tamper-evident gateway audit. | **Imported and exercised for real** (not mocked) by `nasha_lab/warehouse/ops_ai_weir.py` and `nasha_lab/governed/`; tests skip with a stated reason when it is not installed. |
| **Production AI Agent Platform** (separate repository) | Source of ideas and adapted code (hashing embeddings, reciprocal-rank fusion). | **Not integrated**: no import, no shared runtime, no shared database. The NASHA agent is its own small governed planner behind the WEIR. Do not present NASHA as running on the platform. |
| `rag-doc-qa` (`ragqa`) | TF-IDF retriever baseline. | Pinned dependency, used by the knowledge base. |
| `llm-eval-framework` (`llmeval`) | LLM evaluation project. | Installed locally; **not imported** by NASHA. |
""")

(OUT / "LIMITATIONS.md").write_text("""# Limitations (must travel with every claim)
* All data synthetic; costs are planning assumptions; quotes are synthetic; three injected anomalies only.
* No real language-model run (no runtime available); the model planner is verified with scripted clients.
* Tenants are isolated by separate stores and keys, not by processes; reference recipes are shared.
* Prototype identity (HMAC sessions); no TLS; no deployment; no security certification.
* The evaluation is small and deterministic; a perfect score is not evidence of real-world reliability.
* The NASHA commits referenced are local and unpushed.
""")

arts = ["lab/portfolio/nasha-governed-evidence.json", "lab/portfolio/capability-matrix.json", "lab/portfolio/governed-api.openapi.json", "docs/engineering/D-89-CAPABILITY-MATRIX.md"] + [f"docs/portfolio-integration/{p.name}" for p in sorted(OUT.glob("*.md"))]
man = dict(commit=commit, pushed=False, synthetic=True, artifacts=[dict(path=a, sha256=hashlib.sha256((REPO / a).read_bytes()).hexdigest(), bytes=(REPO / a).stat().st_size) for a in arts])
(LAB / "portfolio/evidence-manifest.json").write_text(json.dumps(man, indent=1))
print(len(arts), "artifacts")
