-- id: Q14
-- title: ABC classification of items by gross sales
-- question: Which few items make up 70% / 90% of sales?
-- technique: cumulative share with SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING); class by the cumulative share BEFORE the row so the item that crosses the threshold is still class A
-- expected_shape: one row per item id (10); cumulative_share ends at 1.0; classes A, B, C partition the rows
-- sqlite_specific: none
WITH s AS (SELECT i.item_id, SUM(l.gross_sales_cents) / 100.0 AS sales FROM fact_order_line l JOIN dim_menu_item i USING (item_key) GROUP BY i.item_id),
c AS (SELECT item_id, sales, 1.0 * SUM(sales) OVER (ORDER BY sales DESC, item_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / SUM(sales) OVER () AS cum_share FROM s)
SELECT item_id, ROUND(sales, 2) AS sales_usd, ROUND(cum_share, 4) AS cumulative_share,
       CASE WHEN cum_share - 1.0 * sales / SUM(sales) OVER () < 0.70 THEN 'A' WHEN cum_share - 1.0 * sales / SUM(sales) OVER () < 0.90 THEN 'B' ELSE 'C' END AS abc_class
FROM c ORDER BY sales DESC, item_id
