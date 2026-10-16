# Case 02: Menu items never sold: explanation (NOT candidate-facing)

Skills: three-valued logic, anti-join

x NOT IN (a, b, NULL) evaluates to UNKNOWN for every x that is not a or b, so the filter rejects everything and the trap returns ZERO rows with no error. NOT EXISTS (or LEFT JOIN ... IS NULL, or filtering NULLs out of the subquery) is NULL-safe. Also discuss: what is the 'right' business answer when item_id is unknown for a sale (the NULL sale could have been M3)?
