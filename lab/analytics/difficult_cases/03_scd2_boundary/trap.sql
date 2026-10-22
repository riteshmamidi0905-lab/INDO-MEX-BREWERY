-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT d.item_name, SUM(s.qty) AS units FROM sales s
JOIN dim_item d ON d.item_id = s.item_id AND s.sale_date BETWEEN d.valid_from AND d.valid_to
WHERE s.item_id = 'M04' GROUP BY d.item_name ORDER BY d.item_name;
