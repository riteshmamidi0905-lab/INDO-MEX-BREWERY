-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT substr(s.sale_date,1,7) AS month, SUM(s.amount_usd) - COALESCE(SUM(r.amount_usd),0) AS net_usd
FROM sales s LEFT JOIN returns r ON r.sale_id = s.sale_id GROUP BY 1 ORDER BY 1;
