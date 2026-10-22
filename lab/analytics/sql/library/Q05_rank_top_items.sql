-- id: Q05
-- title: Top three items per site by gross sales (ties kept)
-- question: Which three menu items earn the most at each site?
-- technique: RANK() (not ROW_NUMBER) so ties are kept, filter on the window result via a subquery, SCD2-safe grouping on item_id with the CURRENT name
-- expected_shape: >= 3 rows per site, ranks 1..3 present
-- sqlite_specific: none
WITH item_sales AS (
  SELECT s.site_id, i.item_id, SUM(l.gross_sales_cents) / 100.0 AS sales
  FROM fact_order_line l JOIN dim_site s USING (site_key) JOIN dim_menu_item i USING (item_key) GROUP BY s.site_id, i.item_id),
ranked AS (SELECT *, RANK() OVER (PARTITION BY site_id ORDER BY sales DESC) AS rnk FROM item_sales)
SELECT r.site_id, r.rnk, r.item_id, cur.item_name AS current_name, r.sales
FROM ranked r JOIN dim_menu_item cur ON cur.item_id = r.item_id AND cur.is_current = 1
WHERE r.rnk <= 3 ORDER BY r.site_id, r.rnk, r.item_id
