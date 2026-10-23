# NASHA portfolio integration package (D-89)
For the portfolio team. **Everything here is derived from executed code; nothing is hand-written marketing.** Generated against local NASHA commit `b0e7255` (not pushed). Synthetic data throughout; NASHA is a concept, not an operating business.

| File | Use |
|---|---|
| `lab/portfolio/nasha-governed-evidence.json` | Replayable timelines for 8 executed scenarios, measured metrics, architecture graph with per-component status. The website's player and architecture explorer read this file unchanged. |
| `lab/portfolio/capability-matrix.json` + `docs/engineering/D-89-CAPABILITY-MATRIX.md` | Implemented-and-tested / unverified / designed / blocked / not started, with code and test references. |
| `lab/portfolio/governed-api.openapi.json` | API contract (6 operations) for an "API explorer" panel; the API is tested but not deployed. |
| `lab/portfolio/evidence-manifest.json` | sha256 of each artifact above, for pinning. |
| `WORKFLOW-EXPLAINED.md`, `SECURITY-DEMO-SCENARIOS.md`, `INTERACTIVE-DEMO-SPECS.md`, `PROJECT-CONNECTIONS.md`, `LIMITATIONS.md` | Copy and specs. |

## Rules for the website
1. Never state a capability whose status in the matrix is not IMPLEMENTED_TESTED (or says what it is: blocked, designed, not integrated).
2. Show the commit and the "not pushed" flag until the commits are pushed, then update the evidence file by re-running the exporter.
3. Replays are recordings; no page may imply a live backend or a live model.
4. Reproduce: `cd lab && python3 tools/export_portfolio_evidence.py`.
