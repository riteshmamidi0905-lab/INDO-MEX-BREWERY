SELECT substr(day,1,7) AS month, SUM(amount_usd) AS total_usd, COUNT(*) AS days_observed, SUM(amount_usd) * 1.0 / COUNT(*) AS avg_per_day
FROM daily_sales WHERE day <= (SELECT asof FROM meta) GROUP BY 1 ORDER BY 1;
