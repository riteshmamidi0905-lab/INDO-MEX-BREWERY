SELECT o.site, COUNT(*) AS orders, SUM(o.total_usd) AS revenue_usd
FROM orders o WHERE EXISTS (SELECT 1 FROM order_lines l WHERE l.order_id = o.order_id)
GROUP BY o.site ORDER BY o.site;
