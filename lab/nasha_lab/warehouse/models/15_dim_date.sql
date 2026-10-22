-- model: calendar
-- kind: tables
-- depends: stg_locations, stg_orders
-- The calendar spans the loaded data, so it is rebuilt whenever new partitions arrive (date_key is YYYYMMDD, independent of row order).
CREATE TABLE dim_date AS
WITH RECURSIVE d(day) AS (SELECT (SELECT min(open_date) FROM stg_locations) UNION ALL SELECT date(day,'+1 day') FROM d WHERE day < date((SELECT max(substr(ts,1,10)) FROM stg_orders),'+0 day'))
SELECT CAST(replace(day,'-','') AS INTEGER) AS date_key, day AS date, substr(day,1,7) AS month, CAST(strftime('%w',day) AS INTEGER) AS dow, CASE WHEN CAST(strftime('%w',day) AS INTEGER) IN (0,5,6) THEN 1 ELSE 0 END AS is_weekend_ish FROM d;
CREATE UNIQUE INDEX ux_dim_date ON dim_date(date_key);
