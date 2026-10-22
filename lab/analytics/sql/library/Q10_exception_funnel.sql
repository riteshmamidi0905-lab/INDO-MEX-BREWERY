-- id: Q10
-- title: Inventory exception funnel (count event -> exception -> approval -> resolution)
-- question: Of all weekly count events, how many raise an exception, get approved, and get resolved?
-- technique: stage counts UNIONed into one funnel, conversion vs previous stage and vs start with LAG / FIRST_VALUE windows
-- expected_shape: 4 rows with non-increasing n; stage 1 = snapshots that have a previous count (192). Approval/resolution are SIMULATED stages.
-- sqlite_specific: none
WITH stages AS (
  SELECT 1 AS stage_no, 'count event' AS stage, COUNT(*) AS n FROM fact_inventory_snapshot WHERE prev_date_key <> 0
  UNION ALL SELECT 2, 'exception raised', COUNT(*) FROM fact_exception_event
  UNION ALL SELECT 3, 'approved', COUNT(*) FROM fact_exception_event WHERE approved_ts IS NOT NULL
  UNION ALL SELECT 4, 'resolved', COUNT(*) FROM fact_exception_event WHERE resolved_ts IS NOT NULL)
SELECT stage_no, stage, n,
       ROUND(1.0 * n / LAG(n) OVER (ORDER BY stage_no), 3) AS conv_vs_prev,
       ROUND(1.0 * n / FIRST_VALUE(n) OVER (ORDER BY stage_no), 3) AS conv_vs_start
FROM stages ORDER BY stage_no
