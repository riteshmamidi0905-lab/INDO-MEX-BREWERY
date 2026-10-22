# Second synthetic customer — deployment pattern (SYNTHETIC; no real customer exists)

`nasha_lab/warehouse/tenancy.py` fronts per-tenant warehouses with one gateway. Tested with two generated customers (`cust-a`, `cust-b`: different seeds, site mix and volume) in `tests/test_tenancy.py` (4 tests).

## Onboarding a tenant
1. Generate or ingest the customer's data into its own source folder; run `python -m nasha_lab.warehouse run` → a separate `<tenant>.db` (contracts, quality gates and the publish gate apply per tenant).
2. Register `{tenant_id: path}` in the gateway registry; add explicit grants `{user: {tenant_id}}` (no wildcard; default deny).
3. Each tenant gets its own audit database; the gateway has a separate audit for decisions made before a tenant is chosen.
4. Per-tenant evaluation: re-run `tests/test_ops_ai_warehouse.py`-style independent-oracle checks against that tenant's warehouse before enabling it.

## What the tests prove
Tenants see only their own data (checked against independently recomputed order counts); a user without a grant is refused; arguments naming a tenant/warehouse/path are refused and logged; the same `location_id` resolves per tenant; site-manager scoping still works inside a tenant; audit rows never cross tenants.

## What is NOT claimed
Same process and code for all tenants (a shared-code bug could cross tenants); principals are trusted in-process objects (no identity provider); no network or OS-level isolation; no encryption, quotas or noisy-neighbour control; data is synthetic. This is a design demonstration, not a multi-tenant security certification. A production second customer would also need per-tenant secrets, backups and a separate deployment option.
