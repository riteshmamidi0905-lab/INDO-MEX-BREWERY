-- id: Q04
-- title: Order-value quartiles and their share of sales
-- question: How concentrated is revenue across order-value quartiles?
-- technique: NTILE(4) over orders, then aggregate per bucket; share of total with an empty-OVER window
-- expected_shape: 4 rows; quartile sizes differ by at most 1; share_of_sales sums to 1
-- sqlite_specific: none
WITH q AS (SELECT order_id, order_total_cents, NTILE(4) OVER (ORDER BY order_total_cents, order_id) AS quartile FROM fact_order)
SELECT quartile, COUNT(*) AS orders, MIN(order_total_cents) / 100.0 AS min_usd, MAX(order_total_cents) / 100.0 AS max_usd,
       ROUND(1.0 * SUM(order_total_cents) / SUM(SUM(order_total_cents)) OVER (), 4) AS share_of_sales
FROM q GROUP BY quartile ORDER BY quartile
