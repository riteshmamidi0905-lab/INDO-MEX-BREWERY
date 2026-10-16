# Case 06: Revenue by category when some sales point at unknown items

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

`sales(sale_id, item_id, amount_usd)`, `items(item_id, category)`. Some sales reference item ids that are not in `items`. Report revenue per category, labelling unmatched sales 'UNKNOWN', so that the grand total equals total sales. Order by category. Output: `category, revenue_usd`.
