-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT item_id FROM menu WHERE item_id NOT IN (SELECT item_id FROM sales) ORDER BY item_id;
