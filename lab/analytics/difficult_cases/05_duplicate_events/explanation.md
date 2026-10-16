# Case 05: Completed-order revenue from an event stream with retransmissions: explanation (NOT candidate-facing)

Skills: deduplication, ROW_NUMBER, business keys

SELECT DISTINCT only removes rows identical in EVERY column, and retransmissions differ in received_at, so nothing is removed: 7 completed rows, 162 USD (40+40+25+27+10+10+10). Dedup on the business key (event_id) with ROW_NUMBER() over the authoritative ordering. O2's correction (25 -> 27) shows why 'keep any one' is not enough: expected is 40 + 27 + 10 = 77 over 3 orders. Also count DISTINCT order_id, not rows.
