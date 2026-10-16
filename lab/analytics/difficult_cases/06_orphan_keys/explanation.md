# Case 06: Revenue by category when some sales point at unknown items: explanation (NOT candidate-facing)

Skills: LEFT vs INNER join, unknown member, reconciliation

The INNER JOIN silently drops 14 USD (X9 and the NULL item) so the report totals 35 against 49 of real sales, and nothing signals it. LEFT JOIN from the fact keeps the rows; COALESCE labels them. Variant trap: LEFT JOIN plus WHERE i.category = 'food' re-creates the inner join. In a warehouse the cleaner fix is an 'Unknown' dimension member (key 0) so facts never lose rows; a reconciliation test (sum by category = total sales) is what catches this.
