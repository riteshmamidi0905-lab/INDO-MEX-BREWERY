-- id: Q18
-- title: Near-duplicate orders by content signature (exact timestamp)
-- question: Which different order ids carry an identical site, timestamp and basket?
-- technique: build a basket signature with GROUP_CONCAT over pre-ordered lines, group by (site, ts, signature), keep groups with > 1 distinct order id
-- expected_shape: one row per near-duplicate group; finds the injected exact-timestamp copies but NOT the copies shifted by one second (documented miss; see DQ evaluation)
-- sqlite_specific: GROUP_CONCAT over an ordered subquery (PostgreSQL: STRING_AGG(... ORDER BY ...))
WITH sig AS (
  SELECT o.order_id, o.location_id, o.ts,
         (SELECT GROUP_CONCAT(item_id || 'x' || qty || '@' || unit_price_cents, '|') FROM (SELECT item_id, qty, unit_price_cents FROM raw_order_lines l WHERE l.order_id = o.order_id ORDER BY item_id, qty, unit_price_cents)) AS basket
  FROM (SELECT DISTINCT order_id, location_id, ts FROM raw_orders) o)
SELECT location_id, ts, basket, COUNT(*) AS order_ids, MIN(order_id) AS first_id, MAX(order_id) AS later_id
FROM sig WHERE basket IS NOT NULL GROUP BY location_id, ts, basket HAVING COUNT(*) > 1 ORDER BY ts, location_id
