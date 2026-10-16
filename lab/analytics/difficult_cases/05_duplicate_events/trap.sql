-- The tempting query. It runs and returns plausible-looking rows, and they are WRONG.
SELECT COUNT(*) AS completed_orders, SUM(amount_usd) AS completed_usd FROM (SELECT DISTINCT * FROM events) WHERE event_type = 'completed';
