-- id: Q19
-- title: Late-arriving facts and restated daily totals (inline fixture)
-- question: By how much does a day's reported sales change when late events are loaded afterwards?
-- technique: event time vs load time; cumulative "as of load date" totals versus the final total; late = loaded after the day following the event
-- expected_shape: 3 rows (one per event day) with reported_on_next_day vs final_total; the restatement is exactly the late rows' amounts
-- sqlite_specific: date() arithmetic. Fixture is inline VALUES because the lab generator has no load timestamps.
WITH ev(event_id, event_date, loaded_date, amount) AS (VALUES
  ('e1','2026-03-02','2026-03-03',100),('e2','2026-03-02','2026-03-03',50),('e3','2026-03-02','2026-03-06',70),
  ('e4','2026-03-03','2026-03-04',200),('e5','2026-03-03','2026-03-04',40),
  ('e6','2026-03-04','2026-03-05',90),('e7','2026-03-04','2026-03-09',30),('e8','2026-03-04','2026-03-10',25)),
days AS (SELECT DISTINCT event_date FROM ev)
SELECT d.event_date,
       (SELECT SUM(amount) FROM ev WHERE ev.event_date = d.event_date AND ev.loaded_date <= date(d.event_date, '+1 day')) AS reported_on_next_day,
       (SELECT SUM(amount) FROM ev WHERE ev.event_date = d.event_date) AS final_total,
       (SELECT COUNT(*) FROM ev WHERE ev.event_date = d.event_date AND ev.loaded_date > date(d.event_date, '+1 day')) AS late_rows
FROM days d ORDER BY d.event_date
