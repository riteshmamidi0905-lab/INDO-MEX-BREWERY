-- id: Q08
-- title: Item pair affinity (support and lift)
-- question: Which items are bought together more often than independence would predict?
-- technique: self-join of order lines on order, a < b to count each pair once, COUNT(DISTINCT order) to avoid fan-out, lift = P(a,b) / (P(a) P(b))
-- expected_shape: 45 pairs of the 10 menu items; there is no planted affinity, and every lift is BELOW 1 (0.8-1.0) because the generator draws 1-4 distinct items per order without replacement; read that as a sampling artifact, not substitution
-- sqlite_specific: none
WITH n AS (SELECT COUNT(DISTINCT order_key) AS orders FROM fact_order_line),
item_orders AS (SELECT i.item_id, COUNT(DISTINCT l.order_key) AS orders_with_item FROM fact_order_line l JOIN dim_menu_item i USING (item_key) GROUP BY i.item_id),
lines AS (SELECT DISTINCT l.order_key, i.item_id FROM fact_order_line l JOIN dim_menu_item i USING (item_key)),
pairs AS (SELECT a.item_id AS item_a, b.item_id AS item_b, COUNT(*) AS orders_with_both FROM lines a JOIN lines b ON a.order_key = b.order_key AND a.item_id < b.item_id GROUP BY 1, 2)
SELECT p.item_a, p.item_b, p.orders_with_both,
       ROUND(1.0 * p.orders_with_both / n.orders, 4) AS support,
       ROUND((1.0 * p.orders_with_both / n.orders) / ((1.0 * ia.orders_with_item / n.orders) * (1.0 * ib.orders_with_item / n.orders)), 3) AS lift
FROM pairs p CROSS JOIN n JOIN item_orders ia ON ia.item_id = p.item_a JOIN item_orders ib ON ib.item_id = p.item_b
ORDER BY lift DESC, p.item_a, p.item_b
