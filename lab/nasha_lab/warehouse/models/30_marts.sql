-- model: marts
-- kind: tables
-- depends: fact_order, fact_order_line, fact_return, fact_waste, fact_quality_event, fact_labor_daily, fact_brew_batch, dim_date, dim_location, dim_product, dim_member
-- KPI definitions: docs/KPI-DEFINITIONS (lab/docs/DATA-PLATFORM.md). Every value is SYNTHETIC.
CREATE TABLE mart_daily_location AS
WITH o AS (SELECT date_key, location_key, count(*) orders, sum(subtotal_cents) gross_cents, sum(discount_cents) discount_cents, sum(total_cents) net_cents, sum(n_items) items, sum(member_key IS NOT NULL) member_orders FROM fact_order GROUP BY 1,2),
     c AS (SELECT date_key, location_key, sum(cogs_cents) cogs_cents FROM fact_order_line GROUP BY 1,2),
     w AS (SELECT date_key, location_key, sum(waste_cost_cents) waste_cost_cents, sum(qty_kg) waste_kg FROM fact_waste GROUP BY 1,2),
     q AS (SELECT date_key, location_key, count(*) quality_events FROM fact_quality_event GROUP BY 1,2)
SELECT o.date_key, d.date, d.month, o.location_key, l.location_id, l.format, o.orders, o.items, o.gross_cents, o.discount_cents, o.net_cents, c.cogs_cents, o.net_cents - c.cogs_cents AS gross_margin_cents,
       o.member_orders, f.scheduled_labor_hours, f.actual_labor_hours, f.labor_cost_cents, COALESCE(w.waste_cost_cents,0) waste_cost_cents, COALESCE(w.waste_kg,0) waste_kg, COALESCE(q.quality_events,0) quality_events,
       round(1.0 * o.net_cents / o.orders, 1) AS avg_ticket_cents,
       CASE WHEN f.actual_labor_hours > 0 THEN round(1.0 * o.net_cents / f.actual_labor_hours, 1) END AS sales_per_labor_hour_cents,
       CASE WHEN o.net_cents > 0 THEN round(1.0 * f.labor_cost_cents / o.net_cents, 4) END AS labor_pct_of_sales
FROM o JOIN c USING (date_key, location_key) JOIN dim_date d ON d.date_key = o.date_key JOIN dim_location l ON l.location_key = o.location_key
LEFT JOIN fact_labor_daily f ON f.date_key = o.date_key AND f.location_key = o.location_key LEFT JOIN w ON w.date_key = o.date_key AND w.location_key = o.location_key LEFT JOIN q ON q.date_key = o.date_key AND q.location_key = o.location_key;
CREATE INDEX ix_mdl_month ON mart_daily_location(month, location_id);
CREATE TABLE mart_company_month AS
SELECT month, count(DISTINCT location_id) active_locations, sum(orders) orders, sum(items) items, sum(gross_cents) gross_cents, sum(discount_cents) discount_cents, sum(net_cents) net_cents, sum(cogs_cents) cogs_cents, sum(gross_margin_cents) gross_margin_cents,
       sum(member_orders) member_orders, sum(labor_cost_cents) labor_cost_cents, sum(actual_labor_hours) actual_labor_hours, sum(waste_cost_cents) waste_cost_cents, sum(quality_events) quality_events,
       round(1.0 * sum(net_cents) / sum(orders), 1) avg_ticket_cents, round(1.0 * sum(gross_margin_cents) / sum(net_cents), 4) gross_margin_pct, round(1.0 * sum(labor_cost_cents) / sum(net_cents), 4) labor_pct_of_sales,
       round(1.0 * sum(member_orders) / sum(orders), 4) member_order_share, round(1.0 * sum(net_cents) / sum(actual_labor_hours), 1) sales_per_labor_hour_cents,
       sum(net_cents) - sum(cogs_cents) - sum(labor_cost_cents) - sum(waste_cost_cents) AS contribution_after_labor_cents
FROM mart_daily_location GROUP BY month;
CREATE TABLE mart_location_month AS
SELECT month, location_id, format, sum(orders) orders, sum(net_cents) net_cents, sum(gross_margin_cents) gross_margin_cents, sum(labor_cost_cents) labor_cost_cents, sum(waste_cost_cents) waste_cost_cents, sum(waste_kg) waste_kg,
       sum(quality_events) quality_events, round(1.0 * sum(net_cents) / sum(orders), 1) avg_ticket_cents, round(1.0 * sum(labor_cost_cents) / sum(net_cents), 4) labor_pct_of_sales,
       round(1.0 * sum(net_cents) / sum(actual_labor_hours), 1) sales_per_labor_hour_cents, round(1.0 * sum(waste_cost_cents) / sum(cogs_cents), 4) waste_pct_of_cogs
FROM mart_daily_location GROUP BY month, location_id, format;
CREATE TABLE mart_product_month AS
SELECT substr(d.date,1,7) AS month, p.item_id, p.name, p.category, p.is_concept_sku, sum(f.qty) units, sum(f.gross_cents) gross_cents, sum(f.discount_alloc_cents) discount_cents, sum(f.net_cents) net_cents, sum(f.cogs_cents) cogs_cents,
       sum(f.margin_cents) margin_cents, round(1.0 * sum(f.margin_cents) / sum(f.net_cents), 4) margin_pct
FROM fact_order_line f JOIN dim_date d ON d.date_key = f.date_key JOIN dim_product p ON p.product_key = f.product_key GROUP BY 1, 2;
CREATE TABLE mart_merch_month AS
WITH s AS (SELECT month, item_id, name, units, net_cents FROM mart_product_month WHERE category = 'merch'),
     r AS (SELECT substr(d.date,1,7) month, p.item_id, count(*) returns, sum(r.refund_cents) refund_cents FROM fact_return r JOIN dim_date d ON d.date_key = r.date_key JOIN dim_product p ON p.product_key = r.product_key GROUP BY 1,2)
SELECT s.month, s.item_id, s.name, s.units, s.net_cents, COALESCE(r.returns,0) returns, COALESCE(r.refund_cents,0) refund_cents, round(1.0 * COALESCE(r.returns,0) / s.units, 4) return_rate FROM s LEFT JOIN r USING (month, item_id);
CREATE TABLE mart_loyalty_cohort AS
WITH m AS (SELECT dm.cohort_month, substr(d.date,1,7) AS month, f.member_key, count(*) orders, sum(f.total_cents) net_cents FROM fact_order f JOIN dim_member dm ON dm.member_key = f.member_key JOIN dim_date d ON d.date_key = f.date_key GROUP BY 1,2,3),
     sz AS (SELECT cohort_month, count(*) members FROM dim_member GROUP BY 1)
SELECT m.cohort_month, m.month, sz.members AS cohort_size, count(*) active_members, sum(m.orders) orders, sum(m.net_cents) net_cents, round(1.0 * count(*) / sz.members, 4) retention
FROM m JOIN sz USING (cohort_month) GROUP BY m.cohort_month, m.month;
CREATE TABLE mart_inventory_waste AS
SELECT substr(d.date,1,7) AS month, l.location_id, w.ingredient, sum(w.qty_kg) waste_kg, sum(w.waste_cost_cents) waste_cost_cents, count(*) events FROM fact_waste w JOIN dim_date d ON d.date_key = w.date_key JOIN dim_location l ON l.location_key = w.location_key GROUP BY 1,2,3;
