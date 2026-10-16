-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT i.category, SUM(s.amount_usd) AS revenue_usd FROM sales s JOIN items i ON i.item_id = s.item_id GROUP BY i.category ORDER BY i.category;
