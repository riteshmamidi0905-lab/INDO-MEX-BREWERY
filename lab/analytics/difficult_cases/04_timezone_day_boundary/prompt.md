# Case 04: Orders per LOCAL calendar day across a DST change

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

`orders(order_id, ts_utc)` holds UTC timestamps (ISO 8601 with a trailing Z). The site is in America/Chicago. `tz_offset(valid_from_utc, valid_to_utc, offset_hours)` gives the site's UTC offset for UTC ranges (valid_from inclusive, valid_to exclusive): CDT = -5 until 2026-11-01T07:00:00Z, then CST = -6. Count orders per LOCAL calendar date, ordered by date. Output: `local_date, orders`.
