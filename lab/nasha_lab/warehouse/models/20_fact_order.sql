-- model: fact_order
-- kind: incremental_partition
-- depends: stg_orders, stg_order_lines, dim_location, dim_member, dim_promotion
-- grain: one row per order
CREATE TABLE IF NOT EXISTS fact_order (order_id TEXT PRIMARY KEY, date_key INTEGER, location_key INTEGER, hour INTEGER, channel TEXT, member_key INTEGER, promo_key INTEGER,
  subtotal_cents INTEGER, discount_cents INTEGER, total_cents INTEGER, n_lines INTEGER, n_items INTEGER, _partition TEXT);
INSERT INTO fact_order
SELECT o.order_id, CAST(replace(substr(o.ts,1,10),'-','') AS INTEGER), l.location_key, CAST(substr(o.ts,12,2) AS INTEGER), o.channel, m.member_key, p.promo_key,
       o.subtotal_cents, o.discount_cents, o.total_cents, COALESCE(x.n,0), COALESCE(x.q,0), o._partition
FROM stg_orders o
JOIN dim_location l ON l.location_id = o.location_id
LEFT JOIN dim_member m ON m.member_id = o.member_id
LEFT JOIN dim_promotion p ON p.promo_id = o.promo_id
LEFT JOIN (SELECT order_id, count(*) n, sum(qty) q FROM stg_order_lines WHERE _partition IN ({PARTS}) GROUP BY order_id) x ON x.order_id = o.order_id
WHERE o._partition IN ({PARTS});
