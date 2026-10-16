-- id: Q21
-- title: Median and 90th percentile of order value per site (no percentile function)
-- question: What are the p50 and p90 order values at each site?
-- technique: percentile emulation: ROW_NUMBER and COUNT(*) OVER per site, average the two middle rows for the median, nearest-rank for p90
-- expected_shape: 3 rows; p50 <= p90; matches numpy (median, nearest-rank) on the same data
-- sqlite_specific: none (PostgreSQL/Snowflake: PERCENTILE_CONT / PERCENTILE_DISC)
WITH r AS (SELECT s.site_id, o.order_total_cents AS v, ROW_NUMBER() OVER (PARTITION BY s.site_id ORDER BY o.order_total_cents, o.order_id) AS rn, COUNT(*) OVER (PARTITION BY s.site_id) AS n
           FROM fact_order o JOIN dim_site s USING (site_key))
SELECT site_id, MAX(n) AS orders,
       AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN v END) / 100.0 AS p50_usd,
       MAX(CASE WHEN rn = CAST((0.9 * n) + 0.999999 AS INTEGER) THEN v END) / 100.0 AS p90_usd_nearest_rank
FROM r GROUP BY site_id ORDER BY site_id
