-- id: Q01
-- title: Cumulative gross sales per site
-- question: How does gross sales accumulate day by day at each site, and where does it end up?
-- technique: window aggregate over a grouped aggregate (SUM(SUM(x)) OVER), running total with PARTITION BY / ORDER BY
-- expected_shape: one row per site x order date (3 x 56); cumulative_usd is non-decreasing and ends at the site total
-- sqlite_specific: none
SELECT s.site_id, d.date,
       SUM(l.gross_sales_cents) / 100.0 AS daily_sales_usd,
       SUM(SUM(l.gross_sales_cents) / 100.0) OVER (PARTITION BY s.site_id ORDER BY d.date) AS cumulative_usd
FROM fact_order_line l JOIN dim_site s USING (site_key) JOIN dim_date d USING (date_key)
GROUP BY s.site_id, d.date
ORDER BY s.site_id, d.date
