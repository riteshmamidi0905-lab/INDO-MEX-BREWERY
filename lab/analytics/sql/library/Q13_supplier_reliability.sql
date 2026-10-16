-- id: Q13
-- title: Supplier delivery reliability
-- question: Which suppliers deliver on time, and how late are the late ones? (open POs are excluded: right-censored)
-- technique: conditional aggregation, AVG over a filtered subset, RANK on on-time rate, explicit denominator
-- expected_shape: 5 rows (one per supplier). Delays are SIMULATED from config.SUPPLIER_LATE_PROB, so the ordering is checked against that known truth.
-- sqlite_specific: none
SELECT s.supplier_id, s.status, COUNT(*) AS received_lines,
       ROUND(1.0 * SUM(CASE WHEN p.days_late <= 0 THEN 1 ELSE 0 END) / COUNT(*), 3) AS on_time_rate,
       ROUND(AVG(CASE WHEN p.days_late > 0 THEN p.days_late END), 2) AS avg_days_late_when_late,
       MAX(p.days_late) AS max_days_late,
       RANK() OVER (ORDER BY 1.0 * SUM(CASE WHEN p.days_late <= 0 THEN 1 ELSE 0 END) / COUNT(*)) AS worst_rank
FROM fact_po_line p JOIN dim_supplier s USING (supplier_key) WHERE p.status = 'RECEIVED' GROUP BY s.supplier_id, s.status ORDER BY worst_rank, s.supplier_id
