# Case 04: Orders per LOCAL calendar day across a DST change: explanation (NOT candidate-facing)

Skills: timezones, DST, date boundaries

DATE(ts_utc) is the UTC date, not the business date. e2 (03:30Z) is 22:30 on Oct 31 local, and e6 (05:30Z Nov 2) is 23:30 on Nov 1 local, because the offset changed to -6 at 07:00Z on Nov 1. A fixed -5 offset fixes e2 but wrongly puts e6 on Nov 2. e4 and e5 are both '01:30 local' (the repeated hour), and are distinguishable only in UTC. Rule: store UTC, convert with a dated offset table or a real timezone database, and define the business day explicitly (some venues use a 4 a.m. cutoff).
