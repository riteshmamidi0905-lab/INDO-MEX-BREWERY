-- Loads fact_inventory_snapshot from the staged counts t_snap (one row per site x ingredient x count date).
--   expected_on_hand = previous count + receipts in (prev, t] - theoretical usage in [prev, t) - LOGGED waste in [prev, t)
--   variance_qty     = counted - expected   (= count noise + unlogged shrink + anything the model does not explain)
-- Correlated scalar subqueries (no LATERAL in SQLite). date() arithmetic is SQLite-specific; elsewhere use date +/- interval.
WITH base AS (
  SELECT s.date_key, s.site_key, s.ingredient_key, s.on_hand_qty, s.unit, sd.date AS d,
         (SELECT p.date_key FROM t_snap p WHERE p.site_key=s.site_key AND p.ingredient_key=s.ingredient_key AND p.date_key < s.date_key ORDER BY p.date_key DESC LIMIT 1) AS prev_dk
  FROM t_snap s JOIN dim_date sd ON sd.date_key = s.date_key
), enr AS (
  SELECT b.*, pd.date AS pdate,
         (SELECT p.on_hand_qty FROM t_snap p WHERE p.site_key=b.site_key AND p.ingredient_key=b.ingredient_key AND p.date_key=b.prev_dk) AS prev_qty
  FROM base b LEFT JOIN dim_date pd ON pd.date_key = b.prev_dk
), calc AS (
  SELECT e.*,
    (SELECT COALESCE(SUM(u.theoretical_qty),0) FROM fact_usage_daily u JOIN dim_date ud ON ud.date_key=u.date_key
       WHERE u.site_key=e.site_key AND u.ingredient_key=e.ingredient_key AND ud.date >= e.pdate AND ud.date < e.d) AS usage_q,
    (SELECT COALESCE(SUM(po.qty_received),0) FROM fact_po_line po JOIN dim_date rd ON rd.date_key=po.received_date_key
       WHERE po.site_key=e.site_key AND po.ingredient_key=e.ingredient_key AND po.received_date_key<>0 AND rd.date > e.pdate AND rd.date <= e.d) AS receipt_q,
    (SELECT COALESCE(SUM(w.qty),0) FROM fact_waste_adjustment w JOIN dim_date wd ON wd.date_key=w.date_key
       WHERE w.site_key=e.site_key AND w.ingredient_key=e.ingredient_key AND w.adj_kind='LOGGED_WASTE' AND wd.date >= e.pdate AND wd.date < e.d) AS waste_q,
    (SELECT SUM(u.theoretical_qty) FROM fact_usage_daily u JOIN dim_date ud ON ud.date_key=u.date_key
       WHERE u.site_key=e.site_key AND u.ingredient_key=e.ingredient_key AND ud.date >= date(e.d,'-14 day') AND ud.date < e.d) AS usage14,
    CAST(julianday(e.d) - julianday(MAX(date(e.d,'-14 day'), (SELECT MIN(date) FROM dim_date))) AS INTEGER) AS ndays14
  FROM enr e
)
SELECT date_key, site_key, ingredient_key, on_hand_qty, unit, COALESCE(prev_dk,0),
       CASE WHEN prev_dk IS NULL THEN NULL ELSE ROUND(usage_q,4) END,
       CASE WHEN prev_dk IS NULL THEN NULL ELSE ROUND(receipt_q,4) END,
       CASE WHEN prev_dk IS NULL THEN NULL ELSE ROUND(waste_q,4) END,
       CASE WHEN prev_dk IS NULL THEN NULL ELSE ROUND(prev_qty + receipt_q - usage_q - waste_q,4) END,
       CASE WHEN prev_dk IS NULL THEN NULL ELSE ROUND(on_hand_qty - (prev_qty + receipt_q - usage_q - waste_q),4) END,
       CASE WHEN ndays14 > 0 THEN COALESCE(usage14,0) / ndays14 END
FROM calc
