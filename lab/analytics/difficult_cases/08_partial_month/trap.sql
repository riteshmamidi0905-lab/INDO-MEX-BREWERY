-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT substr(day,1,7) AS month, SUM(amount_usd) AS total_usd, 31 AS days_observed, SUM(amount_usd)/31 AS avg_per_day FROM daily_sales GROUP BY 1 ORDER BY 1;
