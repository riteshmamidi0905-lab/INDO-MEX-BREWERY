# Case 05: Completed-order revenue from an event stream with retransmissions

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

`events(event_id, order_id, event_type, amount_usd, received_at)`. The ingestion layer retransmits events (same `event_id`, later `received_at`); a retransmission may carry a CORRECTED amount, and the latest `received_at` per `event_id` is authoritative. Report the number of orders with a 'completed' event and the total completed amount. Output: `completed_orders, completed_usd`.
