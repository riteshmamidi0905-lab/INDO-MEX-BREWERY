# Case 01: Revenue per site from orders and lines

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

Tables `orders(order_id, site, total_usd)` and `order_lines(order_id, line_no, item, qty)`. Report, per site, the number of orders and the revenue (sum of `orders.total_usd`) for orders that have at least one line, ordered by site. Output columns: `site, orders, revenue_usd`.
