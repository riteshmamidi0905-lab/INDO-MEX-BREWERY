# Ops AI over the warehouse, behind THE WEIR (SYNTHETIC)

`nasha_lab/warehouse/ops_ai_weir.py` plugs the Ops AI tools into the **real** `mcp_weir` Gateway (`Gateway`, `Store`, `parse_policy`, the testbed `notes` upstream) as an in-process upstream named `warehouse`.

## Layers (neither trusts the other)
1. **THE WEIR first:** per-tool policy (`warehouse__*` = `read`, results labelled `internal`), `gate_egress: deny`, `gate_write: approve`, tamper-evident audit chain, approval consumption. A call it does not forward never reaches the warehouse.
2. **Ops AI second:** its own default-deny role/site gate, read-only warehouse connection and audit row.
3. **Join:** WEIR events carry a 16-hex prefix of `call_hash`; the upstream recomputes the same hash from `{"tool": "warehouse__<name>", "args": ...}` and stores it, so `joined_audit()` matches each WEIR decision to the Ops AI row it caused (or shows that WEIR blocked it first).

## What `tests/test_ops_ai_weir.py` proves (4 tests, real gateway, passing locally)
- An allowed read returns the same rows as a direct call; the WEIR chain verifies; the audits join.
- Unknown tools are denied by WEIR and never reach the Ops AI layer (zero Ops audit rows).
- After a session has read `internal` warehouse data, an egress tool (`notes__publish_note`) is denied (`R-GATE`) and no effect occurs.
- A site manager's out-of-scope request is allowed by WEIR but denied by the Ops AI layer (`site_scope`, `role_denied`): defence in depth.
- A write tool (`notes__save_note`) needs approval; nothing executes while pending; after approval it executes once.

## Limits
One gateway/upstream per principal (the upstream does not see the WEIR session); synthetic data; no LLM involved; the WEIR package is a separate repository and must be installed (pinned in CI to a specific commit; here the local editable install of `mcp-weir` was used). WEIR's `flow_conf_secret` rule only blocks `secret`-labelled flows; warehouse reads are `internal`, so egress is blocked by the egress gate, not by the label rule.
