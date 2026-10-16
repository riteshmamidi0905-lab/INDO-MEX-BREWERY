-- id: Q17
-- title: Exact duplicate orders in the raw landing zone
-- question: Which order ids landed more than once, and which copy would a dedup keep?
-- technique: ROW_NUMBER() OVER (PARTITION BY business key ORDER BY load order) = 1 keeps the first; COUNT(*) OVER to see the group size
-- expected_shape: one row per surplus copy (8 injected exact duplicates in this build), each with copy_no = 2
-- sqlite_specific: rowid as the load-order tiebreaker (use an ingestion timestamp / file offset elsewhere)
WITH r AS (SELECT order_id, location_id, ts, total_cents, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY rowid) AS copy_no, COUNT(*) OVER (PARTITION BY order_id) AS copies FROM raw_orders)
SELECT order_id, location_id, ts, total_cents, copy_no, copies FROM r WHERE copy_no > 1 ORDER BY order_id
