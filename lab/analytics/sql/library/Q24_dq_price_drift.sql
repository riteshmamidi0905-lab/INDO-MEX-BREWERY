-- id: Q24
-- title: Line price versus item median price (raw landing)
-- question: Which order lines were charged far from the item's usual price?
-- technique: data-derived reference (item median via window emulation) instead of trusting the menu table; ratio band [0.8, 1.2]
-- expected_shape: rows outside the band; the 10% happy-hour beer discount is inside the band by design; injected drift factors (0.45, 0.5, 1.45, 1.9) are outside
-- sqlite_specific: none
WITH p AS (SELECT item_id, CAST(unit_price_cents AS INTEGER) AS price, ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY CAST(unit_price_cents AS INTEGER)) AS rn, COUNT(*) OVER (PARTITION BY item_id) AS n FROM raw_order_lines),
med AS (SELECT item_id, AVG(price) AS median_price FROM p WHERE rn IN ((n + 1) / 2, (n + 2) / 2) GROUP BY item_id)
SELECT l.order_id, l.line_no, l.item_id, CAST(l.unit_price_cents AS INTEGER) AS price, m.median_price, ROUND(1.0 * CAST(l.unit_price_cents AS INTEGER) / m.median_price, 2) AS ratio
FROM raw_order_lines l JOIN med m USING (item_id)
WHERE 1.0 * CAST(l.unit_price_cents AS INTEGER) / m.median_price NOT BETWEEN 0.8 AND 1.2 ORDER BY l.order_id, l.line_no
