-- id: Q06
-- title: Weekly food-unit mix across the dish rename
-- question: How did the share of food units held by the dish M04 move around the menu change, and under which name?
-- technique: SCD2 name carried on the fact (item_key), weekly grain via dim_date, share-of-group with a partitioned window computed in a CTE BEFORE filtering (a WHERE in the same SELECT would shrink the window's partition)
-- expected_shape: M04 appears as 'Gobi Taco' for weeks before the change date and 'Mango Habanero Gobi' after; the change week has both names
-- sqlite_specific: none
WITH w AS (
  SELECT d.week_start, i.item_id, i.item_name, SUM(l.qty) AS units
  FROM fact_order_line l JOIN dim_date d USING (date_key) JOIN dim_menu_item i USING (item_key)
  WHERE i.category = 'food' GROUP BY d.week_start, i.item_id, i.item_name),
shares AS (SELECT *, ROUND(1.0 * units / SUM(units) OVER (PARTITION BY week_start), 4) AS share_of_food_units FROM w)   -- window BEFORE the M04 filter
SELECT week_start, item_name, units, share_of_food_units FROM shares WHERE item_id = 'M04' ORDER BY week_start, item_name
