-- id: Q09
-- title: Weekly guest-cohort retention (SYNTHETIC guests)
-- question: Of the guests first seen in week c, what share order again k weeks later?
-- technique: cohort = week of first order (dim_guest), activity grid by week offset, retention = active / cohort size; guests only (guest_key <> 0)
-- expected_shape: one row per cohort week x offset (offset 0..7-c); offset 0 retention = 1.0; retention never exceeds 1
-- sqlite_specific: none. Guest ids are SIMULATED (config.GUEST_*); retention reflects that process, not guest behaviour.
WITH act AS (SELECT DISTINCT o.guest_key, d.week_index FROM fact_order o JOIN dim_date d USING (date_key) WHERE o.guest_key <> 0),
coh AS (SELECT g.guest_key, d.week_index AS cohort_week FROM dim_guest g JOIN dim_date d ON d.date_key = g.first_order_date_key WHERE g.guest_key <> 0),
size AS (SELECT cohort_week, COUNT(*) AS cohort_size FROM coh GROUP BY cohort_week)
SELECT c.cohort_week, z.cohort_size, a.week_index - c.cohort_week AS week_offset, COUNT(DISTINCT a.guest_key) AS active_guests,
       ROUND(1.0 * COUNT(DISTINCT a.guest_key) / z.cohort_size, 3) AS retention
FROM coh c JOIN act a ON a.guest_key = c.guest_key AND a.week_index >= c.cohort_week JOIN size z ON z.cohort_week = c.cohort_week
GROUP BY c.cohort_week, a.week_index - c.cohort_week, z.cohort_size ORDER BY c.cohort_week, week_offset
