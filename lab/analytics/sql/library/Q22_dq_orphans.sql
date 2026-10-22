-- id: Q22
-- title: Orphan keys in the raw landing zone
-- question: Which raw order lines point at a menu item or an order that does not exist?
-- technique: anti-join with NOT EXISTS (NULL-safe, unlike NOT IN); UNION ALL of the two orphan kinds
-- expected_shape: rows of kind 'unknown item' (the injected orphan_item defects, 8 in this build); 'missing parent order' = 0
-- sqlite_specific: none
SELECT 'unknown item' AS kind, l.order_id, l.line_no, l.item_id AS bad_key FROM raw_order_lines l
WHERE NOT EXISTS (SELECT 1 FROM raw_menu_items m WHERE m.item_id = l.item_id)
UNION ALL
SELECT 'missing parent order', l.order_id, l.line_no, l.order_id FROM raw_order_lines l
WHERE NOT EXISTS (SELECT 1 FROM raw_orders o WHERE o.order_id = l.order_id)
ORDER BY 1, 2, 3
