SELECT month, SUM(signed) AS net_usd FROM (
  SELECT substr(sale_date,1,7) AS month, amount_usd AS signed FROM sales
  UNION ALL SELECT substr(return_date,1,7), -amount_usd FROM returns) GROUP BY month ORDER BY month;
