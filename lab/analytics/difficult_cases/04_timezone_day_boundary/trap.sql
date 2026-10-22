-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT DATE(ts_utc) AS local_date, COUNT(*) AS orders FROM orders GROUP BY 1 ORDER BY 1;
