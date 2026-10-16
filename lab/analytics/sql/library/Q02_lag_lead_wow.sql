-- id: Q02
-- title: Week-over-week change and next-day look-ahead
-- question: Is a site's daily sales above or below the same weekday one week earlier?
-- technique: LAG(x, 7) for same-weekday comparison on a DENSE daily series, LEAD(x) for the next day; NULL-safe percentage
-- expected_shape: one row per site x date; wow_pct is NULL for each site's first 7 days
-- sqlite_specific: none. Assumes no missing days (see Q15 for the gap check); with gaps LAG(7) would compare the wrong day.
WITH daily AS (
  SELECT s.site_id, d.date, SUM(l.gross_sales_cents) / 100.0 AS sales
  FROM fact_order_line l JOIN dim_site s USING (site_key) JOIN dim_date d USING (date_key) GROUP BY s.site_id, d.date)
SELECT site_id, date, sales,
       LAG(sales, 7) OVER w AS sales_7d_ago,
       ROUND(100.0 * (sales - LAG(sales, 7) OVER w) / NULLIF(LAG(sales, 7) OVER w, 0), 1) AS wow_pct,
       LEAD(sales, 1) OVER w AS next_day_sales
FROM daily WINDOW w AS (PARTITION BY site_id ORDER BY date)
ORDER BY site_id, date
