-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT AVG(rate) AS on_time_rate, COUNT(*) AS known_deliveries FROM (
  SELECT supplier, AVG(on_time) AS rate FROM deliveries GROUP BY supplier);
