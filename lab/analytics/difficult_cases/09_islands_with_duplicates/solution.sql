WITH d AS (SELECT DISTINCT site, day FROM activity),
g AS (SELECT site, day, CAST(julianday(day) AS INTEGER) - ROW_NUMBER() OVER (PARTITION BY site ORDER BY day) AS island FROM d),
isl AS (SELECT site, COUNT(*) AS streak_days, MIN(day) AS streak_start FROM g GROUP BY site, island),
r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY site ORDER BY streak_days DESC, streak_start) AS rn FROM isl)
SELECT site, streak_days, streak_start FROM r WHERE rn = 1 ORDER BY site;
