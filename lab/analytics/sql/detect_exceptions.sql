-- Inventory exceptions derived from the snapshot fact. Thresholds are stated rules (config in the doc), set BEFORE looking at counts:
--   LOW_COVER      : days of cover (on hand / 14-day avg usage) < supplier lead time in days
--   COUNT_VARIANCE : |counted - expected| > 10% of expected
SELECT 'EX-' || s.site_id || '-' || g.ingredient || '-' || d.date || '-' || k.kind AS event_id, f.site_key, f.ingredient_key, f.date_key, k.kind, d.date || 'T08:00:00' AS detected_ts
FROM fact_inventory_snapshot f
JOIN dim_site s ON s.site_key=f.site_key JOIN dim_ingredient g ON g.ingredient_key=f.ingredient_key JOIN dim_date d ON d.date_key=f.date_key
JOIN (SELECT 'LOW_COVER' AS kind UNION ALL SELECT 'COUNT_VARIANCE') k
 ON (k.kind='LOW_COVER' AND f.avg_daily_usage_14d > 0 AND f.on_hand_qty / f.avg_daily_usage_14d < g.lead_time_days)
 OR (k.kind='COUNT_VARIANCE' AND f.expected_on_hand > 0 AND ABS(f.variance_qty) / f.expected_on_hand > 0.10)
ORDER BY f.date_key, f.site_key, f.ingredient_key, k.kind
