-- id: Q11
-- title: Latest days of cover versus supplier lead time
-- question: At the latest count, which site x ingredient pairs would run out before a new order could arrive?
-- technique: latest-row-per-group with ROW_NUMBER, derived ratio, comparison to a dimension attribute, inbound open PO quantity via pre-aggregated subquery
-- expected_shape: 24 rows (3 sites x 8 ingredients); at_risk = cover < lead time AND no open PO quantity covering the gap is NOT modelled (flag is conservative)
-- sqlite_specific: none
WITH latest AS (
  SELECT f.*, ROW_NUMBER() OVER (PARTITION BY f.site_key, f.ingredient_key ORDER BY f.date_key DESC) AS rn FROM fact_inventory_snapshot f),
open_po AS (SELECT site_key, ingredient_key, SUM(qty_ordered) AS open_qty FROM fact_po_line WHERE status = 'OPEN' GROUP BY site_key, ingredient_key)
SELECT s.site_id, g.ingredient, d.date AS count_date, l.on_hand_qty, ROUND(l.avg_daily_usage_14d, 3) AS avg_daily_usage,
       ROUND(l.on_hand_qty / NULLIF(l.avg_daily_usage_14d, 0), 1) AS days_of_cover, g.lead_time_days,
       COALESCE(o.open_qty, 0) AS open_po_qty,
       CASE WHEN l.on_hand_qty / NULLIF(l.avg_daily_usage_14d, 0) < g.lead_time_days THEN 1 ELSE 0 END AS below_lead_time
FROM latest l JOIN dim_site s USING (site_key) JOIN dim_ingredient g USING (ingredient_key) JOIN dim_date d USING (date_key)
LEFT JOIN open_po o ON o.site_key = l.site_key AND o.ingredient_key = l.ingredient_key
WHERE l.rn = 1 ORDER BY days_of_cover, s.site_id, g.ingredient
