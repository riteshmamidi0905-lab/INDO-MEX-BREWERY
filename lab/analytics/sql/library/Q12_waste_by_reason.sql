-- id: Q12
-- title: Logged waste by ingredient and reason
-- question: How much is logged as waste per ingredient, split by reason, relative to theoretical usage?
-- technique: conditional aggregation (pivot via CASE), ratio to a separately pre-aggregated denominator (no fan-out), loss sign convention (qty > 0 = loss)
-- expected_shape: one row per ingredient (8); the reason columns sum to logged_kg; waste events are SIMULATED
-- sqlite_specific: none
WITH w AS (SELECT w.ingredient_key, SUM(w.qty) AS logged_kg,
                  SUM(CASE WHEN r.reason = 'SPOILAGE' THEN w.qty ELSE 0 END) AS spoilage_kg, SUM(CASE WHEN r.reason = 'PREP_TRIM' THEN w.qty ELSE 0 END) AS prep_trim_kg,
                  SUM(CASE WHEN r.reason = 'SPILL' THEN w.qty ELSE 0 END) AS spill_kg, SUM(CASE WHEN r.reason = 'EXPIRED' THEN w.qty ELSE 0 END) AS expired_kg
            FROM fact_waste_adjustment w JOIN dim_waste_reason r USING (reason_key) WHERE w.adj_kind = 'LOGGED_WASTE' GROUP BY w.ingredient_key),
u AS (SELECT ingredient_key, SUM(theoretical_qty) AS usage_kg FROM fact_usage_daily GROUP BY ingredient_key)
SELECT g.ingredient, ROUND(w.logged_kg, 2) AS logged_kg, ROUND(w.spoilage_kg, 2) AS spoilage_kg, ROUND(w.prep_trim_kg, 2) AS prep_trim_kg, ROUND(w.spill_kg, 2) AS spill_kg,
       ROUND(w.expired_kg, 2) AS expired_kg, ROUND(u.usage_kg, 1) AS usage_kg, ROUND(100.0 * w.logged_kg / u.usage_kg, 2) AS waste_pct_of_usage
FROM w JOIN u USING (ingredient_key) JOIN dim_ingredient g USING (ingredient_key) ORDER BY waste_pct_of_usage DESC
