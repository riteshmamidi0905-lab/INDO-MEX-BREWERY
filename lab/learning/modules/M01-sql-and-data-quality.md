# Module M01: SQL and data quality (on the enterprise simulation)

Status for you: NOT ASSESSED. Nothing below is marked complete; do the exercises unaided, then show your work.

**A. Theory.** GROUP BY/HAVING, joins and where a filter belongs (ON vs WHERE), window functions, grain, keys, referential integrity, and why a quality check runs at a specific layer (source, staging, mart).
**B. Small implementation (do alone).** Load the dev profile (`python -m nasha_lab.enterprise_sim --profile dev --out /tmp/sim-dev`) into SQLite (pandas `to_sql`). Write: (1) orders and revenue per site per month; (2) the top 3 items per site by revenue; (3) a 7-day moving average of daily orders per site; (4) loyalty members whose first order precedes their join date (expect none).
**C. Where it appears.** `lab/nasha_lab/enterprise_sim.py::check` (the invariants), `lab/nasha_lab/dq.py` (rules for the 3-site baseline), the P4 mart queries on `career/p4-analytics-mart-clean` (`lab/analytics/sql/library/`).
**D. Debugging.** Copy the dev output, change one `item_id` to `ZZZ` and set one `qty` to 0 in `order_lines`. Predict which checks fail, then run `enterprise_sim.check`. Then find a defect the checker would NOT catch (hint: a price change of +45% on one line) and explain what check you would add.
**E. Design tradeoffs.** Row-level checks vs aggregate checks; failing the build vs quarantining rows; where to put the "total equals line sum" check in an ELT flow.
**F. Interview defence.** Explain a LEFT JOIN turning into an inner join; define grain for `order_lines`; how would you prove a pipeline is re-runnable?
**G. Evidence (fill in only when you did it unaided).** Date / task / link / what you needed help with.
