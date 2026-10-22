-- model: fact_other
-- kind: tables
-- depends: stg_returns, stg_inventory_counts, stg_waste_events, stg_quality_events, stg_shifts, stg_brew_batches, fact_order_line, dim_location, dim_product, dim_employee, ref_ingredient_cost
CREATE TABLE fact_return AS SELECT r.order_id, r.line_no, f.date_key, f.location_key, f.product_key, r.return_reason, r.refund_cents FROM stg_returns r JOIN fact_order_line f ON f.order_id = r.order_id AND f.line_no = r.line_no;
CREATE TABLE fact_inventory_count AS SELECT CAST(replace(i.count_date,'-','') AS INTEGER) AS date_key, l.location_key, i.ingredient, i.qty AS qty_kg FROM stg_inventory_counts i JOIN dim_location l ON l.location_id = i.location_id;
CREATE TABLE fact_waste AS SELECT CAST(replace(w.date,'-','') AS INTEGER) AS date_key, l.location_key, w.ingredient, w.qty_kg, w.reason, CAST(round(w.qty_kg * c.cents_per_kg) AS INTEGER) AS waste_cost_cents FROM stg_waste_events w JOIN dim_location l ON l.location_id = w.location_id JOIN ref_ingredient_cost c ON c.ingredient = w.ingredient;
CREATE TABLE fact_quality_event AS SELECT CAST(replace(q.date,'-','') AS INTEGER) AS date_key, l.location_key, q.event_type, q.severity FROM stg_quality_events q JOIN dim_location l ON l.location_id = q.location_id;
CREATE TABLE fact_labor_daily AS SELECT CAST(replace(s.date,'-','') AS INTEGER) AS date_key, l.location_key, s.scheduled_labor_hours, s.actual_labor_hours,
  CAST(round(COALESCE(w.avg_rate, 1400)) AS INTEGER) AS avg_hourly_rate_cents, CAST(round(s.actual_labor_hours * COALESCE(w.avg_rate, 1400)) AS INTEGER) AS labor_cost_cents
  FROM stg_shifts s JOIN dim_location l ON l.location_id = s.location_id LEFT JOIN (SELECT location_id, avg(hourly_rate_cents) AS avg_rate FROM dim_employee GROUP BY location_id) w ON w.location_id = s.location_id;
CREATE TABLE fact_brew_batch AS SELECT b.batch_id, CAST(replace(b.brew_date,'-','') AS INTEGER) AS date_key, l.location_key, p.product_key, b.planned_liters, b.yield_liters, round(b.yield_liters / b.planned_liters, 4) AS yield_ratio, b.status
  FROM stg_brew_batches b JOIN dim_location l ON l.location_id = b.location_id JOIN dim_product p ON p.item_id = b.beer_id;
