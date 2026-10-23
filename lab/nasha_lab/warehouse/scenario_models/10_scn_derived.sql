-- Scenario tables derived from the published warehouse + the scenario base tables (menu, BOM, prices, inventory counts). SYNTHETIC.
-- Never modifies dim_/fact_/mart_ tables. Portable SQL (same statements run on SQLite and, via sqlglot, PostgreSQL).
CREATE TABLE scn_depletion_day AS
SELECT l.location_id, d.date, c.week, b.ingredient_id, SUM(f.qty * b.ap_qty_per_portion) AS theoretical_qty
FROM fact_order_line f
JOIN dim_product p ON p.product_key = f.product_key
JOIN scn_sim_item_map m ON m.sim_item_id = p.item_id AND m.menu_item_id IS NOT NULL
JOIN scn_recipe_bom b ON b.recipe_id = m.menu_item_id
JOIN scn_calendar c ON c.date_key = f.date_key
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_location l ON l.location_key = f.location_key
GROUP BY l.location_id, d.date, c.week, b.ingredient_id;
CREATE TABLE scn_depletion_week AS
SELECT location_id, week, ingredient_id, SUM(theoretical_qty) AS theoretical_qty FROM scn_depletion_day GROUP BY location_id, week, ingredient_id;
CREATE TABLE scn_item_month AS
SELECT d.month, l.location_id, p.item_id, m.price_basis, SUM(f.qty) AS units, SUM(f.gross_cents) AS v1_gross_cents, SUM(f.net_cents) AS v1_net_cents,
       CASE WHEN m.price_basis = 'v2_approved' THEN SUM(f.qty) * m.effective_price_cents ELSE SUM(f.gross_cents) END AS restated_gross_cents,
       CASE WHEN m.price_basis = 'v2_approved' THEN CAST(round(1.0 * SUM(f.net_cents) / SUM(f.gross_cents) * SUM(f.qty) * m.effective_price_cents) AS INTEGER) ELSE SUM(f.net_cents) END AS restated_net_cents
FROM fact_order_line f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_location l ON l.location_key = f.location_key
JOIN dim_product p ON p.product_key = f.product_key
JOIN scn_sim_item_map m ON m.sim_item_id = p.item_id
GROUP BY d.month, l.location_id, p.item_id, m.price_basis, m.effective_price_cents;
CREATE TABLE scn_menu_profitability_month AS
SELECT i.month, i.location_id, mi.menu_item_id, mi.menu_category, i.units, i.restated_net_cents,
       CAST(round(i.units * (mi.unit_food_cost_cents + mi.unit_consumables_cents)) AS INTEGER) AS food_and_consumables_cents,
       i.restated_net_cents - CAST(round(i.units * (mi.unit_food_cost_cents + mi.unit_consumables_cents)) AS INTEGER) AS gross_profit_cents
FROM scn_item_month i
JOIN scn_sim_item_map m ON m.sim_item_id = i.item_id AND m.menu_item_id IS NOT NULL
JOIN scn_menu_item mi ON mi.menu_item_id = m.menu_item_id;
CREATE TABLE scn_variance_week AS
SELECT i.location_id, i.week, i.ingredient_id, COALESCE(d.theoretical_qty, 0) AS theoretical_qty,
       i.opening_qty + i.receipts_qty - i.closing_counted_qty AS measured_qty,
       i.opening_qty + i.receipts_qty - i.closing_counted_qty - COALESCE(d.theoretical_qty, 0) AS variance_qty,
       CASE WHEN COALESCE(d.theoretical_qty, 0) > 0 THEN round((i.opening_qty + i.receipts_qty - i.closing_counted_qty) / d.theoretical_qty - 1, 4) END AS variance_pct
FROM scn_inventory_week i
LEFT JOIN scn_depletion_week d ON d.location_id = i.location_id AND d.week = i.week AND d.ingredient_id = i.ingredient_id;
CREATE TABLE scn_menu_engineering AS
WITH t AS (SELECT menu_item_id, menu_category, SUM(units) AS units, SUM(gross_profit_cents) AS gp FROM scn_menu_profitability_month GROUP BY menu_item_id, menu_category),
     tot AS (SELECT SUM(units) AS u, SUM(gp) AS g, COUNT(*) AS n FROM t)
SELECT t.menu_item_id, t.menu_category, t.units, round(1.0 * t.units / tot.u, 4) AS mix_pct, round(1.0 * t.gp / t.units, 2) AS gross_profit_per_unit_cents,
       CASE WHEN 1.0 * t.units / tot.u >= 0.7 / tot.n THEN 1 ELSE 0 END AS high_popularity,
       CASE WHEN 1.0 * t.gp / t.units >= 1.0 * tot.g / tot.u THEN 1 ELSE 0 END AS high_margin,
       CASE WHEN 1.0 * t.units / tot.u >= 0.7 / tot.n AND 1.0 * t.gp / t.units >= 1.0 * tot.g / tot.u THEN 'star'
            WHEN 1.0 * t.units / tot.u >= 0.7 / tot.n THEN 'plowhorse'
            WHEN 1.0 * t.gp / t.units >= 1.0 * tot.g / tot.u THEN 'puzzle' ELSE 'dog' END AS menu_class
FROM t CROSS JOIN tot;
