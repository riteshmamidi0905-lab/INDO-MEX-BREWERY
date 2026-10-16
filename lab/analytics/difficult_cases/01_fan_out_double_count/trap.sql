-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT o.site, COUNT(*) AS orders, SUM(o.total_usd) AS revenue_usd
FROM orders o JOIN order_lines l ON l.order_id = o.order_id GROUP BY o.site ORDER BY o.site;
