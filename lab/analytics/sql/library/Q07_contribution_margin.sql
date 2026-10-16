-- id: Q07
-- title: Contribution margin by item version (ASSUMPTION costs)
-- question: Given the ASSUMED costs in analytics/config.py, which item versions contribute most per unit and in total?
-- technique: separate pre-aggregated CTEs per cost component joined on item_key (avoids fan-out), COALESCE for items without recipes, RANK
-- expected_shape: one row per item version (11 sold items incl. both M04 versions); sums to the contribution_margin_usd metric
-- sqlite_specific: none. ALL COSTS ARE ASSUMPTIONS; this is NOT a NASHA margin.
WITH sales AS (SELECT item_key, SUM(qty) AS units, SUM(gross_sales_cents) / 100.0 AS sales FROM fact_order_line GROUP BY item_key),
recipe AS (SELECT b.item_key, SUM(b.kg_per_unit * g.assumed_cost_per_kg) AS ingredient_cost_per_unit FROM bridge_item_ingredient b JOIN dim_ingredient g USING (ingredient_key) GROUP BY b.item_key),
cm AS (
  SELECT i.item_key, i.item_id, i.item_name, i.category, s.units, s.sales,
         s.units * COALESCE(r.ingredient_cost_per_unit, 0) AS ingredient_cost,
         s.sales * CASE i.category WHEN 'food' THEN {{OTHER_FOOD}} ELSE 0 END AS other_cost,
         s.units * CASE i.category WHEN 'beer' THEN {{FIXED_BEER}} WHEN 'na' THEN {{FIXED_NA}} ELSE 0 END AS fixed_cost
  FROM sales s JOIN dim_menu_item i USING (item_key) LEFT JOIN recipe r USING (item_key))
SELECT item_id, item_name, category, units, ROUND(sales, 2) AS sales_usd,
       ROUND(sales - ingredient_cost - other_cost - fixed_cost, 2) AS margin_usd,
       ROUND(100.0 * (sales - ingredient_cost - other_cost - fixed_cost) / sales, 1) AS margin_pct,
       RANK() OVER (ORDER BY (sales - ingredient_cost - other_cost - fixed_cost) DESC) AS margin_rank
FROM cm ORDER BY margin_rank
