WITH latest AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY received_at DESC) AS rn FROM events)
SELECT COUNT(DISTINCT order_id) AS completed_orders, SUM(amount_usd) AS completed_usd FROM latest WHERE rn = 1 AND event_type = 'completed';
