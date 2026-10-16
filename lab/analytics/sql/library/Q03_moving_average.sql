-- id: Q03
-- title: Seven-day moving average of daily orders
-- question: What is the smoothed daily order volume per site, and which points rest on an incomplete window?
-- technique: ROWS BETWEEN 6 PRECEDING AND CURRENT ROW frame; window size counter to flag the warm-up period
-- expected_shape: one row per site x date; window_days = 7 from the 7th day onward
-- sqlite_specific: none
WITH daily AS (
  SELECT s.site_id, d.date, COUNT(*) AS orders FROM fact_order o JOIN dim_site s USING (site_key) JOIN dim_date d USING (date_key) GROUP BY s.site_id, d.date)
SELECT site_id, date, orders,
       ROUND(AVG(orders) OVER w, 2) AS orders_ma7,
       COUNT(*) OVER w AS window_days
FROM daily WINDOW w AS (PARTITION BY site_id ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY site_id, date
