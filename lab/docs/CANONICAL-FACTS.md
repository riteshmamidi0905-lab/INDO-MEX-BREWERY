# Canonical facts: tool counts and test-count provenance

Checked 2026-10-16 against `nasha_lab/tools.py`, git history, and the GitHub Actions log of lab-ci run 38823655823. Frozen Block 3 files are not edited; historical numbers stay historical.

## Tool counts (one number per question; never use a bare "N tools")
| Question | Count | How to verify |
|---|---|---|
| Registered `ToolSpec`s in `tools.TOOLS` (current, and in the frozen Block 3 code commit 647d47e) | **19** | `len(nasha_lab.tools.TOOLS)` |
| Of those, callable (exposed to planners/agent/HTTP) | **17** | `tool_catalog()` / `exposed=True` |
| Registered but FORBIDDEN placeholders (`exposed=False`, EXTERNAL_ACTION: `contact_supplier`, `place_purchase_order`), registered so a forbidden call is refused and logged | **2** | `exposed=False` |
| Offered over the trusted MCP server (`MCP_TOOLS`) | **9** | `nasha_lab.mcp_server.MCP_TOOLS` |
| By permission class (registered) | READ 10, ANALYZE 2, DRAFT 2, MUTATE_SIMULATION 3, EXTERNAL_ACTION 2 | count by `permission` |

**Why older documents say 18.** The Block 2 registry (commit 7532bd4) registered 18 tools. Block 3 commit 504831a added `get_supplier_notes_untrusted` (the untrusted-MCP tool), making 19; README, CASE-STUDY and the evidence diagram were not updated. The frozen Block 3 baseline code therefore already had 19. This is a documentation staleness, not a change of behaviour. `THREAT-MODEL.md`'s "allowlist of 9 typed tools" refers to the trusted MCP surface and is correct.

## Test-count provenance (do not collapse these)
| Number | What it is | Evidence |
|---|---|---|
| **229 passed, 1 skipped** | Frozen Block 3 CI run on code commit 647d47e (historical) | `claims/claims.json` (verified: GitHub Actions job log), `baseline/BASELINE-BLOCK3.json` |
| 228 passed, 2 skipped | Block 3 local authoring sandbox (historical) | `results/test_summary.json` |
| **266 passed, 1 skipped** (267 collected) | lab-ci `test` job on commit 9cb7ca4, run 38823655823, with the pgvector service container | GitHub Actions job log line `266 passed, 1 skipped in 151.14s` |
| **265 passed, 2 skipped** (267 collected) | Local run on the same final state without PostgreSQL/pgvector (one extra test runs in CI) | Local pytest, 2026-10-16 |
| Later counts | Any later change must restate commit, environment and date | - |

Public wording (conservative): "265 passed, 2 skipped locally on the final lab state; GitHub lab-ci green on 9cb7ca4 (266 passed, 1 skipped); the frozen Block 3 CI run had 229."
