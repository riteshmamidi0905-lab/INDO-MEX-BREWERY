# Case 03: Units sold by dish name as of the sale date

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

`dim_item(item_key, item_id, item_name, valid_from, valid_to)` is a Type 2 dimension: a version is valid from `valid_from` (inclusive) up to `valid_to` (exclusive); the open version has `valid_to = '9999-12-31'`. `sales(sale_id, item_id, sale_date, qty)`. Report units sold per `item_name` for item `M04`, ordered by name. Output: `item_name, units`.
