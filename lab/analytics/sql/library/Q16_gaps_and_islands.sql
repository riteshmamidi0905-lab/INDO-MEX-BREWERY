-- id: Q16
-- title: Streaks of above-average sales days (gaps and islands)
-- question: What are the longest consecutive runs of days where a site beat its own average daily sales?
-- technique: gaps-and-islands: island id = day number minus ROW_NUMBER over the filtered rows (constant within a consecutive run)
-- expected_shape: islands per site; lengths sum to the number of above-average days; islands never overlap
-- sqlite_specific: julianday() for a day number; in PostgreSQL use (date - DATE '2000-01-01')
WITH daily AS (SELECT s.site_id, d.date, SUM(l.gross_sales_cents) AS sales FROM fact_order_line l JOIN dim_site s USING (site_key) JOIN dim_date d USING (date_key) GROUP BY s.site_id, d.date),
flag AS (SELECT site_id, date, sales, AVG(sales) OVER (PARTITION BY site_id) AS avg_sales FROM daily),
hi AS (SELECT site_id, date, CAST(julianday(date) AS INTEGER) - ROW_NUMBER() OVER (PARTITION BY site_id ORDER BY date) AS island FROM flag WHERE sales > avg_sales)
SELECT site_id, MIN(date) AS island_start, MAX(date) AS island_end, COUNT(*) AS length_days
FROM hi GROUP BY site_id, island ORDER BY site_id, island_start
