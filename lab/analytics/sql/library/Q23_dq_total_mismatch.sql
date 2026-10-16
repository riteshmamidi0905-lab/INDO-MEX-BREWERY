-- id: Q23
-- title: Order header total versus the sum of its lines (raw landing)
-- question: Which raw orders have a header total that disagrees with their lines?
-- technique: pre-aggregate lines to the order grain BEFORE joining (no fan-out), compare, tolerate nothing (integer cents)
-- expected_shape: rows of order_id with a non-zero diff_cents; includes the injected order_total_mismatch orders (8) and reports honestly any others
-- sqlite_specific: none
WITH ln AS (SELECT order_id, SUM(CAST(qty AS INTEGER) * CAST(unit_price_cents AS INTEGER)) AS lines_cents FROM raw_order_lines GROUP BY order_id)
SELECT o.order_id, CAST(o.total_cents AS INTEGER) AS header_cents, ln.lines_cents, CAST(o.total_cents AS INTEGER) - ln.lines_cents AS diff_cents
FROM (SELECT DISTINCT order_id, total_cents FROM raw_orders) o JOIN ln USING (order_id)
WHERE CAST(o.total_cents AS INTEGER) <> ln.lines_cents ORDER BY o.order_id
