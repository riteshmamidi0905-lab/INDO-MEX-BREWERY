-- id: Q15
-- title: Missing site-days via a recursive calendar
-- question: Are there site-days inside the data window with no orders at all (a silent ingestion gap)?
-- technique: recursive CTE to generate a date spine, CROSS JOIN with sites, anti-join to facts
-- expected_shape: 3 rows (one per site) with missing_days = 0 for this build; the same query would list gaps if a day were dropped
-- sqlite_specific: date(d, '+1 day') arithmetic; in PostgreSQL use d + INTERVAL '1 day' or generate_series
WITH RECURSIVE spine(d) AS (
  SELECT MIN(date) FROM dim_date WHERE date_key IN (SELECT date_key FROM fact_order)
  UNION ALL SELECT date(d, '+1 day') FROM spine WHERE d < (SELECT MAX(date) FROM dim_date WHERE date_key IN (SELECT date_key FROM fact_order))),
grid AS (SELECT s.site_key, s.site_id, sp.d FROM spine sp CROSS JOIN dim_site s WHERE s.site_key <> 0),
have AS (SELECT DISTINCT o.site_key, d.date FROM fact_order o JOIN dim_date d USING (date_key))
SELECT g.site_id, COUNT(*) AS days_in_window, SUM(CASE WHEN h.date IS NULL THEN 1 ELSE 0 END) AS missing_days,
       MIN(CASE WHEN h.date IS NULL THEN g.d END) AS first_missing_day
FROM grid g LEFT JOIN have h ON h.site_key = g.site_key AND h.date = g.d GROUP BY g.site_id ORDER BY g.site_id
