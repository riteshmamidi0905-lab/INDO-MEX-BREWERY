-- model: fact_order_line
-- kind: incremental_partition
-- depends: stg_order_lines, stg_orders, dim_product, dim_location
-- grain: one row per order line. The order-level discount is allocated to lines by cumulative rounding so line allocations sum EXACTLY to the order discount.
CREATE TABLE IF NOT EXISTS fact_order_line (order_id TEXT, line_no INTEGER, date_key INTEGER, location_key INTEGER, product_key INTEGER, qty INTEGER, unit_price_cents INTEGER,
  gross_cents INTEGER, discount_alloc_cents INTEGER, net_cents INTEGER, cogs_cents INTEGER, margin_cents INTEGER, _partition TEXT, PRIMARY KEY (order_id, line_no));
INSERT INTO fact_order_line
WITH l AS (SELECT ol.order_id, ol.line_no, ol.item_id, ol.qty, ol.unit_price_cents, ol.qty * ol.unit_price_cents AS gross, o.discount_cents AS d, o.subtotal_cents AS s, o.location_id, o.ts, ol._partition
           FROM stg_order_lines ol JOIN stg_orders o ON o.order_id = ol.order_id WHERE ol._partition IN ({PARTS})),
c AS (SELECT *, SUM(gross) OVER (PARTITION BY order_id ORDER BY line_no) AS cg FROM l),
a AS (SELECT *, CASE WHEN s = 0 THEN 0 ELSE CAST(round(1.0 * d * cg / s) AS INTEGER) - CAST(round(1.0 * d * (cg - gross) / s) AS INTEGER) END AS alloc FROM c)
SELECT a.order_id, a.line_no, CAST(replace(substr(a.ts,1,10),'-','') AS INTEGER), dl.location_key, p.product_key, a.qty, a.unit_price_cents, a.gross, a.alloc, a.gross - a.alloc,
       a.qty * p.unit_cost_cents, (a.gross - a.alloc) - a.qty * p.unit_cost_cents, a._partition
FROM a JOIN dim_product p ON p.item_id = a.item_id JOIN dim_location dl ON dl.location_id = a.location_id;
