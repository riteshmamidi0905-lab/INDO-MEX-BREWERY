# NASHA data platform (synthetic warehouse, dashboards, product analytics)

**SYNTHETIC DATA / SIMULATED OPERATION.** Built over `nasha_lab.enterprise_sim` output. No real business, customer or employee exists; prices, wages and costs are placeholders; volumes are uncalibrated. Nothing here is a NASHA result. NASHA is a working name (D-79/D-80) and a concept.

## Architecture
simulator (gzip CSV + manifest) -> **contracts** -> **incremental ingestion** (`raw_*` by month partition, quarantine) -> **raw gate** -> **SQL models** (dimensions, facts, marts; lineage recorded) -> **warehouse gate** (independent reconciliation against the source files) -> `warehouse_status = published` -> dashboards and analytics (refuse to run unless published) -> monitoring.
Stack: Python 3, pandas, SQLite (stdlib). No dbt, Airflow or cloud warehouse: the choice keeps it reproducible on a laptop; the module headers (`-- depends:`) are the dbt-style idea without the framework. Code: `lab/nasha_lab/warehouse/`.

Run: `python -m nasha_lab.enterprise_sim --profile full --out SRC && python -m nasha_lab.warehouse run --source SRC --db wh.db && python -m nasha_lab.warehouse.dashboards --db wh.db --out dashboards/` (add `--through 2024-06` to simulate data that has not arrived; `python -m nasha_lab.warehouse monitor|lineage --db wh.db`).

## Data contracts (`contracts.py`)
Per source table: columns and types, nullability, keys, accepted values, row rules (for example `total_cents == subtotal_cents - discount_cents`). A column mismatch rejects the file (`ContractError`); row violations are quarantined with a reason, and a quarantine rate above 0.1% blocks publication.

## Models
Dimensions: location, product (placeholder cost percentages), member, employee, promotion, supplier, date (calendar spans the loaded data and is rebuilt when partitions arrive). Facts: order (order grain), order line (discount allocated to lines by cumulative rounding so allocations sum exactly), return, inventory count, waste (placeholder ingredient costs), quality event, labor day (placeholder wages), brew batch. Marts: daily location, location month, company month, product month, merchandise month, loyalty cohort, inventory and waste.
Incremental: facts rebuild only for month partitions whose input fingerprint changed; a dimension change forces a full fact rebuild.

## KPI definitions (all synthetic)
| KPI | Definition | Grain / source |
|---|---|---|
| Net sales | sum of order totals after discounts | order; `fact_order.total_cents` |
| Gross sales | sum of order subtotals before discounts | order |
| Average ticket | net sales / orders | day x location, month |
| Gross margin | net sales minus placeholder COGS (qty x list price x category cost %) | order line |
| Labor cost / labor % | actual labor hours x average placeholder hourly wage of the site's employees / net sales | day x location |
| Sales per labor hour | net sales / actual labor hours | day x location |
| Waste cost / waste % COGS | kg wasted x placeholder cost per kg / COGS | event; site, month |
| Member order share | orders with a loyalty member / orders | month |
| Retention (cohort) | members active in a month / cohort size (join month) | cohort x month |
| Funnel | joined; first order within 30 days of joining; second order within 60 days of the first (only members with enough elapsed time counted) | member |
| RFM segment | recency, frequency, monetary tertiles; descriptive, not predictive | member |
| Return rate (merch) | returned lines / units | SKU, month |

## Quality gates (blocking unless noted)
Raw: no duplicate order id, line key or member id; no order line without an order, no order at an unknown site, no unknown item, no unknown member, no return without a line, no order before the site opened; quarantine rate. Warehouse (recomputed from the source files with pandas): order count, subtotal, discount and total by month; line count and gross by month; net sales by month x location; exact discount allocation, line net equals order total, line gross equals order subtotal; company-month net equals fact total; dimension row counts; no non-positive net or quantity. Warnings: gross-margin and labor-percentage sanity bands (placeholder inputs). Results are stored in `dq_results`.

## Lineage and monitoring
`lineage` holds model -> dependency edges from the SQL headers (`python -m nasha_lab.warehouse lineage`). `pipeline_runs`, `pipeline_steps`, `load_partitions`, `quarantine`, `dq_results` feed `monitor`: last runs, slowest steps, partition freshness, quarantine counts, failed gates.

## Tested behaviour (`tests/test_warehouse.py`, `tests/test_warehouse_bi.py`)
Full load publishes and reconciles; a rerun is a no-op; incremental arrival equals a one-shot load; a crash mid-load recovers to the identical result; a late correction reloads only the changed partition and is blocked by reconciliation; duplicates and bad values are quarantined or block publication; tampering with the warehouse is detected; a structural contract break rejects the file; dashboards and analytics refuse an unpublished warehouse.

## Measured (see `lab/results/enterprise_full_run.json`)
Recorded from a real full run; regenerate with `nasha_lab.warehouse.record_run`.

## Limits
Placeholder prices, wages, costs; uncalibrated volumes; labor model is a fixed baseline plus a volume term (small profiles show absurd labor %); inventory counts are simulated from volume, so no days-of-cover or variance analysis is offered; no slowly changing dimensions; SQLite is single-writer and would be replaced at scale; promotions have no behavioural response in the simulator; experiment outcomes are simulated from the warehouse baseline with injected effects.
