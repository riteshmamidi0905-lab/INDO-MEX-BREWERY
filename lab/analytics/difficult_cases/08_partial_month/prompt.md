# Case 08: Which month sells best per day?

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

`daily_sales(day, amount_usd)` has one row per trading day. The data is current as of `asof = 2026-03-10` (inclusive) and the site trades every day. Report, per month, `total_usd`, `days_observed` (calendar days from the 1st to the month end or asof, whichever is first) and `avg_per_day`, ordered by month. Output: `month, total_usd, days_observed, avg_per_day`. Which month sells best per day?
