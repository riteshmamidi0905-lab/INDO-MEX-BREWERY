# Interactive demo specifications (all client-side, recorded data)
1. **Trace player** (built in the portfolio candidate): tabs = scenarios; Play/Step/Reset; side panel shows the purchase-order counter, outcome, audit rows. Data: `scenarios[].steps`, `audit`, `purchase_orders_created`. Keyboard: arrow keys on tabs; live region announces steps.
2. **Architecture explorer** (built): nodes from `architecture.nodes`, edges from `architecture.edges`; filter by status; panel lists code and test paths.
3. **Attack gallery** (spec): one card per scenario with a one-line "attack → control → result" and a button that opens the player on that scenario.
4. **Metrics panel** (built as bars): `metrics.ops_ai_evaluation.by_category`, `metrics.governed_workflow_tests`; must show the caveat string verbatim.
5. **API explorer** (spec, not built): render `governed-api.openapi.json`; no "Try it" button, because no public backend exists.
6. **Approval-binding visualiser** (spec): show the call hash inputs (proposal id, reco id, inputs hash, quantity, supplier, quote, amount) and which field a tamper changed, using the `modified_after_approval` scenario. Do not invent hash values: use only fields present in the data.
Constraint: no demo may call a backend, a model or any external service.
