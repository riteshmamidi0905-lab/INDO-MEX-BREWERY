SELECT DATE(datetime(REPLACE(REPLACE(o.ts_utc,'T',' '),'Z',''), t.offset_hours || ' hours')) AS local_date, COUNT(*) AS orders
FROM orders o JOIN tz_offset t ON o.ts_utc >= t.valid_from_utc AND o.ts_utc < t.valid_to_utc
GROUP BY 1 ORDER BY 1;
