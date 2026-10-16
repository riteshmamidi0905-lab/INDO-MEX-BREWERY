SELECT COALESCE(i.category, 'UNKNOWN') AS category, SUM(s.amount_usd) AS revenue_usd
FROM sales s LEFT JOIN items i ON i.item_id = s.item_id GROUP BY COALESCE(i.category, 'UNKNOWN') ORDER BY category;
