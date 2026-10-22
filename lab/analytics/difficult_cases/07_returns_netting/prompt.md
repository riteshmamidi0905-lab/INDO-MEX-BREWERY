# Case 07: Net revenue per month with returns booked in the return month

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

`sales(sale_id, sale_date, amount_usd)`, `returns(return_id, sale_id, return_date, amount_usd)`. A sale can have several (partial) returns, booked on later dates. Net revenue for a month = sales dated in the month minus returns dated in the month. Report every month that has any activity, ordered by month. Output: `month, net_usd` (month as 'YYYY-MM').
