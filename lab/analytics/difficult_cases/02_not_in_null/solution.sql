SELECT m.item_id FROM menu m WHERE NOT EXISTS (SELECT 1 FROM sales s WHERE s.item_id = m.item_id) ORDER BY m.item_id;
