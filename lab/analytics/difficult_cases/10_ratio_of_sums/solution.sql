SELECT 1.0 * SUM(on_time) / COUNT(on_time) AS on_time_rate, COUNT(on_time) AS known_deliveries FROM deliveries;
