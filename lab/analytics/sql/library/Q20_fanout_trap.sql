-- id: Q20
-- title: Fan-out when joining an order header to its lines
-- question: Why does SUM(order_total) after joining lines overstate sales, and what is the safe pattern?
-- technique: demonstrate the trap (header measure repeated per line) next to the correct pre-aggregation; grain awareness
-- expected_shape: 1 row: naive_total_usd > correct_total_usd; correct equals gross sales from the line grain; inflation_factor is the order-value-weighted number of lines per order (larger than the plain mean, shown for contrast)
-- sqlite_specific: none
SELECT ROUND((SELECT SUM(o.order_total_cents) FROM fact_order o JOIN fact_order_line l ON l.order_key = o.order_key) / 100.0, 2) AS naive_total_usd,
       ROUND((SELECT SUM(order_total_cents) FROM fact_order) / 100.0, 2) AS correct_total_usd,
       ROUND((SELECT SUM(gross_sales_cents) FROM fact_order_line) / 100.0, 2) AS line_grain_total_usd,
       ROUND(1.0 * (SELECT SUM(o.order_total_cents) FROM fact_order o JOIN fact_order_line l ON l.order_key = o.order_key) / (SELECT SUM(order_total_cents) FROM fact_order), 3) AS inflation_factor,
       ROUND(1.0 * (SELECT COUNT(*) FROM fact_order_line) / (SELECT COUNT(*) FROM fact_order), 3) AS lines_per_order_unweighted
