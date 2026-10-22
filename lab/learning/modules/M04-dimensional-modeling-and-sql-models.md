# Module M04: dimensional modeling and SQL models (`warehouse/models/*.sql`)

Status for you: NOT ASSESSED.

**A. Architecture.** Dimensions (location, product, member, employee, promotion, supplier, date) with surrogate keys; facts at stated grains (order, order line, return, waste, labor-day, brew batch); marts for KPIs. Models are plain SQL files with `-- depends:` headers; the runner orders them, records lineage and rebuilds incrementally by month. The order discount is allocated to lines by cumulative rounding so allocations sum exactly.
**Concepts.** Grain, surrogate vs natural keys, slowly changing dimensions (not implemented here: say why that matters), window functions (`SUM() OVER`), degenerate dimensions, conformed dimensions, additive vs non-additive measures, incremental models.
**B. Independent exercise.** From `orders` and `order_lines` CSVs, build `fact_order_line` with a per-line discount allocation that sums exactly to the order discount. Prove it with a query.
**C. Debugging challenge.** A dashboard shows March net sales $50k lower than the source. Find the cause using only SQL on the warehouse (hint: a join that drops rows; check `dim_date` span and inner joins). The repo hit this exact bug during development (the calendar was built only on the first load): read the header of `models/15_dim_date.sql` and explain the fix.
**D. Interview questions.** State the grain of every fact table. Why is average ticket not additive? When would you choose a snowflake over a star?
**E. Tradeoffs.** One big table vs star schema; surrogate keys vs natural keys in a small warehouse; incremental vs full rebuild; SQL files vs a framework (dbt) and what you would gain.
**F. Evidence.** Date / task / link.
